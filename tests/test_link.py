"""Amendment v0.6: the link analysis (link.py), on problems with known answers and on a toy GPU that behaves the way
the T4s in runs 4 and 5 did: power that flattens near its limit, and hidden work that displaces verified work once the
GPU is full."""
import json
from dataclasses import replace

import numpy as np
import pytest

from closure import link as K
from closure.cli import main
from closure.criteria import evaluate
from closure.evidence import Signer
from closure.residual import nnls
from closure.sim import LEVELS, SimConfig, SimSource
from closure.trial import TrialConfig, make_order, run_trial

CAP_W = 70.0
# What run 5's T4 did at each requested load level, unlocked, in a Kaggle container (docs/DEVIATIONS.md section 5):
# units of work a second, share of the second it was busy, and watts. Power is flat from half load up, and a unit of
# work takes longer the fuller the GPU is.
UNITS = np.array([0.0, 10.0, 20.0, 32.0, 70.0, 81.0, 91.0, 93.0])
BUSY = np.array([0.0, 0.112, 0.222, 0.335, 0.572, 0.741, 0.945, 0.991])
WATTS = np.array([33.6, 37.3, 41.1, 45.1, 62.7, 63.5, 65.3, 65.5])


def power(busy):
    """Watts at a busy share: a steep rise to 57% busy, then almost flat under the power limit."""
    return np.interp(busy, BUSY, WATTS)


def duty_for(frac):
    """The hidden duty whose power alone is frac of capacity: the label means what it says."""
    return float(np.interp(WATTS[0] + frac * CAP_W, WATTS, BUSY))


class CappedGpu:
    """One GPU, one-second windows, behaving like that T4. Verified work asks for a load level; hidden work takes its
    duty first and the verified work gets what is left of the second, so on a full GPU the units of verified work drop
    while energy and busy time stay where they were."""

    def __init__(self, seed=0, dt=1.0):
        self.rng, self.dt, self.level, self.hold, self.k = np.random.default_rng(seed), dt, 0.5, 0, 0

    def run_block(self, L, spec=None):
        r = self.rng
        X, E, B, hid, hs, lev, t0 = np.zeros((L, 4)), np.zeros(L), np.zeros(L), np.zeros(L), np.zeros(L), np.zeros(L), np.zeros(L)
        for w in range(L):
            if self.hold <= 0:
                self.level, self.hold = float(r.choice(LEVELS)), int(r.integers(30, 181))
            self.hold -= 1
            self.k += 1
            on = spec is not None and (spec.kind != "duty" or (self.k * self.dt) % spec.period_s < spec.duty * spec.period_s)
            h = duty_for(spec.frac) if on else 0.0
            want = float(np.interp(self.level, LEVELS, BUSY))
            total = min(BUSY[-1], want + h)
            verified = total - h
            units = max(0.0, float(np.interp(verified, BUSY, UNITS)) + 0.5 * r.standard_normal()) if verified > 0 else 0.0
            X[w] = [self.dt, units, units, units]
            E[w] = power(total) * self.dt + 1.5 * r.standard_normal()
            B[w] = total * (1 + 0.01 * r.standard_normal()) * self.dt
            hid[w], hs[w], lev[w], t0[w] = (spec.frac * CAP_W * self.dt if on else 0.0), h * self.dt, self.level, self.k * self.dt
        return {"X": X, "E": E, "busy": B, "hidden_j": hid, "t0": t0, "level": lev, "hidden_s": hs}


CAPPED = dict(status="SIMULATED", L=30, n_ref_blocks=120, n_audit_blocks=160, n_regimes=1, alpha=0.01, n_gpu=1,
              p_max_w=CAP_W, classes=("constant", "duty"), intensities=(0.05, 0.2), schedule="balanced", n_per_cell=10,
              calibration="interleaved", warmup_blocks=1)


