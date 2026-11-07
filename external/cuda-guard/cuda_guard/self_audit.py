"""
cuda_guard.self_audit
=======================
Phase 4 (spec Sec. 8) + Phase 5 (spec Sec. 10): software self-audit and
observed-FLOP accounting. The interception logic here is ported from the
single-file prototype's Module 1/4/7 (already verified: the optimizer-
subclass walk is required because SGD/Adam/etc. each define their own
.step(), shadowing the base class -- patching only Optimizer.step silently
misses them). What changed in this port: evidence wording and typed
EvidenceRecord/TamperEvidentLedger output instead of ad hoc dicts.

TERMINOLOGY DISCIPLINE (spec Sec. 8): every event produced here is
TRAINING_API_ACTIVITY_OBSERVED, never TRAINING_PROVEN. Absence of an
intercepted call is NO_TRAINING_API_ACTIVITY_OBSERVED, never
NO_TRAINING_OCCURRED -- this module cannot see calls it isn't hooked into,
by construction (see bypass tests in tests/test_self_audit_bypass.py).
"""

from __future__ import annotations

import os
import threading
import traceback
from datetime import datetime, timezone
from typing import Any, Optional

from .evidence import (
    EvidenceClass, EvidenceLayer, EvidenceRecord, EvidenceSource, EvidenceStatus, TrustRoot,
    ComputeObservation,
)
from .ledger import TamperEvidentLedger


class GovernanceViolationError(RuntimeError):
    def __init__(self, message: str, violation_type: str = "generic",
                 stack_trace: Optional[list] = None):
        super().__init__(message)
        self.violation_type = violation_type
        self.stack_trace = stack_trace or []
        self.timestamp = datetime.now(timezone.utc).isoformat()


def _call_context() -> dict[str, Any]:
    return {"process_id": os.getpid(), "thread_id": threading.get_ident(),
            "timestamp_utc": datetime.now(timezone.utc).isoformat()}


class InferenceOnlyGovernor:
    """Observes (does not merely 'block' -- see class docstring in spec
    Sec. 8) calls to torch.Tensor.backward, torch.autograd.backward, and
    every currently-loaded Optimizer subclass's .step(). Ported verbatim in
    logic from the prototype; only the evidence output changed."""

    def __init__(self, ledger: TamperEvidentLedger):
        self._ledger = ledger
        self._active = False
        self._orig_tensor_backward = None
        self._orig_autograd_backward = None
        self._orig_optim_steps: dict[type, Any] = {}

    @staticmethod
    def _all_optimizer_subclasses() -> set[type]:
        import torch
        seen: set[type] = set()
        stack = [torch.optim.Optimizer]
        while stack:
            cls = stack.pop()
            for sub in cls.__subclasses__():
                if sub not in seen:
                    seen.add(sub)
                    stack.append(sub)
        return seen

    def engage(self) -> None:
        import torch
        if self._active:
            return
        self._orig_tensor_backward = torch.Tensor.backward
        self._orig_autograd_backward = torch.autograd.backward
        governor = self

        def guarded_tensor_backward(tensor_self, *args, **kwargs):
            governor._observe("torch.Tensor.backward() invoked on a governed tensor")

        def guarded_autograd_backward(*args, **kwargs):
            governor._observe("torch.autograd.backward() invoked")

        torch.Tensor.backward = guarded_tensor_backward
        torch.autograd.backward = guarded_autograd_backward

        for cls in self._all_optimizer_subclasses():
            if "step" in cls.__dict__:
                self._orig_optim_steps[cls] = cls.__dict__["step"]

                def make_guard(klass):
                    def guarded_step(opt_self, *args, **kwargs):
                        governor._observe(f"{klass.__name__}.step() invoked (weight update)")
                    return guarded_step

                cls.step = make_guard(cls)

        self._active = True
        self._ledger.record("self_audit_engaged", {
            "module": "InferenceOnlyGovernor",
            "patched_optimizer_classes": [c.__name__ for c in self._orig_optim_steps],
            **_call_context(),
        })

    def disengage(self) -> None:
        import torch
        if not self._active:
            return
        torch.Tensor.backward = self._orig_tensor_backward
        torch.autograd.backward = self._orig_autograd_backward
        for cls, orig in self._orig_optim_steps.items():
            cls.step = orig
        self._orig_optim_steps.clear()
        self._active = False
        self._ledger.record("self_audit_disengaged", {"module": "InferenceOnlyGovernor", **_call_context()})

    def is_active(self) -> bool:
        return self._active

    def _observe(self, operation: str):
        stack = traceback.format_stack()[:-2]
        ctx = _call_context()
        evidence = EvidenceRecord(
            evidence_class=EvidenceClass.SOFTWARE_SELF_AUDIT, source=EvidenceSource.SELF_AUDIT_HOOK,
            status=EvidenceStatus.SUCCESS, trust_root=TrustRoot.GOVERNED_PROCESS_SELF,
            establishes=["TRAINING_API_ACTIVITY_OBSERVED: a training-shaped API call reached "
                         "this hook while it was active"],
            does_not_establish=["that training did not happen via an unhooked route",
                                 "that this process's own willingness to run the hook is honest"],
            detail={"operation": operation, **ctx},
        )
        self._ledger.record_evidence(evidence)
        self._ledger.record("VIOLATION", {"layer": EvidenceLayer.L1_SELF_AUDIT, "reason": operation,
                                            "stack_trace": stack, **ctx})
        raise GovernanceViolationError(
            f"TRAINING_API_ACTIVITY_OBSERVED: {operation}", violation_type="training_api_activity_observed",
            stack_trace=stack)

    @staticmethod
    def classify_precision(tensor) -> str:
        import torch
        known = {}
        for name in ("float8_e4m3fn", "float8_e5m2", "float8_e4m3fnuz", "float8_e5m2fnuz",
                     "float4_e2m1fn_x2", "bfloat16"):
            if hasattr(torch, name):
                known[getattr(torch, name)] = name
        label = known.get(tensor.dtype)
        if label:
            return label
        if tensor.dtype in (torch.float16, torch.float32, torch.float64):
            return str(tensor.dtype).replace("torch.", "")
        return str(tensor.dtype)


