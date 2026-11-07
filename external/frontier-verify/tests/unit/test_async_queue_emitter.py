"""Real tests for AsyncQueueEvidenceEmitter, the reference EvidenceEmitter
implementation. Moved/adapted from Phase 2's example-only test suite now
that this class lives in the real package."""
from __future__ import annotations

import time

from frontier_verify.emitters.async_queue import AsyncQueueEvidenceEmitter
from frontier_verify.emitters.base import EmittedExecution
from frontier_verify.evidence.models import HardwareEvidence, Maturity, ModelIdentity, RuntimeIdentity


def _execution(workload_id: str = "w1") -> EmittedExecution:
    return EmittedExecution(
        workload_id=workload_id,
        model_identity=ModelIdentity(model_digest="d1"),
        runtime_identity=RuntimeIdentity(serving_engine="test-engine"),
        hardware_evidence=HardwareEvidence(provider_name="mock", maturity=Maturity.MOCK, mock=True),
    )


class _FakeClient:
    def __init__(self, delay_seconds: float = 0.0, fail: bool = False):
        self.delay_seconds = delay_seconds
        self.fail = fail
        self.received: list = []

    def submit_evidence(self, evidence):
        time.sleep(self.delay_seconds)
        if self.fail:
            raise RuntimeError("simulated verifier outage")
        self.received.append(evidence)


def test_emit_does_not_block_even_when_client_is_slow():
    slow_client = _FakeClient(delay_seconds=2.0)
    emitter = AsyncQueueEvidenceEmitter(slow_client)

    start = time.monotonic()
    emitter.emit(_execution())
    elapsed = time.monotonic() - start

    assert elapsed < 0.5, f"emit() took {elapsed:.2f}s -- submission leaked into the caller's hot path"
    emitter.stop()


def test_evidence_eventually_reaches_the_client_with_correct_content():
    client = _FakeClient()
    emitter = AsyncQueueEvidenceEmitter(client)

    emitter.emit(_execution(workload_id="specific-workload-42"))
    assert emitter.wait_until_idle(timeout=2.0)

    assert emitter.submitted_count == 1
    assert len(client.received) == 1
    assert client.received[0].workload_ref == "specific-workload-42"
    emitter.stop()


def test_client_failures_are_isolated_and_counted():
    failing_client = _FakeClient(fail=True)
    emitter = AsyncQueueEvidenceEmitter(failing_client)

    emitter.emit(_execution())  # must not raise
    assert emitter.wait_until_idle(timeout=2.0)

    assert emitter.failed_count == 1
    emitter.stop()


def test_queue_overflow_drops_and_counts_rather_than_blocking():
    client = _FakeClient(delay_seconds=1.0)
    emitter = AsyncQueueEvidenceEmitter(client, max_queue=2)

    start = time.monotonic()
    for i in range(20):
        emitter.emit(_execution(workload_id=f"w{i}"))
    elapsed = time.monotonic() - start

    assert elapsed < 1.0, "queue backpressure leaked into the caller"
    assert emitter.dropped_count > 0
    emitter.stop()


def test_wait_until_idle_does_not_deadlock():
    """Regression test for the exact bug found in Phase 3: a prior version
    of this class used queue.Queue.join() here, which blocks forever
    without matching task_done() calls that were never made. This test
    would hang (and fail the CI timeout) if that bug were reintroduced."""
    client = _FakeClient()
    emitter = AsyncQueueEvidenceEmitter(client)
    emitter.emit(_execution())
    result = emitter.wait_until_idle(timeout=3.0)
    assert result is True
    emitter.stop()
