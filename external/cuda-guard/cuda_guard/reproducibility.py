"""
cuda_guard.reproducibility
============================
Phase 12 (spec Sec. 22): controlled reproducibility. Phase 21 (spec Sec. 21):
partial recomputation on a deterministic toy model with honest sampling-
coverage reporting. TimeLockAttestation ported from the prototype, key
provenance documented explicitly per spec Sec. 37.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import random
import secrets
import time
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from .evidence import EvidenceClass, EvidenceRecord, EvidenceSource, EvidenceStatus, RecomputationResult, ReproducibilityReport, TrustRoot
from .ledger import TamperEvidentLedger
from .self_audit import GovernanceViolationError


class DeterminismEngine:
    """warn_only=True by default so a general-purpose run never crashes on
    an op without a deterministic kernel; audit-grade runs should set
    warn_only=False once every op in the target workload is verified
    deterministic-capable (ported unchanged from the prototype)."""

    def __init__(self):
        self.enabled = False

    def enable(self, warn_only: bool = True, seed: int = 0) -> dict[str, Any]:
        import torch
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
        torch.use_deterministic_algorithms(True, warn_only=warn_only)
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        self.enabled = True
        return {"enabled": True, "warn_only": warn_only, "seed": seed,
                "cublas_workspace_config": os.environ.get("CUBLAS_WORKSPACE_CONFIG")}


class TimeLockAttestation:
    """KEY PROVENANCE (spec Sec. 37), stated explicitly rather than implied:
    this HMAC key is generated fresh, in-process, via secrets.token_bytes.
    It is NOT independently rooted -- it proves internal self-consistency
    (a payload wasn't altered after this process signed it) but says
    nothing about the process itself being honest. Key storage: in-memory
    only, never persisted, never logged. Key rotation: a new key every
    process start; there is no cross-run key continuity by design (a
    persistent identity key would need to be provisioned externally, which
    is out of scope for a single-process prototype). Key verification:
    anyone with the returned signature can verify it only if this process
    also discloses the key -- which it does not do automatically anywhere
    in this codebase."""

    def __init__(self, secret_key: Optional[bytes] = None):
        self._key = secret_key or secrets.token_bytes(32)
        self._last_monotonic = -1

    def sign(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = time.time()
        monotonic = time.monotonic_ns()
        nonce = secrets.token_hex(16)
        if monotonic <= self._last_monotonic:
            raise GovernanceViolationError(
                "Monotonic clock did not advance between signatures "
                "(possible replay attack or clock tampering)", violation_type="telemetry_replay_suspected")
        self._last_monotonic = monotonic
        body = json.dumps(payload, sort_keys=True, default=str)
        material = f"{body}|{now}|{monotonic}|{nonce}"
        signature = hmac.new(self._key, material.encode(), hashlib.sha256).hexdigest()
        return {"payload": payload, "wall_clock_utc": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
                "monotonic_ns": monotonic, "nonce": nonce, "signature": signature,
                "key_provenance": "in-process, ephemeral, not independently rooted"}


def hash_bytes(*chunks: bytes) -> str:
    h = hashlib.sha256()
    for c in chunks:
        h.update(c)
    return h.hexdigest()


def check_reproducibility(ledger: TamperEvidentLedger, model, make_input: Callable[[], Any],
                            model_hash: str, seed: int = 0) -> EvidenceRecord:
    """Runs the SAME inference twice under DeterminismEngine and compares
    output hashes. If they differ, records NONDETERMINISTIC honestly --
    never silently retried or the output modified to force a match
    (spec Sec. 22 explicitly forbids that)."""
    import torch
    det = DeterminismEngine()
    det.enable(warn_only=True, seed=seed)
    x = make_input()
    input_hash = hash_bytes(x.detach().cpu().numpy().tobytes()) if hasattr(x, "numpy") else hash_bytes(repr(x).encode())
    env_hash = hash_bytes(str(torch.__version__).encode(), str(os.environ.get("CUBLAS_WORKSPACE_CONFIG")).encode())

    with torch.no_grad():
        out1 = model(x)
    torch.manual_seed(seed)
    with torch.no_grad():
        out2 = model(x)
    h1 = hash_bytes(out1.detach().cpu().numpy().tobytes())
    h2 = hash_bytes(out2.detach().cpu().numpy().tobytes())
    deterministic = h1 == h2

    report = ReproducibilityReport(model_hash=model_hash, input_hash=input_hash, environment_hash=env_hash,
                                    seed=seed, output_hash_run1=h1, output_hash_run2=h2, deterministic=deterministic,
                                    dependency_versions={"torch": torch.__version__})
    ev = EvidenceRecord(
        EvidenceClass.REPRODUCIBILITY, EvidenceSource.OTHER,
        EvidenceStatus.SUCCESS if deterministic else EvidenceStatus.FAILED, TrustRoot.GOVERNED_PROCESS_SELF,
        establishes=[f"two runs of this model+input under fixed seed produced "
                     f"{'identical' if deterministic else 'DIFFERENT (NONDETERMINISTIC)'} output hashes"],
        does_not_establish=["universal deterministic inference across all inputs/hardware -- "
                             "this covers exactly the one model/input/seed/environment tested"],
        detail={"report": report.__dict__})
    ledger.record_evidence(ev)
    return ev


class RecomputationVerifier:
    """Modular sampled-recomputation check (spec Sec. 21). Starts with a
    deterministic toy model; demonstrates randomized sampling. Never claims
    a few samples prove an arbitrary frontier model -- the returned claim
    is always SAMPLED_RECOMPUTATION_SUPPORTED with explicit coverage."""

    def __init__(self, ledger: TamperEvidentLedger):
        self._ledger = ledger

    def verify(self, model, inputs: list, captured_outputs: list, sample_count: int,
               total_population: Optional[int] = None, rng_seed: int = 0) -> EvidenceRecord:
        import torch
        assert len(inputs) == len(captured_outputs)
        rng = random.Random(rng_seed)
        indices = rng.sample(range(len(inputs)), min(sample_count, len(inputs)))
        matches, mismatches = 0, 0
        with torch.no_grad():
            for i in indices:
                recomputed = model(inputs[i])
                same = torch.allclose(recomputed, captured_outputs[i], atol=1e-5)
                matches += int(same)
                mismatches += int(not same)
        coverage = (len(indices) / total_population) if total_population else (len(indices) / len(inputs))
        result = RecomputationResult(
            sample_count=len(indices), total_population=total_population or len(inputs),
            sampling_policy=f"uniform random without replacement, rng_seed={rng_seed}",
            matches=matches, mismatches=mismatches, coverage_fraction=coverage,
            confidence_note=(f"{len(indices)} of {total_population or len(inputs)} samples recomputed "
                              f"and independently compared bitwise-close to captured output. This is "
                              f"SAMPLED evidence, not exhaustive verification -- {mismatches} mismatch(es) "
                              f"found." if mismatches else
                              f"{len(indices)} of {total_population or len(inputs)} samples recomputed and "
                              f"matched. Absence of mismatches in a sample is not proof of correctness "
                              f"across the full unsampled population."))
        ev = EvidenceRecord(
            EvidenceClass.RECOMPUTATION, EvidenceSource.RECOMPUTATION_ENGINE,
            EvidenceStatus.SUCCESS if mismatches == 0 else EvidenceStatus.FAILED, TrustRoot.GOVERNED_PROCESS_SELF,
            establishes=[f"SAMPLED_RECOMPUTATION_SUPPORTED over {len(indices)} sample(s), "
                         f"coverage={coverage:.1%}"],
            does_not_establish=["that an arbitrary un-sampled input would also match",
                                 "correctness of the model architecture itself, only output "
                                 "reproducibility for the sampled inputs"],
            detail=result.__dict__)
        self._ledger.record_evidence(ev)
        return ev
