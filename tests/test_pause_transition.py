import pytest

from closure.pause import transition as X


def test_phase_classifier():
    assert X.classify_phase(False, False, 0.0) == 0
    assert X.classify_phase(False, True, 0.9) == 0                               # no agreement, no phase
    assert X.classify_phase(True, False, 0.0) == 1
    assert X.classify_phase(True, True, 0.1) == 2
    assert X.classify_phase(True, True, 0.6) == 3
    assert X.classify_phase(True, False, 0.6) == 3                               # most inference already on inference-only chips
    assert X.classify_phase(True, True, 0.5) == 2 and X.classify_phase(True, True, 0.5, majority=0.4) == 3
    assert set(X.PHASES) == {0, 1, 2, 3}


def test_phase_durations():
    assert X.phase1_months(13, 6, 7) == 26 == X.phase1_months(*X.JALAPENO_MONTHS.values())
    assert X.phase2_months(47e6, 2.9e6) == pytest.approx(16.2, abs=0.05)
    assert X.phase2_months_growing(47e6, 2.9e6, 0.0) == X.phase2_months(47e6, 2.9e6)
    n = X.phase2_months_growing(47e6, 2.9e6, 0.02)
    assert n < 16.2                                                              # a rising installation rate shortens it
    assert 2.9e6 * (1.02 ** n - 1) / 0.02 == pytest.approx(47e6, rel=1e-9)       # cumulative installs reach the stock exactly then
    assert X.transition_years(26, 16.2) == pytest.approx(3.5, abs=0.05)          # under five years, as the paper concludes


def test_table_4_1_matches_the_paper():
    months = {name: m for name, m, _ in X.TABLE_4_1}
    assert len(X.TABLE_4_1) == 10 and months["Taalas HC1, new model on existing platform"] == 2
    assert months["Cerebras WSE-1"] == 48 and months["OpenAI Jalapeno"] == 26
    assert {k for _, _, k in X.TABLE_4_1} == {"scratch", "derivative"}
    # a derivative of an existing platform is far faster than a first chip
    scratch = [m for _, m, k in X.TABLE_4_1 if k == "scratch"]
    deriv = [m for _, m, k in X.TABLE_4_1 if k == "derivative"]
    assert sum(deriv) / len(deriv) < sum(scratch) / len(scratch)


def test_license_auction_clears_uniformly():
    bids = [X.Bid("a", 50, 3.0), X.Bid("b", 40, 2.0), X.Bid("c", 30, 1.0)]
    r = X.clear_auction(bids, 80)
    assert r["allocations"] == {"a": 50, "b": 30} and r["clearing_price"] == 2.0           # marginal bidder partly filled
    assert r["licensed"] == 80 and r["unallocated"] == 0
    r2 = X.clear_auction(bids, 200)
    assert r2["licensed"] == 120 and r2["unallocated"] == 80 and r2["clearing_price"] == 1.0
    assert X.clear_auction(bids, 0)["allocations"] == {}
    assert X.clear_auction([X.Bid("a", 10, 1.0), X.Bid("a", 5, 2.0)], 12)["allocations"] == {"a": 12}


def test_cap_schedule_and_trade_in():
    assert X.cap_schedule(100, [10, 20, 30, 100]) == [100, 90, 70, 40]
    assert X.cap_schedule(100, [60, 60, 60])[-1] == 0.0                          # never below zero
    prev, new = {"opA": 60.0, "opB": 40.0}, {"opA": 50.0, "opC": 10.0}
    assert X.trade_in_due(prev, new) == {"opA": 10.0, "opB": 40.0}                # whatever was not won again goes back
    assert X.trade_in_due({"opA": 5.0}, {"opA": 5.0}) == {}


def test_reallocation_and_demand_catch_up():
    assert X.reallocation_gain(0.0) == 1.0 and X.reallocation_gain(0.62) == pytest.approx(2.63, abs=0.01)
    # at ten-fold growth a year, a 2.6x one-off supply gain is used up in about five months
    assert X.demand_catches_up_years(X.reallocation_gain(0.62)) * 12 == pytest.approx(5.0, abs=0.1)
    assert X.demand_catches_up_years(10.0) == pytest.approx(1.0)
