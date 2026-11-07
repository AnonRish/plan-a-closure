import json
import math

import numpy as np
import pytest
from scipy import stats

import assurance_curves as ac
from assurance_curves import canary, cli, falsealarm


@pytest.mark.parametrize("fpr", [1e-2, 1e-4, 1e-8, 1e-12, 3.4e-14, 1e-16])
def test_gaussian_threshold_matches_scipy(fpr):
    assert falsealarm.gaussian_threshold_sigma(fpr) == pytest.approx(stats.norm.isf(fpr), rel=1e-9)


def test_certification_bounds_are_tight_and_inverse():
    for p, d in [(1e-3, 0.05), (1e-6, 0.01), (0.2, 0.05)]:
        n = falsealarm.packets_to_certify_fpr(p, d)
        assert (1 - p) ** n <= d < (1 - p) ** (n - 1)
        assert falsealarm.certifiable_fpr(n, d) <= p * (1 + 1e-9)
    assert falsealarm.packets_to_certify_fpr(1e-3, 0.05) == pytest.approx(3 / 1e-3, rel=0.01)   # rule of three


def test_2034_scale_false_alarm_budget():
    """33 B H100e pool, 1 % recompute, 100 H100e-hour packets, one spurious alarm per year tolerated.

    Expected values were recomputed independently with exact rationals and 60-digit floats
    (see VERIFICATION_LOG.md, entry 1: an earlier draft of this test was off by 1000x).
    """
    n = falsealarm.audited_packets_per_year(33e9, 0.01, 100.0)
    assert n == pytest.approx(28_908_000_000, rel=1e-12)        # 33e9 * 0.01 * 8760 / 100
    fpr = falsealarm.max_fpr_for_alarm_budget(n, 1.0)
    assert fpr == pytest.approx(3.4592500345925e-11, rel=1e-12)
    assert falsealarm.gaussian_threshold_sigma(fpr) == pytest.approx(6.5224134, abs=1e-6)
    need = falsealarm.packets_to_certify_fpr(fpr, 0.05)
    assert need == pytest.approx(8.6600629e10, rel=1e-7)
    # Exact identity: certifying a rate of 1 alarm per year takes ln(1/delta) years of audited throughput.
    assert need / n == pytest.approx(math.log(20), rel=1e-6)
    # ...about 3.4x the packets you would get by recomputing the entire 2029 world stock for a year.
    world_2029_packets_per_year = 289e6 * 8760 / 100.0
    assert need / world_2029_packets_per_year == pytest.approx(3.4207, rel=1e-3)


def test_falsealarm_validation():
    with pytest.raises(ValueError):
        falsealarm.gaussian_threshold_sigma(0.0)
    with pytest.raises(ValueError):
        falsealarm.max_fpr_for_alarm_budget(0, 1)
    with pytest.raises(ValueError):
        falsealarm.audited_packets_per_year(1e9, 2.0, 100.0)


def test_canary_detection_matches_simulation():
    q, m = 0.05, 60
    rng = np.random.default_rng(8)
    trials = 200_000
    caught = (rng.random((trials, m)) < q).any(axis=1).mean()     # any canary slipped through
    p = canary.p_catch_suppression(q, m)
    assert abs(caught - p) <= 5 * math.sqrt(p * (1 - p) / trials)


def test_canaries_needed_is_minimal():
    n = canary.canaries_needed(0.01, 0.99)
    assert n == 459
    assert canary.p_catch_suppression(0.01, n) >= 0.99 > canary.p_catch_suppression(0.01, n - 1)
    assert canary.max_undetected_suppression(n, 0.99) <= 0.01 + 1e-12
    assert canary.max_undetected_suppression(0, 0.99) == 1.0


def test_pipeline_detection_with_a_suppressing_server_matches_simulation():
    c, q, n_fake = 0.02, 0.4, 120
    rng = np.random.default_rng(21)
    trials = 30_000
    audited = rng.random((trials, n_fake)) < c
    flagged = rng.random((trials, n_fake)) >= q          # server suppresses with prob q
    caught = (audited & flagged).any(axis=1).mean()
    p = canary.p_detected_with_suppression(c, q, n_fake)
    assert abs(caught - p) <= 5 * math.sqrt(p * (1 - p) / trials)


def test_guaranteed_detection_is_monotone_in_canaries():
    vals = [canary.guaranteed_detection(0.01, m, 0.99, 460) for m in (0, 10, 100, 1000, 10_000)]
    assert vals[0] == 0.0
    assert all(a <= b for a, b in zip(vals, vals[1:]))
    assert vals[-1] > 0.98        # with 10,000 clean canaries the server is nearly irrelevant


def _run(capsys, *argv):
    assert cli.main(list(argv)) == 0
    return json.loads(capsys.readouterr().out)


def test_cli_reproduces_supplement_numbers(capsys):
    r = _run(capsys, "rogue", "--budget", "0.01", "--packet-size", "100", "--size", "10000",
             "--confidence", "0.99", "--hours", "1", "--pool", "33e9")
    assert r["hours_to_detect_poisson"] == pytest.approx(4.6052, rel=1e-4)
    assert r["h100e_hours_to_detect_poisson"] == pytest.approx(46051.7, rel=1e-5)
    assert r["p_detect_within_hours"] == pytest.approx(1 - 0.99**100)
    assert r["recompute_capacity_h100e"] == pytest.approx(330e6)


def test_cli_other_commands(capsys):
    d = _run(capsys, "detect", "--budget", "0.01", "--fake", "460")
    assert d["p_detected_exact"] > d["p_detected_poisson"]
    assert _run(capsys, "min-fake", "--budget", "0.01", "--confidence", "0.99")["fake_packets_exact_int"] == 459
    assert _run(capsys, "budget", "--fake", "460", "--confidence", "0.99")["budget_exact"] < 0.0101
    g = _run(capsys, "granularity", "--budget", "0.01", "--sizes", "10000")
    assert [r["granularity"] for r in g][0].startswith("per-server")
    f = _run(capsys, "false-alarm", "--pool", "33e9", "--budget", "0.01", "--packet-size", "100")
    assert f["gaussian_threshold_sigma"] == pytest.approx(6.5224, abs=1e-3)
    assert f["audited_packets_per_year"] == pytest.approx(28_908_000_000)
    assert _run(capsys, "canary", "--suppression", "0.01")["canaries_needed"] == 459
