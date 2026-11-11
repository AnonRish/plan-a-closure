"""Sizing the unit of work to the GPU, and the self-test that catches a load generator whose levels do not differ.

The first run on real hardware (a Colab T4, docs/DEVIATIONS.md) stopped at hw-selftest with r2 = 0.72: an 8192 x 8192
bf16 unit took about half a second against a 100 ms slot, so every load level above zero ran flat out. These tests need
no torch and no GPU; tests/test_torch_cpu.py runs the real load generator through the same failure and its fix.
"""
import json
from types import SimpleNamespace

import numpy as np

from closure.hw import selftest as ST
from closure.hw.workloads import (MIN_DIM, characterise_hidden, duty_for_watts, measure_idle_w, native_half,
                                  size_unit)
from pathlib import Path

from closure.tier0 import _trial_clock_args, _unit_args


def test_size_unit_halves_until_one_unit_fits_the_budget():
    t8192 = 0.54                                                # bf16 on a T4, from the Colab run (seconds per unit)
    dim, mem, t, tried = size_unit(lambda d, m: t8192 * (d / 8192) ** 3, 8192, 1 << 29, budget_s=0.02)
    assert [x["dim"] for x in tried] == [8192, 4096, 2048] and dim == 2048 and mem == 1 << 27
    assert t <= 0.02 and t == tried[-1]["unit_s"]
    dim, *_ = size_unit(lambda d, m: 0.002, 8192, 1 << 29, budget_s=0.02)     # an H100 already fits: unchanged
    assert dim == 8192