def test_exact_solver_agrees_with_the_slow_one_and_never_goes_negative():
    rng = np.random.default_rng(0)
    for trial in range(120):
        n = int(rng.integers(2, 12))
        A = np.abs(rng.standard_normal((300, n)))
        if trial % 3 == 0:
            A[:, -1] = A[:, 0]                                      # a duplicated column, as the hardware features are
        y = A @ np.maximum(rng.standard_normal(n), 0) + 0.1 * rng.standard_normal(300)
        xe, xs = K.nnls_exact(A, y), nnls(A, y)
        assert (xe >= 0).all()
        assert np.sum((A @ xe - y) ** 2) <= np.sum((A @ xs - y) ** 2) * (1 + 1e-9)


def test_curve_follows_a_flattening_power_curve_and_bends_evenly_across_a_gap():
    rng = np.random.default_rng(1)
    i = rng.integers(0, len(UNITS), 6000)                                       # the eight levels: nothing between
    units = np.where(UNITS[i] > 0, UNITS[i] + 0.5 * rng.standard_normal(6000), 0.0).clip(0)      # 32 and 70 units
    X = np.column_stack([np.ones(6000), units, units, units])
    c = K.Curve.fit(X, WATTS[i] + 1.5 * rng.standard_normal(6000))
    at = lambda u: float(c.predict(np.array([[1.0, u, u, u]]))[0])              # noqa: E731
    for u, w in zip(UNITS, WATTS):
        assert at(u) == pytest.approx(w, abs=0.5)
    assert all(at(u + 1) >= at(u) - 1e-9 for u in range(0, 110))                # more work never predicts less
    assert at(40) < at(51) < at(62) and at(32) < at(51) < at(70)                # the gap is crossed without a step
    assert max(at(u + 4) - at(u) for u in range(32, 66)) < 0.6 * (at(70) - at(32))
    line = nnls(X, WATTS[i])
    assert float(np.array([1.0, 70.0, 70.0, 70.0]) @ line) < WATTS[4] - 3.0     # the straight line: 4 W short at half load
    assert 0.05 < c.partial_load_slack() < 0.5 and K.Curve.fit(X, 30 + 0.3 * units).partial_load_slack() < 0.01


def test_straight_line_fails_on_a_capped_gpu_and_the_link_analysis_does_not(tmp_path):
    """Run 5 in miniature. The straight-line analysis is several watts out at half load, so it misses hidden loads
    and its bound does not hold. The link analysis keeps false alarms in check, catches every hidden load of 5% of
    capacity or more, and its floor time bound covers the seconds the hidden load ran. Its energy bound does not
    cover the hidden load's solo energy, and cannot: on a full GPU the hidden load adds no energy (A1 fails), which
    is why H1.4 is read on time."""
    out, cover, energy_cover = {}, [], []
    for analysis in ("linear", "link"):
        fp = det = n_fp = n_det = 0
        for seed in (1, 2, 3):
            cfg = TrialConfig(**{**CAPPED, "analysis": analysis, "seed": seed})
            r = run_trial(CappedGpu(seed), cfg, tmp_path / f"{analysis}{seed}")
            fp, n_fp = fp + r["false_positive"]["combined"]["k"], n_fp + r["false_positive"]["combined"]["n"]
            d = r["detection_at_or_above_fraction"]["0.05"]["pooled_nonslack"]
            det, n_det = det + d["k"], n_det + d["n"]
            if analysis == "link":
                cover.append(r["bound"]["time"]["coverage_floor_bound"])
                energy_cover.append(r["bound"]["coverage_nonslack"])
                ev = evaluate(r, 0.01)
                assert r["methods_used"]["combined"] == ["conformal"] and ev["H1.1"]["holds"]
                assert ev["H1.4"]["basis"] == "time" and ev["H1.4"]["holds"]
                assert r["link"]["partial_load_slack"] > 0.05
            else:
                assert r["methods_used"]["combined"] == ["gaussian"]            # alpha/2 needs 199 reference blocks
                assert evaluate(r, 0.01)["H1.4"]["basis"] == "energy"
        out[analysis] = (fp / n_fp, det / n_det)
    assert out["linear"][1] < 0.9                                               # hidden loads of 5% and more missed
    assert out["link"][0] <= 0.03 and out["link"][1] >= 0.95
    assert min(cover) >= 0.95 and max(energy_cover) < 0.95


