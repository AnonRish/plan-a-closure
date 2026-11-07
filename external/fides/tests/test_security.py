import pytest

from fides.security import (
    detection_probability,
    poisson_detection_probability,
    repeated_detection_probability,
    monte_carlo_detection_rate,
)


def test_exact_formula_matches_monte_carlo_simulation():
    cases = [(34, 32, 5), (25, 3, 4), (50, 1, 10), (20, 10, 3), (28, 3, 6)]
    for n, k, m in cases:
        analytical = detection_probability(n, k, m)
        empirical = monte_carlo_detection_rate(n, k, m, trials=30000, seed=42)
        assert abs(analytical - empirical) < 0.02, (n, k, m, analytical, empirical)


def test_detection_probability_zero_when_no_bad_events():
    assert detection_probability(30, 0, 5) == 0.0


def test_detection_probability_certain_when_sample_exceeds_good_events():
    # if n - k < m, every possible sample must include a bad event
    assert detection_probability(10, 8, 5) == 1.0


def test_detection_probability_rejects_oversized_sample():
    with pytest.raises(ValueError):
        detection_probability(10, 2, 11)


def test_poisson_approximation_converges_to_exact_for_large_populations():
    # F_fake = k / n small, N_verified = m: the two formulas should agree
    # closely once n is large enough for the finite-population correction
    # in the exact hypergeometric formula to matter less.
    n, k, m = 10_000, 50, 500
    exact = detection_probability(n, k, m)
    approx = poisson_detection_probability(n_verified=m, f_fake=k / n)
    assert abs(exact - approx) < 0.01


def test_repeated_detection_compounds_towards_certainty():
    p = 0.4
    assert repeated_detection_probability(p, 1) == pytest.approx(0.4)
    assert repeated_detection_probability(p, 0) == 0.0
    assert repeated_detection_probability(p, 10) > 0.99
