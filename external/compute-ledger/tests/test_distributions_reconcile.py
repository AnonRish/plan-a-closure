"""The hidden-compute distribution and the declared-versus-estimated posterior, against scipy/numpy."""
import math
import random

import numpy as np
import pytest
from hypothesis import given, settings, strategies as st
from scipy import integrate, stats

from compute_ledger.distributions import TwoPieceLogNormal, Z90
from compute_ledger.reconcile import (Estimate, Fitted, Flat, HalfNormal, consistency, posterior_hidden,
                                      sum_quantiles)

PLAN = (0.001 * 289e6, 1.5e6, 0.014 * 289e6)       # the published hidden-compute p10, median, p90 (H100e)


# ------------------------------------------------------------------------------------------ distribution --

def test_reproduces_the_three_published_quantiles_exactly():
    d = TwoPieceLogNormal(*PLAN)
    assert d.ppf(0.1) == pytest.approx(PLAN[0], rel=1e-12)
    assert d.ppf(0.5) == pytest.approx(PLAN[1], rel=1e-12)
    assert d.ppf(0.9) == pytest.approx(PLAN[2], rel=1e-12)
    assert d.sigma_lo > d.sigma_hi                       # skewed: a single lognormal could not match all three
    assert Z90 == pytest.approx(stats.norm.ppf(0.9), rel=1e-12)


@settings(max_examples=100, deadline=None)
@given(st.floats(1e-3, 1e3), st.floats(0.05, 2.0))
def test_symmetric_case_is_exactly_scipys_lognormal(m, sigma):
    d = TwoPieceLogNormal(m * math.exp(-Z90 * sigma), m, m * math.exp(Z90 * sigma))
    ref = stats.lognorm(s=sigma, scale=m)
    for p in (0.01, 0.1, 0.3, 0.5, 0.7, 0.9, 0.99):
        assert d.ppf(p) == pytest.approx(ref.ppf(p), rel=1e-9)
    for x in (m / 3, m, 2 * m):
        assert d.cdf(x) == pytest.approx(ref.cdf(x), rel=1e-9)
        assert d.pdf(x) == pytest.approx(ref.pdf(x), rel=1e-9)
    assert d.mean() == pytest.approx(ref.mean(), rel=1e-9)


@settings(max_examples=100, deadline=None)
@given(st.floats(1e-6, 1 - 1e-6))
def test_cdf_inverts_ppf_and_ppf_is_monotone(p):
    d = TwoPieceLogNormal(*PLAN)
    assert d.cdf(d.ppf(p)) == pytest.approx(p, abs=1e-9)
    assert d.ppf(min(p + 1e-7, 1 - 1e-9)) >= d.ppf(p)


def test_density_integrates_to_one_and_mean_matches_quadrature():
    """Integrate in log space, x = m*exp(u), where the integrand is Gaussian-shaped (quad over [m, inf) on the raw
    heavy lognormal tail does not converge to 1e-9)."""
    d = TwoPieceLogNormal(*PLAN)
    m = d.p50
    mass = lambda a, b: integrate.quad(lambda u: d.pdf(m * math.exp(u)) * m * math.exp(u), a, b, limit=200, epsabs=1e-13, epsrel=1e-12)[0]
    first = lambda a, b: integrate.quad(lambda u: (m * math.exp(u)) ** 2 * d.pdf(m * math.exp(u)), a, b, limit=200, epsabs=1e-3, epsrel=1e-12)[0]
    lo_u, hi_u = -12 * d.sigma_lo, 12 * d.sigma_hi
    assert mass(lo_u, 0) == pytest.approx(0.5, abs=1e-9) and mass(0, hi_u) == pytest.approx(0.5, abs=1e-9)
    assert d.mean() == pytest.approx(first(lo_u, 0) + first(0, hi_u), rel=1e-7)