def test_interleaved_conformal_threshold_holds_its_level_whatever_the_drift():
    """The claim the link analysis rests on: with reference blocks at random positions through the run, a conformal
    threshold keeps false alarms at alpha for scores that are autocorrelated, trending and jump halfway, because no
    distribution or independence is assumed. Calibrating on the first stretch only does not survive the same data."""
    rng = np.random.default_rng(7)
    cfg = TrialConfig(n_ref_blocks=144, n_audit_blocks=396)
    inter, seq = [], []
    for _ in range(300):
        e, x = rng.standard_normal(540), np.zeros(540)
        for t in range(1, 540):
            x[t] = 0.9 * x[t - 1] + e[t]                                         # strongly autocorrelated
        x = x + np.linspace(0, 3, 540) + 2.0 * (np.arange(540) >= 270)           # a trend and a jump
        ref = np.array(make_order(cfg, rng), bool)
        thr, how = K._upper(x[ref], 0.01, float(ref.sum()))
        assert how == "conformal"
        inter.append(float(np.mean(x[~ref] > thr)))
        seq.append(float(np.mean(x[144:] > K._upper(x[:144], 0.01, 144.0)[0])))
    assert np.mean(inter) <= 0.012
    assert np.mean(seq) > 0.2


def test_audit_bounds_and_small_sample_fallback(tmp_path):
    src = CappedGpu(4)
    ref = [src.run_block(30) for _ in range(40)]
    X = np.concatenate([b["X"] for b in ref])
    ys = {"energy": np.concatenate([b["E"] for b in ref]), "busy": np.concatenate([b["busy"] for b in ref])}
    cal = K.calibrate(X, ys, 30, seed=0, exchangeable_by_design=True)
    a = K.audit(cal, X, ys, 0.01)
    assert a["method"]["combined"].startswith("student-t")                       # 40 blocks: no conformal 1% quantile
    assert (a["ub_floor"]["busy"] >= a["ub"]["busy"] - 1e-9).all()               # the floor never explains more
    assert (a["ub_floor"]["energy"] >= a["ub"]["energy"] - 1e-9).all()
    res = run_trial(CappedGpu(5), TrialConfig(**{**CAPPED, "analysis": "link", "n_ref_blocks": 40, "seed": 5}), tmp_path)
    ev = evaluate(res, 0.01)
    assert not ev["H1.1"]["holds"] and ev["outcome"] == "UNDERPOWERED"           # v0.6: no conformal threshold, no claim
    with pytest.raises(ValueError):
        K.calibrate(X[:240], {k: v[:240] for k, v in ys.items()}, 30)            # 8 blocks cannot be cross-fitted


def test_reanalyze_reproduces_the_registered_analysis_and_labels_any_other_post_hoc(tmp_path, capsys):
    cfg = TrialConfig(**{**CAPPED, "analysis": "linear", "seed": 6})
    res = run_trial(CappedGpu(6), cfg, tmp_path)
    assert main(["reanalyze", "--run", str(tmp_path)]) == 0
    same = json.loads((tmp_path / "results_reanalysis.json").read_text())
    assert not same["reanalysis"]["post_hoc"]
    assert {k: v for k, v in same.items() if k != "reanalysis"} == json.loads((tmp_path / "results.json").read_text())
    capsys.readouterr()
    assert main(["reanalyze", "--run", str(tmp_path), "--analysis", "link"]) == 0
    text = capsys.readouterr().out
    post = json.loads((tmp_path / "results_posthoc_link.json").read_text())
    assert "POST HOC" in post["status"] and post["reanalysis"]["post_hoc"] and "post hoc reading" in text
    assert post["analysis"] == "link" and res["analysis"] == "linear"
    assert json.loads((tmp_path / "results.json").read_text())["analysis"] == "linear"   # the signed results untouched