def test_size_unit_stops_at_the_smallest_size_when_nothing_fits():
    dim, mem, t, tried = size_unit(lambda d, m: 10.0, 1024, 1 << 20, budget_s=0.02)
    assert dim == MIN_DIM and t == 10.0 and len(tried) == 1 + (1024 // MIN_DIM).bit_length() - 1


def _torch(major):
    return SimpleNamespace(bfloat16="bf16", float16="fp16",
                           cuda=SimpleNamespace(get_device_capability=lambda dev: (major, 0)))


def test_native_half_is_fp16_before_compute_capability_8_and_bf16_from_it():
    assert native_half(_torch(7), "cuda:0") == "fp16"           # T4 (7.5), V100 (7.0): no bf16 tensor cores
    assert native_half(_torch(8), "cuda:0") == "bf16"           # A100, L4, H100
    assert native_half(_torch(9), "cuda:1") == "bf16"
    assert native_half(_torch(7), "cpu") == "bf16"              # CPU runs (tests, rehearsal) are unchanged


def test_idle_power_is_read_from_the_energy_counter():
    clock = {"t": 0.0}

    class Reader:
        def energy_j(self):
            return 30.0 * 2 * clock["t"]                       # two GPUs idling at 30 W each

    def sleep(s):
        clock["t"] += s
    w = measure_idle_w(Reader(), n_gpu=2, seconds=3.0, settle_s=2.0, sleep=sleep, now=lambda: clock["t"])
    assert abs(w - 30.0) < 1e-9


def _rows(units_by_level, power, idle=30.0, windows=30, seed=0):
    """(level, x, energy) windows: units per window from units_by_level(level, rng); energy from power(units)."""
    rng = np.random.default_rng(seed)
    rows = []
    for lv in ST.LEVELS:
        for _ in range(windows):
            u = float(units_by_level(lv, rng))
            rows.append((lv, [1.0, u, u, u], idle + power(lv, u, rng)))
    return rows


def test_saturated_levels_fail_and_say_why():
    # The T4 run: every level above zero runs flat out at the power cap; 1 or 2 units finish in a window.
    rows = _rows(lambda lv, r: 0 if lv == 0 else r.choice([1, 2], p=[0.15, 0.85]),
                 lambda lv, u, r: 0.0 if lv == 0 else 38.0 + r.normal(0, 4.0))
    out = ST.report(rows, unit={"unit_s": 0.54, "slot_s": 0.1})
    assert not out["pass"] and not out["levels_distinct"] and out["work_ratio_25_to_100"] > 0.8
    assert out["r2"] < 0.9                                     # and it fails the pre-registered criterion as well
    assert "did not change the work done" in out["diagnosis"] and "540 ms against a 100 ms slot" in out["diagnosis"]


def test_two_clusters_can_fit_well_and_still_fail_the_distinct_levels_check():
    # Without the v0.3 check this would pass: idle and flat-out windows alone give a high r2, but the levels did nothing.
    rows = _rows(lambda lv, r: 0 if lv == 0 else 20, lambda lv, u, r: 0.0 if lv == 0 else 38.0 + r.normal(0, 0.3))
    out = ST.report(rows)
    assert out["r2"] > 0.99 and not out["pass"] and not out["levels_distinct"]


def test_healthy_levels_pass():
    rows = _rows(lambda lv, r: max(0, round(lv * 100 + r.normal(0, 1.0))), lambda lv, u, r: 0.38 * u + r.normal(0, 0.3))
    out = ST.report(rows)
    assert out["pass"] and out["levels_distinct"] and out["r2"] > 0.99 and "diagnosis" not in out
    assert abs(out["theta"]["duration_s"] - 30.0) < 0.5 and abs(out["idle_power_w"] - 30.0) < 0.2
    assert abs(out["work_ratio_25_to_100"] - 0.25) < 0.02 and set(out["per_level"]) == {"0", "0.25", "0.5", "0.75", "1"}


def test_levels_that_differ_but_energy_that_does_not_track_them_is_explained():
    rows = _rows(lambda lv, r: round(lv * 100), lambda lv, u, r: r.normal(19.0, 12.0))
    out = ST.report(rows)
    assert not out["pass"] and out["levels_distinct"] and "energy did not track the counted work" in out["diagnosis"]


def test_no_work_counted_is_reported_as_a_dead_load_generator():
    out = ST.report(_rows(lambda lv, r: 0, lambda lv, u, r: r.normal(0, 0.5)))
    assert not out["pass"] and "load generator did not run" in out["diagnosis"]


def test_tier0_passes_the_selftest_unit_on_to_the_probe_and_the_trial():
    log = "GPU: cuda:0 = ...\nunit of work: 4096x4096 float16 GEMM ...\n" + json.dumps(
        {"r2": 0.97, "pass": True, "unit": {"dim": 4096, "mem_elems": 1 << 28, "dtype": "float16"}}, indent=2)
    assert _unit_args(log) == ["--dim", "4096", "--mem-elems", str(1 << 28)]
    assert _unit_args(json.dumps({"r2": 0.97, "pass": True})) == []          # mock runs print no unit
    assert _unit_args("Traceback (most recent call last): ...") == []


RUN3_PROBE = Path(__file__).resolve().parents[1] / "results" / "shakedown-2026-11-08-colab-t4-run3" / "extracted" / "probe.json"


def test_tier0_locks_the_trial_at_the_highest_clock_the_t4_held_under_its_cap(tmp_path):
    # Run 3's probe: locks at 1575 and 1335 MHz were pulled down to 1125 and 975 MHz by the 70 W cap at full load;
    # 1110 MHz held at 65.2 W. The trial then calibrates and audits at one clock.
    assert _trial_clock_args(RUN3_PROBE) == ["--lock-clock-mhz", "1110"]
    pr = json.loads(RUN3_PROBE.read_text())
    pr["status"] = "REHEARSAL"
    (tmp_path / "p.json").write_text(json.dumps(pr))
    assert _trial_clock_args(tmp_path / "p.json") == []                      # never on a rehearsal or mock probe
    assert _trial_clock_args(tmp_path / "missing.json") == []


class _SoloRig:
    """A load generator and energy counter in one, on a virtual clock: idle 30 W, hidden work at 80 W per unit duty up
    to 10% duty and 45 W per unit duty after (not the 40 W that the power limit less idle power suggests; run 4's T4
    drew 73 W per unit duty with clocks locked)."""

    def __init__(self, idle_drift_w_per_s=0.0):
        self.state, self.gpus, self.t, self.e = {"level": 0.0, "hid_duty": 0.0, "hid_gpus": frozenset()}, [0, 1], 0.0, 0.0
        self.drift = idle_drift_w_per_s

    def watts(self, t):
        d = self.state["hid_duty"] if self.state["hid_gpus"] else 0.0
        return 2 * (30.0 + self.drift * t + 80.0 * min(d, 0.1) + 45.0 * max(d - 0.1, 0.0))

    def sleep(self, s):
        self.e += self.watts(self.t + s / 2) * s            # exact for power that changes linearly
        self.t += s

    def energy_j(self):
        return self.e


def test_hidden_load_is_characterised_alone_and_labels_are_read_off_the_measured_curve():
    """Until 0.8.0 a label of x% was turned into a duty by assuming the GPU draws its power limit while busy. Run 4's T4
    drew nearly twice that in its bursts, and its "5%" hidden load drew 11% of capacity. The solo run measures the curve."""
    rig = _SoloRig()
    was = rig.state
    solo = characterise_hidden(rig, rig, 2, duties=(0.05, 0.1, 0.4), on_s=5.0, idle_s=2.0, settle_s=1.0,
                               sleep=rig.sleep, now=lambda: rig.t)
    assert rig.state is was                                              # the load is left as it was found
    assert solo["duty"] == [0.05, 0.1, 0.4] and np.allclose(solo["idle_w_per_gpu"], 30.0)
    assert np.allclose(solo["watts_per_gpu"], [4.0, 8.0, 21.5])
    table = list(zip(solo["duty"], solo["watts_per_gpu"]))
    assert duty_for_watts(table, 0.0) == 0.0
    assert duty_for_watts(table, 2.0) == 0.025 and duty_for_watts(table, 8.0) == 0.1          # 80 W per unit duty
    assert abs(duty_for_watts(table, 3.5) - 0.04375) < 1e-12                                   # 5% of a 70 W GPU
    assert abs(duty_for_watts(table, 14.75) - 0.25) < 1e-12                                    # on the second segment
    assert abs(duty_for_watts(table, 30.5) - 0.6) < 1e-12 and duty_for_watts(table, 500.0) == 1.0   # extended, capped
    old_estimate = 3.5 / (70.0 - 30.0)                  # what 0.7.0 would have run for the same label: twice the duty
    assert old_estimate > 1.9 * duty_for_watts(table, 3.5)
    # idle power that creeps up as the GPU warms (0.05 W a second here, 1.2 W over one measurement) cancels, because
    # each duty is measured between an idle reading before it and one after
    warm = _SoloRig(idle_drift_w_per_s=0.05)
    solo = characterise_hidden(warm, warm, 2, duties=(0.05, 0.1, 0.4), on_s=5.0, idle_s=2.0, settle_s=1.0,
                               sleep=warm.sleep, now=lambda: warm.t)
    assert np.allclose(solo["watts_per_gpu"], [4.0, 8.0, 21.5], atol=1e-9)
