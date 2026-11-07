"""
cuda_guard.evidence
====================
Phase 1 (spec Sec. 1, 2, 5, 29): the typed evidence model. Nothing in this
module *observes* anything — these are the domain objects every other
module in the package is required to populate, and the vocabulary the rest
of the package must use consistently instead of ad-hoc strings or a bare
``verified = True``.

Three category markers (spec Sec. 1) are used in docstrings throughout this
package to say exactly how a claim is known:
    VERIFIED_FROM_REPOSITORY  - demonstrated by source, tests, or local execution
    REAL_BUT_HARDWARE_DEPENDENT - genuinely available tech this environment can't exercise
    PROTOTYPE_RESEARCH        - not established as a complete, working mechanism
A capability must never be moved from the second or third category into the
first without a demonstrated (re-runnable, in this repo's tests/) reason.
"""

from __future__ import annotations

import enum
import hashlib
import json
import secrets
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Capability status (spec Sec. 2) — status of a CLASS of thing this package
# can do, assigned once per capability in the registry (Phase 32), not per
# observation.
# ---------------------------------------------------------------------------
class CapabilityStatus(str, enum.Enum):
    REAL_AND_TESTABLE = "REAL_AND_TESTABLE"
    REAL_BUT_HARDWARE_DEPENDENT = "REAL_BUT_HARDWARE_DEPENDENT"
    PROTOTYPE_RESEARCH = "PROTOTYPE_RESEARCH"
    SIMULATED_FOR_DEVELOPMENT = "SIMULATED_FOR_DEVELOPMENT"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    NOT_TECHNICALLY_PROVABLE_BY_THIS_LAYER = "NOT_TECHNICALLY_PROVABLE_BY_THIS_LAYER"

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# Evidence status (spec Sec. 2) — status of ONE evidence-collection attempt.
# ---------------------------------------------------------------------------
class EvidenceStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    SIMULATED = "SIMULATED"
    UNVERIFIED = "UNVERIFIED"

    def __str__(self) -> str:
        return self.value


class EpistemicClass(str, enum.Enum):
    """What an evidence item epistemically IS. Not interchangeable (spec
    Sec. 2): UNAVAILABLE is always ABSENCE_OF_EVIDENCE, never
    EVIDENCE_OF_FAILURE, no matter how suggestive the absence looks."""
    EVIDENCE_OF_SUCCESS = "EVIDENCE_OF_SUCCESS"
    EVIDENCE_OF_FAILURE = "EVIDENCE_OF_FAILURE"
    ABSENCE_OF_EVIDENCE = "ABSENCE_OF_EVIDENCE"

    def __str__(self) -> str:
        return self.value


# The ONLY place this mapping is decided. Every EvidenceRecord derives its
# epistemic class from its status through this function so no call site can
# hand-pick the wrong classification for a given status.
_STATUS_TO_EPISTEMIC: dict[EvidenceStatus, EpistemicClass] = {
    EvidenceStatus.SUCCESS: EpistemicClass.EVIDENCE_OF_SUCCESS,
    EvidenceStatus.FAILED: EpistemicClass.EVIDENCE_OF_FAILURE,
    EvidenceStatus.UNAVAILABLE: EpistemicClass.ABSENCE_OF_EVIDENCE,
    EvidenceStatus.NOT_APPLICABLE: EpistemicClass.ABSENCE_OF_EVIDENCE,
    EvidenceStatus.SIMULATED: EpistemicClass.ABSENCE_OF_EVIDENCE,
    EvidenceStatus.UNVERIFIED: EpistemicClass.ABSENCE_OF_EVIDENCE,
}


def epistemic_class_for(status: EvidenceStatus) -> EpistemicClass:
    return _STATUS_TO_EPISTEMIC[status]


