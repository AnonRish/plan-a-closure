import math

import pytest
from hypothesis import assume, given, settings, strategies as st
from scipy import stats

import assurance_curves as ac
from assurance_curves import core


def test_ln100_matches_appendix_constant():
    assert ac.LN_100 == pytest.approx(4.605170185988092, rel=1e-15)
    assert 1 - math.exp(-ac.LN_100) == pytest.approx(0.99, abs=1e-15)


@pytest.mark.parametrize("c,n", [(0.01, 100), (1e-6, 10**6), (0.5, 3), (1e-3, 4605), (0.9, 1), (1e-9, 10)])
def test_exact_matches_scipy_binomial(c, n):
    assert ac.p_undetected_exact(c, n) == pytest.approx(stats.binom.pmf(0, n, c), rel=1e-12)
    assert ac.p_detected_exact(c, n) == pytest.approx(stats.binom.sf(0, n, c), rel=1e-9)


@pytest.mark.parametrize("N,F,n", [(100, 5, 10), (1000, 1, 999), (1000, 50, 20), (10**6, 100, 5000), (50, 25, 25), (10, 3, 8)])
def test_hypergeometric_matches_scipy(N, F, n):
    ref = stats.hypergeom.sf(0, N, F, n)
    assert ac.p_detected_hypergeometric(N, F, n) == pytest.approx(ref, rel=1e-8, abs=1e-12)


def test_hypergeometric_edge_cases():
    assert ac.p_detected_hypergeometric(100, 0, 50) == 0.0
    assert ac.p_detected_hypergeometric(100, 5, 0) == 0.0
    assert ac.p_detected_hypergeometric(100, 5, 100) == 1.0
    assert ac.p_detected_hypergeometric(10, 5, 6) == 1.0      # pigeonhole
    with pytest.raises(ValueError):
        ac.p_detected_hypergeometric(10, 11, 2)


@settings(max_examples=300, deadline=None)
@given(c=st.floats(1e-9, 1.0), n=st.floats(0, 1e7))
def test_poisson_form_is_conservative(c, n):
    # ln(1-c) <= -c  =>  1-(1-c)^n >= 1-exp(-c n)
    assert ac.p_detected_poisson(n, c) <= ac.p_detected_exact(c, n) + 1e-15


@settings(max_examples=200, deadline=None)
@given(c=st.floats(1e-6, 0.999), n1=st.floats(0, 1e5), n2=st.floats(0, 1e5))
def test_detection_monotone_in_fakes(c, n1, n2):
    lo, hi = sorted((n1, n2))
    assert ac.p_detected_exact(c, lo) <= ac.p_detected_exact(c, hi) + 1e-15


@settings(max_examples=200, deadline=None)
@given(c1=st.floats(1e-6, 1), c2=st.floats(1e-6, 1), n=st.floats(0, 1e5))
def test_detection_monotone_in_budget(c1, c2, n):
    lo, hi = sorted((c1, c2))
    assert ac.p_detected_exact(lo, n) <= ac.p_detected_exact(hi, n) + 1e-15


@settings(max_examples=400, deadline=None)
@given(N=st.integers(2, 400), data=st.data())
def test_sampling_without_replacement_never_worse_than_with(N, data):
    F = data.draw(st.integers(1, N))
    n = data.draw(st.integers(0, N))
    hyper = ac.p_detected_hypergeometric(N, F, n)
    indep = ac.p_detected_exact(n / N, F)
    assert hyper >= indep - 1e-12


@settings(max_examples=300, deadline=None)
@given(c=st.floats(1e-5, 0.999), conf=st.floats(1e-6, 1 - 1e-9))
def test_min_fake_packets_is_minimal(c, conf):
    n = ac.min_fake_packets_exact(c, conf)
    assert ac.p_detected_exact(c, n) >= conf
    assert n == 1 or ac.p_detected_exact(c, n - 1) < conf


@settings(max_examples=300, deadline=None)
@given(n=st.floats(1, 1e9), conf=st.floats(1e-6, 1 - 1e-9))
def test_required_budget_inverts_detection(n, conf):
    c = ac.required_budget(n, conf)
    assume(0 < c < 1)
    assert ac.p_detected_exact(c, n) == pytest.approx(conf, rel=1e-6)


def test_poisson_budget_matches_appendix_rule():
    # "C * N_fake just needs to exceed about 4.6"
    assert ac.required_budget(460.517, 0.99, model="poisson") == pytest.approx(0.01, rel=1e-5)
    assert ac.fake_packets_for_confidence(0.01, 0.99, model="poisson") == pytest.approx(460.517, rel=1e-6)


def test_nines_round_trip():
    assert ac.nines(0.99) == pytest.approx(2.0, rel=1e-12)
    assert ac.nines(1 - 1e-8) == pytest.approx(8.0, rel=1e-6)
    assert ac.confidence_from_nines(5) == pytest.approx(0.99999, rel=1e-12)
    assert math.isinf(ac.nines(1.0))


def test_extreme_values_do_not_round_to_zero_or_one():
    # 1e-12 budget, 1 fake packet: detection is 1e-12, not 0
    assert ac.p_detected_exact(1e-12, 1) == pytest.approx(1e-12, rel=1e-6)
    # huge n: undetected probability underflows gracefully to 0, not NaN
    assert ac.p_undetected_exact(0.5, 1e9) == 0.0
    assert ac.p_detected_exact(0.5, 1e9) == 1.0


@pytest.mark.parametrize("bad", [-0.1, 1.5, float("nan")])
def test_rejects_invalid_probabilities(bad):
    with pytest.raises(ValueError):
        ac.p_detected_exact(bad, 10)
    with pytest.raises(ValueError):
        ac.p_detected_exact(0.1, -1)


