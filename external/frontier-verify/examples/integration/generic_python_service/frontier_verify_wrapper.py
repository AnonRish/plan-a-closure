"""Minimal integration pattern for a generic Python inference service:
wrap an EXISTING inference function so it emits evidence asynchronously,
without blocking the actual response and without requiring any change to
the function's own logic (brief section 8: "Do NOT require modification
of the inference engine itself where avoidable").

Phase 3: this is now a thin usage example of
frontier_verify.emitters.async_queue.AsyncQueueEvidenceEmitter (real
package code, real tests in tests/unit/test_async_queue_emitter.py) via
the formal EvidenceEmitter interface
(frontier_verify.emitters.base.EmittedExecution/EvidenceEmitter), not a
duplicate implementation. Phase 2's version of this file OWNED the async
queue logic directly; Phase 3 moved that logic into the real package
specifically so a second integration (docs/integrations/triton.md's
OpenTelemetry adapter) could reuse it instead of re-implementing the same
thread/queue pattern a second time.
"""
from __future__ import annotations

import uuid
from collections.abc import Callable
from functools import wraps
from typing import Any

from frontier_verify.emitters.async_queue import AsyncQueueEvidenceEmitter
from frontier_verify.emitters.base import EmittedExecution
from frontier_verify.evidence.models import HardwareEvidence, Maturity, ModelIdentity, RuntimeIdentity

# Re-exported so existing callers/tests that imported AsyncEvidenceSubmitter
# from this module keep working under its Phase 3 name and real location.
AsyncEvidenceSubmitter = AsyncQueueEvidenceEmitter


def verify_and_serve(
    model_digest: str,
    serving_engine: str,
    submitter: AsyncQueueEvidenceEmitter,
) -> Callable:
    """Decorator: wraps an existing inference function so every call
    emits an EmittedExecution via `submitter` (any EvidenceEmitter). The
    wrapped function's own return value and behavior are untouched."""

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            result = fn(*args, **kwargs)  # the real inference call, unmodified
            execution = EmittedExecution(
                workload_id=str(uuid.uuid4()),
                model_identity=ModelIdentity(model_digest=model_digest),
                runtime_identity=RuntimeIdentity(serving_engine=serving_engine),
                hardware_evidence=HardwareEvidence(provider_name="mock", maturity=Maturity.MOCK, mock=True),
            )
            submitter.emit(execution)  # async -- never blocks `result`
            return result

        return wrapped

    return decorator
