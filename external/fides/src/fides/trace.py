"""
Synthetic execution trace generation and data model.

Models the kernel-level event stream an accelerator would emit during a
training step vs. an inference (decode) step. The statistical signatures
encoded here are drawn from well-documented differences between training
and inference workloads on modern accelerators:

  * Training invokes backward-pass kernels (grad convs / grad attention)
    roughly 1:1 with forward kernels, plus a periodic optimizer-state
    write (Adam m/v buffers etc).
  * Inference is forward-only; autoregressive decode additionally shows a
    monotonically growing KV-cache allocation that resets at sequence
    boundaries.
  * Multi-device training shows gradient all-reduce collectives sized to
    parameter count, at a fixed per-step cadence; tensor-parallel
    inference shows all-reduce/all-gather sized to activation width, at a
    per-token cadence.

These are approximations for a reference implementation / testbed, not a
claim that any one signal is individually sufficient against an adaptive
adversary -- see spec/PROTOCOL.md section 4 for the threat model, and note
that the Compute Verification Project is running an open red-teaming
competition against exactly this class of structural classifier.

generate_mixed_epoch() additionally models the more realistic adversarial
case: a device doing legitimate inference serving while quietly running a
handful of covert gradient steps on the side, then declaring the whole
epoch "inference".
"""

from dataclasses import dataclass, field
from enum import Enum


class KernelOp(Enum):
    FORWARD_MATMUL = "forward_matmul"
    FORWARD_ATTENTION = "forward_attention"
    BACKWARD_MATMUL = "backward_matmul"
    BACKWARD_ATTENTION = "backward_attention"
    OPTIMIZER_UPDATE = "optimizer_update"
    ALLREDUCE_GRAD = "allreduce_grad"
    ALLREDUCE_ACTIVATION = "allreduce_activation"
    KV_CACHE_WRITE = "kv_cache_write"
    KV_CACHE_RESET = "kv_cache_reset"


@dataclass
class KernelEvent:
    op: KernelOp
    timestamp_ns: int
    duration_ns: int
    bytes_read: int
    bytes_written: int
    flops: int


@dataclass
class ExecutionEpoch:
    """A bounded window of kernel events -- the unit that gets committed
    by the packet-hashing tap (see spec/PROTOCOL.md section 3)."""

    epoch_id: int
    events: list = field(default_factory=list)

    def duration_ns(self) -> int:
        if not self.events:
            return 0
        return self.events[-1].timestamp_ns - self.events[0].timestamp_ns


def _forward_block(t: int) -> tuple:
    events = [
        KernelEvent(KernelOp.FORWARD_MATMUL, t, 1_200_000, 8_000_000, 8_000_000, 4_000_000_000),
        KernelEvent(KernelOp.FORWARD_ATTENTION, t + 1_200_000, 900_000, 6_000_000, 6_000_000, 2_500_000_000),
    ]
    return events, t + 1_200_000 + 900_000


def generate_training_epoch(epoch_id: int, n_layers: int = 8, world_size: int = 1, seed: int = None) -> ExecutionEpoch:
    t = 0
    events = []
    for _ in range(n_layers):
        blk, t = _forward_block(t)
        events.extend(blk)
    for _ in range(n_layers):
        events.append(KernelEvent(KernelOp.BACKWARD_ATTENTION, t, 1_400_000, 9_000_000, 9_000_000, 5_000_000_000))
        t += 1_400_000
        events.append(KernelEvent(KernelOp.BACKWARD_MATMUL, t, 1_800_000, 12_000_000, 12_000_000, 6_500_000_000))
        t += 1_800_000
    events.append(KernelEvent(KernelOp.OPTIMIZER_UPDATE, t, 500_000, 40_000_000, 40_000_000, 200_000_000))
    t += 500_000
    if world_size > 1:
        events.append(KernelEvent(KernelOp.ALLREDUCE_GRAD, t, 3_000_000, 200_000_000, 200_000_000, 0))
        t += 3_000_000
    return ExecutionEpoch(epoch_id, events)


def generate_inference_epoch(epoch_id: int, n_layers: int = 8, seq_position: int = 0, world_size: int = 1, seed: int = None) -> ExecutionEpoch:
    t = 0
    events = []
    for _ in range(n_layers):
        blk, t = _forward_block(t)
        events.extend(blk)
        events.append(KernelEvent(KernelOp.KV_CACHE_WRITE, t, 80_000, 50_000, 500_000 + seq_position * 2_000, 0))
        t += 80_000
    if world_size > 1:
        events.append(KernelEvent(KernelOp.ALLREDUCE_ACTIVATION, t, 400_000, 4_000_000, 4_000_000, 0))
        t += 400_000
    if seq_position > 0 and seq_position % 512 == 0:
        events.append(KernelEvent(KernelOp.KV_CACHE_RESET, t, 10_000, 0, 0, 0))
        t += 10_000
    return ExecutionEpoch(epoch_id, events)


def generate_mixed_epoch(epoch_id: int, n_layers: int = 8, sneak_layers: int = 1, seq_position: int = 0, seed: int = None) -> ExecutionEpoch:
    """Mostly-inference epoch with a small number of covert backward /
    optimizer events mixed in. Models the realistic threat: a device
    serving genuine inference traffic while quietly running a few
    gradient steps on production data, then declaring the whole epoch
    'inference' to the registry."""
    epoch = generate_inference_epoch(epoch_id, n_layers=n_layers, seq_position=seq_position, world_size=1, seed=seed)
    t = epoch.duration_ns() + 100_000
    for _ in range(sneak_layers):
        epoch.events.append(KernelEvent(KernelOp.BACKWARD_ATTENTION, t, 1_400_000, 9_000_000, 9_000_000, 5_000_000_000))
        t += 1_400_000
        epoch.events.append(KernelEvent(KernelOp.BACKWARD_MATMUL, t, 1_800_000, 12_000_000, 12_000_000, 6_500_000_000))
        t += 1_800_000
    epoch.events.append(KernelEvent(KernelOp.OPTIMIZER_UPDATE, t, 500_000, 40_000_000, 40_000_000, 200_000_000))
    return epoch