class EvidenceClass(str, enum.Enum):
    SOFTWARE_SELF_AUDIT = "SOFTWARE_SELF_AUDIT"
    HARDWARE_ATTESTATION = "HARDWARE_ATTESTATION"
    DEVICE_IDENTITY = "DEVICE_IDENTITY"
    REGISTRY_AUTHORIZATION = "REGISTRY_AUTHORIZATION"
    COMPUTE_OBSERVATION = "COMPUTE_OBSERVATION"
    NETWORK_OBSERVATION = "NETWORK_OBSERVATION"
    POWER_OBSERVATION = "POWER_OBSERVATION"
    REPRODUCIBILITY = "REPRODUCIBILITY"
    RECOMPUTATION = "RECOMPUTATION"
    MODEL_IDENTITY = "MODEL_IDENTITY"
    LEDGER_INTEGRITY = "LEDGER_INTEGRITY"
    EXTERNAL_EVIDENCE = "EXTERNAL_EVIDENCE"

    def __str__(self) -> str:
        return self.value


class TrustRoot(str, enum.Enum):
    """WHO/WHAT roots an evidence item's trust. The single field most
    responsible for not letting one layer inherit another's proof power."""
    GOVERNED_PROCESS_SELF = "GOVERNED_PROCESS_SELF"                       # L1
    NVIDIA_SIGNING_INFRASTRUCTURE = "NVIDIA_SIGNING_INFRASTRUCTURE"        # L2
    REGISTRY_OPERATOR = "REGISTRY_OPERATOR"                                # L3
    INDEPENDENT_PHYSICAL_INFRASTRUCTURE = "INDEPENDENT_PHYSICAL_INFRASTRUCTURE"  # L4
    INDEPENDENT_EXTERNAL_VERIFIER = "INDEPENDENT_EXTERNAL_VERIFIER"        # L5
    LOCAL_DEVELOPMENT_FIXTURE = "LOCAL_DEVELOPMENT_FIXTURE"                # simulated/dev only

    def __str__(self) -> str:
        return self.value


class EvidenceSource(str, enum.Enum):
    SELF_AUDIT_HOOK = "SELF_AUDIT_HOOK"
    NVML = "NVML"
    NRAS_LOCAL_VERIFIER = "NRAS_LOCAL_VERIFIER"
    NRAS_REMOTE = "NRAS_REMOTE"
    LOCAL_REGISTRY = "LOCAL_REGISTRY"
    LD_PRELOAD_INTERCEPTOR = "LD_PRELOAD_INTERCEPTOR"
    PCAP_FILE = "PCAP_FILE"
    LIVE_INTERFACE = "LIVE_INTERFACE"
    EXTERNAL_TAP_FEED = "EXTERNAL_TAP_FEED"
    RECOMPUTATION_ENGINE = "RECOMPUTATION_ENGINE"
    EXTERNAL_PDU_FEED = "EXTERNAL_PDU_FEED"
    MANUAL_TEST_FIXTURE = "MANUAL_TEST_FIXTURE"
    OTHER = "OTHER"

    def __str__(self) -> str:
        return self.value


class RegistryStatus(str, enum.Enum):
    AUTHORIZED = "AUTHORIZED"
    DENIED = "DENIED"
    UNKNOWN = "UNKNOWN"
    EXPIRED = "EXPIRED"

    def __str__(self) -> str:
        return self.value


class EvidenceLayer(str, enum.Enum):
    """The five Trust Architecture layers (spec Sec. 7). Shared here because
    self_audit, hardware, network_evidence, external_evidence, and verdict
    all need to tag records with the layer they belong to."""
    L1_SELF_AUDIT = "L1_self_audit"
    L2_HARDWARE_ROOTED_TRUST = "L2_hardware_rooted_trust"
    L3_VERIFIER_AUTHORIZATION = "L3_verifier_authorization"
    L4_INFRASTRUCTURE_PHYSICAL = "L4_infrastructure_physical"
    L5_INDEPENDENT_EXTERNAL = "L5_independent_external"

    def __str__(self) -> str:
        return self.value


