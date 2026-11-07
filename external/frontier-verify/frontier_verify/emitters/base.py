"""EmittedExecution and EvidenceEmitter.

Phase 2 built one integration (the generic Python wrapper) that
constructed `Evidence` objects inline, ad hoc. That doesn't scale to a
second and third integration (vLLM, Triton) without duplicating the same
"turn what I know into Evidence and get it to the verifier" logic in each
one, with each integration needing to understand `Evidence`'s internal
schema directly. This module fixes that: an inference-engine integration
constructs an `EmittedExecution` -- a plain description of what it
actually observed, in vocabulary an integration author already has
naturally available (a workload id, model/runtime identity, timing,
whatever hardware evidence exists) -- and hands it to an `EvidenceEmitter`,
which owns the "how does this become Evidence and get submitted" logic.
The integration author never needs to know how verification is ultimately
performed, per the brief's own framing of this requirement.
"""
from __future__ import annotations

import abc
from datetime import datetime, timezone

from pydantic import BaseModel, Field

from frontier_verify.evidence.models import HardwareEvidence, ModelIdentity, RuntimeIdentity


class EmittedExecution(BaseModel):
    """What an inference-engine integration actually knows, in its own
    natural vocabulary -- workload identity, model/runtime identity,
    timing, and whatever hardware evidence is available (MOCK if nothing
    real exists yet, same honesty rule as everywhere else in this repo).
    Does NOT include Evidence-schema-specific concerns like evidence_id
    generation or digesting -- that's EvidenceEmitter's job, not the
    integration's."""

    workload_id: str
    model_identity: ModelIdentity
    runtime_identity: RuntimeIdentity
    hardware_evidence: HardwareEvidence
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    integrity_note: str | None = None
    """Free-text field for integration-specific integrity information that
    doesn't fit ModelIdentity/RuntimeIdentity's fixed schema -- e.g. a
    Triton trace span ID, a vLLM request ID. Deliberately NOT structured
    further in Phase 3: adding fields to accommodate one integration
    before a second one exists to compare against would be guessing at a
    schema, not designing one."""


class EvidenceEmitter(abc.ABC):
    """The interface an inference-engine integration emits executions to.
    Implementations decide how (or whether) an EmittedExecution becomes
    Evidence, gets submitted, and what happens if submission fails --
    none of which the calling integration needs to know."""

    @abc.abstractmethod
    def emit(self, execution: EmittedExecution) -> None:
        """MUST NOT raise for ordinary submission failures (a slow or
        unreachable verifier) -- see AsyncQueueEvidenceEmitter for the
        reference implementation of that contract. MAY raise for
        programmer errors (e.g. malformed EmittedExecution that failed
        pydantic validation before this was even called)."""
        raise NotImplementedError
