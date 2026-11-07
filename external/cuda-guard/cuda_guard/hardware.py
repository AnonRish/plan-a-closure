"""
cuda_guard.hardware
=====================
Phases 6 (model identity), 7 (device discovery), 8 (real NVIDIA attestation),
9 (device authorization registry), and 18 (attestation+authorization
composition). The attestation adapter is ported from the prototype's
NRASAttestationAdapter (already proven against the real installed
nv-attestation-sdk, including the fix for the SDK's ~30s no-driver timeout
and its internal logging bug) -- logic unchanged, evidence output re-typed.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Optional

from .evidence import (
    DeviceIdentity, EvidenceClass, EvidenceRecord, EvidenceSource, EvidenceStatus,
    RegistryResult, RegistryStatus, TrustRoot,
)
from .ledger import TamperEvidentLedger

try:
    import pynvml
    _PYNVML_OK = True
except ImportError:
    _PYNVML_OK = False
    pynvml = None

try:
    from nv_attestation_sdk import attestation as _nv_attestation
    _NV_ATTESTATION_SDK_OK = True
except ImportError:
    _NV_ATTESTATION_SDK_OK = False
    _nv_attestation = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Phase 7: device discovery
# ---------------------------------------------------------------------------
class DeviceDiscovery:
    """Real pynvml queries when available; a single explicitly-emulated
    device record otherwise, so downstream code never branches on
    "GPU or not". GPU UUID is identity/inventory evidence ONLY -- never
    equated with AUTHORIZED (that's a separate registry lookup, below)."""

    def __init__(self):
        self.available = False
        self._nvml = None
        if _PYNVML_OK:
            try:
                pynvml.nvmlInit()
                self._nvml = pynvml
                self.available = True
            except Exception:
                self.available = False

    def query(self) -> list[DeviceIdentity]:
        if not self.available:
            return [self._emulated()]
        try:
            n = self._nvml.nvmlDeviceGetCount()
        except Exception:
            return [self._emulated()]
        out = [self._query_one(i) for i in range(n)]
        return out or [self._emulated()]

    def _query_one(self, index: int) -> DeviceIdentity:
        h = self._nvml.nvmlDeviceGetHandleByIndex(index)

        def _s(x):
            return x.decode() if isinstance(x, bytes) else x

        def _safe(fn, default):
            try:
                return fn()
            except Exception:
                return default

        uuid_ = _s(_safe(lambda: self._nvml.nvmlDeviceGetUUID(h), f"GPU-EMU-{index}"))
        name = _s(_safe(lambda: self._nvml.nvmlDeviceGetName(h), "unknown"))
        mem = _safe(lambda: self._nvml.nvmlDeviceGetMemoryInfo(h), None)
        cc = _safe(lambda: self._nvml.nvmlDeviceGetCudaComputeCapability(h), None)
        cc_str = f"sm_{cc[0]}{cc[1]}" if cc else None
        driver_version = _s(_safe(lambda: self._nvml.nvmlSystemGetDriverVersion(), None))
        cuda_version = _safe(lambda: self._nvml.nvmlSystemGetCudaDriverVersion(), None)
        return DeviceIdentity(uuid=uuid_, name=name, compute_capability=cc_str,
                               driver_version=driver_version, cuda_version=str(cuda_version) if cuda_version else None,
                               vram_total_mb=(mem.total // (1024 * 1024)) if mem else None,
                               source=EvidenceSource.NVML, is_emulated=False)

    @staticmethod
    def _emulated() -> DeviceIdentity:
        return DeviceIdentity(uuid=f"GPU-EMULATED-{secrets.token_hex(6)}", name="Emulated (no NVML/driver present)",
                               compute_capability=None, source=EvidenceSource.NVML, is_emulated=True)

    def as_evidence(self, devices: list[DeviceIdentity]) -> EvidenceRecord:
        return EvidenceRecord(
            EvidenceClass.DEVICE_IDENTITY, EvidenceSource.NVML,
            EvidenceStatus.SUCCESS if self.available else EvidenceStatus.SIMULATED,
            TrustRoot.GOVERNED_PROCESS_SELF if self.available else TrustRoot.LOCAL_DEVELOPMENT_FIXTURE,
            establishes=["device UUID/name/compute-capability as reported by NVML" if self.available
                         else "nothing -- no NVML/driver present, this is an emulated placeholder record"],
            does_not_establish=["device authorization (see DeviceRegistry)", "firmware integrity (see attestation)"],
            detail={"devices": [asdict(d) for d in devices]},
        )


# ---------------------------------------------------------------------------
# Phase 8: real NVIDIA attestation
# ---------------------------------------------------------------------------
class NRASAttestationAdapter:
    """Ported from the prototype's proven implementation. Gated to
    Hopper-or-newer hardware to avoid the SDK's real ~30s no-driver
    evidence-collection timeout; runs under a bounded executor as a second
    safety net; captures the SDK's own internal logging bug's stderr output
    rather than leaking it. See prototype session notes / Trust Architecture
    doc Sec. 4 for the full mechanism writeup -- unchanged here."""

    NRAS_GPU_URL = "https://nras.attestation.nvidia.com/v4/attest/gpu"
    _CLAIM_FIELDS = (
        "secboot", "dbgstat", "measres", "hwmodel",
        "x-nvidia-gpu-driver-rim-signature-verified", "x-nvidia-gpu-vbios-rim-signature-verified",
        "x-nvidia-gpu-attestation-report-signature-verified", "x-nvidia-gpu-attestation-report-nonce-match",
        "x-nvidia-gpu-driver-version", "x-nvidia-gpu-vbios-version",
    )

    def __init__(self, ledger: TamperEvidentLedger):
        self._ledger = ledger

    def attempt(self, cc_capable_gpu_suspected: bool, nonce: str, timeout_s: float = 35.0) -> dict[str, Any]:
        if not _NV_ATTESTATION_SDK_OK:
            result = {"attempted": False, "reason": "nv-attestation-sdk not installed"}
            self._ledger.record("nras_attestation_skipped", result)
            return result
        if not cc_capable_gpu_suspected:
            result = {"attempted": False,
                      "reason": "no Hopper-or-newer CUDA device detected; skipped to avoid the "
                                "SDK's ~30s no-driver evidence-collection timeout"}
            self._ledger.record("nras_attestation_skipped", result)
            return result

        import concurrent.futures
        import contextlib
        import io

        def _run() -> dict[str, Any]:
            client = _nv_attestation.Attestation()
            client.set_name("cuda_guard")
            client.set_nonce(nonce)
            api_key = os.environ.get("NVIDIA_NRAS_API_KEY")
            if api_key:
                client.set_service_key(api_key)
                client.add_verifier(_nv_attestation.Devices.GPU, _nv_attestation.Environment.REMOTE, self.NRAS_GPU_URL, "")
                verifier_mode = "remote_nras"
            else:
                client.add_verifier(_nv_attestation.Devices.GPU, _nv_attestation.Environment.LOCAL, "", "")
                verifier_mode = "local_verifier"
            evidence_list = client.get_evidence()
            if not evidence_list:
                return {"verifier_mode": verifier_mode, "evidence_found": False}
            passed = client.attest(evidence_list)
            token = client.get_token()
            claims = self._extract_claims(token) if token else {}
            return {"verifier_mode": verifier_mode, "evidence_found": True,
                    "attest_result": bool(passed), "token_present": bool(token), "claims": claims}

        stderr_buf = io.StringIO()
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = pool.submit(_run)
        try:
            with contextlib.redirect_stderr(stderr_buf):
                outcome = future.result(timeout=timeout_s)
            pool.shutdown(wait=False, cancel_futures=True)
            outcome["attempted"] = True
            self._ledger.record("nras_attestation_attempt", outcome)
            return outcome
        except concurrent.futures.TimeoutError:
            pool.shutdown(wait=False, cancel_futures=True)
            outcome = {"attempted": True, "evidence_found": False, "reason": f"SDK call exceeded {timeout_s}s bound"}
            self._ledger.record("nras_attestation_attempt", outcome)
            return outcome
        except Exception as exc:
            pool.shutdown(wait=False, cancel_futures=True)
            outcome = {"attempted": True, "evidence_found": False, "reason": f"exception: {exc}"}
            self._ledger.record("nras_attestation_attempt", outcome)
            return outcome

    @classmethod
    def _extract_claims(cls, token_str: str) -> dict[str, Any]:
        try:
            import jwt as _pyjwt
        except ImportError:
            return {}
        out: dict[str, Any] = {}
        try:
            outer = json.loads(token_str)
            if len(outer) < 2:
                return {}
            for verifier_name, entry in outer[1].items():
                if len(entry) < 2:
                    continue
                for device_id, device_token in entry[1].items():
                    decoded = _pyjwt.decode(device_token, options={"verify_signature": False})
                    out[f"{verifier_name}/{device_id}"] = {k: decoded[k] for k in cls._CLAIM_FIELDS if k in decoded}
        except Exception:
            return {}
        return out


def run_attestation(ledger: TamperEvidentLedger, cc_capable_gpu_suspected: bool,
                     device_uuid: Optional[str]) -> EvidenceRecord:
    """Top-level entry point producing a properly-typed EvidenceRecord with
    exactly the states spec Sec. 16 requires distinguished:
      HARDWARE_ATTESTATION_UNAVAILABLE - SDK missing or sub-Hopper GPU (we
        never attempted -- absence of evidence)
      SUCCESS with attest_result=False   - we DID challenge real hardware
        and it failed (evidence of failure, logged as VIOLATION downstream)
      SUCCESS with attest_result=True    - genuine firmware-integrity proof
    Scope discipline (spec Sec. 16): the returned record's `establishes`
    NEVER claims workload intent, training/inference, physical location, or
    policy authorization -- those are structurally different questions."""
    nonce = secrets.token_hex(32)
    adapter = NRASAttestationAdapter(ledger)
    real = adapter.attempt(cc_capable_gpu_suspected, nonce)

    if not real.get("attempted"):
        ev = EvidenceRecord(
            EvidenceClass.HARDWARE_ATTESTATION, EvidenceSource.NRAS_LOCAL_VERIFIER,
            EvidenceStatus.UNAVAILABLE, TrustRoot.NVIDIA_SIGNING_INFRASTRUCTURE,
            establishes=[], does_not_establish=["anything -- HARDWARE_ATTESTATION_UNAVAILABLE, "
                                                 "not attempted, not a failure"],
            detail={"nras_status": "HARDWARE_ATTESTATION_UNAVAILABLE", "reason": real.get("reason"), "nonce": nonce})
    elif not real.get("evidence_found"):
        ev = EvidenceRecord(
            EvidenceClass.HARDWARE_ATTESTATION, EvidenceSource.NRAS_LOCAL_VERIFIER,
            EvidenceStatus.UNAVAILABLE, TrustRoot.NVIDIA_SIGNING_INFRASTRUCTURE,
            establishes=[], does_not_establish=["anything -- HARDWARE_PRESENT_NO_EVIDENCE: Hopper+ GPU "
                                                 "detected but CC evidence could not be collected "
                                                 "(e.g. CC mode not enabled for this SKU)"],
            detail={"nras_status": "HARDWARE_PRESENT_NO_EVIDENCE", "nonce": nonce})
    elif real.get("attest_result"):
        ev = EvidenceRecord(
            EvidenceClass.HARDWARE_ATTESTATION, EvidenceSource.NRAS_LOCAL_VERIFIER,
            EvidenceStatus.SUCCESS, TrustRoot.NVIDIA_SIGNING_INFRASTRUCTURE,
            establishes=["hardware/firmware integrity evidence: this Hopper+ GPU's firmware "
                         "matches NVIDIA's signed reference state, challenged freshly via nonce"],
            does_not_establish=["workload intent", "training vs. inference", "physical location",
                                 "policy authorization -- see DeviceRegistry for that, separately"],
            detail={"nras_status": "HARDWARE_BACKED", "claims": real.get("claims", {}),
                    "device_uuid": device_uuid, "nonce": nonce})
    else:
        ev = EvidenceRecord(
            EvidenceClass.HARDWARE_ATTESTATION, EvidenceSource.NRAS_LOCAL_VERIFIER,
            EvidenceStatus.FAILED, TrustRoot.NVIDIA_SIGNING_INFRASTRUCTURE,
            establishes=["HARDWARE_BACKED_ATTEST_FAILED: real hardware was challenged and the "
                         "challenge-response failed -- an adverse finding, not absence of evidence"],
            does_not_establish=[],
            detail={"nras_status": "HARDWARE_BACKED_ATTEST_FAILED", "claims": real.get("claims", {}),
                    "device_uuid": device_uuid, "nonce": nonce})
        ledger.record("VIOLATION", {"layer": "L2_hardware_rooted_trust",
                                     "reason": "real NVIDIA attestation challenge-response failed",
                                     "claims": real.get("claims", {})})
    ledger.record_evidence(ev)
    return ev


# ---------------------------------------------------------------------------
# Phase 9: device authorization registry
# ---------------------------------------------------------------------------
class DeviceRegistry:
    """A LOCAL_DEMO_REGISTRY (spec Sec. 17) -- labeled as such everywhere it
    surfaces, never presented as if it were a real signed remote registry."""

    def __init__(self, registry_version: str = "local-demo-v0"):
        self._entries: dict[str, RegistryResult] = {}
        self.registry_version = registry_version

    def register(self, device_uuid: str, status: RegistryStatus, **kwargs) -> None:
        self._entries[device_uuid] = RegistryResult(
            device_uuid=device_uuid, status=status, registry_version=self.registry_version,
            registry_label="LOCAL_DEMO_REGISTRY", **kwargs)

    def check(self, device_uuid: str) -> RegistryResult:
        if device_uuid in self._entries:
            return self._entries[device_uuid]
        return RegistryResult(device_uuid=device_uuid, status=RegistryStatus.UNKNOWN,
                               registry_version=self.registry_version, registry_label="LOCAL_DEMO_REGISTRY")

    def as_evidence(self, result: RegistryResult) -> EvidenceRecord:
        return EvidenceRecord(
            EvidenceClass.REGISTRY_AUTHORIZATION, EvidenceSource.LOCAL_REGISTRY, EvidenceStatus.SUCCESS,
            TrustRoot.REGISTRY_OPERATOR,
            establishes=[f"registry status={result.status.value} for device {result.device_uuid} "
                         f"as of this LOCAL_DEMO_REGISTRY lookup"],
            does_not_establish=["physical location (a location_identifier field exists but is only as "
                                 "trustworthy as whoever populated the registry)",
                                 "that the device is telling the truth about its own identity"],
            detail=asdict(result))


# --- Phase 18: attestation + authorization composition ----------------------
def compose_device_authorization(attestation_ev: EvidenceRecord, registry_result: RegistryResult) -> dict[str, Any]:
    """Requires independent evidence from BOTH layers for a strong
    conclusion (spec Sec. 18). Never lets registry=unknown quietly become
    AUTHORIZED just because attestation succeeded, and never lets a valid
    registry entry erase a failed attestation."""
    attestation_ok = attestation_ev.status == EvidenceStatus.SUCCESS
    if attestation_ev.status == EvidenceStatus.FAILED:
        return {"conclusion": "DEVICE_AUTHORIZATION_ADVERSE",
                "reason": "attestation failed -- this is an adverse finding regardless of registry status"}
    if attestation_ok and registry_result.status == RegistryStatus.AUTHORIZED:
        return {"conclusion": "DEVICE_AUTHORIZATION_SUPPORTED",
                "reason": "independent evidence from both L2 (attestation) and L3 (registry) agree"}
    if attestation_ok and registry_result.status == RegistryStatus.UNKNOWN:
        return {"conclusion": "VERIFICATION_INCOMPLETE",
                "reason": "attestation succeeded but registry has no entry -- NOT upgraded to AUTHORIZED"}
    if attestation_ok and registry_result.status == RegistryStatus.DENIED:
        return {"conclusion": "DEVICE_AUTHORIZATION_ADVERSE",
                "reason": "registry explicitly denies this device even though attestation succeeded"}
    if attestation_ok and registry_result.status == RegistryStatus.EXPIRED:
        return {"conclusion": "DEVICE_AUTHORIZATION_ADVERSE", "reason": "registry entry expired"}
    return {"conclusion": "VERIFICATION_INCOMPLETE", "reason": "no hardware attestation evidence available"}


# ---------------------------------------------------------------------------
# Phase 6 + 13: model identity and continuity
# ---------------------------------------------------------------------------
class ModelIdentity:
    def __init__(self, ledger: TamperEvidentLedger):
        self._ledger = ledger
        self._registry: dict[str, dict[str, Any]] = {}

    def register(self, model_hash: str, metadata: dict[str, Any]) -> None:
        self._registry[model_hash] = metadata

    @staticmethod
    def hash_state_dict(state_dict: dict[str, Any]) -> str:
        hasher = hashlib.sha256()
        for name in sorted(state_dict.keys()):
            tensor = state_dict[name]
            hasher.update(name.encode())
            try:
                hasher.update(tensor.detach().cpu().contiguous().numpy().tobytes())
            except Exception:
                hasher.update(repr(tensor).encode())
        return hasher.hexdigest()

    def check(self, model_hash: str) -> EvidenceRecord:
        meta = self._registry.get(model_hash)
        ev = EvidenceRecord(
            EvidenceClass.MODEL_IDENTITY, EvidenceSource.OTHER, EvidenceStatus.SUCCESS,
            TrustRoot.GOVERNED_PROCESS_SELF,
            establishes=[f"SHA-256 of this state_dict {'matches' if meta else 'does not match'} "
                         "a registered hash at the moment measured"],
            does_not_establish=["that the model cannot later be modified -- a hash proves identity "
                                 "at measurement time only (see ModelContinuity for tracking across a run)"],
            detail={"hash": model_hash, "approved": meta is not None, "metadata": meta})
        self._ledger.record_evidence(ev)
        return ev


class ModelContinuity:
    """Stronger than a one-time hash (spec Sec. 13): tracks
    model_hash_before/during/after across a governed run. If continuous
    measurement isn't possible (which it structurally isn't for arbitrary
    unattended runtime -- only at explicit checkpoint calls), that
    limitation is stated, not glossed over."""

    def __init__(self, ledger: TamperEvidentLedger):
        self._ledger = ledger
        self.checkpoints: dict[str, str] = {}

    def checkpoint(self, label: str, model_hash: str) -> None:
        self.checkpoints[label] = model_hash
        self._ledger.record("model_continuity_checkpoint", {"label": label, "hash": model_hash})

    def report(self) -> EvidenceRecord:
        before, during, after = self.checkpoints.get("before"), self.checkpoints.get("during"), self.checkpoints.get("after")
        unchanged = len({v for v in (before, during, after) if v is not None}) <= 1
        ev = EvidenceRecord(
            EvidenceClass.MODEL_IDENTITY, EvidenceSource.OTHER,
            EvidenceStatus.SUCCESS if self.checkpoints else EvidenceStatus.NOT_APPLICABLE,
            TrustRoot.GOVERNED_PROCESS_SELF,
            establishes=[f"model hash was {'stable' if unchanged else 'DIFFERENT'} across the "
                         f"{len(self.checkpoints)} checkpoint(s) actually measured"],
            does_not_establish=["continuous integrity between checkpoints -- only the instants "
                                 "actually measured are covered; a swap-and-swap-back between "
                                 "checkpoints is invisible to this mechanism, stated plainly"],
            detail={"checkpoints": self.checkpoints, "unchanged": unchanged})
        self._ledger.record_evidence(ev)
        return ev
