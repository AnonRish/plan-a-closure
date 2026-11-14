"""How much efficiency slack each rule a regime could adopt leaves (slack_left.py), and the probe's null twin
(amendment v0.8). The reading is arithmetic on the probe's own cells and decides nothing; the published probes are
read in tests/test_runs_on_record.py."""
import json

from closure import slack_left as S
from closure.cli import main
from closure.hw import probe as P


def M(power, level, T=10.0, flop=0.0, err=4e-3):
    return {"energy_j": power * T, "time_s": T, "units": 1 if flop else 0, "flop": flop, "level": level,
            "busy_frac": 0.5, "feasible": True, "sm_mhz": 1500.0, "rel_err": err}


def probe_of(spec, levels=(0.0, 0.5), wiggle=1e-3, rig=None) -> dict:
    """spec: name -> (kind, value, idle watts, watts at load 0.5); four samples per cell with a small wiggle."""
    vs, smp = [], {}
    for name, (kind, value, idle, hi) in spec.items():
        vs.append(P.Variant(name, kind, value))
        for l in levels:
            base = idle if l == 0.0 else hi
            smp[(name, l)] = [M(base * (1 + wiggle * (-1) ** i), l, flop=(0.0 if l == 0.0 else 1e12)) for i in range(4)]
    out = P.summarize(vs, levels, smp, rel_tol=5e-3)
    out["rig"] = rig or {}
    return out


FULL = {"ref": ("reference", None, 100, 300),
        "A": ("clock_cap", 900.0, 99, 240),        # a lower clock: saves about 20% under load
        "D": ("kernel", "cublaslt", 100, 270),     # another BLAS library: about 10%
        "Z": ("operand", "zeros", 100, 180)}       # the same stack on cheap data: about 40%


def rule(rep, key):
    return next(r for r in rep["rules"] if r["rule"] == key)


def test_nothing_fixed_reproduces_s_max_and_each_rule_takes_its_kinds_away():
    pr = probe_of(FULL)
    rep = S.reading(pr)
    assert rep["reproduces_s_max"] is True and rule(rep, "none")["s"] == pr["s_max"]
    assert rule(rep, "none")["at"]["variant"] == "Z"
    for key in ("clocks", "clocks_power", "stack"):          # pinning the stack leaves the data
        assert rule(rep, key)["at"]["variant"] == "Z"
    assert rule(rep, "data")["at"]["variant"] == "A"          # accounting for the data leaves the clocks
    both = rule(rep, "stack_data")
    assert both["nothing_left_in_sweep"] and both["s"] == 0.0 and both["at"] is None
    lines = "\n".join(S.summary_lines(rep))
    assert "nothing left in this sweep (not a measured zero)" in lines and "decides nothing" in lines


def test_a_kind_the_probe_could_not_try_makes_every_rule_that_leaves_it_free_a_lower_bound():
    spec = {**{k: v for k, v in FULL.items() if k != "A"}, "F": ("precision", "fp16", 100, 296)}
    rep = S.reading(probe_of(spec))                                  # no device control: no clock or power variants
    assert rep["kinds_not_measured"] == ["clock_cap", "power_cap"]
    assert rule(rep, "none")["lower_bound"] and rule(rep, "clocks")["lower_bound"]
    assert rule(rep, "data")["free_not_measured"] == ["clock_cap", "power_cap"]
    assert not rule(rep, "clocks_power")["lower_bound"] and not rule(rep, "stack")["lower_bound"]
    assert ">= " in "\n".join(S.summary_lines(rep))


def test_the_under_load_reading_sets_idle_cells_aside():
    spec = {"ref": ("reference", None, 100, 300),
            "F": ("precision", "fp16", 80, 300),      # an idle "saving" a precision cannot make: drift
            "D": ("kernel", "cublaslt", 100, 285)}
    rep = S.reading(probe_of(spec))
    r = rule(rep, "none")
    assert r["at"]["variant"] == "F" and r["at"]["level"] == 0.0
    assert r["at_under_load"]["variant"] == "D" and r["s_under_load"] < r["s"]
    assert r["largest_point_under_load"]["variant"] == "D"


def test_the_slack_inflated_gap_under_each_rule_holds_the_gap_and_load_as_measured():
    pr = probe_of(FULL)
    rep = S.reading(pr, gap=0.0562, load=0.7)
    assert abs(rule(rep, "none")["slack_inflated_gap"] - (0.0562 + pr["s_max"] * 0.7)) < 1e-12
    assert rule(rep, "stack_data")["slack_inflated_gap"] == 0.0562
    assert all("slack_inflated_gap" not in r for r in S.reading(pr)["rules"])


