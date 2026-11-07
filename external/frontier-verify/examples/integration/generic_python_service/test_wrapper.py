"""Real tests -- not a demo script -- for the generic Python integration
wrapper. The most important one proves asynchronicity concretely (a slow
fake client must not slow down the wrapped function) rather than assuming
it from the thread-based design.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from frontier_verify_wrapper import AsyncEvidenceSubmitter, verify_and_serve


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


def test_wrapped_function_return_value_is_unaffected():
    def my_inference(x: int) -> int:
        return x * 2

    submitter = AsyncEvidenceSubmitter(_FakeClient())
    wrapped = verify_and_serve(model_digest="d1", serving_engine="test-engine", submitter=submitter)(my_inference)

    assert wrapped(21) == 42
    submitter.stop()


def test_wrapped_function_returns_immediately_even_when_client_is_slow():
    """The core latency-isolation claim, made concrete: a client that
    takes 2 seconds per submission must not add meaningfully to the
    wrapped function's own (near-instant) return time."""

    def instant_inference() -> str:
        return "result"

    slow_client = _FakeClient(delay_seconds=2.0)
    submitter = AsyncEvidenceSubmitter(slow_client)
    wrapped = verify_and_serve(model_digest="d1", serving_engine="e", submitter=submitter)(instant_inference)

    start = time.monotonic()
    result = wrapped()
    elapsed = time.monotonic() - start

    assert result == "result"
    assert elapsed < 0.5, f"wrapped call took {elapsed:.2f}s -- evidence submission leaked into the hot path"
    submitter.stop()


def test_evidence_eventually_reaches_the_client():
    def inference() -> int:
        return 1

    client = _FakeClient()
    submitter = AsyncEvidenceSubmitter(client)
    wrapped = verify_and_serve(model_digest="d1", serving_engine="e", submitter=submitter)(inference)

    wrapped()
    submitter.wait_until_idle(timeout=2.0)

    assert submitter.submitted_count == 1
    assert len(client.received) == 1
    submitter.stop()


def test_client_failures_are_isolated_and_counted_not_raised_to_the_caller():
    def inference() -> int:
        return 1

    failing_client = _FakeClient(fail=True)
    submitter = AsyncEvidenceSubmitter(failing_client)
    wrapped = verify_and_serve(model_digest="d1", serving_engine="e", submitter=submitter)(inference)

    result = wrapped()  # must not raise, even though the client always fails
    submitter.wait_until_idle(timeout=2.0)

    assert result == 1
    assert submitter.failed_count == 1
    submitter.stop()


def test_queue_overflow_drops_and_counts_rather_than_blocking():
    def inference() -> int:
        return 1

    client = _FakeClient(delay_seconds=1.0)  # slow enough that the queue backs up
    submitter = AsyncEvidenceSubmitter(client, max_queue=2)
    wrapped = verify_and_serve(model_digest="d1", serving_engine="e", submitter=submitter)(inference)

    start = time.monotonic()
    for _ in range(20):
        wrapped()
    elapsed = time.monotonic() - start

    assert elapsed < 1.0, "queue backpressure leaked into the caller -- calls should never block on a full queue"
    assert submitter.dropped_count > 0
    submitter.stop()
