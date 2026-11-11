"""Amendment v0.5: the balanced schedule, interleaved calibration, warm-up blocks, the corrected busy-time figure and the
pre-registered decision rules (criteria.py), on the simulator."""
import json
from collections import Counter
from dataclasses import replace

import numpy as np
import pytest

from closure.cli import PROFILES, _cfg, main
from closure.criteria import evaluate, summary_lines
from closure.evidence import Signer, verify_commit
from closure.sim import SimConfig, SimSource
from closure.trial import TrialConfig, make_order, make_schedule, run_trial

SMALL = dict(status="SIMULATED", L=30, n_ref_blocks=60, n_audit_blocks=120, n_regimes=1, alpha=0.01,
             classes=("constant", "duty"), intensities=(0.05, 0.2), schedule="balanced", n_per_cell=10)


class Step:
    """The simulator with a power offset that switches on halfway through the run: a GPU whose cooling changes."""

    def __init__(self, src, watts, at_block):
        self.src, self.w, self.at, self.k = src, watts, at_block, 0

    def run_block(self, L, spec=None):
        b = dict(self.src.run_block(L, spec))
        if self.k >= self.at:
            b["E"] = b["E"] + self.w * self.src.cfg.dt
        self.k += 1
        return b


class Dies:
    """The simulator until a time limit's SIGTERM arrives, which hw/gpu.py's stop handlers turn into SystemExit."""

    def __init__(self, src, after):
        self.src, self.after, self.k = src, after, 0

    def run_block(self, L, spec=None):
        if self.k >= self.after:
            raise SystemExit(143)
        self.k += 1
        return self.src.run_block(L, spec)


def test_balanced_schedule_fills_every_cell_exactly_in_random_order():
    cfg = TrialConfig(**SMALL)
    s = make_schedule(cfg, np.random.default_rng(0))
    cells = Counter((x["kind"], x["frac"]) for x in s if x is not None)
    assert len(s) == 120 and set(cells.values()) == {10} and len(cells) == 4 and s.count(None) == 80
    assert s != sorted(s, key=lambda x: (x is None, str(x)))                           # shuffled, not grouped
    assert make_schedule(cfg, np.random.default_rng(0)) == s                           # deterministic given the seed
    with pytest.raises(ValueError):
        make_schedule(replace(cfg, n_per_cell=31), np.random.default_rng(0))           # 4 x 31 > 120


def test_long_profile_has_enough_null_blocks_for_h1_2_and_twelve_per_cell():
    cfg = _cfg("long", 1, "SIMULATED")
    s = make_schedule(cfg, np.random.default_rng(1))
    assert s.count(None) == 204 >= 200
    assert set(Counter((x["kind"], x["frac"]) for x in s if x).values()) == {12}
    blocks = cfg.warmup_blocks + cfg.n_ref_blocks + cfg.n_audit_blocks
    assert 8.5 <= blocks * cfg.L * cfg.dt / 3600 <= 9.5                              # fits a 12-hour session
    for name in ("smoke", "medium", "long", "hw-short", "hw-full", "rehearsal"):       # v0.6: every hardware profile
        p = PROFILES[name]
        assert (p["calibration"], p["schedule"], p["analysis"]) == ("interleaved", "balanced", "link")
        assert name == "rehearsal" or p["n_ref_blocks"] >= 99                         # a conformal threshold at 0.01


def test_medium_profile_is_the_smallest_that_can_decide_the_rules_and_fits_a_colab_session():
    cfg = _cfg("medium", 1, "SIMULATED")
    s = make_schedule(cfg, np.random.default_rng(1))
    assert s.count(None) == 204 >= 200                                               # H1.2 needs 200 null blocks
    cells = Counter((x["kind"], x["frac"]) for x in s if x)
    assert set(cells.values()) == {6} and len(cells) == 16
    for kind in cfg.classes:                                                         # H1.3 primary, per class: 8 or more
        assert sum(n for (k, f), n in cells.items() if k == kind and f >= 0.05) == 18
    blocks = cfg.warmup_blocks + cfg.n_ref_blocks + cfg.n_audit_blocks
    assert blocks * cfg.L * cfg.dt / 3600 < 4.0 and cfg.n_ref_blocks >= 99


