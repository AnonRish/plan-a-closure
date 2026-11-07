import math

import pytest

from closure.pause import thresholds as T
from closure.pause.units import H100E_FLOP_PER_YEAR, H100E_FLOPS, h100e, h100e_years, oom, sig


def test_table_3_1_values_at_full_precision():
    t = T.treaty_thresholds()
    # reference values from the paper's calculation supplement, carried unrounded
    assert t["F_E"] == pytest.approx(6_387_820, abs=2)
    assert t["F_B"] == pytest.approx(175_665_057, abs=5)
    assert t["F_P"] == pytest.approx(148_400, rel=0.002)
    for k, printed in T.TABLE_3_1_PRINTED.items():
        assert t[k] == pytest.approx(printed, rel=0.03), k
    assert sig(t["F_E"]) == 6.4e6 and sig(t["N_T"]) == 1.3e10 and sig(t["F_B"]) == 1.8e8


def test_h100e_constants():
    assert H100E_FLOP_PER_YEAR == pytest.approx(3.1e22, rel=0.01)
    assert h100e(H100E_FLOPS) == 1.0 and h100e(2.5 * H100E_FLOPS) == 2.5
    assert h100e_years(H100E_FLOP_PER_YEAR) == pytest.approx(1.0) and oom(1000.0) == pytest.approx(3.0)
    assert sig(1_757_000, 2) == 1_800_000 and sig(0.012345, 3) == 0.0123


def test_utilization_is_harmonic():
    assert T.blended_utilization(0.4, 0.4, 0.125) == pytest.approx(1 / (0.6 / 0.4 + 0.4 / 0.125))
    assert T.blended_utilization(0.0, 0.4, 0.125) == pytest.approx(0.4)
    assert T.blended_utilization(1.0, 0.4, 0.125) == pytest.approx(0.125)


def test_fleet_threshold_scaling_laws():
    p = T.ThresholdParams()
    assert T.overt_breakout_fleet(p.with_(t_b=4.0)) == pytest.approx(T.overt_breakout_fleet(p) / 2)
    assert T.covert_evasion_fleet(p.with_(t_e=10.0)) == pytest.approx(T.covert_evasion_fleet(p) / 2)
    # utilisation enters inversely
    assert T.fleet_h100e(5.0, 1e28, 2.0, 0.25) == pytest.approx(2 * T.fleet_h100e(5.0, 1e28, 2.0, 0.5))
    # a larger frozen frontier scales the covert fleet linearly (beta_E is fixed)
    assert T.covert_evasion_fleet(p.with_(c_f=4e27)) == pytest.approx(2 * T.covert_evasion_fleet(p))


def test_blind_leap_overhead_closed_form_matches_geometric_sum():
    rho_f, delta = 6.3, 1 / 3
    for beta in (10.0, 100.0, 1000.0):
        n = round(math.log10(beta) / delta)
        total = sum(rho_f * beta ** (i / n) for i in range(1, n + 1)) / beta     # overhead of the whole programme
        assert T.research_overhead(beta, rho_f, delta) == pytest.approx(total)
    assert T.blind_factor(0.5) == 1.0 and T.blind_factor(1.0) == 1.0           # at or below the frontier there is no ladder
    assert T.blind_steps(100.0) == pytest.approx(6.0) and T.blind_steps(1.5) == 1.0


def test_chinchilla_mapping_roundtrip():
    assert T.params_for_compute(T.compute_for_params(7e9)) == pytest.approx(7e9)
    assert T.compute_for_params(8e9, overtrain=100.0) == pytest.approx(12_000 * (8e9) ** 2)
    assert T.params_for_compute(2e24) == pytest.approx(129e9, rel=0.01)       # section 6.2.5: about 130B


def test_is_beyond_threshold_either_ceiling():
    assert T.is_beyond_threshold(3e24, 5e9, 2e24, 13e9)           # over the compute ceiling
    assert T.is_beyond_threshold(1e24, 20e9, 2e24, 13e9)          # over the parameter ceiling (e.g. heavily overtrained)
    assert not T.is_beyond_threshold(1e24, 5e9, 2e24, 13e9)


def test_erosion_and_years_for_oom():
    assert T.erode(100.0, 2.0, 10.0) == pytest.approx(1.0)
    assert T.years_for_oom(2.0, 1.57) == pytest.approx(10.2, abs=0.1)         # a decade at the paper's 57% a year
    assert T.years_for_oom(1.0, 10 ** 0.2) == pytest.approx(5.0)
    assert T.oom_per_year(10.0) == 1.0


def test_breakout_sensitivity_and_pause_delay():
    rows = {r["n_steps"]: r for r in T.breakout_sensitivity()}
    assert rows[6]["C_B"] == pytest.approx(2e29) and rows[4]["C_B"] == pytest.approx(4.3e28, rel=0.01)
    assert rows[4]["F_B_T2"] == pytest.approx(36.5e6, rel=0.01)
    assert rows[4]["F_B_T1"] == pytest.approx(2 * rows[4]["F_B_T2"])           # horizon enters inversely
    assert all(rows[n + 1]["F_B_T2"] > rows[n]["F_B_T2"] for n in range(3, 8))
    p = T.ThresholdParams()
    d = T.pause_delay(p, 0.5)
    assert d["F_E"] == pytest.approx(T.covert_evasion_fleet(p) * p.g ** 0.5)  # F_E follows the frontier
    assert d["beta_B"] == pytest.approx(p.c_b / (p.c_f * p.g ** 0.5))         # C_B is absolute: fewer blind steps left
    assert T.pause_delay(p, 2.0)["F_B"] < T.overt_breakout_fleet(p)
    assert T.months_per_blind_step(p) == pytest.approx(6.1, abs=0.1)


def test_private_evasion_fleet_and_pareto_stress():
    p = T.ThresholdParams()
    f = T.private_evasion_fleet(p)
    assert T.private_evasion_fleet(p, undetected_runs_at_ct=200.0) == pytest.approx(2 * f)
    assert T.pareto_mean(2.0) == 2.0 and T.pareto_mean(1.0) == math.inf
    assert T.private_evasion_stress(p, theta=2.0) == pytest.approx(8 * f)      # 4*theta/(theta-1) at theta = 2
    assert T.private_evasion_stress(p, theta=2.0, x_max=1e4) < T.private_evasion_stress(p, theta=2.0)
    assert T.pareto_mean(1.0, x_max=100.0) == pytest.approx(math.log(100) / 0.99)