def test_unreachable_confidence_raises():
    with pytest.raises(ValueError):
        ac.min_fake_packets_exact(0.0, 0.5)
    with pytest.raises(ValueError):
        ac.min_fake_packets_exact(0.1, 1.0)


# ---- high-precision cross-check (mpmath, 60 digits) -------------------------------------
def _mp_hypergeom_detect(N, F, n):
    import mpmath as mp
    mp.mp.dps = 60
    N, F, n = map(mp.mpf, (N, F, n))
    lr = (mp.loggamma(N - F + 1) - mp.loggamma(N - F - n + 1)) - (mp.loggamma(N + 1) - mp.loggamma(N - n + 1))
    return float(-mp.expm1(lr))


# Cases chosen at *moderate* detection probability, where absolute error in the exponent shows up
# as relative error in the answer. The old log-gamma implementation failed most of these by 1e-6..1e-4.
_HG_CASES = [
    (10**6, 100, 5000), (10**7, 100, 10**4), (10**8, 100, 10**5), (10**8, 10, 10**6),
    (10**9, 10**3, 10**6), (1_900_000_000, 10**6, 10**4), (1_900_000_000, 100, 10**6),
    (5 * 10**9, 50, 10**9), (10**11, 10**4, 10**7), (10**12, 10**6, 10**4), (10**15, 300, 10**12),
    (30, 4, 9), (10**4, 9000, 500),
]


@pytest.mark.parametrize("N,F,n", _HG_CASES)
def test_hypergeometric_matches_60_digit_reference(N, F, n):
    ref = _mp_hypergeom_detect(N, F, n)
    got = ac.p_detected_hypergeometric(N, F, n)
    assert got == pytest.approx(ref, rel=1e-12, abs=1e-15)


@pytest.mark.parametrize("N,F,n", [(10**12, 3 * 10**6, 3 * 10**6), (5 * 10**11, 2_100_000, 2_200_000), (10**13, 4 * 10**6, 2 * 10**7)])
def test_midpoint_regime_matches_reference(N, F, n):
    """Both n and F exceed the 2e6 direct limit: the log1p midpoint rule is what runs."""
    assert min(n, F) > core._DIRECT_LIMIT and n * F < core._SATURATED * N
    assert ac.p_detected_hypergeometric(N, F, n) == pytest.approx(_mp_hypergeom_detect(N, F, n), rel=1e-15)


def test_midpoint_expansion_error_matches_the_first_omitted_term_when_forced_at_small_scale(monkeypatch):
    monkeypatch.setattr(core, "_DIRECT_LIMIT", 10)
    for N, F, n in [(10**6, 10**3, 10**3), (10**7, 3 * 10**3, 10**4), (10**8, 10**4, 2 * 10**4), (10**5, 300, 2000)]:
        x_ = n * F / N
        got = ac.p_detected_hypergeometric(N, F, n)
        assert abs(got - _mp_hypergeom_detect(N, F, n)) <= 4 * x_ * (n / N) ** 4 / 80 + 1e-15


@settings(max_examples=300, deadline=None)
@given(N=st.integers(2, 3000), data=st.data())
def test_hypergeometric_symmetry_between_audited_and_fake(N, data):
    F = data.draw(st.integers(0, N))
    n = data.draw(st.integers(0, N))
    assert ac.p_detected_hypergeometric(N, F, n) == pytest.approx(ac.p_detected_hypergeometric(N, n, F), rel=1e-11, abs=1e-15)


def test_hypergeometric_saturation_and_direct_limit_are_consistent():
    # just below / above the saturation line the two sides agree to float64
    assert ac.p_detected_hypergeometric(10**9, 100, 10**8 * 4 - 1) == pytest.approx(1.0, abs=2**-56)
    assert ac.p_detected_hypergeometric(10**9, 100, 10**8 * 4 + 1) == 1.0
    # blocked summation (a > one 2**20 block) equals the closed-form check at a=2e6
    assert ac.p_detected_hypergeometric(10**11, 10**3, 2_000_000) == pytest.approx(
        _mp_hypergeom_detect(10**11, 10**3, 2_000_000), rel=1e-12)


# ---- independent exact oracle: Python big integers (int/int true division is correctly rounded) ----------
def _exact_detect(N, F, n):
    from math import comb
    total = comb(N, n)
    return (total - comb(N - F, n)) / total          # exact integer difference, so no 1 - (1 - tiny) cancellation


@pytest.mark.parametrize("N,F,n", [(10, 3, 4), (1000, 5, 50), (10**5, 100, 1000), (10**6, 1, 1), (10**6, 100, 5000),
                                   (300_000, 3, 2999), (2000, 1999, 1), (50_000, 20_000, 3)])
def test_hypergeometric_matches_exact_integer_arithmetic(N, F, n):
    assert ac.p_detected_hypergeometric(N, F, n) == pytest.approx(_exact_detect(N, F, n), rel=1e-13, abs=1e-300)


@settings(max_examples=300, deadline=None)
@given(N=st.integers(1, 2500), data=st.data())
def test_hypergeometric_matches_exact_integer_arithmetic_property(N, data):
    F = data.draw(st.integers(1, N))
    n = data.draw(st.integers(1, N))
    assume(n <= N - F)                                      # otherwise the pigeonhole shortcut returns exactly 1
    assert ac.p_detected_hypergeometric(N, F, n) == pytest.approx(_exact_detect(N, F, n), rel=1e-12, abs=1e-300)
