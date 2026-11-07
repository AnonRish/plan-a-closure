import math

import numpy as np
import pytest

import assurance_curves as ac
from assurance_curves import RogueDeploymentModel, granularity_table


def test_reproduces_the_supplements_worked_numbers():
    """Appendix / 2034 section: C=1 %, 100 H100e-hour packets, 99 % confidence."""
    m = RogueDeploymentModel(budget=0.01, packet_size=100.0)
    assert m.h100e_hours_to_detect(0.99, model="poisson") == pytest.approx(46051.70185988092, rel=1e-12)  # "~46,000"
    assert m.hours_to_detect(10_000, 0.99, model="poisson") == pytest.approx(4.6052, rel=1e-4)          # "~4.6 hours"
    assert m.hours_to_detect(1_000, 0.99, model="poisson") == pytest.approx(46.052, rel=1e-4)           # "~46 hours"


def test_exact_form_is_about_half_a_percent_faster_at_one_percent_budget():
    m = RogueDeploymentModel(0.01, 100.0)
    exact = m.h100e_hours_to_detect(0.99)
    assert exact == pytest.approx(math.log(0.01) / math.log(0.99) * 100, rel=1e-12)
    assert 0.994 < exact / m.h100e_hours_to_detect(0.99, model="poisson") < 0.996


def test_detection_probability_curve_points():
    m = RogueDeploymentModel(0.01, 100.0)
    assert m.p_detect(10_000, 1) == pytest.approx(1 - 0.99**100, rel=1e-12)      # 63.4 % in one hour
    assert m.p_detect(10_000, 0) == 0.0
    assert m.p_detect(1_000, 168) < m.p_detect(10_000, 168) <= 1.0
    assert math.isinf(m.hours_to_detect(0, 0.99))


def test_recompute_capacity_is_the_hidden_cost():
    m = RogueDeploymentModel(0.01, 100.0)
    cap = m.recompute_capacity_h100e(33e9)
    assert cap == pytest.approx(330e6)
    assert cap > 289e6   # more than the entire 2029 world stock in the supplement (224M+26M+39M)


def test_granularity_table_orders_of_magnitude():
    rows = granularity_table(0.01, 0.99, [10_000], model="poisson")
    by = {r["granularity"]: r["hours_to_detect_10000_h100e"] for r in rows}
    assert by["per-GPU (2034)"] == pytest.approx(4.6052, rel=1e-4)
    assert by["per-shelf (2032)"] == pytest.approx(18.42, rel=1e-3)
    assert by["per-server (2030)"] == pytest.approx(184.2, rel=1e-3)
    assert by["per-server (2030)"] / by["per-GPU (2034)"] == pytest.approx(40.0, rel=1e-9)


def test_model_validation():
    with pytest.raises(ValueError):
        RogueDeploymentModel(0.0, 100.0)
    with pytest.raises(ValueError):
        RogueDeploymentModel(0.01, 0.0)


def test_assurance_curve_identities():
    nv = 10_000.0
    f = np.array([1e-6, 1e-5, 1e-4, 1e-3])
    conf = ac.confidence_for_fraction(nv, f)
    assert conf == pytest.approx(1 - np.exp(-nv * f), rel=1e-12)
    # nines computed directly agree with nines of the confidence
    for fi, ci in zip(f, conf):
        assert ac.nines_for_fraction(nv, fi) == pytest.approx(ac.nines(float(ci)), rel=1e-9)
    assert ac.fraction_for_confidence(nv, conf) == pytest.approx(f, rel=1e-9)
    assert ac.coverage_for_confidence(nv, 0.99) == pytest.approx(1 - math.log(100) / nv)


def test_default_curve_spans_one_percent_to_eight_nines():
    c = ac.assurance_curve(1e6)
    assert c.confidence[0] == pytest.approx(0.00995, abs=1e-4)
    assert c.nines[-1] == pytest.approx(8.0, abs=1e-3)
    assert np.all(np.diff(c.confidence) > 0)
    assert len(c.as_rows()) == len(c.f_star)


def test_more_audits_shift_the_curve():
    f = 1e-4
    assert ac.confidence_for_fraction(100, f) < ac.confidence_for_fraction(1e4, f) < ac.confidence_for_fraction(1e7, f)
