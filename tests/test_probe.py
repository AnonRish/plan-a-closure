import importlib.util
import json
import subprocess
import types

import numpy as np
import pytest

from closure.cli import main
from closure.hw import probe as P
from closure.pause import bridge


def M(power, level, T=10.0, flop=0.0, feasible=True, err=4e-3, busy=0.5, sm=1500.0):
    return {"energy_j": power * T, "time_s": T, "units": 1 if flop else 0, "flop": flop, "level": level,
            "busy_frac": busy, "feasible": feasible, "sm_mhz": sm, "rel_err": err}


def samples_for(spec, levels=(0.0, 0.5), flop_hi=1e12, wiggle=1e-3):
    """spec: name -> dict(kind, idle, hi, err, feasible_hi). Four samples per cell with a tiny alternating wiggle."""
    vs, smp = [], {}
    for name, d in spec.items():
        vs.append(P.Variant(name, d["kind"]))
        for l in levels:
            base = d["idle"] if l == 0.0 else d["hi"]
            smp[(name, l)] = [M(base * (1 + wiggle * (-1) ** i), l, flop=(0.0 if l == 0.0 else flop_hi),
                                feasible=(d.get("feasible_hi", True) or l == 0.0), err=d.get("err", 4e-3)) for i in range(4)]
    return vs, smp


SPEC = {"ref": dict(kind="reference", idle=100, hi=300),
        "A": dict(kind="clock_cap", idle=90, hi=200),                       # real saving, keeps up
        "B": dict(kind="power_cap", idle=100, hi=150, feasible_hi=False),   # cheap but cannot keep up
        "C": dict(kind="precision", idle=100, hi=100, err=0.05),            # cheap but numerically worse: not allowed
        "D": dict(kind="kernel", idle=100, hi=290)}


def test_summarize_counts_only_feasible_allowed_variants_for_slack():
    vs, smp = samples_for(SPEC)
    r = P.summarize(vs, (0.0, 0.5), smp, rel_tol=5e-3)
    by = {v["name"]: v for v in r["variants"]}
    assert by["C"]["allowed"] is False and by["A"]["allowed"] and by["B"]["allowed"]
    assert 1 - 200 / 300 <= r["s_max"] < 0.36               # A at level 0.5; B (infeasible) and C (not allowed) would give > 0.5
    assert r["s_max_at"]["variant"] == "A" and r["s_max_at"]["level"] == 0.5
    assert r["n_allowed_variants"] == 2 and r["h1_6_variants_ok"] is False
    assert any("H1.6 needs at least 3" in n for n in r["notes"])


def test_energy_floor_is_the_lowest_dynamic_joules_per_flop_even_for_infeasible_variants():
    vs, smp = samples_for(SPEC)
    r = P.summarize(vs, (0.0, 0.5), smp, rel_tol=5e-3)
    assert r["e_floor_at"]["variant"] == "B"                # (150-100) W x 10 s / 1e12 FLOP
    assert abs(r["e_floor_j_per_flop"] - 5e-10) < 5e-12
    cell_c = [c for v in r["variants"] if v["name"] == "C" for c in v["levels"] if c["level"] == 0.5][0]
    assert "dynamic_j_per_flop" not in cell_c               # no energy above idle: not a floor candidate


def test_slack_is_an_upper_confidence_bound_so_noise_inflates_it():
    spec = {"ref": dict(kind="reference", idle=100, hi=300), "A": dict(kind="clock_cap", idle=90, hi=200)}
    vs, quiet = samples_for(spec, wiggle=1e-4)
    _, noisy = samples_for(spec, wiggle=5e-2)
    rq = P.summarize(vs, (0.0, 0.5), quiet, 5e-3)
    rn = P.summarize(vs, (0.0, 0.5), noisy, 5e-3)
    cq = [c for c in rq["variants"][1]["levels"] if c["level"] == 0.5][0]
    cn = [c for c in rn["variants"][1]["levels"] if c["level"] == 0.5][0]
    assert cq["saving_upper95"] >= cq["saving_point"] and cn["saving_upper95"] > cn["saving_point"]
    assert rn["s_max"] > rq["s_max"]


