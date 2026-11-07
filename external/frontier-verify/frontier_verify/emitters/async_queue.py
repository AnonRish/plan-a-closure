"""AsyncQueueEvidenceEmitter: the reference EvidenceEmitter implementation.

MATURITY: EXPERIMENTAL. Real, tested background-thread submission -- moved
here from examples/integration/generic_python_service/ in Phase 3, since
it's now shared infrastructure multiple integrations use (the generic
wrapper AND the Triton OTel adapter both build on this), not example-only
code. The example directory imports this rather than duplicating it.
"""
from __future__ import annotations

import queue
import threading
import time
import uuid
from typing import Any, Protocol

from frontier_verify.emitters.base import EmittedExecution, EvidenceEmitter
from frontier_verify.evidence.models import Evidence


class EvidenceSubmitClient(Protocol):
    """Structural type: anything with a submit_evidence(Evidence) method
    works here, so tests can supply a fake without needing a real running
    verifier API."""

    def submit_evidence(self, evidence: Evidence) -> Any: ...


class AsyncQueueEvidenceEmitter(EvidenceEmitter):
    """A background thread drains a bounded queue of Evidence (built from
    each EmittedExecution) and submits them one at a time via `client`, so
    the caller's hot path never blocks on network I/O -- verified
    concretely in tests/unit/test_async_queue_emitter.py, not just
    asserted here."""

    def __init__(self, client: EvidenceSubmitClient, max_queue: int = 1000):
        self.client = client
        self._queue: queue.Queue[Evidence] = queue.Queue(maxsize=max_queue)
        self._stop = threading.Event()
        self._processing = threading.Event()  # set while an item is actively being submitted
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()
        self.dropped_count = 0
        self.submitted_count = 0
        self.failed_count = 0

    def emit(self, execution: EmittedExecution) -> None:
        evidence = Evidence(
            evidence_id=str(uuid.uuid4()),
            model_identity=execution.model_identity,
            runtime_identity=execution.runtime_identity,
            hardware_evidence=execution.hardware_evidence,
            workload_ref=execution.workload_id,
            created_at=execution.started_at,
        )
        try:
            self._queue.put_nowait(evidence)
        except queue.Full:
            # Evidence collection must NEVER apply backpressure to real
            # inference traffic -- dropping under overload, with the drop
            # counted and observable, is correct here; blocking is not.
            self.dropped_count += 1

    def _worker(self) -> None:
        while not self._stop.is_set():
            try:
                evidence = self._queue.get(timeout=0.1)
            except queue.Empty:
                continue
            self._processing.set()
            try:
                self.client.submit_evidence(evidence)
                self.submitted_count += 1
            except Exception:  # noqa: BLE001 -- deliberate: a background emitter must
                # never let a client failure propagate and kill the worker thread.
                # Counted in failed_count, never raised.
                self.failed_count += 1
            finally:
                self._processing.clear()

    def wait_until_idle(self, timeout: float = 5.0) -> bool:
        """Test/shutdown helper: block until the queue is empty AND
        nothing is mid-submission. NOT part of the hot-path contract --
        production code should never call this on a request thread.

        Does NOT use queue.Queue.join() -- that blocks forever without
        matching task_done() calls for every put(), which this class
        never made in its Phase 2 predecessor and which hung an actual
        test run when tried. Polling both queue emptiness and an explicit
        "processing" flag avoids that entirely and has a real timeout."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._queue.empty() and not self._processing.is_set():
                return True
            time.sleep(0.01)
        return self._queue.empty() and not self._processing.is_set()

    def stop(self, timeout: float = 2.0) -> None:
        self._stop.set()
        self._thread.join(timeout=timeout)
