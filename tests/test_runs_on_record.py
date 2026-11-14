"""The hardware runs on record (results/), re-read from the bundles as they came back.

Each bundle must be the file whose SHA-256 docs/DEVIATIONS.md gives, pass `closure verify`, and still give, from its
raw data, the numbers the documents quote: the registered analysis as signed; for runs 4 and 5 the post hoc reading
with the link analysis (amendment v0.6), which was chosen after those data were seen and is labelled so; and for runs
6 to 8, the first prospective tests of that amendment, the campaign's pooled reading, run 8's two missed blocks and
what set its threshold, and the post hoc reading with the `link-full` comparison (amendment v0.7).
Counts are allowed to move by a block where a different linear-algebra library could round a borderline score the other
way; `closure tier0` leaves this file out of its unit-test step for the same reason.
"""
import json
from pathlib import Path

import pytest

from closure import physics, tier0
from closure.cli import main
from closure.criteria import evaluate

RESULTS = Path(__file__).resolve().parents[1] / "results"
KAGGLE_67, COLAB_8 = "shakedown-2026-11-11-kaggle-t4-runs6-7", "shakedown-2026-11-12-colab-t4-run8"
RECORD = {                      # name: (folder, trial, the bundle's file name, its browsable copy)
    "run1": ("shakedown-2026-11-08-colab-t4", "T1-smoke", "tier0_bundle.tar.gz", "extracted"),
    "run3": ("shakedown-2026-11-08-colab-t4-run3", "T1-smoke", "tier0_bundle.tar.gz", "extracted"),
    "run4": ("shakedown-2026-11-08-colab-t4-run4", "T1-smoke", "tier0_bundle.tar.gz", "extracted"),
    "run5": ("shakedown-2026-11-08-kaggle-t4-run5", "T1-long", "tier0_bundle.tar.gz", "extracted"),
    "run6": (KAGGLE_67, "T1-long", "gpu0-tier0_bundle.tar.gz", "extracted/gpu0"),
    "run7": (KAGGLE_67, "T1-long", "gpu1-tier0_bundle.tar.gz", "extracted/gpu1"),
    "run8": (COLAB_8, "T1-medium", "tier0_bundle.tar.gz", "extracted"),
}
SHA256 = {
    "run1": "2fd41f34f679dc061b899e89bfce1c9fcdc62fbf2840f89205561fa2ec409a5f",
    "run3": "58a273addfd4419ea39c1fc99a025ed4c21dd0514323ecd2d2311ed2aff0e042",
    "run4": "bdcfcb280770b7abe4b4783989d796a0fabc8a0764978eb357a398fbd124d7c6",
    "run5": "dd7e99973459c74557a4fc5707ebef6f16f54d937bfac564c31a6f300d710a1f",
    "run6": "b0d99770ef90d069555a4acab85d4d08d9db1d5b431f3fd6dc105ca0ba4345d3",
    "run7": "9a136d861ea55ee710a7a93b0249762f70fe1661feeebe9c1ced04e4f96cef05",
    "run8": "3efade48adb610882a635fc18f7644b4fbba4b4a09800e43510d5d445911f569",
}


@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    out = {}
    for name, (folder, trial, tgz, _) in RECORD.items():
        root = tier0.unpack(RESULTS / folder / tgz, tmp_path_factory.mktemp(name), SHA256[name])
        out[name] = root / trial
    return out


@pytest.fixture(scope="module")
def link_full(runs):
    """The `link-full` reading of runs 6 to 8, written beside each unpacked trial. Their pre-registrations (0.8.0) do
    not declare it, so it is POST HOC there."""
    out = {}
    for name in ("run6", "run7", "run8"):
        path = runs[name] / "results_posthoc_link-full.json"
        assert main(["reanalyze", "--run", str(runs[name]), "--analysis", "link-full", "--out", str(path)]) == 0
        out[name] = json.loads(path.read_text())
    return out


