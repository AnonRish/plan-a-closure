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


class ExactMeter:
    """Energy of a modelled GPU: idle watts always, plus (busy - idle) while a unit runs. Exact and linear in work, so a
    shortfall in the self-test's fit can only come from the load generator."""

    def __init__(self, idle_w=30.0, busy_w=68.0):
        import threading
        self.idle, self.busy, self.lock = idle_w, busy_w, threading.Lock()
        self.t0, self.since, self.busy_s = time.perf_counter(), None, 0.0

    def begin(self):
        with self.lock:
            self.since = time.perf_counter()

    def end(self):
        with self.lock:
            self.busy_s += time.perf_counter() - self.since
            self.since = None

    def energy_j(self):
        with self.lock:
            now = time.perf_counter()
            busy = self.busy_s + ((now - self.since) if self.since is not None else 0.0)
            return self.idle * (now - self.t0) + (self.busy - self.idle) * busy

    def util(self):
        return 1.0 if self.since is not None else 0.0


def _slow_matmul(meter, seconds_at_512):
    def mm(A, B):                                                   # a GEMM's time grows as dim**3
        meter.begin()
        time.sleep(seconds_at_512 * (A.shape[0] / 512) ** 3)
        meter.end()
        return A
    return mm


def _selftest(load, meter, dt=0.2, windows=10):
    from closure.hw.selftest import LEVELS, report
    from closure.hw.source import HwSource
    src = HwSource(meter, load, dt=dt, sub=dt / 4, n_gpu=1)
    rows = []
    try:
        for level in LEVELS:
            src.force_level = level
            for _ in range(windows):
                b = src.run_block(1, None)
                rows.append((level, b["X"][0], b["E"][0]))
    finally:
        load.stop()
    return report(rows, load.describe())


def test_a_unit_longer_than_the_slot_reproduces_the_t4_failure_and_sizing_fixes_it(monkeypatch):
    """The Colab T4 run at a fifth of the time scale: a 20 ms slot and a 108 ms unit (a 100 ms slot and a 540 ms unit on
    the T4), idle 30 W and 68 W while a unit runs (the T4 is capped at 70 W)."""
    from closure.hw.workloads import TorchLoad
    meter = ExactMeter()
    monkeypatch.setattr(torch, "matmul", _slow_matmul(meter, 0.108))
    old = _selftest(TorchLoad([0], dim=512, mem_elems=1 << 12, slot_s=0.02, device="cpu", auto_size=False), meter)
    assert not old["pass"] and not old["levels_distinct"] and old["work_ratio_25_to_100"] > 0.8
    assert "did not change the work done" in old["diagnosis"]

    meter = ExactMeter()
    monkeypatch.setattr(torch, "matmul", _slow_matmul(meter, 0.108))
    load = TorchLoad([0], dim=512, mem_elems=1 << 12, slot_s=0.02, device="cpu")
    u = load.describe()
    assert u["dim"] == 128 and u["fits_slot"] and [x["dim"] for x in u["tried"]] == [512, 256, 128]
    new = _selftest(load, meter)
    assert new["pass"] and new["levels_distinct"] and new["r2"] > 0.95, new
    assert new["work_ratio_25_to_100"] < 0.5


def test_load_generator_counts_units_as_they_finish():
    from closure.hw.workloads import TorchLoad
    load = TorchLoad([0], dim=64, mem_elems=1 << 12, slot_s=0.02, device="cpu")
    try:
        assert load.describe()["dtype"] == "bfloat16" and load.errors == []
        load.set_state(1.0)
        time.sleep(0.05)
        first = load.pop_units()[0]
        time.sleep(0.05)
        assert first > 0 and load.pop_units()[0] > 0                 # no slot-sized lumps: every pop finds work
    finally:
        load.stop()


def test_hidden_load_runs_at_the_duty_asked_for_even_below_one_gemm_a_slot():
    """Hidden GEMMs are paid for from a running credit, so a duty smaller than one GEMM per slot is met on average
    instead of being rounded up to one GEMM in every slot, and the seconds it really ran are counted."""
    from closure.hw.workloads import TorchLoad
    load = TorchLoad([0], dim=256, mem_elems=1 << 12, slot_s=0.02, device="cpu")
    try:
        one = load._time_unit("cpu", 256, 1 << 12)
        assert load.pop_hidden_s() == 0.0
        for duty in (0.05, 0.3):
            load.state = {"level": 0.0, "hid_duty": duty, "hid_gpus": frozenset([0])}
            time.sleep(0.2)
            load.pop_hidden_s()
            t0 = time.perf_counter()
            time.sleep(1.5)
            ran, wall = load.pop_hidden_s(), time.perf_counter() - t0
            assert 0.5 * duty < ran / wall < 1.6 * duty + one / wall, (duty, ran / wall)
        # under full verified load the hidden load still takes its share of the wall time (the credit is topped up by
        # the clock, not by the slot), and it is the verified work that gives way
        load.state = {"level": 1.0, "hid_duty": 0.0, "hid_gpus": frozenset()}
        time.sleep(0.2)
        load.pop_units()
        time.sleep(1.0)
        alone = load.pop_units()[0]
        load.state = {"level": 1.0, "hid_duty": 0.5, "hid_gpus": frozenset([0])}
        time.sleep(0.2)
        load.pop_hidden_s(), load.pop_units()
        t0 = time.perf_counter()
        time.sleep(1.5)
        ran, wall, units = load.pop_hidden_s(), time.perf_counter() - t0, load.pop_units()[0]
        assert 0.4 < ran / wall < 0.65, ran / wall                      # a per-slot credit would give a third
        assert 0.25 * alone < units / wall < 0.75 * alone, (units / wall, alone)
        load.state = {"level": 0.0, "hid_duty": 0.0, "hid_gpus": frozenset()}
        time.sleep(0.2)
        load.pop_hidden_s()
        time.sleep(0.3)
        assert load.pop_hidden_s() == 0.0                               # no hidden load, nothing counted
        load.hidden_table = [(0.1, 8.0), (0.4, 20.0)]
        load.set_state(0.0, 3.5 / load.p_max)                           # ask for 3.5 W of hidden load
        assert abs(load.state["hid_duty"] - 0.04375) < 1e-9
    finally:
        load.stop()
