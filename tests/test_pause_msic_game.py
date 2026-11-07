import pytest

from closure.pause import msic_econ as M
from closure.pause import pausegame as G


def test_msic_adoption_rule_and_panel():
    assert M.adopt(0.01, 0.85, 500e9, 10e6) and not M.adopt(1e-5, 0.85, 500e9, 10e6)
    d = M.zipf_demand(315, 1.1)
    assert sum(d) == pytest.approx(1.0) and d == sorted(d, reverse=True)
    cheap, costly = M.panel(d, 0.85, 500e9, 10e6), M.panel(d, 0.85, 500e9, 500e6)
    assert cheap["designs"] > costly["designs"] and cheap["msic_token_share"] > costly["msic_token_share"]
    assert cheap["msic_token_share"] + cheap["flexible_token_share"] == pytest.approx(1.0)
    assert costly["savings_vs_all_flexible"] == pytest.approx(0.85 * costly["msic_token_share"] - costly["designs"] * 500e6 / 500e9)
    assert M.panel(d, 0.85, 2e12, 500e6)["designs"] >= costly["designs"]          # a larger lifetime bill justifies more chips
    assert M.panel(d, 0.60, 500e9, 500e6)["designs"] <= costly["designs"]         # a smaller saving, fewer
    assert M.unserved_share_bound(d, 0.85, 500e9, 500e6) == costly["flexible_token_share"]
    assert M.normalise({"a": 3, "b": 1}) == [0.75, 0.25]


def test_stranded_capital_and_breakeven():
    st = M.stranded_capital(0.5, 0.5, 1.0, 0.85, 0.3, 2e12, 500e6)
    assert st == pytest.approx(45.25e9, rel=1e-3)
    f = M.breakeven_fraction(0.85, 0.3, 2e12, st)
    assert f == pytest.approx(0.0887, abs=1e-3)
    # at the break-even fraction the two ways of serving the model cost the same
    assert f * 0.15 * 0.3 * 2e12 + st == pytest.approx(f * 0.3 * 2e12)
    assert M.stranded_capital(0.0, 0.0, 1.0, 0.85, 0.3, 2e12, 500e6) == 0.0          # nothing installed, nothing stranded


def test_prices_utilisation_and_replacement():
    assert M.savings_from_prices(7.6, 20.2) == pytest.approx(0.624, abs=0.001)
    assert M.savings_from_prices(0.75, 3.63) == pytest.approx(0.793, abs=0.001)
    assert M.utilisation_adjusted_savings(0.85, 1.0) == pytest.approx(0.85)
    assert M.utilisation_adjusted_savings(0.85, 0.5) == pytest.approx(0.70)
    lo = M.replacement_cost_fraction(0.85, 196, 10e6, 500e9)
    hi = M.replacement_cost_fraction(0.85, 60, 500e6, 500e9)
    assert 0.30 < lo < 0.32 and 0.40 < hi < 0.43


def test_total_variation_and_load_demand(tmp_path):
    assert M.total_variation({"a": 0.5, "b": 0.5}, {"a": 0.5, "b": 0.5}) == 0.0
    assert M.total_variation({"a": 1.0, "b": 0.0}, {"a": 0.0, "b": 1.0}) == pytest.approx(1.0)
    # only models in both are compared, renormalised
    assert M.total_variation({"a": 0.5, "b": 0.3, "c": 0.2}, {"a": 0.2, "b": 0.3, "d": 0.5}) == pytest.approx(0.225)
    p = tmp_path / "d.csv"
    p.write_text("model,tokens\nm1,300\nm2,100\nm1,100\nbad,not-a-number\n", encoding="utf-8")
    assert M.load_demand(str(p), "model", "tokens") == {"m1": 400.0, "m2": 100.0}


def test_game_classification_and_equilibria():
    assert G.classify(5, 3, 1, 0) == "prisoners_dilemma" and G.classify(4, 5, 2, 0) == "stag_hunt"
    assert G.classify(5, 3, 0, 1) == "chicken" and G.classify(3, 5, 1, 2) == "harmony"
    assert G.pure_equilibria(5, 3, 1, 0) == [("race", "race")]                    # a dilemma has no pause equilibrium
    assert sorted(G.pure_equilibria(4, 5, 2, 0)) == [("pause", "pause"), ("race", "race")]
    assert sorted(G.pure_equilibria(5, 3, 0, 1)) == [("pause", "race"), ("race", "pause")]


def test_patience_threshold_closed_form_matches_bisection():
    for d in (0.2, 0.5, 0.9, 1.0):
        assert G.patience_threshold(5, 3, 1, d) == pytest.approx(G.threshold_with_detection(5, 3, 1, d), abs=1e-6)
    assert G.grim_threshold(5, 3, 1) == 0.5 == G.threshold_with_detection(5, 3, 1, 1.0)
    assert G.patience_threshold(5, 3, 1, 0.0) is None


def test_monitoring_quality_changes_the_threshold():
    thr = [G.threshold_with_detection(5, 3, 1, d) for d in (0.1, 0.3, 0.6, 1.0)]
    assert thr == sorted(thr, reverse=True)                                       # better detection, less patience needed
    assert G.sustainable(5, 3, 1, 0.8, 0.5) and not G.sustainable(5, 3, 1, 0.4, 0.5)
    assert G.patience_threshold(5, 3, 1, 0.9, 0.1) > G.patience_threshold(5, 3, 1, 0.9, 0.0)      # false alarms raise the bar
    assert G.patience_threshold(5, 3, 1, 0.1, 0.2) is None                        # a signal no likelier after defection: never
    d = G.min_detection(5, 3, 1, 0.8)
    assert G.sustainable(5, 3, 1, 0.8, d + 1e-6) and not G.sustainable(5, 3, 1, 0.8, d - 1e-4)
    assert G.min_detection(5, 3, 1, 0.3) is None                                  # too impatient even with certain detection
    out = G.monitoring_supports_pause((5, 3, 1, 0), 0.8, 0.5)
    assert out["game"] == "prisoners_dilemma" and out["sustainable"] and out["patience_needed"] == pytest.approx(2 / 3, abs=1e-3)
    assert out["detection_needed"] == pytest.approx(G.min_detection(5, 3, 1, 0.8))
