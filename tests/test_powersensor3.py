"""PowerSensor3 dumps as the independent meter: the format its host library writes, read back in constant memory, the
printed-time rounding of relative dumps undone, and the recorder run against a stand-in for the Python binding."""
import json
import sys
import types

import numpy as np
import pytest

from closure import dcbus as D
from closure.cli import main

HEADER = "marker time dt_micro device_timestamp current0 voltage0 power0 current1 voltage1 power1 power_total"


def _write_dump(path, t, p_aux, p_slot, absolute=True, markers=(), truncate_last=False):
    """The layout of PowerSensor::dump()/dumpCurrentWattToFile(): absolute times with std::fixed and six decimals,
    relative times with the stream's default six significant figures."""
    with open(path, "w") as f:
        f.write(HEADER + "\n")
        prev = t[0]
        for k, (tk, a, s) in enumerate(zip(t, p_aux, p_slot)):
            ts = f"{tk:.6f}" if absolute else format(tk, ".6g")
            m = "Q" if k in markers else "S"
            v_a, v_s = 12.05, 11.98
            f.write(f"{m} {ts} {int(1e6 * (tk - prev))} {123456 + k} {a / v_a:.6f} {v_a} {a:.6f} "
                    f"{s / v_s:.6f} {v_s} {s:.6f} {a + s:.6f}\n")
            prev = tk
        if truncate_last:
            f.write("S 1763 50")


def _trace(n_s=5.0, rate=20_000, t_start=1_763_130_000.0, seed=0, idle=250.0, swing=60.0):
    rng = np.random.default_rng(seed)
    t = t_start + np.arange(int(n_s * rate)) / rate
    aux = idle + swing * (np.sin(2 * np.pi * 0.9 * (t - t_start)) > 0) + rng.normal(0, 3, len(t))   # square-wave load
    slot = np.full(len(t), 40.0) + rng.normal(0, 0.5, len(t))
    return t, aux, slot


def test_absolute_dump_reads_back_with_its_energy(tmp_path):
    t, aux, slot = _trace()
    _write_dump(tmp_path / "d.txt", t, aux, slot, markers={10, 20}, truncate_last=True)
    r = D.powersensor3_to_csv(tmp_path / "d.txt", tmp_path / "bus.csv", window_s=0.01)
    p = aux + slot
    e_true = float(np.sum(0.5 * (p[1:] + p[:-1]) * np.diff(t)))
    assert r["absolute_times"] and r["t0_applied"] is None and r["sensor_pairs"] == 2
    assert r["rows_in"] == len(t) and r["rows_skipped"] == 1 and r["markers"] == 2       # markers are samples too
    assert abs(r["energy_j_in"] - e_true) / e_true < 1e-6
    assert 19_000 < r["sample_rate_hz"] < 21_000 and 315 < r["mean_w"] < 330      # 250 + 60/2 + 40 W
    tb, pb = D.load_csv(tmp_path / "bus.csv")
    assert abs(tb[0] - (t[0] + 0.005)) < 1e-6 and len(tb) == pytest.approx(500, abs=1)
    starts = t[0] + np.arange(0.5, 4.0, 1.0)                                    # away from the first half window
    assert np.allclose(D.window_energy(tb, pb, starts, 1.0), D.window_energy(t, p, starts, 1.0), rtol=2e-3)
    assert D.check_absolute_power(tb, pb)["ok"]


def test_relative_dump_needs_t0_and_its_rounded_times_are_spread_out(tmp_path):
    # A dump started long after its PowerSensor object was created: printed to six significant figures, every 0.1 s of
    # samples share one time. Spreading them evenly puts each window's energy back where it was drawn.
    t, aux, slot = _trace(n_s=60.0, rate=2_000, t_start=10_000.0, seed=3, idle=100.0, swing=500.0)
    _write_dump(tmp_path / "rel.txt", t, aux, slot, absolute=False)
    with pytest.raises(ValueError, match="relative times"):
        D.powersensor3_to_csv(tmp_path / "rel.txt", tmp_path / "x.csv")
    t0 = 1_763_000_000.0
    r = D.powersensor3_to_csv(tmp_path / "rel.txt", tmp_path / "bus.csv", window_s=0.01, t0=t0)
    assert not r["absolute_times"] and r["t0_applied"] == t0 and r["max_rows_sharing_one_printed_time"] >= 150
    tb, pb = D.load_csv(tmp_path / "bus.csv")
    p = aux + slot
    starts = np.arange(10_001.3, 10_058.0, 1.0)
    truth = D.window_energy(t, p, starts, 1.0)
    got = D.window_energy(tb - t0, pb, starts, 1.0)
    assert np.max(np.abs(got - truth) / truth) < 0.01
    # the same rows without spreading: whole 0.1 s steps land in one window, and a 1 s window is off by several percent
    q = np.array([float(format(x, ".6g")) for x in t])
    naive = D.window_energy(q, p, starts, 1.0)
    assert np.max(np.abs(naive - truth) / truth) > 0.03