def test_sampling_reproduces_the_quantiles():
    d = TwoPieceLogNormal(*PLAN)
    rng = random.Random(3)
    xs = np.array([d.sample(rng) for _ in range(200_000)])
    for p, want in ((0.1, PLAN[0]), (0.5, PLAN[1]), (0.9, PLAN[2])):
        assert np.quantile(xs, p) == pytest.approx(want, rel=0.02)
    assert xs.mean() == pytest.approx(d.mean(), rel=0.03)


def test_distribution_input_validation():
    for bad in ((1, 1, 2), (2, 1, 3), (0, 1, 2), (1, 2, 2), (-1, 1, 2)):
        with pytest.raises(ValueError):
            TwoPieceLogNormal(*bad)
    d = TwoPieceLogNormal(*PLAN)
    for p in (0.0, 1.0, -0.1):
        with pytest.raises(ValueError):
            d.ppf(p)
    assert d.cdf(0) == 0.0 and d.pdf(-1) == 0.0


# --------------------------------------------------------------------------------------------- estimate ----

@pytest.mark.parametrize("level", [0.5, 0.8, 0.9, 0.95])
def test_estimate_sigma_from_the_stated_interval(level):
    e = Estimate(222e6, 226e6, level)
    assert e.sigma == pytest.approx(4e6 / (2 * stats.norm.ppf(0.5 + level / 2)), rel=1e-12)
    assert e.center == 224e6


def test_estimate_validation():
    for args in ((5, 5), (6, 5), (0, 5), (-1, 5)):
        with pytest.raises(ValueError):
            Estimate(*args)
    with pytest.raises(ValueError):
        Estimate(1, 2, 1.0)


def test_consistency_against_scipy():
    e = Estimate(222e6, 226e6)
    for declared in (224e6, 222e6, 218e6, 227e6):
        c = consistency(declared, e)
        assert c.z == pytest.approx((224e6 - declared) / e.sigma, rel=1e-12)
        assert c.p_if_complete == pytest.approx(stats.norm.sf(c.z), rel=1e-9)


# --------------------------------------------------------------------------------------------- posterior ---

CASES = [(224e6, 222e6, 226e6), (26e6, 25e6, 27e6), (100e6, 103e6, 109e6), (100e6, 95e6, 99e6),
         (100e6, 80e6, 90e6), (50e6, 50e6, 52e6)]


def flat_reference(declared, e):
    m, s = e.center - declared, e.sigma
    return stats.truncnorm(a=-m / s, b=np.inf, loc=m, scale=s), s


@pytest.mark.parametrize("declared,lo,hi", CASES)
def test_flat_prior_is_a_truncated_normal(declared, lo, hi):
    e = Estimate(lo, hi)
    post = posterior_hidden(declared, e)
    ref, s = flat_reference(declared, e)
    for p in (0.01, 0.1, 0.5, 0.9, 0.99):
        assert abs(post.quantile(p) - ref.ppf(p)) < 2e-4 * s, p
    assert abs(post.mean - ref.mean()) < 2e-4 * s
    for x in (0.0, 0.5 * s, 2 * s):
        assert post.prob_exceeds(x) == pytest.approx(ref.sf(x), abs=1e-5)
    assert post.cdf[0] == 0.0 and post.cdf[-1] == pytest.approx(1.0, abs=1e-12)
    assert all(b >= a for a, b in zip(post.cdf, post.cdf[1:]))


@pytest.mark.parametrize("declared,lo,hi", CASES[:4])
@pytest.mark.parametrize("tau_frac", [0.5, 2.0])
def test_half_normal_prior_is_again_a_truncated_normal(declared, lo, hi, tau_frac):
    e = Estimate(lo, hi)
    s, m = e.sigma, e.center - declared
    tau = tau_frac * s
    post = posterior_hidden(declared, e, HalfNormal(tau))
    prec = 1 / tau ** 2 + 1 / s ** 2
    sd = prec ** -0.5
    mu = (m / s ** 2) / prec
    ref = stats.truncnorm(a=-mu / sd, b=np.inf, loc=mu, scale=sd)
    for p in (0.1, 0.5, 0.9, 0.99):
        assert abs(post.quantile(p) - ref.ppf(p)) < 2e-4 * s, p