class NCCLAuditor:
    """Software size-threshold heuristic on torch.distributed collectives.
    Self-documents its own limitation per spec Sec. 19: this observes
    payload size/pattern, never semantic intent."""

    def __init__(self, ledger: TamperEvidentLedger, threshold_bytes: int = 10 * 1024 * 1024):
        self._ledger = ledger
        self.threshold_bytes = threshold_bytes
        self._orig: dict[str, Any] = {}
        self._active = False

    def _check(self, op_name: str, nbytes: int) -> EvidenceRecord:
        flagged = nbytes > self.threshold_bytes
        evidence = EvidenceRecord(
            evidence_class=EvidenceClass.NETWORK_OBSERVATION, source=EvidenceSource.SELF_AUDIT_HOOK,
            status=EvidenceStatus.SUCCESS, trust_root=TrustRoot.GOVERNED_PROCESS_SELF,
            establishes=[f"NETWORK_BEHAVIORAL_CORROBORATION: {op_name}() payload was {nbytes} bytes"],
            does_not_establish=["workload semantic intent (R&D vs. deployment) -- size/pattern carries no such tag",
                                 "traffic this process did not route through torch.distributed"],
            detail={"op": op_name, "bytes": nbytes, "flagged": flagged, "threshold_bytes": self.threshold_bytes},
        )
        self._ledger.record_evidence(evidence)
        if flagged:
            reason = (f"covert multi-node sync suspected: {op_name}() payload {nbytes} bytes "
                      f"exceeds configured threshold {self.threshold_bytes} bytes")
            self._ledger.record("VIOLATION", {"layer": EvidenceLayer.L1_SELF_AUDIT, "reason": reason})
        return evidence

    def engage(self) -> None:
        import torch.distributed as dist
        if self._active:
            return
        auditor = self
        for name in ("all_reduce", "broadcast", "all_gather_into_tensor"):
            if hasattr(dist, name):
                orig = getattr(dist, name)
                self._orig[name] = orig

                def make_wrapper(op_name, orig_fn):
                    def wrapped(tensor, *args, **kwargs):
                        try:
                            nbytes = tensor.element_size() * tensor.nelement()
                        except Exception:
                            nbytes = 0
                        ev = auditor._check(op_name, nbytes)
                        if ev.detail["flagged"]:
                            raise GovernanceViolationError(f"NETWORK_BEHAVIORAL_CORROBORATION flagged: {op_name}")
                        return orig_fn(tensor, *args, **kwargs)
                    return wrapped

                setattr(dist, name, make_wrapper(name, orig))
        self._active = True

    def disengage(self) -> None:
        import torch.distributed as dist
        for name, orig in self._orig.items():
            setattr(dist, name, orig)
        self._orig.clear()
        self._active = False

    def is_active(self) -> bool:
        return self._active

    def simulate_collective(self, op_name: str, tensor) -> EvidenceRecord:
        """Exercises the identical policy logic without needing a real
        process group -- see prototype's rationale (a real dist call with no
        process group just raises an unrelated ValueError)."""
        nbytes = tensor.element_size() * tensor.nelement()
        return self._check(op_name, nbytes)


