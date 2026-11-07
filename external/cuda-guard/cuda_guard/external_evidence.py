"""
cuda_guard.external_evidence
===============================
Phase 14 (spec Sec. 24): power/PDU ingestion, used ONLY as plausibility/
anomaly evidence -- never converted into exact FLOPs. Phase 15 (spec Sec.
23): memory wipe, scoped strictly to APPLICATION_BUFFER_WIPE, never claiming
PROVEN_GPU_MEMORY_ERASURE. Phase 25 (spec Sec. 25): the categorized external
evidence API, vendor-independent.
"""

from __future__ import annotations

import ctypes
import enum
from datetime import datetime, timezone
from typing import Any, Optional

from .evidence import EvidenceClass, EvidenceRecord, EvidenceSource, EvidenceStatus, PowerObservation, TrustRoot
from .ledger import TamperEvidentLedger


class ExternalEvidenceCategory(str, enum.Enum):
    POWER = "POWER"
    NETWORK = "NETWORK"
    PHYSICAL_INSPECTION = "PHYSICAL_INSPECTION"
    EXTERNAL_ATTESTATION = "EXTERNAL_ATTESTATION"
    OTHER = "OTHER"

    def __str__(self) -> str:
        return self.value


def ingest_external_evidence(ledger: TamperEvidentLedger, category: ExternalEvidenceCategory,
                               trust_root: TrustRoot, raw_reference: str, normalized_evidence: dict[str, Any],
                               integrity_metadata: Optional[dict[str, Any]] = None) -> EvidenceRecord:
    """Vendor-independent ingestion point (spec Sec. 25). This is the ONLY
    place Layer 4/5 evidence enters the system -- nothing in this package
    calls this with fabricated data anywhere."""
    ev = EvidenceRecord(
        EvidenceClass.EXTERNAL_EVIDENCE, EvidenceSource.OTHER, EvidenceStatus.SUCCESS, trust_root,
        establishes=[f"external {category.value} evidence was ingested from {raw_reference}"],
        does_not_establish=["anything this package cannot independently verify about the "
                             "external source's own integrity"],
        detail={"category": category.value, "raw_reference": raw_reference,
                "normalized_evidence": normalized_evidence, "integrity_metadata": integrity_metadata or {}})
    ledger.record_evidence(ev)
    ledger.record_external_evidence(category.value.lower(), ev.to_dict())
    return ev


def correlate_power_with_compute(power_observations: list[PowerObservation], observed_flops: int,
                                   runtime_s: float) -> dict[str, Any]:
    """Plausibility/anomaly evidence ONLY (spec Sec. 24) -- never a
    FLOPs-from-watts calculation presented as exact."""
    if not power_observations:
        return {"claim": "PLAUSIBILITY_EVIDENCE", "status": "NO_POWER_DATA",
                "note": "no independent power measurements available to correlate against"}
    avg_watts = sum(p.power_watts for p in power_observations) / len(power_observations)
    energy_joules = avg_watts * runtime_s
    # A rough, explicitly-labeled-approximate FLOPs/joule envelope for plausibility only --
    # NEVER used to assert an exact FLOP count, only a coarse consistency check.
    plausible_flops_low, plausible_flops_high = energy_joules * 1e9, energy_joules * 5e11
    within_envelope = plausible_flops_low <= observed_flops <= plausible_flops_high if observed_flops > 0 else None
    return {
        "claim": "PLAUSIBILITY_EVIDENCE",
        "avg_power_watts": avg_watts, "runtime_s": runtime_s, "energy_joules": energy_joules,
        "observed_flops": observed_flops, "rough_plausible_flops_envelope": [plausible_flops_low, plausible_flops_high],
        "within_envelope": within_envelope,
        "scope_note": "This is a coarse, order-of-magnitude plausibility envelope, not a "
                      "precise FLOPs-from-watts conversion (which is workload- and "
                      "precision-dependent). Use only to flag gross anomalies, never to "
                      "assert an exact compute figure.",
    }


class ApplicationMemoryWiper:
    """Phase 15 (spec Sec. 23): APPLICATION_BUFFER_WIPE only. This can prove
    its own allocated buffer was overwritten in application-owned memory; it
    CANNOT prove physical VRAM erasure at the hardware level, and never
    claims to."""

    def __init__(self, ledger: TamperEvidentLedger):
        self._ledger = ledger
        self._tracked: dict[int, int] = {}  # id(buffer) -> size

    def allocate_and_track(self, size_bytes: int) -> bytearray:
        buf = bytearray(size_bytes)
        for i in range(size_bytes):
            buf[i] = 0xAB  # non-zero marker so a wipe is independently verifiable, not just "still zero"
        self._tracked[id(buf)] = size_bytes
        return buf

    def wipe(self, buf: bytearray) -> EvidenceRecord:
        size = self._tracked.get(id(buf), len(buf))
        for i in range(len(buf)):
            buf[i] = 0
        verified = all(b == 0 for b in buf)
        ev = EvidenceRecord(
            EvidenceClass.EXTERNAL_EVIDENCE, EvidenceSource.OTHER,
            EvidenceStatus.SUCCESS if verified else EvidenceStatus.FAILED, TrustRoot.GOVERNED_PROCESS_SELF,
            establishes=[f"APPLICATION_BUFFER_WIPE: a {size}-byte application-owned buffer was "
                         f"overwritten with zeros and independently re-read to confirm"],
            does_not_establish=["PROVEN_GPU_MEMORY_ERASURE -- this never touches physical VRAM; "
                                 "it demonstrates only that THIS process's own allocated buffer "
                                 "was overwritten, verifiable at the application level only"],
            detail={"size_bytes": size, "verified_all_zero": verified})
        self._ledger.record_evidence(ev)
        return ev


class HardwareBackedErasureAdapter:
    """Abstraction for future hardware-backed erasure evidence (spec Sec.
    23's explicit ask), e.g. an NVIDIA CC-mode session teardown that
    cryptographically proves memory was released/re-keyed. Not implemented
    -- no public API surface for this was confirmed during the Rev. 2
    hardware review. Clean interface only."""

    def request_erasure_proof(self, device_uuid: str) -> EvidenceRecord:
        return EvidenceRecord(
            EvidenceClass.EXTERNAL_EVIDENCE, EvidenceSource.OTHER, EvidenceStatus.NOT_APPLICABLE,
            TrustRoot.NVIDIA_SIGNING_INFRASTRUCTURE, establishes=[],
            does_not_establish=["anything -- NOT_IMPLEMENTED, no confirmed public API for "
                                 "hardware-backed VRAM erasure proof exists to build against"],
            detail={"device_uuid": device_uuid, "capability_status": "NOT_IMPLEMENTED"})