# ---------------------------------------------------------------------------
# Base evidence envelope
# ---------------------------------------------------------------------------
@dataclass
class EvidenceRecord:
    """Base unit every observation-producing module returns. Answers, per
    spec Sec. 5: what happened, when, what trust root supports it, real or
    simulated, what it establishes, what it does not establish. Carries a
    content hash for replay/integrity checks independent of ledger position."""
    evidence_class: EvidenceClass
    source: EvidenceSource
    status: EvidenceStatus
    trust_root: TrustRoot
    establishes: list[str]
    does_not_establish: list[str]
    timestamp_utc: str = field(default_factory=_now)
    detail: dict[str, Any] = field(default_factory=dict)
    record_id: str = field(default_factory=lambda: secrets.token_hex(8))

    @property
    def epistemic_class(self) -> EpistemicClass:
        return epistemic_class_for(self.status)

    @property
    def is_simulated(self) -> bool:
        return self.status == EvidenceStatus.SIMULATED

    def content_hash(self) -> str:
        payload = json.dumps(asdict(self), sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["epistemic_class"] = self.epistemic_class.value
        return d


# ---------------------------------------------------------------------------
# Typed payload shapes (spec Sec. 5's explicit list). Each is normally
# carried inside an EvidenceRecord.detail, and each producing module also
# returns the typed object directly so callers get real attributes, not
# untyped dict lookups.
# ---------------------------------------------------------------------------
@dataclass
class DeviceIdentity:
    uuid: str
    name: str
    compute_capability: Optional[str]
    driver_version: Optional[str] = None
    cuda_version: Optional[str] = None
    vram_total_mb: Optional[int] = None
    source: EvidenceSource = EvidenceSource.NVML
    is_emulated: bool = False


@dataclass
class RegistryResult:
    device_uuid: str
    status: RegistryStatus
    authorization_scope: Optional[str] = None
    operator: Optional[str] = None
    location_identifier: Optional[str] = None
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    registry_version: Optional[str] = None
    signature: Optional[str] = None
    registry_label: str = "LOCAL_DEMO_REGISTRY"


@dataclass
class ComputeObservation:
    operation: str
    observed_flops: int          # OBSERVED_FLOPS / LOWER_BOUND_FLOPS -- never TOTAL_GPU_FLOPS
    tensor_shapes: list
    dtype: str
    device: str
    run_id: str
    model_id: Optional[str] = None
    timestamp_utc: str = field(default_factory=_now)


@dataclass
class NetworkObservation:
    source_ip: Optional[str]
    dest_ip: Optional[str]
    protocol: Optional[str]
    packet_length: int
    direction: Optional[str]
    flow_id: Optional[str]
    timestamp: float
    capture_source: EvidenceSource
    packet_hash: Optional[str] = None


@dataclass
class PowerObservation:
    timestamp_utc: str
    power_watts: float
    device_or_rack_id: str
    measurement_source: str
    sampling_interval_s: Optional[float] = None
    trust_level: TrustRoot = TrustRoot.INDEPENDENT_PHYSICAL_INFRASTRUCTURE
    integrity_metadata: dict = field(default_factory=dict)


@dataclass
class ReproducibilityReport:
    model_hash: str
    input_hash: str
    environment_hash: str
    seed: int
    output_hash_run1: str
    output_hash_run2: str
    deterministic: bool
    dependency_versions: dict = field(default_factory=dict)


@dataclass
class RecomputationResult:
    sample_count: int
    total_population: Optional[int]
    sampling_policy: str
    matches: int
    mismatches: int
    coverage_fraction: Optional[float]
    confidence_note: str
    claim: str = "SAMPLED_RECOMPUTATION_SUPPORTED"


# ---------------------------------------------------------------------------
# Unsupported-claim guardrail (spec Sec. 29) — represented as data so tests
# and documentation generation can reference the SAME list rather than two
# independently-maintained copies drifting apart.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class UnsupportedClaim:
    claim: str
    why_wrong: str
    correct_framing: str


UNSUPPORTED_CLAIMS: tuple[UnsupportedClaim, ...] = (
    UnsupportedClaim(
        "e-fuses identify training vs. inference / gate Tensor Core instructions by workload type",
        "GEMM/Tensor Core instructions are identical in forward and backward passes; no ISA-level tag exists for a fuse to gate on.",
        "E-fuse revocation is whole-chip firmware/secure-boot signing-key revocation.",
    ),
    UnsupportedClaim(
        "NVIDIA attestation proves physical location",
        "Attestation proves firmware/hardware integrity, not geography.",
        "Location/authorization is a verifier-side registry decision applied to an otherwise-valid attestation.",
    ),
    UnsupportedClaim(
        "NVIDIA attestation proves workload intent (training vs. inference, R&D vs. deployment)",
        "Attestation is a firmware-integrity challenge-response; it carries no workload-semantic payload.",
        "Describe attestation strictly as hardware/firmware integrity evidence.",
    ),
    UnsupportedClaim(
        "NVSwitch knows 'authorized R&D' vs. 'restricted deployment'",
        "The switch observes payload size/pattern only; it has no semantic channel for job purpose.",
        "NETWORK_BEHAVIORAL_CORROBORATION at best, never a semantic-intent proof.",
    ),
    UnsupportedClaim(
        "network traffic alone proves semantic intent (training/inference)",
        "Traffic pattern is a correlate, not a direct observation of workload type.",
        "NETWORK_BEHAVIORAL_CORROBORATION, combined with other layers.",
    ),
    UnsupportedClaim(
        "power reveals exact FLOPs",
        "Power-to-FLOP correlation is workload- and precision-dependent, not a precise conversion.",
        "Power is plausibility/anomaly evidence only.",
    ),
    UnsupportedClaim(
        "FLOP hooks observe every GPU operation",
        "Only the specifically-hooked call sites (F.linear, torch.matmul, etc.) are counted.",
        "OBSERVED_FLOPS / LOWER_BOUND_FLOPS through the hooked call sites, not TOTAL_GPU_FLOPS.",
    ),
    UnsupportedClaim(
        "backward-pass interception proves no training occurred",
        "Absence of an intercepted call is absence of evidence, not proof of absence of training.",
        "NO_TRAINING_API_ACTIVITY_OBSERVED, never NO_TRAINING_OCCURRED.",
    ),
    UnsupportedClaim(
        "a model hash prevents later model replacement",
        "A hash proves identity at the instant it was measured.",
        "Add continuity tracking (before/during/after) and state the gap explicitly where continuous measurement isn't possible.",
    ),
    UnsupportedClaim(
        "a passive tap proves all cluster computation",
        "A tap observes what it is physically positioned to see, nothing upstream or on unobserved paths.",
        "Scope every network claim to the capture source's actual vantage point.",
    ),
    UnsupportedClaim(
        "software proves physical VRAM erasure",
        "Only a hardware-backed mechanism can prove physical erasure; software can prove its own buffer was overwritten.",
        "APPLICATION_BUFFER_WIPE, never PROVEN_GPU_MEMORY_ERASURE.",
    ),
    UnsupportedClaim(
        "simulated attestation is genuine attestation",
        "A SIMULATED evidence status is definitionally not a real hardware measurement.",
        "Always label simulated output SIMULATED, in code and in every surface that displays it.",
    ),
    UnsupportedClaim(
        "missing hardware evidence is equivalent to failed attestation",
        "UNAVAILABLE (absence of evidence) and FAILED (evidence of failure) are different epistemic classes.",
        "HARDWARE_PRESENT_NO_EVIDENCE / HARDWARE_ATTESTATION_UNAVAILABLE vs. HARDWARE_BACKED_ATTEST_FAILED are never merged.",
    ),
)
