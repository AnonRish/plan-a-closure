import pytest

from closure.pause import bridge as B

FLOOR = 0.5e-12
TAU = 700 / (FLOOR * 989e12)
SYN = {"status": "MEASURED", "closure_gap_fraction": 0.02,
       "hidden_compute_at_gap_per_week": {"energy_floor_j_per_flop": FLOOR},
       "bound": {"coverage_slack_expected_to_fail": 0.1},
       "detection_combined": {"constant": {"0.1": {"k": 19, "n": 20, "rate": 0.95, "cp95_lower": 0.78},
                                           "0.01": {"k": 1, "n": 20, "rate": 0.05, "cp95_lower": 0.001}}}}


def test_closure_discount_from_synthetic_results():
    d = B.closure_discount(SYN)
    assert d["pi_e"] == 0.02 and d["tau_e"] == pytest.approx(TAU) and d["gap"] == 0.02
    assert any("slack" in c for c in d["caveats"]) and not any("SIMULATED" in c for c in d["caveats"])
    assert any("SIMULATED" in c for c in B.closure_discount(dict(SYN, status="SIMULATED"))["caveats"])
    none = B.closure_discount(dict(SYN, closure_gap_fraction=None))
    assert none["pi_e"] == 1.0 and any("no discount" in c for c in none["caveats"])
    assert B.closure_discount(dict(SYN, closure_gap_fraction=3.0))["pi_e"] == 1.0   # a discount never exceeds one
    assert B.closure_discount(SYN, e_floor_j_per_flop=1e-12)["tau_e"] == pytest.approx(TAU / 2)
    assert B.closure_discount({"closure_gap_fraction": 0.02})["e_floor_j_per_flop"] == B.DEFAULT_E_FLOOR_J_PER_FLOP


def test_blended_pi_and_source():
    assert B.blended_pi(0.02, 1.0) == 0.02 and B.blended_pi(0.02, 0.0, 0.001) == 0.001
    assert B.blended_pi(0.02, 0.5, 0.001) == pytest.approx(0.0105)
    src = B.transitional_source(35.2e6, SYN, audit_coverage=0.5)
    assert src.k_e == pytest.approx(35.2e6 * (0.5 * 0.02 * TAU + 0.5 * 0.001))      # audited part at the measured gap
    assert src.k_b == 35.2e6 and src.retires                                         # seizure is charged in full regardless
    assert B.transitional_source(1e6, SYN, 1.0).k_e == pytest.approx(1e6 * 0.02 * TAU)
    assert B.transitional_source(1e6, SYN, 0.0).k_e == pytest.approx(1e6 * 0.001)    # nothing audited: the paper's assumption


def test_detection_at_and_game():
    assert B.detection_at(SYN, 0.1) == 0.78 and B.detection_at(SYN, 0.1, conservative=False) == 0.95
    assert B.detection_at(SYN, 0.5) is None and B.detection_at(SYN, 0.1, "dilute") is None
    ok = B.monitoring_supports_pause(SYN, (5, 3, 1, 0), 0.9, 0.1)
    assert ok["detect"] == 0.78 and ok["sustainable"] is True
    weak = B.monitoring_supports_pause(SYN, (5, 3, 1, 0), 0.9, 0.01)               # detects 0.1% of the time
    assert weak["sustainable"] is False and weak["patience_needed"] > 0.99
    assert B.monitoring_supports_pause(SYN, (5, 3, 1, 0), 0.9, 0.5)["sustainable"] is None


def test_bridge_on_a_real_quick_trial(tmp_path):
    from closure.cli import _cfg
    from closure.sim import SimConfig, SimSource
    from closure.trial import run_trial
    res = run_trial(SimSource(SimConfig(), seed=5), _cfg("quick", 5, "SIMULATED"), tmp_path)
    d = B.closure_discount(res)
    assert 0 < d["pi_e"] <= 1 and d["gap"] == res["closure_gap_fraction"]
    assert any("SIMULATED" in c for c in d["caveats"])
    audited = B.transitional_source(35.2e6, res, 1.0)
    assert audited.k_e == pytest.approx(35.2e6 * d["pi_e"] * d["tau_e"])
    assert B.transitional_source(35.2e6, res, 0.0).k_e == pytest.approx(35.2e6 * 0.001)
