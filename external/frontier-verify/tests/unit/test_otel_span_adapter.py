"""Tests OTelSpanEvidenceAdapter against REAL opentelemetry-sdk spans --
generated via the actual SDK's TracerProvider, not hand-built dicts
pretending to be spans. What these spans do NOT prove: that they match
what a real Triton `--trace-config mode=opentelemetry` deployment would
actually emit -- see docs/integrations/triton.md and this module's own
docstring for that honest gap.
"""
from __future__ import annotations

from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from frontier_verify.emitters.async_queue import AsyncQueueEvidenceEmitter
from frontier_verify.emitters.otel_span import DEFAULT_ATTRIBUTE_MAP, OTelSpanEvidenceAdapter


class _FakeClient:
    def __init__(self):
        self.received = []

    def submit_evidence(self, evidence):
        self.received.append(evidence)


def _make_real_span(attributes: dict):
    """Builds and captures a genuine opentelemetry.sdk.trace.ReadableSpan
    via the real SDK -- InMemorySpanExporter is OTel's own test utility
    for exactly this purpose, not something this project invented."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider(resource=Resource.create({"service.name": "test-triton"}))
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    tracer = provider.get_tracer("test")

    with tracer.start_as_current_span("inference_request") as span:
        for key, value in attributes.items():
            span.set_attribute(key, value)

    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    return spans[0]


def test_adapter_converts_a_real_otel_span_using_default_attribute_names():
    client = _FakeClient()
    emitter = AsyncQueueEvidenceEmitter(client)
    adapter = OTelSpanEvidenceAdapter(emitter)

    span = _make_real_span(
        {
            "gen_ai.request.model": "llama-3-70b-instruct",
            "gen_ai.request.model.version": "1.2.0",
            "gen_ai.system": "triton",
            "triton.request_id": "req-abc-123",
        }
    )

    adapter.on_span_end(span)
    assert emitter.wait_until_idle(timeout=2.0)

    assert len(client.received) == 1
    evidence = client.received[0]
    assert evidence.model_identity.name == "llama-3-70b-instruct"
    assert evidence.model_identity.version == "1.2.0"
    assert evidence.model_identity.model_digest.startswith("unverified-name:")
    assert evidence.runtime_identity.serving_engine == "triton"
    assert evidence.workload_ref == "req-abc-123"
    emitter.stop()


def test_adapter_falls_back_gracefully_when_expected_attributes_are_absent():
    """If Triton's real span attribute names differ from this module's
    unconfirmed defaults, the adapter must not crash -- it should produce
    honest 'unknown' placeholders rather than raising, since a missing
    attribute is exactly the failure mode this module's docstring warns
    is plausible."""
    client = _FakeClient()
    emitter = AsyncQueueEvidenceEmitter(client)
    adapter = OTelSpanEvidenceAdapter(emitter)

    span = _make_real_span({"some.unrelated.attribute": "value"})

    adapter.on_span_end(span)
    assert emitter.wait_until_idle(timeout=2.0)

    evidence = client.received[0]
    assert evidence.model_identity.name == "unknown-model"
    assert evidence.runtime_identity.serving_engine == "triton"  # the module's own fallback default
    emitter.stop()


def test_adapter_accepts_a_custom_attribute_map_for_a_real_deployment():
    """The configurability this module's docstring promises, exercised
    directly: a real Triton deployment with different span attribute
    names can correct the mapping without touching this module's code."""
    client = _FakeClient()
    emitter = AsyncQueueEvidenceEmitter(client)
    custom_map = dict(DEFAULT_ATTRIBUTE_MAP)
    custom_map["model_name"] = "my_custom_triton_attribute.model_name"
    adapter = OTelSpanEvidenceAdapter(emitter, attribute_map=custom_map)

    span = _make_real_span({"my_custom_triton_attribute.model_name": "custom-model-name"})

    adapter.on_span_end(span)
    assert emitter.wait_until_idle(timeout=2.0)

    assert client.received[0].model_identity.name == "custom-model-name"
    emitter.stop()


def test_adapter_extracts_real_span_timing():
    client = _FakeClient()
    emitter = AsyncQueueEvidenceEmitter(client)
    adapter = OTelSpanEvidenceAdapter(emitter)

    span = _make_real_span({"gen_ai.request.model": "m"})
    adapter.on_span_end(span)
    assert emitter.wait_until_idle(timeout=2.0)

    evidence = client.received[0]
    # Real timing from the real span -- not a hardcoded value -- so a
    # sane comparison is "close to now", not an exact timestamp match.
    import datetime as dt

    assert (dt.datetime.now(dt.timezone.utc) - evidence.created_at).total_seconds() < 10
    emitter.stop()
