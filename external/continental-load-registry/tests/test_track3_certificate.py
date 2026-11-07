import math

import pytest

from track3_certificate import one_sided_failure_upper_bound as ub


def _cdf(k, n, p):
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))


@pytest.mark.parametrize("n,delta", [(100, 0.05), (1000, 0.05), (100_000, 0.05), (5_000_000, 0.01)])
def test_zero_failure_bound_matches_closed_form(n, delta):
    assert ub(0, n, delta) == pytest.approx(1 - delta ** (1 / n), rel=1e-6)


@pytest.mark.parametrize("k,n", [(1, 100), (2, 200), (3, 500)])
def test_bound_solves_the_binomial_tail_equation(k, n):
    assert _cdf(k, n, ub(k, n, 0.05)) == pytest.approx(0.05, abs=1e-9)


@pytest.mark.parametrize("k,n", [(100, 100_000), (200, 300_000), (5000, 10_000_000)])
def test_large_samples_do_not_overflow(k, n):
    p = ub(k, n, 0.05)
    assert k / n < p < 3 * k / n


def test_bound_is_monotone_in_failures():
    vals = [ub(k, 1000, 0.05) for k in range(6)]
    assert vals == sorted(vals)


def test_all_failures_gives_one():
    assert ub(10, 10, 0.05) == 1.0