class ObservedFlopLedger:
    """OBSERVED_FLOPS / LOWER_BOUND_FLOPS through specifically-hooked call
    sites -- never TOTAL_GPU_FLOPS (spec Sec. 10). Renamed from the
    prototype's FlopLedger.total_flops for exactly this reason."""

    def __init__(self):
        self.observed_flops_lower_bound = 0
        self.observations: list[ComputeObservation] = []

    def record_gemm(self, operation: str, m: int, n: int, k: int, dtype_label: str,
                     run_id: str = "default", model_id: Optional[str] = None) -> ComputeObservation:
        flops = 2 * int(m) * int(n) * int(k)
        self.observed_flops_lower_bound += flops
        obs = ComputeObservation(operation=operation, observed_flops=flops,
                                  tensor_shapes=[[m, k], [k, n]], dtype=dtype_label,
                                  device="unspecified", run_id=run_id, model_id=model_id)
        self.observations.append(obs)
        return obs

    def summary(self) -> dict[str, Any]:
        by_dtype: dict[str, int] = {}
        by_op: dict[str, int] = {}
        for o in self.observations:
            by_dtype[o.dtype] = by_dtype.get(o.dtype, 0) + o.observed_flops
            by_op[o.operation] = by_op.get(o.operation, 0) + o.observed_flops
        return {
            "observed_flops_lower_bound": self.observed_flops_lower_bound,
            "gemm_call_count": len(self.observations),
            "flops_by_dtype": by_dtype, "flops_by_operation": by_op,
            "terminology_note": "OBSERVED_FLOPS / LOWER_BOUND_FLOPS through hooked call sites "
                                 "only -- NOT total device FLOPs. Any GEMM issued through an "
                                 "unhooked API is invisible to this ledger.",
        }


def install_flop_hooks(ledger: ObservedFlopLedger, dtype_label_fn, run_id: str = "default"):
    """Wraps F.linear and torch.matmul so GEMMs issued during a forward
    pass through THESE TWO call sites are counted automatically. Any other
    op (conv, custom kernel, a different framework) is invisible to this --
    stated in ObservedFlopLedger.summary()'s terminology_note, not just here."""
    import torch
    import torch.nn.functional as F
    orig_linear = F.linear
    orig_matmul = torch.matmul

    def hooked_linear(input, weight, bias=None):
        out = orig_linear(input, weight, bias)
        try:
            batch_elems = input.numel() // input.shape[-1]
            in_f, out_f = weight.shape[1], weight.shape[0]
            ledger.record_gemm("F.linear", batch_elems, out_f, in_f, dtype_label_fn(input), run_id)
        except Exception:
            pass
        return out

    def hooked_matmul(a, b, *args, **kwargs):
        out = orig_matmul(a, b, *args, **kwargs)
        try:
            if a.dim() >= 2 and b.dim() >= 2:
                m, k, n = a.shape[-2], a.shape[-1], b.shape[-1]
                batch = 1
                for d in a.shape[:-2]:
                    batch *= d
                ledger.record_gemm("torch.matmul", m * batch, n, k, dtype_label_fn(a), run_id)
        except Exception:
            pass
        return out

    F.linear = hooked_linear
    torch.matmul = hooked_matmul
    return {"F.linear": orig_linear, "torch.matmul": orig_matmul}


def remove_flop_hooks(originals: dict[str, Any]) -> None:
    import torch
    import torch.nn.functional as F
    F.linear = originals["F.linear"]
    torch.matmul = originals["torch.matmul"]
