"""Device-adaptive probe settings and the deeper preflight, without a GPU (NVML is faked)."""
import json
import sys
import types

from closure import cli
from closure.hw import probe as P


def test_pick_clocks_uses_only_supported_clocks_spread_down_from_just_below_the_maximum():
    h100 = list(range(1980, 344, -15))                                 # an H100-like ladder of supported SM clocks
    got = P.pick_clocks(h100)
    assert len(got) == 6 and set(got) <= set(h100) and 1980 not in got
    assert got == sorted(got, reverse=True) and got[-1] >= 0.25 * 1980 and got[0] == 1965
    assert P.pick_clocks([1410, 1395, 1380]) == [1395, 1380]           # short ladders are used as they are
    assert P.pick_clocks([]) == [] and P.pick_clocks([1500]) == []
    assert P.pick_clocks(P.FakeProbeRig().supported_clocks()) == list(P.FALLBACK_CLOCKS)


def test_power_caps_are_raised_to_the_settable_minimum():
    assert P.pick_power_caps(700.0, (200.0, 700.0)) == [0.7, 0.5]
    assert P.pick_power_caps(250.0, (150.0, 250.0)) == [0.7, 0.61]    # 0.5 x 250 W is below the 150 W floor
    assert P.pick_power_caps(300.0, (290.0, 300.0)) == []             # no room to cap: no power variants
    assert P.pick_power_caps(700.0, None) == [0.7, 0.5]


def test_hw_probe_records_where_its_clocks_and_caps_came_from(tmp_path):
    f = tmp_path / "p.json"
    assert cli.main(["hw-probe", "--mock", "--out", str(f), "--repeats", "2"]) == 0
    s = json.loads(f.read_text())["settings"]
    assert s["clocks_mhz"] == [float(c) for c in P.FALLBACK_CLOCKS] and "supported clocks" in s["clock_source"]
    assert s["power_caps"] == [0.7, 0.5] and "device minimum" in s["power_cap_source"]
    g = tmp_path / "q.json"
    assert cli.main(["hw-probe", "--mock", "--out", str(g), "--repeats", "2", "--clocks", "1500,900"]) == 0
    assert json.loads(g.read_text())["settings"]["clocks_mhz"] == [1500.0, 900.0]


def _fake_pynvml(mig=0, persistence=1, procs=(), clocks=(1980, 1500, 1005, 510), limits=(200000, 700000)):
    N = types.SimpleNamespace()
    N.nvmlInit = lambda: None
    N.nvmlDeviceGetHandleByIndex = lambda i: "h"
    N.nvmlDeviceGetMigMode = lambda h: (mig, mig)
    N.nvmlDeviceGetPersistenceMode = lambda h: persistence
    N.nvmlDeviceGetComputeRunningProcesses = lambda h: list(procs)
    N.nvmlDeviceGetSupportedMemoryClocks = lambda h: [2619, 1593]
    N.nvmlDeviceGetSupportedGraphicsClocks = lambda h, m: list(clocks)
    N.nvmlDeviceGetPowerManagementLimitConstraints = lambda h: limits
    return N


def test_gpu_readiness_warns_about_mig_persistence_and_shared_gpus(monkeypatch):
    rows = []

    def add(name, status, detail=""):
        rows.append((name, status, detail))
    monkeypatch.setitem(sys.modules, "pynvml", _fake_pynvml())
    cli._gpu_readiness(add)
    by = {n: s for n, s, _ in rows}
    assert by["MIG disabled"] == "PASS" and by["persistence mode on"] == "PASS"
    assert by["supported SM clocks listed"] == "PASS" and by["power-limit range"] == "PASS"
    assert all(s != "FAIL" for _, s, _ in rows)                        # readiness never fails a run, it warns
    rows.clear()
    monkeypatch.setitem(sys.modules, "pynvml", _fake_pynvml(mig=1, persistence=0, procs=[object()], clocks=()))
    cli._gpu_readiness(add)
    by = {n: s for n, s, _ in rows}
    assert by["MIG disabled"] == "WARN" and by["persistence mode on"] == "WARN"
    assert by["no other compute processes on GPU 0"] == "WARN" and by["supported SM clocks listed"] == "WARN"
