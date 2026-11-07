import numpy as np

from closure.conformal import (cp_lower, cp_upper, jarque_bera_p, lower_conformal_quantile, t_upper,
                               upper_conformal_quantile)


def test_t_quantiles_match_published_tables():
    for a, nu, ref in ((0.025, 10, 2.2281), (0.005, 30, 2.7500), (0.005, 2, 9.9248), (0.025, 1, 12.7062),
                       (0.0005, 10, 4.5869)):
        assert abs(t_upper(a, nu) - ref) < 2e-4


def test_clopper_pearson_known_values():
    assert abs(cp_upper(0, 100, 0.95) - (1 - 0.05 ** (1 / 100))) < 1e-3
    assert abs(cp_lower(100, 100, 0.95) - 0.05 ** (1 / 100)) < 1e-3
    assert cp_upper(0, 0) == 1.0 and cp_lower(0, 50) == 0.0


def test_conformal_quantiles_are_finite_sample_valid():
    rng = np.random.default_rng(0)
    n, alpha, trials = 199, 0.05, 6000
    x = rng.standard_normal((trials, n + 1))
    s = np.sort(x[:, :n], axis=1)
    j = int(np.floor(alpha * (n + 1)))
    up = (x[:, n] > s[:, n - j]).mean()
    lo = (x[:, n] < s[:, j - 1]).mean()
    sigma = np.sqrt(alpha * (1 - alpha) / trials)
    assert up <= alpha + 3 * sigma and lo <= alpha + 3 * sigma
    assert up >= alpha - 3 * sigma  # and not wildly conservative


def test_conformal_returns_infinite_when_too_few_samples():
    assert upper_conformal_quantile(np.arange(10), 0.01) == float("inf")
    assert lower_conformal_quantile(np.arange(10), 0.01) == float("-inf")


def test_jarque_bera_discriminates():
    rng = np.random.default_rng(1)
    assert jarque_bera_p(rng.standard_normal(2000)) > 0.01
    assert jarque_bera_p(rng.exponential(size=2000)) < 1e-6