def test_the_null_twin_is_reported_and_never_counted():
    spec = {"ref": ("reference", None, 100, 300),
            "twin": ("null", None, 100, 282),         # the reference again, measured while the GPU drifted: 6%
            "D": ("kernel", "cublaslt", 100, 291),    # 3%
            "Z": ("operand", "zeros", 100, 294)}      # 2%
    pr = probe_of(spec)
    assert pr["s_max_at"]["variant"] == "D" and pr["s_null_at"]["variant"] == "twin"
    assert pr["s_null"] > pr["s_max"] and pr["e_floor_at"]["variant"] != "twin"
    band = pr["declared_band_j_per_flop"]
    assert band["lo_at"]["variant"] != "twin" and band["hi_at"]["variant"] != "twin"
    rep = S.reading(pr)
    t = rep["null_twin"]
    assert t["deliberate"] and not t["counted_in_s_max"] and t["variant"] == "twin"
    assert abs(t["at"]["upper95"] - pr["s_null"]) < 1e-12
    assert all((r["at"] or {}).get("variant") != "twin" for r in rep["rules"])
    assert "the null twin" in "\n".join(S.summary_lines(rep))


def test_an_fp16_variant_on_a_gpu_whose_native_half_is_fp16_is_found_as_an_accidental_twin():
    spec = {"ref": ("reference", None, 100, 300), "F": ("precision", "fp16", 100, 294),
            "T": ("precision", "tf32", 100, 330)}
    t = S.twin(probe_of(spec, rig={"reference_dtype": "float16"}))
    assert t["variant"] == "F" and not t["deliberate"] and t["counted_in_s_max"]
    assert S.twin(probe_of(spec, rig={"reference_dtype": "bfloat16"})) is None


def test_the_cli_probe_runs_the_null_twin_and_keeps_every_measurement(tmp_path):
    f = tmp_path / "p.json"
    assert main(["hw-probe", "--mock", "--out", str(f), "--repeats", "2"]) == 0
    pr = json.loads(f.read_text())
    twin = next(v for v in pr["variants"] if v["name"] == "null-twin")
    assert twin["class"] == "null" and pr["s_null"] is not None and pr["s_max_at"]["variant"] != "null-twin"
    assert all(len(c["power_w"]) == c["n"] == (4 if v["kind"] == "reference" else 2)     # the reference brackets
               for v in pr["variants"] for c in v["levels"])                                 # every round
    g = tmp_path / "q.json"
    assert main(["hw-probe", "--mock", "--out", str(g), "--repeats", "2", "--no-null-twin"]) == 0
    assert json.loads(g.read_text())["s_null"] is None


def test_cli_slack_left_reads_a_sealed_probe_and_a_trial_and_refuses_an_edited_probe(tmp_path, capsys):
    f = tmp_path / "p.json"
    assert main(["hw-probe", "--mock", "--out", str(f), "--repeats", "2"]) == 0
    capsys.readouterr()
    assert main(["slack-left", "--probe", str(f)]) == 0
    out = capsys.readouterr().out
    assert "nothing fixed (the registered s_max)" in out and "null twin" in out
    run = tmp_path / "run"
    assert main(["sim-trial", "--profile", "smoke", "--seed", "4", "--out", str(run), "--probe", str(f)]) == 0
    capsys.readouterr()
    assert main(["slack-left", "--run", str(run), "--json"]) == 0
    rep = json.loads(capsys.readouterr().out)
    assert rep["probe_bound_to_trial"] is True and rep["reproduces_s_max"] is True
    res = json.loads((run / "results.json").read_text())
    if res["closure_gap_fraction"] is not None:
        assert abs(rule(rep, "none")["slack_inflated_gap"] - res["slack"]["slack_inflated_gap_fraction"]) < 1e-12
    bad = json.loads(f.read_text())
    bad["s_max"] = 0.0
    f.write_text(json.dumps(bad))
    assert main(["slack-left", "--probe", str(f)]) == 2
    assert main(["slack-left"]) == 2


def test_the_round_paired_reading_takes_drift_between_rounds_out():
    """A GPU drifting 2% a round: the twin's registered bound is inflated by the drift; paired by round it is zero, and
    a variant that saves 3% in every round is bounded at 3%."""
    levels, rounds, d = (0.0, 0.5), 4, 0.02
    vs = [P.Variant("ref", "reference"), P.Variant("twin", "null"), P.Variant("D", "kernel", "cublaslt")]
    smp = {(v.name, l): [] for v in vs for l in levels}
    for r in range(rounds):
        for l in levels:
            base = (100.0 if l == 0.0 else 300.0) * (1 + d * r)
            fl = 0.0 if l == 0.0 else 1e12
            smp[("ref", l)] += [M(base, l, flop=fl), M(base, l, flop=fl)]       # the brackets of round r
            smp[("twin", l)].append(M(base, l, flop=fl))
            smp[("D", l)].append(M(0.97 * base, l, flop=fl))
    pr = P.summarize(vs, levels, smp, rel_tol=5e-3)
    pa = S.paired(pr)
    assert pa["rounds"] == rounds and pa["s_null_paired"] == 0.0 and pr["s_null"] > 0.03
    assert abs(pa["s_max_paired"] - 0.03) < 1e-9 and pa["at"]["variant"] == "D" and pr["s_max"] > 0.06
    assert "round-paired" in "\n".join(S.summary_lines(S.reading(pr)))
    old = {**pr, "variants": [{**v, "levels": [{k: x for k, x in c.items() if k != "power_w"} for c in v["levels"]]}
                              for v in pr["variants"]]}
    assert S.paired(old) is None                       # probes before v0.8 did not keep per-round powers