def test_interleaved_order_puts_one_reference_block_in_each_stretch():
    cfg = TrialConfig(**SMALL)
    o = make_order(cfg, np.random.default_rng(2))
    assert len(o) == 180 and sum(o) == 60
    assert all(sum(o[3 * j:3 * j + 3]) == 1 for j in range(60))                         # 180 / 60 = 3 per stretch
    odd = TrialConfig(**{**SMALL, "n_ref_blocks": 7, "n_audit_blocks": 23})            # stretches of 4 or 5
    oo = make_order(odd, np.random.default_rng(3))
    cuts = [(j * 30) // 7 for j in range(8)]
    assert sum(oo) == 7 and all(sum(oo[cuts[j]:cuts[j + 1]]) == 1 for j in range(7))


def test_interleaved_trial_commits_everything_before_any_data_and_verifies(tmp_path):
    cfg = TrialConfig(**{**SMALL, "calibration": "interleaved", "warmup_blocks": 2, "seed": 4})
    run_trial(SimSource(SimConfig(), seed=4), cfg, tmp_path, Signer())
    phases = [json.loads(l)["record"]["phase"] for l in open(tmp_path / "chain.jsonl")]
    assert phases == ["prereg", "audit_data", "calibration", "results"]
    pre = json.loads((tmp_path / "prereg.json").read_text())
    assert "order_commitment" in pre and "calibration_head" not in pre
    assert main(["verify", str(tmp_path)]) == 0
    z = np.load(tmp_path / "raw.npz")
    assert len(z["ref_E"]) == 60 * 30 and len(z["aud_E"]) == 120 * 30 and len(z["warm_E"]) == 2 * 30
    t_ref, t_aud = z["ref_t0"][::30], z["aud_t0"][::30]
    assert t_ref.min() < t_aud.min() + 3 * 30 and t_ref.max() > t_aud.max() - 3 * 30   # calibration spans the run
    rev = json.loads((tmp_path / "schedule_reveal.json").read_text())
    rev["order"] = rev["order"][1:] + rev["order"][:1]                                 # claim other reference blocks
    (tmp_path / "schedule_reveal.json").write_text(json.dumps(rev))
    assert main(["verify", str(tmp_path)]) == 1


def test_interleaving_keeps_false_alarms_in_check_when_the_gpu_changes_halfway(tmp_path):
    """Sequential calibration sees only the first part of the run, so a step change in power floods the audit with
    energy false alarms; with interleaved calibration the same step reaches reference and audit blocks alike (it widens
    the null instead, and the autocorrelation it causes shrinks n_eff, which H1.1 then reports)."""
    fpr, neff = {}, {}
    for cal in ("sequential", "interleaved"):
        for seed in (5, 12):
            cfg = TrialConfig(**{**SMALL, "calibration": cal, "seed": seed})
            res = run_trial(Step(SimSource(SimConfig(), seed=seed), 900.0, 90), cfg, tmp_path / f"{cal}{seed}")
            fpr[cal, seed] = res["false_positive"]["energy"]["rate"]
            neff[cal, seed] = res["calibration_n_eff"]["energy"][0]
    assert all(fpr["sequential", s] > 0.5 for s in (5, 12))
    assert all(fpr["interleaved", s] <= 3 * 0.01 for s in (5, 12))
    assert all(neff["interleaved", s] < 15 for s in (5, 12))


def test_busy_figure_is_a_fraction_of_capacity_time_not_energy(tmp_path):
    cfg = TrialConfig(**{**SMALL, "seed": 6})
    res = run_trial(SimSource(SimConfig(), seed=6), cfg, tmp_path)
    md = res["min_detectable_fraction_per_regime"]
    from closure import residual as R
    from closure.trial import collect, fit_channels
    calE, calB = fit_channels(collect(SimSource(SimConfig(), seed=6), cfg, cfg.n_ref_blocks), cfg)
    # busy time is the mean utilisation over the GPUs times the seconds, so a block holds at most L x dt of it
    assert md["busy"][0] == pytest.approx(R.min_detectable(calB, 0, cfg.alpha, cfg.beta) / (cfg.L * cfg.dt))
    assert md["energy"][0] == pytest.approx(
        R.min_detectable(calE, 0, cfg.alpha, cfg.beta) / (cfg.n_gpu * cfg.p_max_w * cfg.L * cfg.dt))


def _res(**over):
    """A results.json-shaped dict that passes every rule; override parts to break one."""
    det = {"k": 100, "n": 100, "rate": 1.0, "cp95_lower": 0.9705}
    r = {"status": "HARDWARE (NVML energy counter; spoofable)",
         "normality_p": {"energy": [0.4], "busy": [0.3]}, "calibration_n_eff": {"energy": [40.0], "busy": [30.0]},
         "false_positive": {"combined": {"k": 2, "n": 204, "rate": 2 / 204, "cp95_upper": 0.034}},
         "detection_at_or_above_fraction": {t: {"constant": dict(det), "pooled_nonslack": dict(det)}
                                            for t in ("0.05", "0.02")},
         "bound": {"coverage_nonslack": 0.99}, "closure_gap_fraction": 0.0316,
         "slack": {"s_max": 0.01, "slack_inflated_gap_fraction": 0.04}}
    r.update(over)
    return r


def test_decision_rules_follow_the_preregistration():
    ev = evaluate(_res(), 0.01)
    assert ev["outcome"] == "PASS-primary" and ev["H1.1"]["holds"] and ev["H1.2"]["holds"] and ev["H1.4"]["holds"]
    assert "shakedown" in ev["scope"] and ev["H1.3"]["primary"]["pooled_nonslack"]["certified"]
    assert evaluate(_res(slack={"s_max": 0.0, "slack_inflated_gap_fraction": 0.0178}), 0.01)["outcome"] == "PASS-stretch"
    smoke = evaluate(_res(false_positive={"combined": {"k": 3, "n": 23, "rate": 3 / 23, "cp95_upper": 0.30}}), 0.01)
    assert smoke["outcome"] == "NOT DECIDED" and smoke["H1.2"]["holds"] is None and "23 null" in smoke["why"]
    many = evaluate(_res(false_positive={"combined": {"k": 7, "n": 204, "rate": 7 / 204, "cp95_upper": 0.06}}), 0.01)
    assert many["outcome"] == "FAIL" and many["H1.2"]["holds"] is False
    skew = evaluate(_res(normality_p={"energy": [3e-12], "busy": [0.42]}), 0.01)
    assert skew["outcome"] == "UNDERPOWERED"
    assert evaluate(_res(slack={"s_max": None, "slack_inflated_gap_fraction": None}), 0.01)["outcome"] == "NOT DECIDED"
    assert evaluate(_res(closure_gap_fraction=None), 0.01)["outcome"] == "FAIL"
    few = _res()
    few["detection_at_or_above_fraction"]["0.05"]["constant"] = {"k": 6, "n": 6, "rate": 1.0, "cp95_lower": 0.61}
    assert evaluate(few, 0.01)["H1.3"]["primary"]["constant"]["holds"] is None             # fewer than 8 blocks
    text = "\n".join(summary_lines(evaluate(_res(), 0.01)))
    assert "PASS-primary" in text and "certified at 95%" in text and "100/100" in text


def test_run_3_reads_as_underpowered_and_too_small():
    from pathlib import Path
    run3 = Path(__file__).resolve().parents[1] / "results" / "shakedown-2026-11-08-colab-t4-run3" / "extracted"
    ev = evaluate(json.loads((run3 / "T1-smoke" / "results.json").read_text()), 0.01)
    assert ev["outcome"] == "UNDERPOWERED" and ev["H1.2"]["holds"] is None and ev["H1.3"] is None
    assert any("not computed" in x for x in summary_lines(ev))


def test_criteria_command_reads_a_trial_folder(tmp_path, capsys):
    run_trial(SimSource(SimConfig(), seed=7), TrialConfig(**{**SMALL, "seed": 7}), tmp_path)
    capsys.readouterr()
    assert main(["criteria", "--run", str(tmp_path)]) == 0
    assert "H1.2 false alarms" in capsys.readouterr().out
    assert main(["criteria", "--run", str(tmp_path), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["H1.2"]["holds"] is None                    # 80 null blocks < 200


def test_a_stopped_trial_keeps_its_finished_blocks_and_reveals_the_schedule(tmp_path):
    from closure.tier0 import summary
    cfg = TrialConfig(**{**SMALL, "calibration": "interleaved", "warmup_blocks": 2, "seed": 8})
    run = tmp_path / "T1-long"
    with pytest.raises(SystemExit):
        run_trial(Dies(SimSource(SimConfig(), seed=8), 2 + 100), cfg, run, Signer())
    assert not (run / "results.json").exists() and not (run / "raw.npz").exists()
    z = np.load(run / "raw_partial.npz")
    n_ref, n_aud = len(z["ref_E"]) // 30, len(z["aud_E"]) // 30
    assert len(z["warm_E"]) == 2 * 30 and n_ref + n_aud == 100
    rev = json.loads((run / "schedule_reveal.json").read_text())
    pre = json.loads((run / "prereg.json").read_text())
    assert verify_commit(rev["order"], pre["order_commitment"], rev["order_nonce"])
    assert verify_commit(rev["schedule"], pre["schedule_commitment"], rev["nonce"])
    assert sum(rev["order"][:100]) == n_ref                          # the finished blocks follow the committed order
    rec = [json.loads(line)["record"] for line in open(run / "chain.jsonl")][-1]
    assert rec["phase"] == "interrupted" and rec["blocks"] == {"warm": 2, "ref": n_ref, "aud": n_aud}
    text = summary(tmp_path, [], True, "start", "hw-trial", trial="T1-long")
    assert "stopped before its data were complete (SystemExit: 143)" in text and "raw_partial.npz" in text

    seq = tmp_path / "seq"                                             # sequential: stopped during the audit
    with pytest.raises(SystemExit):
        run_trial(Dies(SimSource(SimConfig(), seed=9), 60 + 25), TrialConfig(**{**SMALL, "seed": 9}), seq)
    z = np.load(seq / "raw_partial.npz")
    assert len(z["ref_E"]) == 60 * 30 and len(z["aud_E"]) == 25 * 30 and "warm_E" not in z