def test_fitted_prior_matches_an_independent_fine_grid():
    d = TwoPieceLogNormal(*PLAN)
    e = Estimate(222e6, 226e6)
    declared = 224e6
    post = posterior_hidden(declared, e, Fitted(d))
    # independent: a different grid (numpy, 400,001 points, Simpson on the cumulative sum)
    h = np.linspace(1e-9, post.grid[-1], 400_001)
    like = stats.norm.pdf(e.center, loc=declared + h, scale=e.sigma)
    w = np.array([d.pdf(x) for x in h]) * like
    cdf = np.concatenate(([0.0], np.cumsum(0.5 * (w[1:] + w[:-1]) * np.diff(h))))
    cdf /= cdf[-1]
    for p in (0.1, 0.5, 0.9):
        assert abs(post.quantile(p) - np.interp(p, cdf, h)) < 2e-3 * e.sigma, p


def test_an_estimate_far_below_the_declaration_is_numerically_stable():
    e = Estimate(100e6, 104e6)
    post = posterior_hidden(150e6, e)                       # declared 30+ sigma above the estimate
    assert all(math.isfinite(x) for x in post.pdf) and post.cdf[-1] == pytest.approx(1.0)
    assert post.median < 0.05 * e.sigma


def test_posterior_and_consistency_agree_on_the_direction():
    e = Estimate(222e6, 226e6)
    above = posterior_hidden(224e6 - 5e6, e)       # estimate well above the declaration: hidden stock is large
    level = posterior_hidden(224e6, e)
    assert above.median > 4e6 > level.median
    assert consistency(224e6 - 5e6, e).p_if_complete < 0.01


@settings(max_examples=40, deadline=None)
@given(st.floats(-3, 3), st.floats(-3, 3))
def test_median_is_monotone_in_the_estimate_centre(a, b):
    lo, hi = sorted((a, b))
    s = 1.0
    d = 100.0
    mk = lambda c: posterior_hidden(d, Estimate(c - 1.2816 * s, c + 1.2816 * s), n=4001).median
    assert mk(d + lo) <= mk(d + hi) + 1e-9


def test_wider_estimates_leave_more_room_for_hidden_stock():
    narrow = posterior_hidden(224e6, Estimate(223e6, 225e6))
    wide = posterior_hidden(224e6, Estimate(220e6, 228e6))
    assert wide.quantile(0.9) > narrow.quantile(0.9) > 0


def test_sum_of_independent_posteriors_matches_numpy():
    pa = posterior_hidden(224e6, Estimate(222e6, 226e6))
    pb = posterior_hidden(26e6, Estimate(25e6, 27e6))
    q = sum_quantiles([pa, pb], (0.1, 0.5, 0.9), n=200_000, seed=5)
    rng = np.random.default_rng(11)
    xa = np.interp(rng.random(1_000_000), pa.cdf, pa.grid)
    xb = np.interp(rng.random(1_000_000), pb.cdf, pb.grid)
    ref = np.quantile(xa + xb, (0.1, 0.5, 0.9))
    for got, want in zip(q, ref):
        assert got == pytest.approx(want, rel=0.02)
    assert q[1] > pa.median and q[1] > pb.median


def test_posterior_input_validation():
    with pytest.raises(ValueError):
        posterior_hidden(0.0, Estimate(1, 2))
    with pytest.raises(ValueError):
        HalfNormal(0)
    post = posterior_hidden(10.0, Estimate(9.0, 11.0))
    with pytest.raises(ValueError):
        post.quantile(1.5)
    assert post.prob_exceeds(-1) == 1.0 and post.prob_exceeds(1e9) == 0.0
