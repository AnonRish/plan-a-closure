import pytest
from .handoff import evaluate, evaluate_scenario, full_table, breakeven_d_prob, DEFAULTS

# The published 4x3 table, transcribed exactly from the re-fetched source page.
# (alignment_scenario, deal_decline_scenario) -> (net_percent, recommendation)
PUBLISHED_TABLE = {
    ("High confidence alignment solution", "Low risk"): (-0.05, "Delay"),
    ("High confidence alignment solution", "Medium risk"): (0.50, "Hand off"),
    ("High confidence alignment solution", "High risk"): (3.38, "Hand off"),
    ("Alignment probably solved", "Low risk"): (-0.95, "Delay"),
    ("Alignment probably solved", "Medium risk"): (-0.43, "Delay"),
    ("Alignment probably solved", "High risk"): (2.33, "Hand off"),
    ("Alignment likely solved", "Low risk"): (-2.96, "Delay"),
    ("Alignment likely solved", "Medium risk"): (-2.52, "Delay"),
    ("Alignment likely solved", "High risk"): (-0.20, "Delay"),
    ("Alignment clearly unsolved", "Low risk"): (-2.00, "Delay"),
    ("Alignment clearly unsolved", "Medium risk"): (-1.94, "Delay"),
    ("Alignment clearly unsolved", "High risk"): (-1.65, "Delay"),
}


@pytest.mark.parametrize("scenario_key,expected", list(PUBLISHED_TABLE.items()))
def test_matches_published_table_exactly(scenario_key, expected):
    a_name, d_name = scenario_key
    expected_pct, expected_rec = expected
    result = evaluate_scenario(a_name, d_name)
    assert result.net * 100 == pytest.approx(expected_pct, abs=0.01)
    assert result.recommendation == expected_rec


def test_full_table_covers_all_twelve_published_cells():
    table = full_table()
    count = sum(len(row) for row in table.values())
    assert count == 12
    assert count == len(PUBLISHED_TABLE)


def test_worked_example_from_the_page_defaults():
    """d_prob=3%, a_prob=99.5%, d_loss=20%, a_change=0.1% ->
    benefit 0.60%, cost 0.10%, net +0.50%, 'Hand off now (weak)' on the page."""
    r = evaluate(**DEFAULTS)
    assert r.benefit_of_handoff * 100 == pytest.approx(0.60, abs=0.01)
    assert r.cost_of_handoff * 100 == pytest.approx(0.10, abs=0.01)
    assert r.net * 100 == pytest.approx(0.50, abs=0.01)
    assert r.recommendation == "Hand off"


def test_recommendation_sign_matches_net_sign():
    r_pos = evaluate(d_prob=0.5, a_prob=0.9, d_loss=0.5, a_change=0.01)
    r_neg = evaluate(d_prob=0.001, a_prob=0.9, d_loss=0.1, a_change=0.5)
    assert r_pos.recommendation == "Hand off"
    assert r_neg.recommendation == "Delay"


def test_higher_deal_decline_probability_pushes_toward_handoff():
    low = evaluate(d_prob=0.01, a_prob=0.9, d_loss=0.2, a_change=0.01)
    high = evaluate(d_prob=0.20, a_prob=0.9, d_loss=0.2, a_change=0.01)
    assert high.net > low.net


def test_higher_alignment_gain_pushes_toward_delay():
    low_gain = evaluate(d_prob=0.05, a_prob=0.9, d_loss=0.2, a_change=0.005)
    high_gain = evaluate(d_prob=0.05, a_prob=0.9, d_loss=0.2, a_change=0.05)
    assert high_gain.net < low_gain.net


def test_breakeven_reproduces_zero_net():
    a_prob, d_loss, a_change = 0.90, 0.25, 0.015
    d_star = breakeven_d_prob(a_prob, d_loss, a_change)
    r = evaluate(d_prob=d_star, a_prob=a_prob, d_loss=d_loss, a_change=a_change)
    assert r.net == pytest.approx(0.0, abs=1e-12)


def test_breakeven_matches_default_scenario_direction():
    """At the page's own defaults (net = +0.50%, i.e. already past breakeven),
    the breakeven d_prob should be LOWER than the actual default d_prob --
    confirming the defaults already clear the threshold, consistent with the
    page's own 'Hand off now' recommendation at those settings."""
    d_star = breakeven_d_prob(DEFAULTS["a_prob"], DEFAULTS["d_loss"], DEFAULTS["a_change"])
    assert d_star < DEFAULTS["d_prob"]
