"""Simulate the audit mechanism packet by packet; formulas must land inside 5 sigma."""
import numpy as np
import pytest

import assurance_curves as ac


def _within(freq, p, trials, k=5.0):
    se = max(np.sqrt(p * (1 - p) / trials), 1e-9)
    return abs(freq - p) <= k * se


@pytest.mark.parametrize("N,F,c", [(2000, 30, 0.01), (2000, 460, 0.01), (500, 5, 0.2), (1000, 100, 0.005)])
def test_independent_audit_matches_exact(N, F, c):
    rng = np.random.default_rng(12345)
    trials = 20_000
    is_fake = np.zeros(N, bool)
    is_fake[:F] = True
    audited = rng.random((trials, N)) < c
    detected = (audited & is_fake).any(axis=1)
    assert _within(detected.mean(), ac.p_detected_exact(c, F), trials)


@pytest.mark.parametrize("N,F,n", [(1000, 10, 20), (1000, 100, 30), (400, 3, 100), (2000, 50, 40)])
def test_fixed_count_audit_matches_hypergeometric(N, F, n):
    rng = np.random.default_rng(777)
    trials = 12_000
    idx = np.argpartition(rng.random((trials, N)), n - 1, axis=1)[:, :n]   # n audited positions
    detected = (idx < F).any(axis=1)                                       # fakes sit at positions 0..F-1
    assert _within(detected.mean(), ac.p_detected_hypergeometric(N, F, n), trials)


def test_poisson_understates_detection_when_budget_is_large():
    # c = 0.3, 5 fakes: Poisson says 1-exp(-1.5)=0.777, truth is 1-0.7^5=0.832
    assert ac.p_detected_poisson(5, 0.3) == pytest.approx(0.7769, abs=1e-4)
    assert ac.p_detected_exact(0.3, 5) == pytest.approx(0.83193, abs=1e-5)
    rng = np.random.default_rng(1)
    trials = 40_000
    detected = (rng.random((trials, 5)) < 0.3).any(axis=1)
    assert _within(detected.mean(), ac.p_detected_exact(0.3, 5), trials)
    assert not _within(detected.mean(), ac.p_detected_poisson(5, 0.3), trials)
