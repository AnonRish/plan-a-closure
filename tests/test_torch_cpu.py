"""The real torch code paths (probe rig, load generator, residency prover, reproducibility check) run on CPU torch.

Skipped where torch is not installed. CPU runs check shapes, dtypes and API use; they say nothing about CUDA timing,
NVML or clock control, which only a GPU run (closure tier0) can check."""
import time

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from closure import state as S  # noqa: E402
from closure.hw import probe as P  # noqa: E402
from closure.repro import torch_repro_check  # noqa: E402


class WallReader:
    """Energy as 150 W times wall time: enough for the rig's bookkeeping, not a measurement."""

    def __init__(self):
        self.t0 = time.perf_counter()

    def energy_j(self):
        return 150.0 * (time.perf_counter() - self.t0)

    def power_limit_w(self):
        return 300.0

    def sm_clock_mhz(self):
        return 1000.0

    def info(self):
        return {"reader": "wall-clock stand-in"}


def _rig():
    rig = P.TorchRig(dim=64, mem_elems=1 << 12, window_s=0.3, reader=WallReader(), device="cpu", control=False)
    rig.SETTLE_S, rig.WARMUP_S, rig.CALIB_S = 0.1, 0.1, 0.2
    return rig


def test_probe_rig_runs_reference_operand_and_precision_variants_on_cpu():
    vs = P.default_variants(clocks=(1500,), power_caps=(0.7,), precisions=("fp16", "int8", "fp8"), kernels=(),
                            operands=P.DEFAULT_OPERANDS)
    r = P.run_probe(_rig(), vs, levels=(0.0, 0.5), repeats=1, seed=0)
    names = {v["name"] for v in r["variants"]}
    assert {"reference", "operand-sparse90", "operand-lowent", "operand-zeros", "precision-fp16"} <= names
    assert any("device control is off" in n for n in r["notes"])           # clock and power variants are dropped, noted
    for low in ("precision-int8", "precision-fp8"):                         # measured, or dropped with a reason
        assert low in names or any(f"{low} dropped" in n for n in r["notes"])
    by = {v["name"]: v for v in r["variants"]}
    assert by["operand-zeros"]["class"] == "operand" and by["operand-zeros"]["allowed"]
    if "precision-int8" in by:
        assert by["precision-int8"]["rel_err"] > by["reference"]["rel_err"] and not by["precision-int8"]["allowed"]


def test_operand_patterns_have_the_intended_statistics():
    rig = _rig()
    zeros = rig._activations("zeros", torch.bfloat16)
    sparse = rig._activations("sparse90", torch.bfloat16)
    low = rig._activations("lowent", torch.bfloat16)
    assert float(zeros.abs().sum()) == 0.0
    assert 0.8 < float((sparse == 0).float().mean()) < 0.97
    assert set(torch.unique(low.float()).tolist()) <= {-1.0, 0.0, 1.0}


def test_load_generator_runs_units_on_cpu():
    from closure.hw.workloads import TorchLoad
    load = TorchLoad([0], dim=64, mem_elems=1 << 12, slot_s=0.02, device="cpu")
    try:
        load.set_state(0.5)
        time.sleep(0.3)
        assert load.pop_units()[0] > 0
    finally:
        load.stop()


def test_residency_prover_answers_challenges_correctly_on_cpu():
    v = S.Verifier(n_blocks=8, block_bytes=1 << 16)
    p = S.TorchProver("cpu", 1 << 16)
    S.fill(v, p)
    r = S.run_challenge(v, p, 4, 1e9)
    assert r["digest_ok"] and r["passed"]


def test_reproducibility_check_runs_on_cpu():
    r = torch_repro_check("cpu", batch_sizes=(1, 4), n=4)
    assert r["device"] == "cpu" and 0.0 <= r["bitwise_equal_rate"] <= 1.0 and np.isfinite(r["max_abs_diff"])