def test_refusals(tmp_path):
    t, aux, slot = _trace(n_s=0.2)
    _write_dump(tmp_path / "abs.txt", t, aux, slot)
    with pytest.raises(ValueError, match="already has absolute"):
        D.powersensor3_to_csv(tmp_path / "abs.txt", tmp_path / "x.csv", t0=1.0)
    (tmp_path / "other.csv").write_text("timestamp_s,power_w\n0,1\n")
    with pytest.raises(ValueError, match="not a PowerSensor3 dump"):
        D.powersensor3_to_csv(tmp_path / "other.csv", tmp_path / "x.csv")
    (tmp_path / "empty.txt").write_text(HEADER + "\n")
    with pytest.raises(ValueError, match="no samples"):
        D.powersensor3_to_csv(tmp_path / "empty.txt", tmp_path / "x.csv")


def test_dcbus_import_cli_then_dcbus_analyze_reads_the_meter(tmp_path, capsys):
    # A simulated trial, and a PowerSensor3 dump of the same energy with relative times from t = 0 (--t0 0).
    run = tmp_path / "run"
    assert main(["sim-trial", "--profile", "smoke", "--seed", "4", "--out", str(run)]) == 0
    z = np.load(run / "raw.npz")
    t0 = np.concatenate([z["ref_t0"], z["aud_t0"]])
    E = np.concatenate([z["ref_E"], z["aud_E"]])
    tb = np.arange(0, t0[-1] + 20, 0.05)
    idx = np.clip(np.floor(tb - t0[0]).astype(int), 0, len(E) - 1)
    _write_dump(tmp_path / "ps3.txt", tb, E[idx] * 0.8, E[idx] * 0.2, absolute=False)
    capsys.readouterr()
    assert main(["dcbus-import", str(tmp_path / "ps3.txt"), str(tmp_path / "bus.csv")]) == 2        # no --t0
    assert "relative times" in capsys.readouterr().err
    assert main(["dcbus-import", str(tmp_path / "ps3.txt"), str(tmp_path / "bus.csv"), "--t0", "0"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["source"] == "PowerSensor3 dump" and out["rows_in"] == len(tb)
    assert main(["dcbus-analyze", "--run", str(run), "--csv", str(tmp_path / "bus.csv")]) == 0
    mc = json.loads((run / "results_dcbus.json").read_text())["meter_check"]
    assert mc["ok"] and 0.9 < mc["bus_to_nvml_energy_ratio"] < 1.1


class _FakePowerSensor:
    """Stands in for PowerSensor3's pybind11 module: dump(path, True) starts a dump with absolute times."""
    made = []

    def __init__(self, device):
        self.device, self.f = device, None
        _FakePowerSensor.made.append(self)

    def get_name(self, i):
        return ["GPU aux 12V", "PCIe slot 12V", "", ""][i]

    def dump(self, filename, use_absolute_timestamp):
        if filename:
            assert use_absolute_timestamp is True
            self.f = open(filename, "w")
            self.f.write(HEADER + "\n")
            import time
            t = time.time()
            for k in range(2000):                                   # 0.1 s at 20 kHz, written at once
                tk = t + k / 20_000
                self.f.write(f"S {tk:.6f} 50 {k} 25.0 12.0 300.0 3.3 12.0 40.0 340.0\n")
        else:
            self.f.close()
            self.f = None


def test_meter_log_records_with_absolute_times_and_converts(tmp_path, monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "powersensor", types.SimpleNamespace(PowerSensor=_FakePowerSensor))
    dump = tmp_path / "logs" / "bus.ps3.txt"
    assert main(["meter-log", "--device", "/dev/ttyACM9", "--out", str(dump), "--seconds", "0.3"]) == 0
    out = capsys.readouterr().out
    assert "GPU aux 12V" in out and "absolute times" in out and _FakePowerSensor.made[-1].f is None    # closed
    r = json.loads(out[out.index("{"):out.rindex("}") + 1])
    assert r["absolute_times"] and r["rows_in"] == 2000 and abs(r["mean_w"] - 340.0) < 1e-6
    assert (tmp_path / "logs" / "bus.ps3.csv").exists()
    assert main(["meter-log", "--out", str(dump), "--seconds", "0.1"]) == 2              # never appended to


def test_meter_log_without_the_binding_says_how_to_get_it(tmp_path, monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "powersensor", None)                               # import fails
    assert main(["meter-log", "--out", str(tmp_path / "d.txt"), "--seconds", "0.1"]) == 2
    err = capsys.readouterr().err
    assert "PYTHON_BINDINGS=ON" in err and "dcbus-import" in err
