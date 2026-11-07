"""Operand slack and the int8/fp8 energy floor (v0.3.0). The matched-energy attack of Kimpson, Baker and Graham
(arXiv 2610.07476) runs declared work on cheap operands and spends the saved energy on covert int8 work: the probe has to
see both."""
import json
import types

import pytest

from closure.cli import main
from closure.hw import probe as P


def M(power, level, T=10.0, flop=0.0, feasible=True, err=4e-3):
    return {"energy_j": power * T, "time_s": T, "units": 1 if flop else 0, "flop": flop, "level": level,
            "busy_frac": 0.5, "feasible": feasible, "sm_mhz": 1500.0, "rel_err": err}


def samples_for(spec, levels=(0.0, 0.5), flop_hi=1e12, wiggle=1e-3):
    vs, smp = [], {}
    for name, d in spec.items():
        vs.append(P.Variant(name, d["kind"]))
        for l in levels:
            base = d["idle"] if l == 0.0 else d["hi"]
            smp[(name, l)] = [M(base * (1 + wiggle * (-1) ** i), l, flop=(0.0 if l == 0.0 else flop_hi),
                                err=d.get("err", 4e-3)) for i in range(4)]
    return vs, smp


SPEC = {"ref": dict(kind="reference", idle=100, hi=300),
        "A": dict(kind="clock_cap", idle=90, hi=240),               # stack saving 0.20
        "B": dict(kind="power_cap", idle=100, hi=250),              # 0.17
        "D": dict(kind="kernel", idle=100, hi=270),                 # 0.10
        "Z": dict(kind="operand", idle=100, hi=180, err=0.9)}       # same stack, cheap data: 0.40, outputs differ by design


def test_operand_slack_counts_without_the_numerics_gate_and_is_reported_apart_from_stack_slack():
    vs, smp = samples_for(SPEC)
    r = P.summarize(vs, (0.0, 0.5), smp, rel_tol=5e-3)
    by = {v["name"]: v for v in r["variants"]}
    assert by["Z"]["class"] == "operand" and by["Z"]["allowed"] and by["A"]["class"] == "stack"
    assert 0.40 <= r["s_operand"] < 0.41 and 0.20 <= r["s_stack"] < 0.21
    assert r["s_max"] == r["s_operand"] and r["s_max_at"]["variant"] == "Z" and r["s_max_at"]["class"] == "operand"
    assert r["n_allowed_variants"] == 3 and r["n_operand_variants"] == 1 and r["h1_6_variants_ok"]   # H1.6 counts stacks only
    assert not any("operand slack was not measured" in n for n in r["notes"])


def test_operand_variants_never_set_the_floor_but_widen_the_declared_band():
    vs, smp = samples_for(SPEC)
    r = P.summarize(vs, (0.0, 0.5), smp, rel_tol=5e-3)
    # dynamic J/FLOP: ref 2.0e-9, A 1.5e-9, B 1.5e-9, D 1.7e-9, Z 0.8e-9 (cheapest, but data, not covert work)
    assert r["e_floor_at"]["variant"] != "Z" and abs(r["e_floor_j_per_flop"] - 1.5e-9) < 1e-11
    band = r["declared_band_j_per_flop"]
    assert band["lo_at"]["variant"] == "Z" and band["hi_at"]["variant"] == "ref"
    assert abs(r["band_over_floor"] - (2.0e-9 - 0.8e-9) / 1.5e-9) < 0.01


def test_without_operand_variants_the_probe_says_so():
    spec = {k: v for k, v in SPEC.items() if k != "Z"}
    vs, smp = samples_for(spec)
    r = P.summarize(vs, (0.0, 0.5), smp, rel_tol=5e-3)
    assert r["s_operand"] is None and r["s_max"] == r["s_stack"] and r["n_operand_variants"] == 0
    assert any("operand slack was not measured" in n for n in r["notes"])


def test_int8_sets_the_floor_on_the_fake_rig_but_never_counts_as_slack():
    vs = P.default_variants(clocks=(1500,), power_caps=(0.7,), precisions=("fp16", "int8"), kernels=("cublaslt",),
                            operands=("zeros",))
    r = P.run_probe(P.FakeProbeRig(seed=2), vs, repeats=3, seed=2)
    by = {v["name"]: v for v in r["variants"]}
    assert by["precision-int8"]["allowed"] is False and by["operand-zeros"]["allowed"] is True
    assert r["e_floor_at"]["variant"] == "precision-int8"
    assert r["s_max_at"]["variant"] != "precision-int8" and r["s_operand"] is not None


def test_cli_probe_sweeps_operands_int8_and_fp8_by_default(tmp_path):
    f = tmp_path / "p.json"
    assert main(["hw-probe", "--mock", "--out", str(f), "--repeats", "2"]) == 0
    pr = json.loads(f.read_text())
    names = {v["name"] for v in pr["variants"]}
    assert {"operand-sparse90", "operand-lowent", "operand-zeros", "precision-int8", "precision-fp8"} <= names
    assert pr["n_operand_variants"] == 3 and pr["s_max"] >= max(pr["s_stack"], pr["s_operand"])
    assert pr["band_over_floor"] is not None and P.verify_seal(pr)
    g = tmp_path / "q.json"
    assert main(["hw-probe", "--mock", "--out", str(g), "--repeats", "2", "--operands", ""]) == 0
    assert json.loads(g.read_text())["s_operand"] is None


class FakeTorch:
    float32, bfloat16 = "f32", "bf16"

    def __init__(self, int_mm=None, scaled=None, f8=False):
        if int_mm:
            self._int_mm = int_mm
        if scaled:
            self._scaled_mm = scaled
        if f8:
            self.float8_e4m3fn = "f8"
        self.cuda = types.SimpleNamespace(synchronize=lambda dev: None)

    def ones(self, *a, **k):
        return 1.0


def test_low_precision_and_unknown_operand_paths_become_dropped_variants_not_crashes():
    rig = P.TorchRig.__new__(P.TorchRig)                 # no GPU: exercise the dispatch only
    rig.dev, rig.dim, rig.torch = "cuda:0", 64, FakeTorch()
    with pytest.raises(P.Unavailable, match="int8"):
        rig._lowp_mm("int8")
    with pytest.raises(P.Unavailable, match="fp8"):
        rig._lowp_mm("fp8")

    def boom(a, b):
        raise RuntimeError("no kernel image for this GPU")
    rig.torch = FakeTorch(int_mm=boom)
    mm = rig._lowp_mm("int8")
    with pytest.raises(P.Unavailable, match="RuntimeError"):
        rig._run_lowp("int8", lambda: mm(1, 2))
    rig.torch = FakeTorch(scaled=lambda a, b, **k: ("out", "amax"), f8=True)
    assert rig._lowp_mm("fp8")(1, 2) == "out"           # older torch returned (out, amax)
    with pytest.raises(P.Unavailable, match="operand pattern"):
        rig._activations("weird", "bf16")
