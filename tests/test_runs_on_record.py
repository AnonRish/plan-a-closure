"""The hardware runs on record (results/), re-read from the bundles as they came back.

Each bundle must be the file whose SHA-256 docs/DEVIATIONS.md gives, pass `closure verify`, and still give, from its
raw data, the numbers the documents quote: the registered analysis as signed, and for runs 4 and 5 the post hoc
reading with the link analysis (amendment v0.6), which was chosen after those data were seen and is labelled so.
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
RECORD = {
    "run1": ("shakedown-2026-11-08-colab-t4", "T1-smoke"),
    "run3": ("shakedown-2026-11-08-colab-t4-run3", "T1-smoke"),
    "run4": ("shakedown-2026-11-08-colab-t4-run4", "T1-smoke"),
    "run5": ("shakedown-2026-11-08-kaggle-t4-run5", "T1-long"),
}
SHA256 = {
    "run1": "2fd41f34f679dc061b899e89bfce1c9fcdc62fbf2840f89205561fa2ec409a5f",
    "run3": "58a273addfd4419ea39c1fc99a025ed4c21dd0514323ecd2d2311ed2aff0e042",
    "run4": "bdcfcb280770b7abe4b4783989d796a0fabc8a0764978eb357a398fbd124d7c6",
    "run5": "dd7e99973459c74557a4fc5707ebef6f16f54d937bfac564c31a6f300d710a1f",
}


@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    out = {}
    for name, (folder, trial) in RECORD.items():
        root = tier0.unpack(RESULTS / folder / "tier0_bundle.tar.gz", tmp_path_factory.mktemp(name), SHA256[name])
        out[name] = root / trial
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
        folder = RESULTS / RECORD[name][0] / "extracted"
        for f in folder.rglob("*"):                                 # the browsable copy is the bundle's own files
            if f.is_file():
                assert f.read_bytes() == (run.parent / f.relative_to(folder)).read_bytes(), f


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
