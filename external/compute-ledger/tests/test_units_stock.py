import math

import pytest
from hypothesis import given, settings, strategies as st

from compute_ledger import planA, stock, units


def test_h100e_conversions_round_trip():
    assert units.h100e_from_tpp(15_800) == 1.0
    assert units.tpp_from_h100e(0.25) == 3950.0


@given(st.floats(min_value=1e-3, max_value=1e9, allow_nan=False))
def test_tpp_round_trip(x):
    assert units.h100e_from_tpp(units.tpp_from_h100e(x)) == pytest.approx(x, rel=1e-12)


def test_ai_relevance_matches_the_plans_three_examples():
    d = planA.load()["ai_relevance_floors"]
    chips = {k: units.ChipSpec(**v) for k, v in d["chips"].items()}
    assert units.ai_relevant(chips["A100"]) and units.ai_relevant(chips["H100"])
    assert not units.ai_relevant(chips["RTX 4090"])          # clears compute and bandwidth, fails capacity and NIC
    assert units.failing_floors(chips["RTX 4090"]) == {"tpp": False, "memory_bandwidth": False,
                                                        "memory_capacity": True, "nic": True}


def test_code_constants_equal_the_data_file():
    d = planA.load()
    f = d["ai_relevance_floors"]["floors"]
    assert units.FLOORS == units.ChipSpec(f["tpp"], f["memory_bandwidth_tbps"], f["memory_capacity_gb"], f["nic_gbps"])
    assert units.H100_TPP == d["tpp"]["h100"] and units.AI_FLOOR_TPP == d["tpp"]["ai_floor"]
    assert d["tpp"]["ai_floor"] < d["tpp"]["a100"]           # "set just below an A100"


# ------------------------------------------------------------------------------------------ stock -----------

def test_half_life_is_a_half_life():
    assert stock.roll_forward(100.0, [0.0] * 15, 15)[-1] == pytest.approx(50.0)
    assert stock.survival_factor(None) == 1.0


@settings(max_examples=200, deadline=None)
@given(st.floats(0, 1e9), st.lists(st.floats(0, 1e9), min_size=1, max_size=8), st.floats(1, 40))
def test_roll_forward_equals_the_closed_form(s0, prod, hl):
    f = 2 ** (-1 / hl)
    n = len(prod)
    want = f ** n * s0 + sum(f ** (n - 1 - k) * p for k, p in enumerate(prod))
    assert stock.roll_forward(s0, prod, hl)[-1] == pytest.approx(want, rel=1e-9, abs=1e-6)


@given(st.floats(0, 1e6), st.lists(st.floats(0, 1e6), min_size=1, max_size=6), st.floats(0.5, 1000))
def test_roll_forward_is_linear(s0, prod, k):
    a = stock.roll_forward(s0, prod, 15)
    b = stock.roll_forward(k * s0, [k * p for p in prod], 15)
    assert b[-1] == pytest.approx(k * a[-1], rel=1e-9, abs=1e-9)


def published_series():
    w = planA.load()["world_stock_series"]
    ys = sorted(w["production"])
    return w, [w["production"][y] for y in ys], [w["jan1"][str(int(y) + 1)] for y in ys], w["jan1"][ys[0]]


def test_reproduces_the_published_world_stock_series():
    w, prod, published, s0 = published_series()
    got = stock.roll_forward(s0, prod, w["survival_half_life_years"])
    assert len(got) == 4
    for g, p in zip(got, published):
        assert abs(g - p) < 0.5e6
    assert got[-1] == pytest.approx(289.0e6, abs=0.5e6)


def test_the_published_series_is_not_a_running_sum():
    _, prod, published, s0 = published_series()
    assert stock.roll_forward(s0, prod, None)[-1] - published[-1] > 9e6        # 298.8M against 289.0M


def test_implied_survival_brackets_the_half_life_factor():
    w, prod, published, s0 = published_series()
    opening = [s0] + published[:-1]
    f = stock.survival_factor(w["survival_half_life_years"])
    for s, p, nxt in zip(opening, prod, published):
        assert abs(stock.implied_survival(s, p, nxt) - f) < 0.002


def test_china_follows_a_running_sum_within_rounding():
    c = planA.load()["china"]
    ys = sorted(c["added_per_year"])
    got = stock.roll_forward(c["stock_end_of_year"][ys[0]], [c["added_per_year"][y] for y in ys[1:]], None)
    for g, y in zip(got, ys[1:]):
        assert abs(g - c["stock_end_of_year"][y]) <= 0.15e6


def test_input_validation():
    with pytest.raises(ValueError):
        stock.roll_forward(-1, [1], 15)
    with pytest.raises(ValueError):
        stock.roll_forward(1, [-1], 15)
    with pytest.raises(ValueError):
        stock.survival_factor(0)
    with pytest.raises(ValueError):
        stock.implied_survival(0, 1, 1)
    assert stock.roll_forward(5.0, [], 15) == []
