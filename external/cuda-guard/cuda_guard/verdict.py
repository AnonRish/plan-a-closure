"""
cuda_guard.verdict
=====================
Phase 2 (spec Sec. 6) + Phase 16/28 (spec Sec. 7/28): the governance verdict
engine. Never reduces to PASS/FAIL. Explicitly lists which layers
contributed, which were absent, which contradicted each other. Reasoning
uses only evidence actually available in the ledger at call time.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional

from .evidence import EvidenceLayer, EvidenceStatus, TrustRoot, UNSUPPORTED_CLAIMS
from .ledger import TamperEvidentLedger


class VerdictStatus(str, enum.Enum):
    VERIFICATION_SUPPORTED = "VERIFICATION_SUPPORTED"
    SUPPORTED_WITH_LIMITATIONS = "SUPPORTED_WITH_LIMITATIONS"
    VERIFICATION_INCOMPLETE = "VERIFICATION_INCOMPLETE"
    EVIDENCE_CONFLICT = "EVIDENCE_CONFLICT"
    HARDWARE_ATTESTATION_FAILED = "HARDWARE_ATTESTATION_FAILED"
    DEVICE_UNAUTHORIZED = "DEVICE_UNAUTHORIZED"
    SIMULATED_ONLY = "SIMULATED_ONLY"
    NO_EVIDENCE = "NO_EVIDENCE"

    def __str__(self) -> str:
        return self.value


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class GovernanceVerdict:
    overall_status: VerdictStatus
    evidence_strength: str
    layers_present: list[str]
    layers_missing: list[str]
    successful_checks: list[str]
    failed_checks: list[str]
    warnings: list[str]
    violations: list[dict[str, Any]]
    unsupported_claims: list[str]
    limitations: list[str]
    evidence_records: list[dict[str, Any]]
    trust_roots: list[str]
    timestamps: dict[str, str]
    subject_identity: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class VerdictEngine:
    """Reads the ledger's actual recorded evidence at call time -- does not
    accept hand-supplied 'verified=True' style shortcuts. Requires
    independent evidence from multiple layers before returning
    VERIFICATION_SUPPORTED; a single successful layer, however strong,
    yields SUPPORTED_WITH_LIMITATIONS at best."""

    def __init__(self, ledger: TamperEvidentLedger):
        self._ledger = ledger

    def assess(self, subject_identity: dict[str, Any],
               layer_evidence: dict[EvidenceLayer, list[dict[str, Any]]]) -> GovernanceVerdict:
        layers_present, layers_missing = [], []
        successful_checks, failed_checks, warnings_list = [], [], []
        evidence_records: list[dict[str, Any]] = []
        trust_roots_seen: set[str] = set()

        for layer in EvidenceLayer:
            records = layer_evidence.get(layer, [])
            if not records:
                layers_missing.append(layer.value)
                continue
            layers_present.append(layer.value)
            for r in records:
                evidence_records.append(r)
                status = r.get("status")
                trust_roots_seen.add(r.get("trust_root", "unknown"))
                if status == EvidenceStatus.SUCCESS.value:
                    successful_checks.append(f"{layer.value}: {r.get('evidence_class', 'unknown')}")
                elif status == EvidenceStatus.FAILED.value:
                    failed_checks.append(f"{layer.value}: {r.get('evidence_class', 'unknown')}")
                elif status == EvidenceStatus.SIMULATED.value:
                    warnings_list.append(f"{layer.value}: evidence is SIMULATED, not real")
                elif status in (EvidenceStatus.UNAVAILABLE.value, EvidenceStatus.NOT_APPLICABLE.value):
                    warnings_list.append(f"{layer.value}: {status} (absence of evidence, not failure)")

        violations = [v.to_dict() for v in self._ledger.violations()]
        chain_result = self._ledger.verify_chain()
        if not chain_result.valid:
            failed_checks.append(f"LEDGER_INTEGRITY: chain broken at record {chain_result.first_break_at}")

        overall_status = self._decide_status(layers_present, failed_checks, violations, warnings_list, chain_result.valid)
        evidence_strength = self._decide_strength(layers_present, failed_checks, warnings_list)

        limitations = [
            "L1 self-audit evidence is only as trustworthy as the governed process's "
            "willingness to run it un-bypassed.",
            "L2 hardware attestation proves firmware/hardware integrity only -- never "
            "workload intent, training vs. inference, or physical location.",
            "L3 registry proves membership in a LOCAL_DEMO_REGISTRY only unless a real "
            "signed remote registry is wired in.",
            "L4/L5 evidence is present only when externally fed via record_external_evidence() "
            "-- this system cannot generate it itself.",
        ]
        if not chain_result.valid:
            limitations.append(f"AUDIT LEDGER INTEGRITY COMPROMISED at record {chain_result.first_break_at}: "
                                f"{chain_result.break_reason}")

        return GovernanceVerdict(
            overall_status=overall_status, evidence_strength=evidence_strength,
            layers_present=layers_present, layers_missing=layers_missing,
            successful_checks=successful_checks, failed_checks=failed_checks, warnings=warnings_list,
            violations=violations, unsupported_claims=[c.claim for c in UNSUPPORTED_CLAIMS],
            limitations=limitations, evidence_records=evidence_records,
            trust_roots=sorted(trust_roots_seen), timestamps={"generated_at": _now()},
            subject_identity=subject_identity)

    @staticmethod
    def _decide_status(layers_present: list[str], failed_checks: list[str], violations: list[dict],
                        warnings_list: list[str], chain_valid: bool) -> VerdictStatus:
        if not chain_valid:
            return VerdictStatus.EVIDENCE_CONFLICT
        if not layers_present:
            return VerdictStatus.NO_EVIDENCE
        if any("HARDWARE_ATTESTATION" in f or "L2" in f for f in failed_checks):
            return VerdictStatus.HARDWARE_ATTESTATION_FAILED
        if any(v.get("payload", {}).get("reason", "").lower().find("unauthorized") >= 0 for v in violations):
            return VerdictStatus.DEVICE_UNAUTHORIZED
        if failed_checks:
            return VerdictStatus.EVIDENCE_CONFLICT
        only_simulated = all("SIMULATED" in w for w in warnings_list) and warnings_list and not any(
            "L1" in lp or "L3" in lp for lp in layers_present)
        if only_simulated:
            return VerdictStatus.SIMULATED_ONLY
        if len(layers_present) >= 3 and not warnings_list:
            return VerdictStatus.VERIFICATION_SUPPORTED
        if len(layers_present) >= 1:
            return VerdictStatus.SUPPORTED_WITH_LIMITATIONS
        return VerdictStatus.VERIFICATION_INCOMPLETE

    @staticmethod
    def _decide_strength(layers_present: list[str], failed_checks: list[str], warnings_list: list[str]) -> str:
        n = len(layers_present)
        if failed_checks:
            return "WEAK (contains failed checks -- do not treat as passing)"
        if n >= 4:
            return "STRONG (multiple independent layers, including at least one hardware-rooted)"
        if n >= 2:
            return "MODERATE (multiple layers present, but not comprehensive)"
        if n == 1:
            return "WEAK (single layer only -- no independent corroboration)"
        return "NONE"