def _close(a, b, tol=1e-6):
    if isinstance(a, dict):
        return isinstance(b, dict) and set(a) == set(b) and all(_close(a[k], b[k], tol) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(_close(x, y, tol) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        return a is not None and b is not None and abs(a - b) <= tol * max(1.0, abs(a), abs(b))
    return a == b


def test_every_bundle_is_the_file_that_came_back_and_passes_verify(runs, capsys):
    for name, run in runs.items():
        if name != "run1":                                          # run 1 stopped before its trial (DEVIATIONS 1)
            assert main(["verify", str(run)]) == 0, name
        folder = RESULTS / RECORD[name][0] / RECORD[name][3]
        seen = 0
        for f in folder.rglob("*"):                                 # the browsable copy is the bundle's own files
            if f.is_file():
                assert f.read_bytes() == (run.parent / f.relative_to(folder)).read_bytes(), f
                seen += 1
        assert seen > 5, name
        assert SHA256[name] in (RESULTS / RECORD[name][0] / "README.md").read_text(), name
    assert all(SHA256[name] in (RESULTS.parent / "docs" / "DEVIATIONS.md").read_text() for name in SHA256)


def test_unpack_refuses_a_bundle_with_another_hash(tmp_path):
    with pytest.raises(ValueError, match="is not the bundle"):
        tier0.unpack(RESULTS / RECORD["run5"][0] / "tier0_bundle.tar.gz", tmp_path / "x", "0" * 64)


@pytest.mark.parametrize("name", ["run4", "run5"])
def test_the_registered_analysis_is_reproduced_from_the_raw_data(runs, name, tmp_path, capsys):
    out = tmp_path / "again.json"
    assert main(["reanalyze", "--run", str(runs[name]), "--out", str(out)]) == 0
    signed, again = json.loads((runs[name] / "results.json").read_text()), json.loads(out.read_text())
    assert "POST HOC" not in again["status"] and again["analysis"] == "linear"
    for key, value in signed.items():
        if key == "false_positive":                 # since 0.8.0 the table also counts scheduled loads that never ran
            again[key] = {k: v for k, v in again[key].items() if k != "scheduled_but_never_active"}
        if key == "methods_used":                   # ... and names the method behind the combined test
            assert again[key]["combined"] == ["gaussian"]       # the fallback that 0.7.0 did not report
            again[key] = {k: v for k, v in again[key].items() if k != "combined"}
        assert _close(value, again[key]), key


def test_run5_as_registered_failed_the_false_alarm_rule_at_one_load_level(runs, tmp_path, capsys):
    """Section 5 of docs/DEVIATIONS.md: 11 false alarms in 204 null blocks, every one in a block that spent most of its
    time at requested level 0.5, where the GPU drew about 4 W more than a straight line through the other levels."""
    out = tmp_path / "again.json"
    assert main(["reanalyze", "--run", str(runs["run5"]), "--out", str(out)]) == 0
    res = json.loads(out.read_text())
    fp = res["false_positive"]["combined"]
    assert (fp["k"], fp["n"]) == (11, 204)
    ev = evaluate(res, 0.01)
    assert ev["H1.2"]["holds"] is False and ev["H1.1"]["holds"] is False and ev["outcome"] == "UNDERPOWERED"
    cfg, W, _ = physics.windows(runs["run5"])
    aud = W["src"] == "aud"
    flagged = [b for b, (kind, flag) in enumerate(zip(res["blocks"]["kind"], res["blocks"]["flag_combined"]))
               if kind == "none" and flag]
    assert len(flagged) == 11
    for b in flagged:
        lev = W["lev"][aud & (W["blk"] == b)]
        assert (lev == 0.5).mean() > 0.5, b


def test_run5_physics_power_is_not_a_straight_line_in_work_and_hidden_load_displaces_work(runs):
    rep = physics.report(runs["run5"])
    by = {r["level"]: r for r in rep["by_level"]}
    assert "regenerated" in rep["levels_source"]
    line = by[0.0]["watts"] + (by[1.0]["watts"] - by[0.0]["watts"]) * by[0.5]["units_per_s"] / by[1.0]["units_per_s"]
    assert 3.0 < by[0.5]["watts"] - line < 7.0                      # half load sits well above the straight line
    assert by[0.5]["busy_ms_per_unit"] < 0.85 * by[0.3]["busy_ms_per_unit"]     # ... on a faster clock (not locked)
    solo = {r["label_fraction"]: r for r in rep["hidden_load_on_an_idle_gpu"]}
    assert 1.8 < solo[0.02]["watts_added"] / solo[0.02]["label_watts"] < 2.4    # the 2% label drew about 4%
    assert 1.05 < solo[0.2]["watts_added"] / solo[0.2]["label_watts"] < 1.25
    full = {r["label_fraction"]: r for r in rep["hidden_load_effect"] if r["level"] == 1.0}
    assert abs(full[0.2]["watts_added"]) < 1.0 and full[0.2]["units_per_s_change"] < -25    # displaced, not added


def test_run5_post_hoc_link_reading(runs, tmp_path, capsys):
    out = tmp_path / "link.json"
    assert main(["reanalyze", "--run", str(runs["run5"]), "--analysis", "link", "--out", str(out)]) == 0
    assert "POST HOC reading (link)" in capsys.readouterr().out
    res = json.loads(out.read_text())
    assert "POST HOC" in res["status"] and res["methods_used"]["combined"] == ["conformal"]
    fp = res["false_positive"]["combined"]
    assert fp["n"] == 204 and abs(fp["k"] - 4) <= 1
    d5 = res["detection_at_or_above_fraction"]["0.05"]["pooled_nonslack"]
    d2 = res["detection_at_or_above_fraction"]["0.02"]["pooled_nonslack"]
    assert d5["n"] == 102 and d5["k"] >= 101 and d2["n"] == 145 and d2["k"] >= 141
    ev = evaluate(res, 0.01)
    assert ev["scope"].startswith("post hoc reading") and ev["H1.1"]["holds"] and ev["H1.2"]["holds"]
    # the run did not count hidden seconds (0.8.0 does), so H1.4 is read on energy against labels that understate the
    # load, on a GPU where hidden work near the power limit adds no energy: it fails, as section 5 explains
    assert ev["H1.4"]["basis"] == "energy" and ev["H1.4"]["holds"] is False and ev["outcome"] == "FAIL"
    assert res["bound"]["coverage_floor_bound"] >= 0.99
    assert abs(res["closure_gap_fraction"] - 0.0316) < 1e-3


def test_run4_physics_clocks_locked_time_adds_up_and_the_labels_understate_the_load(runs):
    rep = physics.report(runs["run4"])
    by = {r["level"]: r for r in rep["by_level"]}
    per_unit = [by[lv]["busy_ms_per_unit"] for lv in (0.1, 0.2, 0.3, 0.5, 0.7)]
    assert max(per_unit) / min(per_unit) < 1.06                     # one clock: a unit of work takes the same time
    solo = {r["label_fraction"]: r for r in rep["hidden_load_on_an_idle_gpu"]}
    assert 1.6 < solo[0.2]["watts_added"] / solo[0.2]["label_watts"] < 2.1      # the 20% label drew about 37%
    low = [r for r in rep["hidden_load_effect"] if r["label_fraction"] == 0.2 and r["level"] in (0.0, 0.2, 0.3)]
    assert len(low) == 3 and all(0.33 < r["busy_share_added"] < 0.42 for r in low)   # the same busy time at each


def test_run4_post_hoc_link_reading_is_underpowered(runs, tmp_path, capsys):
    out = tmp_path / "link.json"
    assert main(["reanalyze", "--run", str(runs["run4"]), "--analysis", "link", "--out", str(out)]) == 0
    res = json.loads(out.read_text())
    assert res["methods_used"]["combined"][0].startswith("student-t") and res["link"]["reference_blocks"] == 60
    ev = evaluate(res, 0.01)
    assert ev["H1.1"]["holds"] is False and ev["outcome"] == "UNDERPOWERED" and ev["H1.2"]["holds"] is None
    assert res["false_positive"]["combined"]["n"] == 23 and res["false_positive"]["combined"]["k"] <= 3


# Runs 6 to 8 (0.8.0): the first prospective tests of amendment v0.6. DEVIATIONS sections 6 and 7.

def _rules(res):
    return evaluate(res, 0.01)


def _per_class(level):
    return {c: (v["k"], v["n"], v["holds"]) for c, v in level.items() if c != "pooled_nonslack"}


@pytest.mark.parametrize("name", ["run6", "run7", "run8"])
def test_the_link_analysis_as_signed_is_reproduced_from_the_raw_data(runs, name, tmp_path, capsys):
    out = tmp_path / "again.json"
    assert main(["reanalyze", "--run", str(runs[name]), "--out", str(out)]) == 0
    signed, again = json.loads((runs[name] / "results.json").read_text()), json.loads(out.read_text())
    assert "POST HOC" not in again["status"] and again["analysis"] == "link" and signed["analysis"] == "link"
    assert again["methods_used"]["combined"] == ["conformal"]
    assert "scores" in again and "scores" not in signed            # reported since 0.9.0 (amendment v0.7 (b))
    for key, value in signed.items():
        assert _close(value, again[key], tol=1e-9), key


def test_runs_6_and_7_read_as_the_campaign_they_were_declared_as(runs, tmp_path, capsys):
    """Section 6: every rule the trial decides holds on the pooled campaign, the 2% level included, and the outcome is
    FAIL on the slack-inflated gap alone, as amendment v0.6 said beforehand of a T4."""
    out = tmp_path / "pooled.json"
    assert main(["pool", "--runs", str(runs["run6"]), str(runs["run7"]), "--out", str(out)]) == 0
    pooled, back = json.loads(out.read_text()), json.loads((RESULTS / KAGGLE_67 / "pooled.json").read_text())
    ev, theirs = _rules(pooled), _rules(back)
    assert ev["H1.1"]["holds"] and ev["H1.2"]["holds"] and (ev["H1.2"]["k"], ev["H1.2"]["n"]) == (3, 408)
    assert _per_class(ev["H1.3"]["primary"]) == {"constant": (72, 72, True), "idle_gap": (18, 18, True),
                                                 "duty": (48, 48, True), "dilute": (72, 72, True)}
    assert _per_class(ev["H1.3"]["stretch"]) == {"constant": (92, 96, True), "idle_gap": (26, 26, True),
                                                 "duty": (72, 72, True), "dilute": (95, 96, True)}
    all5 = ev["H1.3"]["primary"]["pooled_nonslack"]
    assert (all5["k"], all5["n"]) == (210, 210) and all5["cp95_lower"] == pytest.approx(0.05 ** (1 / 210), abs=1e-6)
    assert ev["H1.4"]["holds"] and ev["H1.4"]["basis"] == "time" and ev["H1.4"]["time"]["n"] == 321
    assert ev["H1.4"]["coverage_nonslack"] == 1.0                    # the floor time bound covered every hidden block
    assert ev["outcome"] == "FAIL" and "slack-inflated" in ev["why"]
    assert ev["closure_gap_fraction"] == pytest.approx(0.0562, abs=1e-4)
    assert ev["slack_inflated_gap_fraction"] == pytest.approx(0.1226, abs=1e-3)
    for key in ("H1.2", "H1.3", "H1.4", "outcome", "closure_gap_fraction", "slack_inflated_gap_fraction"):
        assert _close(theirs[key], ev[key], tol=1e-9), key           # the reading the Kaggle session wrote itself
    for name, k, n in (("run6", 3, 204), ("run7", 0, 204)):
        fp = json.loads((runs[name] / "results.json").read_text())["false_positive"]["combined"]
        assert (fp["k"], fp["n"]) == (k, n)


def test_a_campaign_is_read_whole_or_not_at_all(runs, tmp_path, capsys):
    assert main(["pool", "--runs", str(runs["run6"]), "--out", str(tmp_path / "half.json")]) != 0
    assert not (tmp_path / "half.json").exists()


def test_run8_failed_h13_by_one_block_in_each_of_two_classes_under_a_threshold_two_blocks_set(runs, tmp_path, capsys):
    """Section 7: no false alarm in 204, and constant 17/18 and dilute 17/18 at 5% or more. The threshold is the
    largest of 150 reference scores; the two largest are more than twice the third, both from blocks in which the
    verifier asked for the GPU flat out nearly throughout."""
    out = tmp_path / "again.json"
    assert main(["reanalyze", "--run", str(runs["run8"]), "--out", str(out)]) == 0
    res = json.loads(out.read_text())
    ev = _rules(res)
    assert ev["H1.1"]["holds"] and ev["H1.2"]["holds"] and (ev["H1.2"]["k"], ev["H1.2"]["n"]) == (0, 204)
    assert _per_class(ev["H1.3"]["primary"]) == {"constant": (17, 18, False), "dilute": (17, 18, False),
                                                 "duty": (9, 9, True), "idle_gap": (0, 0, None)}
    assert ev["H1.4"]["holds"] and ev["H1.4"]["time"]["n"] == 73 and ev["outcome"] == "FAIL"
    sc = res["scores"]
    top = sorted(sc["reference"]["combined"], reverse=True)
    assert len(top) == 150 and sc["threshold"] == pytest.approx(top[0]) and top[0] == pytest.approx(4.73, abs=0.01)
    assert top[1] == pytest.approx(4.39, abs=0.01) and top[2] < 0.4 * top[0]
    kinds, frac, flags = res["blocks"]["kind"], res["blocks"]["hidden_fraction"], res["blocks"]["flag_combined"]
    missed = [b for b, (k, f, hit) in enumerate(zip(kinds, frac, flags)) if k not in ("none", "slack") and f >= 0.05 * (1 - 1e-6) and not hit]
    assert missed == [68, 213] and [kinds[b] for b in missed] == ["constant", "dilute"]
    assert [round(sc["audit"]["combined"][b], 2) for b in missed] == [3.78, 2.78]
    assert max(s_ for s_, k in zip(sc["audit"]["combined"], kinds) if k == "none") < 3.0     # so: no false alarm
    cfg, W, _ = physics.windows(runs["run8"])
    ref = W["src"] == "ref"
    for b in sorted(range(150), key=lambda i: -sc["reference"]["combined"][i])[:2]:
        assert (W["lev"][ref & (W["blk"] == b)] >= 1.0).mean() > 0.9, b


def test_run8_at_full_load_the_power_limit_held_the_gpu_and_the_clock_lock_did_not(runs):
    rep = physics.report(runs["run8"])
    by = {r["level"]: r for r in rep["by_level"]}
    low = [by[lv]["busy_ms_per_unit"] for lv in (0.1, 0.2, 0.3, 0.5, 0.7)]
    assert max(low) / min(low) < 1.03                               # one clock: a unit of work takes one time ...
    assert by[1.0]["busy_ms_per_unit"] > 1.04 * max(low)            # ... until the limiter slows the GPU
    assert 69.0 < by[1.0]["watts"] <= 70.0 and rep["capacity_w"] == pytest.approx(70.0)
    full = {r["label_fraction"]: r for r in rep["hidden_load_effect"] if r["level"] == 1.0}
    assert abs(full[0.2]["watts_added"]) < 1.0 and full[0.2]["units_per_s_change"] < -25     # displaced, not added


@pytest.mark.parametrize("name", ["run6", "run7"])
def test_runs_6_and_7_hidden_work_at_the_power_limit_displaces_verified_work(runs, name):
    rep = physics.report(runs[name])
    by = {r["level"]: r for r in rep["by_level"]}
    full = {r["label_fraction"]: r for r in rep["hidden_load_effect"] if r["level"] == 1.0}
    assert abs(full[0.2]["watts_added"]) < 1.0 and full[0.2]["units_per_s_change"] < -30
    # nearly one rate of verified work at requested levels 0.9 and 1, and two busy times
    assert by[1.0]["units_per_s"] / by[0.9]["units_per_s"] < 1.05
    assert by[0.9]["busy_share"] == pytest.approx(0.935, abs=0.01) and by[1.0]["busy_share"] == pytest.approx(0.989, abs=0.005)


def test_link_full_on_runs_6_to_8_is_post_hoc_and_is_what_the_documents_say(runs, link_full, tmp_path, capsys):
    """The comparison amendment v0.7 declares for later runs, read on the runs that suggested it: labelled POST HOC,
    deciding nothing. Better pooled, and not uniformly better one trial at a time; the documents say both."""
    for name, res in link_full.items():
        assert "POST HOC" in res["status"] and res["analysis"] == "link-full" and res["methods_used"]["combined"] == ["conformal"]
        assert _rules(res)["scope"].startswith("post hoc reading")
    out = tmp_path / "pooled-full.json"
    assert main(["pool", "--runs", str(runs["run6"]), str(runs["run7"]), "--results", "results_posthoc_link-full.json",
                 "--out", str(out)]) == 0
    ev = _rules(json.loads(out.read_text()))
    assert ev["H1.2"]["n"] == 408 and abs(ev["H1.2"]["k"] - 2) <= 1
    p5, p2 = ev["H1.3"]["primary"]["pooled_nonslack"], ev["H1.3"]["stretch"]["pooled_nonslack"]
    assert (p5["k"], p5["n"]) == (210, 210) and p2["n"] == 290 and abs(p2["k"] - 287) <= 1
    assert ev["H1.4"]["holds"] and ev["closure_gap_fraction"] == pytest.approx(0.0316, abs=1e-4)
    assert ev["outcome"] == "FAIL" and ev["slack_inflated_gap_fraction"] > 0.05         # the slack decides, as before
    sd = {name: (json.loads((runs[name] / "results.json").read_text())["link"]["block_residual_sd"]["busy"],
                 res["link"]["block_residual_sd"]["busy"]) for name, res in link_full.items()}
    assert all(after < 0.75 * before for before, after in sd.values()), sd       # the busy-time curve fits closer
    six, seven, eight = (_rules(link_full[n]) for n in ("run6", "run7", "run8"))
    c6 = six["H1.3"]["stretch"]["constant"]
    assert c6["n"] == 48 and c6["k"] <= 46                           # run 6 alone: the 2% constant class slips
    assert seven["H1.4"]["time"]["coverage_nonslack"] < 0.9 and seven["H1.4"]["holds"]  # reported only; the rule holds
    e5 = eight["H1.3"]["primary"]
    assert eight["H1.2"]["k"] == 0 and (e5["pooled_nonslack"]["k"], e5["pooled_nonslack"]["n"]) == (45, 45)
    assert all(v["holds"] is not False for v in e5.values()) and eight["outcome"] == "FAIL"
    assert eight["closure_gap_fraction"] == pytest.approx(0.0562, abs=1e-4)


def test_the_table_of_runs_on_record_is_current_and_says_what_the_bundles_say():
    """results/README.md is generated (`python results/record.py --write`): every cell after the first two columns
    comes from a bundle, so the page a visitor reads first cannot drift from the evidence."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("record", RESULTS / "record.py")
    record = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(record)
    text = record.page()
    assert (RESULTS / "README.md").read_text(encoding="utf-8") == text, "run `python results/record.py --write`"
    rows = {line.split("|")[1].strip(): line for line in text.splitlines() if line.startswith("| ") and "---" not in line}
    assert set(rows) >= {"1", "2", "3", "4", "5", "6", "7", "8", "**6 + 7**"}
    assert "holds: 3/408" in rows["**6 + 7**"] and "holds: 210/210" in rows["**6 + 7**"] and "**FAIL**" in rows["**6 + 7**"]
    assert "**fails**: 43/45" in rows["8"] and "holds: 0/204" in rows["8"] and "**FAIL**" in rows["8"]
    assert "**fails**: 11/204" in rows["5"] and "UNDERPOWERED" in rows["5"]
    assert all(rows[r].count("passes") == 1 for r in "345678") and "PASS" not in text      # no run has passed
    for name, sha in SHA256.items():
        if name != "run2":
            assert sha[:16] in text, name


def test_the_slack_left_page_is_current_and_reproduces_what_each_trial_signed(runs, capsys):
    """results/SLACK_LEFT.md is generated (`python results/slack_left.py --write`) from the same bundles. With nothing
    fixed the reading must give each trial's signed s_max and slack-inflated gap; the page decides nothing."""
    import importlib.util
    from closure.slack_left import reading
    spec = importlib.util.spec_from_file_location("slack_left_page", RESULTS / "slack_left.py")
    page = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(page)
    text = page.page()
    assert (RESULTS / "SLACK_LEFT.md").read_text(encoding="utf-8") == text, "run `python results/slack_left.py --write`"
    assert "It decides nothing" in text and "not a measured zero" in text
    for name in ("run3", "run4", "run5", "run6", "run7", "run8"):
        probe = json.loads((runs[name] / "probe.json").read_text())
        res = json.loads((runs[name] / "results.json").read_text())
        rep = reading(probe, res["closure_gap_fraction"], res["slack"]["mean_predicted_fraction_of_capacity"])
        none, both = rep["rules"][0], rep["rules"][-1]
        assert rep["reproduces_s_max"] and abs(none["slack_inflated_gap"] - res["slack"]["slack_inflated_gap_fraction"]) < 1e-12
        assert both["nothing_left_in_sweep"] and both["slack_inflated_gap"] == res["closure_gap_fraction"]
        assert rep["null_twin"]["variant"] == "precision-fp16" and not rep["null_twin"]["deliberate"]   # a T4's fp16
        assert (rep["kinds_not_measured"] == ["clock_cap", "power_cap"]) == (name in ("run5", "run6", "run7"))
        capsys.readouterr()
        assert main(["slack-left", "--run", str(runs[name])]) == 0
        assert "WARNING" not in capsys.readouterr().out