def test_run_probe_on_the_fake_rig_measures_three_variants_and_a_floor():
    rig = P.FakeProbeRig(seed=3)
    r = P.run_probe(rig, P.default_variants(), repeats=3, seed=3)
    assert r["h1_6_variants_ok"] and r["n_allowed_variants"] >= 3
    assert 0.0 < r["s_max"] < 1.0 and r["e_floor_j_per_flop"] > 0
    by = {v["name"]: v for v in r["variants"]}
    assert not [c for c in by["clock-510MHz"]["levels"] if c["level"] == 0.9][0]["feasible"]    # cannot keep up at 90% load
    assert [c for c in by["clock-510MHz"]["levels"] if c["level"] == 0.25][0]["feasible"]


def test_a_disallowed_numerics_variant_is_measured_but_never_counted_as_slack():
    vs = P.default_variants(clocks=(), power_caps=(), precisions=("fp8",), kernels=("cublaslt", "other"))
    r = P.run_probe(P.FakeProbeRig(seed=1), vs, repeats=3)
    by = {v["name"]: v for v in r["variants"]}
    assert by["precision-fp8"]["allowed"] is False
    assert r["s_max"] < 0.1                                 # the fp8 variant saves ~40% and must not be counted
    assert r["n_allowed_variants"] == 2 and not r["h1_6_variants_ok"]


def test_unavailable_variants_are_dropped_with_a_note():
    class Flaky(P.FakeProbeRig):
        def measure(self, v, level):
            if v.name == "clock-780MHz":
                raise P.Unavailable("clock not supported")
            return super().measure(v, level)
    r = P.run_probe(Flaky(seed=2), P.default_variants(), repeats=2)
    assert "clock-780MHz" not in [v["name"] for v in r["variants"]]
    assert any("clock-780MHz dropped: clock not supported" in n for n in r["notes"])


def test_run_probe_validates_its_inputs():
    with pytest.raises(ValueError):
        P.run_probe(P.FakeProbeRig(), P.default_variants(), levels=(0.25, 0.5))
    with pytest.raises(ValueError):
        P.run_probe(P.FakeProbeRig(), P.default_variants() + [P.Variant("ref2", "reference")])


def test_seal_detects_any_edit_and_survives_a_json_roundtrip():
    res = P.seal(P.run_probe(P.FakeProbeRig(seed=1), P.default_variants(), repeats=2), "MOCK", {"rig": "fake"})
    assert P.verify_seal(json.loads(json.dumps(res)))
    edited = json.loads(json.dumps(res))
    edited["s_max"] = 0.0
    assert not P.verify_seal(edited)


# ------------------------------------------------------------------ TorchRig control flow on a virtual clock
class VClock:
    def __init__(self):
        self.t, self.e, self.idle_w, self.busy_w = 0.0, 0.0, 100.0, 400.0

    def now(self):
        return self.t

    def sleep(self, s):
        self.t += s
        self.e += self.idle_w * s

    def work(self, s):
        self.t += s
        self.e += (self.idle_w + self.busy_w) * s


class FakeReader:
    """Reports what the (recorded) nvidia-smi calls set, as NVML does on a real GPU."""
    def __init__(self, clk):
        self.clk, self.limit_w, self.clock = clk, 700.0, None

    def energy_j(self):
        return self.clk.e

    def power_limit_w(self):
        return self.limit_w

    def sm_clock_mhz(self):
        return float(self.clock or 1980.0)

    def info(self):
        return {"fake": True}


class VRig(P.TorchRig):
    def __init__(self, clk, unit_s=0.01, **kw):
        self.clk, self.unit_s, self.smi, self.cur = clk, unit_s, [], None
        super().__init__(reader=FakeReader(clk), time_fn=clk.now, sleep_fn=clk.sleep, **kw)

    def _smi(self, *a):
        self.smi.append(a)
        if a[0] == "-lgc":
            self.reader.clock = float(str(a[1]).split(",")[0])
        elif a[0] == "-rgc":
            self.reader.clock = None
        elif a[0] == "-pl":
            self.reader.limit_w = float(a[1])

    def _restore_numerics(self):
        pass

    def _set_blas(self, lib):
        pass

    def apply(self, v):
        self.cur = v
        super().apply(v)

    def _dtype(self, v):
        return "bf16"

    def _tensors(self, v):
        return None, None, None

    def _rel_err(self, v):
        return 1e-3 if v.kind == "precision" else 0.0

    def _unit(self, A, B, big):
        self.clk.work(self.unit_s * (3.0 if self.cur is not None and self.cur.kind == "clock_cap" else 1.0))


