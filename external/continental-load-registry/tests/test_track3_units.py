import json
from pathlib import Path

import pytest

import track3_units as u

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("name", list(u.SUPPLEMENT_1GW_EXAMPLES))
def test_reproduces_the_supplements_1gw_examples(name):
    ex = u.SUPPLEMENT_1GW_EXAMPLES[name]
    got = u.h100e_from_facility_mw(1000.0, ex["year"], u.DEFAULT_PUE, ex["efficiency_gap"])
    assert got == pytest.approx(ex["stated_h100e"], rel=0.03)  # the supplement rounds to 2 digits


def test_baseline_year_uses_the_baseline_watts():
    assert u.it_watts_per_h100e(2026.0) == 833.0


def test_efficiency_improves_each_year():
    assert u.it_watts_per_h100e(2027.0) == pytest.approx(833.0 / 1.37)


@pytest.mark.parametrize("year,gap,pue", [(2026.5, 1.0, 1.4), (2028.6, 3.7, 1.2)])
def test_facility_conversion_round_trips(year, gap, pue):
    h = u.h100e_from_facility_mw(250.0, year, pue, gap)
    assert u.facility_mw_from_h100e(h, year, pue, gap) == pytest.approx(250.0)


def test_threshold_record_for_the_suppplements_example_t():
    rec = u.threshold_record(30000, 2028.6)
    assert rec["unit"] == "H100e"
    assert rec["it_mw"] == pytest.approx(11.02, abs=0.01)
    assert rec["facility_mw"] == pytest.approx(rec["it_mw"] * 1.4)


@pytest.mark.parametrize("bad", [dict(pue=0.9), dict(efficiency_gap=0.0), dict(efficiency_gap=-1.0)])
def test_invalid_assumptions_are_rejected(bad):
    with pytest.raises(ValueError):
        u.h100e_from_facility_mw(10.0, 2028.0, **bad)


def test_negative_power_is_rejected():
    with pytest.raises(ValueError):
        u.h100e_from_it_mw(-1.0, 2028.0)


def test_data_file_matches_the_module():
    d = json.loads((ROOT / "data/track3/h100e_conversion.json").read_text(encoding="utf-8"))
    assert d["baseline_year"] == u.BASELINE_YEAR
    assert d["us_it_watts_per_h100e_at_baseline"] == u.US_IT_WATTS_PER_H100E_AT_BASELINE
    assert d["us_efficiency_progress_per_year"] == u.US_EFFICIENCY_PROGRESS_PER_YEAR
    assert d["china_domestic_efficiency_gap"] == u.CHINA_DOMESTIC_EFFICIENCY_GAP
    assert d["default_pue"] == u.DEFAULT_PUE
    for name, ex in u.SUPPLEMENT_1GW_EXAMPLES.items():
        assert d["supplement_1gw_examples"][name]["stated_h100e"] == ex["stated_h100e"]
        assert d["supplement_1gw_examples"][name]["computed_h100e"] == round(
            u.h100e_from_facility_mw(1000.0, ex["year"], u.DEFAULT_PUE, ex["efficiency_gap"])
        )
