from fides.trace import (
    KernelOp,
    generate_training_epoch,
    generate_inference_epoch,
    generate_mixed_epoch,
)


def test_training_epoch_has_backward_and_optimizer_events():
    epoch = generate_training_epoch(epoch_id=0, n_layers=4, seed=1)
    ops = [e.op for e in epoch.events]
    assert KernelOp.BACKWARD_MATMUL in ops
    assert KernelOp.BACKWARD_ATTENTION in ops
    assert KernelOp.OPTIMIZER_UPDATE in ops
    assert KernelOp.KV_CACHE_WRITE not in ops


def test_inference_epoch_has_no_backward_or_optimizer_events():
    epoch = generate_inference_epoch(epoch_id=0, n_layers=4, seed=1)
    ops = [e.op for e in epoch.events]
    assert KernelOp.BACKWARD_MATMUL not in ops
    assert KernelOp.BACKWARD_ATTENTION not in ops
    assert KernelOp.OPTIMIZER_UPDATE not in ops
    assert KernelOp.KV_CACHE_WRITE in ops


def test_multi_device_training_includes_gradient_allreduce():
    epoch = generate_training_epoch(epoch_id=0, n_layers=2, world_size=4, seed=1)
    assert KernelOp.ALLREDUCE_GRAD in [e.op for e in epoch.events]


def test_single_device_training_has_no_allreduce():
    epoch = generate_training_epoch(epoch_id=0, n_layers=2, world_size=1, seed=1)
    assert KernelOp.ALLREDUCE_GRAD not in [e.op for e in epoch.events]


def test_mixed_epoch_contains_both_inference_and_training_signal():
    epoch = generate_mixed_epoch(epoch_id=0, n_layers=6, sneak_layers=1, seed=1)
    ops = [e.op for e in epoch.events]
    assert KernelOp.KV_CACHE_WRITE in ops  # legitimate inference signal
    assert KernelOp.BACKWARD_MATMUL in ops  # covert training signal
    assert KernelOp.OPTIMIZER_UPDATE in ops


def test_mixed_epoch_bad_event_count_scales_with_sneak_layers():
    small = generate_mixed_epoch(epoch_id=0, n_layers=6, sneak_layers=1, seed=1)
    large = generate_mixed_epoch(epoch_id=0, n_layers=6, sneak_layers=3, seed=1)
    bad_ops = {KernelOp.BACKWARD_MATMUL, KernelOp.BACKWARD_ATTENTION, KernelOp.OPTIMIZER_UPDATE}
    small_bad = sum(1 for e in small.events if e.op in bad_ops)
    large_bad = sum(1 for e in large.events if e.op in bad_ops)
    assert large_bad > small_bad
