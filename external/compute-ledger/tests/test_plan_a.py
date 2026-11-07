import copy

import pytest

from compute_ledger import planA


def by_name(checks):
    return {c.name: c for c in checks}


def test_every_published_figure_is_reproduced_from_its_inputs():
    checks = planA.reproduce()
    assert len(checks) >= 30
    assert [c.name for c in checks if not c.ok] == []


def test_headline_figures():
    c = by_name(planA.reproduce())
    world = c["world stock, Jan 1 2029, from 2025-28 production with a 15-year half-life"]
    assert round(world.computed / 1e6) == 289 and abs(world.computed - 289.0e6) < 0.5e6
    assert [round(c["%s stock from the 85/15 rule" % k].computed / 1e6) for k in ("US", "China", "RoW")] == [224, 26, 39]
    assert [round(c["%s share of world (%%)" % k].computed) for k in ("US", "China", "RoW")] == [77, 9, 14]
    hidden = c["hidden compute: median / world stock (%)"]
    assert round(hidden.computed, 1) == 0.5 and hidden.computed == pytest.approx(100 * 1.5e6 / 289e6)
    assert c["datacenter bins + in-transit + AI consumer = world stock"].computed == pytest.approx(288.9e6, abs=0.1e6)
    assert round(c["share of datacenter compute in sites of 10K H100e or more (%)"].computed) == 99


def test_the_running_sum_convention_is_rejected_by_the_published_series():
    c = by_name(planA.reproduce())["same, as a pure running sum (no retirement)"]
    assert c.expect_match is False and c.ok and abs(c.diff) > 9e6


def mutated(path_edit):
    d = copy.deepcopy(planA.load())
    path_edit(d)
    return planA.reproduce(d)


@pytest.mark.parametrize("name,edit", [
    ("production series", lambda d: d["world_stock_series"]["production"].update({"2028": 169.7e6})),
    ("half-life", lambda d: d["world_stock_series"].update({"survival_half_life_years": 3})),
    ("85/15 split", lambda d: d["owners"].update({"us_share_of_non_china": 0.8})),
    ("a datacenter bin", lambda d: d["locations"]["datacenter_bins"][1].update({"h100e": 100e6})),
    ("hidden median", lambda d: d["hidden_compute"].update({"median_h100e": 3e6})),
    ("China additions", lambda d: d["china"]["added_per_year"].update({"2028": 5e6})),
    ("published world total", lambda d: d["owners"].update({"published_world_total": 300e6})),
    ("TPP floor", lambda d: d["tpp"].update({"ai_floor": 8000})),
])
def test_the_checker_can_fail(name, edit):
    """Negative controls: a tampered input must make at least one check fail, otherwise the checks prove nothing."""
    assert any(not c.ok for c in mutated(edit)), name


def test_data_file_integrity():
    d = planA.load()
    for key, src in d["sources"].items():
        assert src["url"].startswith("https://") and src["status"], key
    for block in ("tpp", "ai_relevance_floors", "world_stock_series", "china", "owners", "locations", "hidden_compute", "uncertainty_2028"):
        assert any(d[block]["source"].startswith(k) for k in d["sources"]), block        # every block names a declared source
    assert sum(d["owners"]["published"].values()) == d["owners"]["published_world_total"]
    assert d["locations"]["share_denominator"] == d["world_stock_series"]["jan1"]["2029"]
    parts = [b["share_pct"] for b in d["locations"]["datacenter_bins"]] + [d["locations"]["in_transit"]["share_pct"], d["locations"]["ai_consumer"]["share_pct"]]
    assert sum(parts) == pytest.approx(100.0, abs=0.3)


def test_printed_precision_rule():
    assert [planA.printed_halfwidth(x) for x in (0.1, 0.32, 12.0, 3.5, 51.4, 0.9)] == pytest.approx([0.05, 0.005, 0.05, 0.05, 0.05, 0.05])
