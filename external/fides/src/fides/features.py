"""
Feature extraction: turns a raw ExecutionEpoch into a small statistical
fingerprint that captures the training-vs-inference signal without
revealing weights, activations, or user data -- only kernel-level metadata
(op type, timing, byte counts) that a tap/runtime can expose without
touching model IP. This is the "privacy level" axis the AI 2040
verification supplement scores solutions on: low-level access (tokens,
weights, algorithms) is explicitly something the field wants to avoid
requiring.
"""

from dataclasses import dataclass

from .trace import ExecutionEpoch, KernelOp


@dataclass
class EpochFingerprint:
    epoch_id: int
    n_events: int
    backward_ratio: float  # backward kernels / forward kernels
    has_optimizer_update: bool
    allreduce_bytes_per_event: float
    kv_cache_present: bool
    arithmetic_intensity: float  # flops / bytes moved; higher = more compute-bound

    def as_tuple(self):
        return (
            round(self.backward_ratio, 4),
            self.has_optimizer_update,
            round(self.allreduce_bytes_per_event, 2),
            self.kv_cache_present,
            round(self.arithmetic_intensity, 4),
        )


def extract(epoch: ExecutionEpoch) -> EpochFingerprint:
    fwd = sum(1 for e in epoch.events if e.op in (KernelOp.FORWARD_MATMUL, KernelOp.FORWARD_ATTENTION))
    bwd = sum(1 for e in epoch.events if e.op in (KernelOp.BACKWARD_MATMUL, KernelOp.BACKWARD_ATTENTION))
    has_opt = any(e.op == KernelOp.OPTIMIZER_UPDATE for e in epoch.events)

    ar_events = [e for e in epoch.events if e.op in (KernelOp.ALLREDUCE_GRAD, KernelOp.ALLREDUCE_ACTIVATION)]
    ar_bytes = (sum(e.bytes_written for e in ar_events) / len(ar_events)) if ar_events else 0.0

    kv_present = any(e.op == KernelOp.KV_CACHE_WRITE for e in epoch.events)

    total_flops = sum(e.flops for e in epoch.events)
    total_bytes = sum(e.bytes_read + e.bytes_written for e in epoch.events) or 1
    arithmetic_intensity = total_flops / total_bytes

    return EpochFingerprint(
        epoch_id=epoch.epoch_id,
        n_events=len(epoch.events),
        backward_ratio=(bwd / fwd) if fwd else 0.0,
        has_optimizer_update=has_opt,
        allreduce_bytes_per_event=ar_bytes,
        kv_cache_present=kv_present,
        arithmetic_intensity=arithmetic_intensity,
    )