def test_torchrig_measure_runs_fixed_work_per_slot_and_flags_variants_that_cannot_keep_up():
    clk = VClock()
    rig = VRig(clk)
    ref = P.Variant("reference", "reference")
    rig.prepare(ref)
    assert abs(rig.t_unit_ref - 0.01) < 1e-9
    idle = rig.measure(ref, 0.0)
    assert idle["units"] == 0 and abs(idle["energy_j"] / idle["time_s"] - 100.0) < 1.0
    half = rig.measure(ref, 0.5)                                  # 5 units per 100 ms slot -> 50% busy
    assert half["feasible"] and abs(half["busy_frac"] - 0.5) < 0.01
    assert abs(half["energy_j"] / half["time_s"] - 300.0) < 3.0   # 100 W idle + 0.5 x 400 W
    assert half["units"] == 5 * int(rig.T / rig.SLOT_S) and half["flop"] == half["units"] * 2 * rig.dim ** 3
    slow = P.Variant("clock-1000MHz", "clock_cap", 1000.0)       # 3x slower per unit
    assert not rig.measure(slow, 0.5)["feasible"]                 # 15 ms x 5 = 150 ms > 100 ms slot
    assert rig.measure(slow, 0.25)["feasible"]
    assert ("-lgc", "1000,1000") in rig.smi and ("-rgc",) in rig.smi and ("-pl", 700) in rig.smi
    r = P.run_probe(rig, [ref, slow, P.Variant("powercap-70pct", "power_cap", 0.7), P.Variant("kernel-x", "kernel", "x")],
                    repeats=2, seed=1)
    assert r["reference"] == "reference" and {v["name"] for v in r["variants"]} == {"reference", "clock-1000MHz",
                                                                                      "powercap-70pct", "kernel-x"}


def test_torchrig_smi_failures_are_classified(monkeypatch):
    from closure.hw import gpu as G
    rig = VRig(VClock())

    def run(rc, err):
        monkeypatch.setattr(G.subprocess, "run", lambda *a, **k: types.SimpleNamespace(returncode=rc, stderr=err, stdout=""))
        return lambda: P.TorchRig._smi(rig, "-lgc", "1000,1000")
    run(0, "")()                                                  # success: nothing raised
    with pytest.raises(P.Unavailable, match="Specified clock"):
        run(1, "Specified clock is not supported")()
    assert rig.control                                            # one unsupported clock does not end device control
    with pytest.raises(P.Unavailable, match="needs root"):        # without root: dropped and noted, the probe goes on
        run(1, "Insufficient Permissions")()
    assert not rig.control
    with pytest.raises(P.Unavailable, match="needs root"):        # and no further nvidia-smi calls are attempted
        P.TorchRig._smi(rig, "-pl", 500)


def test_torchrig_checks_that_clock_locks_and_power_caps_took_effect():
    clk = VClock()
    rig = VRig(clk)
    rig.prepare(P.Variant("reference", "reference"))
    lock = P.Variant("clock-1000MHz", "clock_cap", 1000.0)
    assert rig.measure(lock, 0.25)["sm_mhz"] == 1000.0
    rig.reset()                                                   # unlocked again: the GPU reports its boost clock
    rig._smi = lambda *a: rig.smi.append(a)                      # nvidia-smi says yes and changes nothing (some VMs)
    with pytest.raises(P.Unavailable, match="was not applied"):
        rig.measure(lock, 0.25)
    with pytest.raises(P.Unavailable, match="was not applied"):
        rig.apply(P.Variant("powercap-70pct", "power_cap", 0.7))


# ------------------------------------------------------------------ binding the probe into a trial
def _probe(tmp_path):
    f = tmp_path / "does" / "not" / "exist" / "probe.json"                 # the output directory is created
    assert main(["hw-probe", "--mock", "--out", str(f), "--repeats", "2"]) == 0
    return f


def test_hw_probe_refuses_without_confirmation(tmp_path):
    assert main(["hw-probe", "--out", str(tmp_path / "p.json")]) == 2


