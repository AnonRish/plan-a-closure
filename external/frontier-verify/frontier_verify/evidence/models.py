"""Evidence schema.

See docs/evidence-model.md for the design rationale. Every model in this file
implements .digest() using frontier_verify.core.canonical, so any two
evidence bundles with identical content produce identical digests regardless
of field order or construction path.

MATURITY: EXPERIMENTAL (real, tested, but a Phase 1 schema -- see
docs/ai2040-coverage-matrix.md for what fields are aspirational vs populated
today).
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from frontier_verify.core.canonical import digest as canonical_digest


class Maturity(str, Enum):
    """The only vocabulary Frontier Verify is allowed to use when describing
    how real a component or a piece of evidence is. See section 4 of the
    source specification -- a component is not PRODUCTION_READY merely
    because it runs, and nothing may claim a maturity level it hasn't
    earned."""

    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    MOCK = "MOCK"
    SIMULATED = "SIMULATED"
    EXPERIMENTAL = "EXPERIMENTAL"
    RESEARCH = "RESEARCH"
    VALIDATED = "VALIDATED"
    PRODUCTION_READY = "PRODUCTION_READY"


class ModelIdentity(BaseModel):
    """What model was (claimed to be) running. In Phase 1 every field here
    is self-reported by the prover -- nothing independently confirms it.
    See docs/threat-model.md, question A."""

    model_digest: str
    weights_digest: str | None = None
    tokenizer_digest: str | None = None
    architecture_digest: str | None = None
    config_digest: str | None = None
    quantization: str | None = None
    name: str | None = None
    version: str | None = None

    def digest(self) -> str:
        return canonical_digest(self.model_dump(exclude_none=True, mode="json"))


class RuntimeIdentity(BaseModel):
    """What serving stack was (claimed to be) running it. Same self-report
    caveat as ModelIdentity."""

    serving_engine: str | None = None
    engine_version: str | None = None
    container_digest: str | None = None
    hardware_summary: str | None = None

    def digest(self) -> str:
        return canonical_digest(self.model_dump(exclude_none=True, mode="json"))


class HardwareEvidence(BaseModel):
    """Output of an AttestationProvider. `mock` and `maturity` are not
    decorative -- frontier_verify.policies.evaluator actually reads `mock`
    and refuses to grant assurance above L1 when it's True and the policy
    doesn't explicitly allow it. See frontier_verify/policies/evaluator.py.
    """

    provider_name: str
    maturity: Maturity
    mock: bool
    claims: dict = Field(default_factory=dict)
    raw_evidence_digest: str | None = None
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def digest(self) -> str:
        return canonical_digest(self.model_dump(exclude_none=True, mode="json"))


class Evidence(BaseModel):
    """The bundle a prover submits: what model, on what runtime, on what
    (attested-or-mock) hardware, for what workload."""

    evidence_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    model_identity: ModelIdentity
    runtime_identity: RuntimeIdentity
    hardware_evidence: HardwareEvidence
    workload_ref: str | None = None

    def digest(self) -> str:
        return canonical_digest(self.model_dump(exclude_none=True, mode="json"))
