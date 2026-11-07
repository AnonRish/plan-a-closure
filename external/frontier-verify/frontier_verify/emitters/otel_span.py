"""Consumes OpenTelemetry spans and converts them into EmittedExecution,
for integrations (Triton's trace export, or anything else that emits
OTel spans) that report evidence-relevant metadata as span attributes
rather than through a Python API this repository can call directly.

MATURITY: EXPERIMENTAL. Built against the REAL `opentelemetry-sdk`
package (not a hand-rolled stand-in) -- tested with genuine
`opentelemetry.sdk.trace.ReadableSpan` objects, not synthetic dicts
pretending to be spans. What's honestly UNTESTED: whether Triton's actual
`--trace-config mode=opentelemetry` output uses the attribute names this
module defaults to. Those defaults follow OpenTelemetry's published GenAI
semantic conventions (`gen_ai.request.model`, `gen_ai.system`, etc.) where
they plausibly apply, but this project has no live Triton instance to
confirm against -- see docs/integrations/triton.md. The mapping is
deliberately configurable specifically so a real Triton deployment can
correct it without touching this module's code.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from frontier_verify.emitters.base import EmittedExecution, EvidenceEmitter
from frontier_verify.evidence.models import HardwareEvidence, Maturity, ModelIdentity, RuntimeIdentity

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import ReadableSpan

# Best-effort defaults, not confirmed against real Triton output -- see
# this module's docstring. Override via `attribute_map` in
# OTelSpanEvidenceAdapter's constructor if a real deployment's span
# attributes differ, which they may well.
DEFAULT_ATTRIBUTE_MAP: dict[str, str] = {
    "model_name": "gen_ai.request.model",
    "model_version": "gen_ai.request.model.version",
    "serving_engine": "gen_ai.system",
    "workload_id": "triton.request_id",
}


class OTelSpanEvidenceAdapter:
    """Not itself an EvidenceEmitter -- it converts spans into
    EmittedExecution and hands them to one, so it composes with any
    EvidenceEmitter implementation (AsyncQueueEvidenceEmitter or a future
    one) rather than owning submission logic itself."""

    def __init__(
        self,
        emitter: EvidenceEmitter,
        attribute_map: dict[str, str] | None = None,
    ):
        self.emitter = emitter
        self.attribute_map = attribute_map or dict(DEFAULT_ATTRIBUTE_MAP)

    def on_span_end(self, span: ReadableSpan) -> None:
        """Call this from an OpenTelemetry SpanProcessor's on_end() hook,
        or from a batch consumer iterating over exported spans -- either
        way, this method is the actual conversion logic, kept separate
        from any specific OTel wiring mechanism so it's testable without
        standing up a real SpanProcessor pipeline."""
        attrs = dict(span.attributes or {})

        model_name = attrs.get(self.attribute_map["model_name"], "unknown-model")
        model_version = attrs.get(self.attribute_map["model_version"])
        serving_engine = attrs.get(self.attribute_map["serving_engine"], "triton")
        workload_id = str(attrs.get(self.attribute_map["workload_id"], span.context.span_id if span.context else "unknown"))

        started_at = self._ns_to_datetime(span.start_time) if span.start_time else datetime.now(timezone.utc)
        completed_at = self._ns_to_datetime(span.end_time) if span.end_time else None

        execution = EmittedExecution(
            workload_id=workload_id,
            model_identity=ModelIdentity(
                model_digest=f"unverified-name:{model_name}",  # NOT a real content digest --
                # see this module's docstring: a span attribute name is not
                # a weights hash. Prefixed so this is impossible to mistake
                # for a real ModelIdentity.model_digest downstream.
                name=model_name,
                version=str(model_version) if model_version is not None else None,
            ),
            runtime_identity=RuntimeIdentity(serving_engine=str(serving_engine)),
            hardware_evidence=HardwareEvidence(provider_name="mock", maturity=Maturity.MOCK, mock=True),
            started_at=started_at,
            completed_at=completed_at,
            integrity_note=f"otel_trace_id={format(span.context.trace_id, '032x')}" if span.context else None,
        )
        self.emitter.emit(execution)

    @staticmethod
    def _ns_to_datetime(nanoseconds: int) -> datetime:
        return datetime.fromtimestamp(nanoseconds / 1e9, tz=timezone.utc)