def test_probe_flows_into_the_trial_report_the_prereg_and_verify(tmp_path, capsys):
    f = _probe(tmp_path)
    pr = json.loads(f.read_text())
    run = tmp_path / "run"
    assert main(["sim-trial", "--profile", "smoke", "--seed", "4", "--out", str(run), "--probe", str(f)]) == 0
    res = json.loads((run / "results.json").read_text())
    assert res["slack"]["s_max"] == pr["s_max"] and res["hidden_compute_at_gap_per_week"]["energy_floor_j_per_flop"] == pr["e_floor_j_per_flop"]
    assert "hw-probe" in res["slack"]["source"] and pr["sha256"][:16] in res["hidden_compute_at_gap_per_week"]["energy_floor_source"]
    if res["closure_gap_fraction"] is not None:
        g, s = res["closure_gap_fraction"], res["slack"]
        assert abs(s["slack_inflated_gap_fraction"] - (g + s["s_max"] * s["mean_predicted_fraction_of_capacity"])) < 1e-12
        assert s["slack_inflated_gap_fraction"] > g
    assert "slack-inflated gap" in (run / "results.md").read_text() or res["closure_gap_fraction"] is None
    pre = json.loads((run / "prereg.json").read_text())
    assert pre["cfg"]["probe_sha256"] == pr["sha256"] and len(pre["code"]["src_sha256"]) == 64
    capsys.readouterr()
    assert main(["verify", str(run)]) == 0 and '"probe_hash_ok": true' in capsys.readouterr().out
    (run / "probe.json").write_text((run / "probe.json").read_text().replace('"status": "MOCK"', '"status": "MOCK "'))
    assert main(["verify", str(run)]) == 1                        # an edited probe.json no longer matches the pre-registration


def test_a_probe_must_be_sealed_and_a_mock_probe_cannot_feed_a_hardware_trial(tmp_path):
    from closure.cli import _apply_probe
    from closure.trial import TrialConfig
    f = _probe(tmp_path)
    with pytest.raises(SystemExit, match="MOCK|mock"):
        _apply_probe(TrialConfig(), f, tmp_path / "o", hardware=True)
    _apply_probe(TrialConfig(), f, tmp_path / "o2", hardware=False)       # fine for a rehearsal
    bad = json.loads(f.read_text())
    bad["s_max"] = 0.0
    f.write_text(json.dumps(bad))
    with pytest.raises(SystemExit, match="seal"):
        _apply_probe(TrialConfig(), f, tmp_path / "o3", hardware=False)


def test_mock_hw_trial_accepts_a_probe(tmp_path):
    f = _probe(tmp_path)
    assert main(["hw-trial", "--mock", "--profile", "smoke", "--out", str(tmp_path / "r"), "--probe", str(f)]) == 0
    assert main(["verify", str(tmp_path / "r")]) == 0


def test_report_says_plainly_when_slack_was_not_measured(tmp_path):
    assert main(["sim-trial", "--profile", "smoke", "--out", str(tmp_path)]) == 0
    assert json.loads((tmp_path / "results.json").read_text())["slack"]["s_max"] is None
    assert "NOT MEASURED" in (tmp_path / "results.md").read_text()


def test_bridge_charges_the_slack_inflated_gap_when_slack_was_measured():
    base = {"status": "HARDWARE", "closure_gap_fraction": 0.02, "bound": {"coverage_slack_expected_to_fail": 0.4},
            "hidden_compute_at_gap_per_week": {"energy_floor_j_per_flop": 1e-12}}
    plain = bridge.closure_discount(base)
    assert plain["pi_e"] == 0.02 and any("excludes that class" in c for c in plain["caveats"])
    with_slack = bridge.closure_discount({**base, "slack": {"s_max": 0.3, "source": "probe",
                                                            "slack_inflated_gap_fraction": 0.12}})
    assert with_slack["pi_e"] == 0.12 and any("measured efficiency slack" in c for c in with_slack["caveats"])
    assert not any("excludes that class" in c for c in with_slack["caveats"])


@pytest.mark.skipif(importlib.util.find_spec("pynvml") is not None, reason="pynvml is installed here")
def test_missing_hardware_dependency_gives_an_actionable_message_not_a_traceback(capsys):
    assert main(["hw-selftest"]) == 2
    err = capsys.readouterr().err
    assert "pynvml" in err and '.[hw]' in err