def test_pool_reads_a_declared_campaign_whole_and_calls_anything_else_post_hoc(tmp_path, capsys):
    runs = []
    for i in (1, 2):
        cfg = TrialConfig(**{**CAPPED, "analysis": "link", "seed": 10 + i,
                             "campaign": {"id": "two-gpus", "index": i, "size": 2}})
        run_trial(CappedGpu(10 + i), cfg, tmp_path / f"t{i}", Signer())
        runs.append(str(tmp_path / f"t{i}"))
    out = tmp_path / "pooled.json"
    assert main(["pool", "--runs", runs[0], "--out", str(out)]) == 2                     # half a campaign: refused
    assert main(["pool", "--runs", *runs, "--out", str(out)]) == 0
    pooled = json.loads(out.read_text())
    each = [json.loads((tmp_path / f"t{i}" / "results.json").read_text()) for i in (1, 2)]
    fp = pooled["false_positive"]["combined"]
    assert fp["n"] == 240 and fp["k"] == sum(r["false_positive"]["combined"]["k"] for r in each)
    assert pooled["pooling"] == {**pooled["pooling"], "declared_beforehand": True, "complete": True}
    assert pooled["status"].startswith("POOLED (campaign 'two-gpus', 2 of 2 trials)")
    assert len(pooled["blocks"]["kind"]) == 320 and "POST HOC" not in pooled["status"]
    assert [t["seed"] for t in pooled["pooling"]["trials"]] == [11, 12]
    assert len({t["schedule_commitment"] for t in pooled["pooling"]["trials"]}) == 2
    capsys.readouterr()
    assert main(["pool", "--runs", runs[0], "--allow-partial", "--out", str(out)]) == 0
    assert "post hoc reading" in capsys.readouterr().out
    other = replace(TrialConfig(**{**CAPPED, "analysis": "link", "seed": 13}), L=20)
    run_trial(CappedGpu(13), other, tmp_path / "t3", Signer())
    assert main(["pool", "--runs", runs[0], str(tmp_path / "t3"), "--out", str(out)]) == 2  # different designs
    sims = []
    for seed in (1, 2):
        sims.append(str(tmp_path / f"sim{seed}"))
        run_trial(SimSource(SimConfig(), seed=seed), TrialConfig(status="SIMULATED", L=30, n_ref_blocks=60, seed=seed,
                                                                 n_audit_blocks=60, n_regimes=1, alpha=0.01), sims[-1],
                  Signer())
    assert main(["pool", "--runs", *sims, "--out", str(out)]) == 0                        # never declared together
    assert "POOLED POST HOC" in json.loads(out.read_text())["status"]


def test_pool_rests_on_verified_trials_and_counts_none_twice(tmp_path, capsys):
    """A pooled reading is only as good as its trials: each must pass `closure verify`, and the same trial given
    twice (which would double its blocks) is refused."""
    runs = []
    for i in (1, 2):
        cfg = TrialConfig(**{**CAPPED, "analysis": "link", "seed": 20 + i,
                             "campaign": {"id": "c", "index": i, "size": 2}})
        run_trial(CappedGpu(20 + i), cfg, tmp_path / f"t{i}", Signer())
        runs.append(tmp_path / f"t{i}")
    out = tmp_path / "pooled.json"
    capsys.readouterr()
    assert main(["pool", "--runs", str(runs[0]), str(runs[0]), "--allow-partial", "--out", str(out)]) == 2
    assert "the same trial" in capsys.readouterr().out
    res = json.loads((runs[1] / "results.json").read_text())
    res["false_positive"]["combined"]["k"] = 0
    res["blocks"]["flag_combined"] = [False] * len(res["blocks"]["flag_combined"])       # a result edited afterwards
    (runs[1] / "results.json").write_text(json.dumps(res))
    assert main(["pool", "--runs", *map(str, runs), "--out", str(out)]) == 2
    assert "fails `closure verify` (results_hash_ok)" in capsys.readouterr().out
    unsigned = tmp_path / "u"
    run_trial(CappedGpu(30), TrialConfig(**{**CAPPED, "analysis": "link", "seed": 30}), unsigned)
    assert main(["pool", "--runs", str(runs[0]), str(unsigned), "--allow-partial", "--out", str(out)]) == 2
    assert "signature_ok" in capsys.readouterr().out and not out.exists()
