import math

import numpy as np
import pytest

from covert_timing_warden.channels import LevelChannel, QuantileChannel, random_symbols
from covert_timing_warden.detect import Warden, conformal_p, min_reference_windows
from covert_timing_warden.stats import DETECTORS, Context
from covert_timing_warden.traffic import BurstyMarkov, LogNormalIID

W, ALPHA = 200, 0.05


def _windows(stream):
    return stream[: (stream.size // W) * W].reshape(-1, W)


@pytest.fixture(scope="module")
def iid_warden():
    ref = LogNormalIID().sample(2 * 520 * W, np.random.default_rng(100))
    return Warden(ref, window=W, alpha=ALPHA)


@pytest.fixture(scope="module")
def bursty_warden():
    ref = BurstyMarkov().sample(2 * 520 * W, np.random.default_rng(200))
    return Warden(ref, window=W, alpha=ALPHA)


def _rate_ci(rate, n, R=None, k=4.0):
    """k-sigma slack for an observed alarm rate: test-sample noise, plus calibration noise when R null windows are used."""
    a = max(rate, ALPHA)
    var = a * (1 - a) / n + (a * (1 - a) / (R + 2) if R else 0.0)
    return k * math.sqrt(var)


def test_min_reference_windows_arithmetic():
    assert min_reference_windows(0.01, 6) == 1199
    assert min_reference_windows(0.05, 6) == 239
    with pytest.raises(ValueError):
        min_reference_windows(0.0, 6)


def test_refuses_a_reference_too_short_to_ever_alarm():
    ref = LogNormalIID().sample(60_000, np.random.default_rng(1))
    with pytest.raises(ValueError, match="never alarm"):
        Warden(ref, window=W, alpha=0.01)
    with pytest.raises(ValueError):
        Warden(np.array([1.0, -1.0] * 100_000), window=W, alpha=0.05)
    with pytest.raises(ValueError):
        Warden(ref, window=W, alpha=0.5, detectors=["nope"])


def test_window_shape_is_enforced(iid_warden):
    with pytest.raises(ValueError):
        iid_warden.test(np.ones(W + 1))


def test_conformal_p_is_exactly_uniform_by_enumeration():
    """R+1 exchangeable values, each in turn the test value: the one-sided ranks are exactly {1..R+1}/(R+1)."""
    for R in (1, 2, 5, 9):
        vals = np.arange(R + 1, dtype=float) * 1.7 + 0.3
        lows, highs = [], []
        for i in range(R + 1):
            null = np.sort(np.delete(vals, i))
            lows.append((1 + np.searchsorted(null, vals[i], side="right")) / (R + 1))
            highs.append((1 + R - np.searchsorted(null, vals[i], side="left")) / (R + 1))
        want = np.arange(1, R + 2) / (R + 1)
        assert np.allclose(np.sort(lows), want) and np.allclose(np.sort(highs), want)
    assert conformal_p(np.sort(np.full(50, 3.0)), 3.0) == 1.0          # all ties: never an alarm
    assert conformal_p(np.arange(100.0), 1e9) == pytest.approx(2 / 101)  # smallest attainable two-sided p
    assert conformal_p(np.arange(100.0), 49.5) == 1.0


def test_p_values_are_super_uniform_when_averaged_over_calibration_sets():
    """The real statistics on real (synthetic) windows, many independent calibration sets.

    A single warden's realised rate has calibration noise of about sqrt(a(1-a)/(R+2)); the *average* over
    calibration sets must not exceed the level. (A first version of this test ignored calibration noise and
    failed at 4.1 sigma of test noise alone; see VERIFICATION_LOG.md.)
    """
    rng = np.random.default_rng(300)
    pool = LogNormalIID().sample(100_000, rng)
    ctx = Context(np.quantile(pool, np.linspace(0, 1, 9)[1:-1]), np.sort(pool))
    n_bank = 3600
    bank = LogNormalIID().sample(n_bank * W, rng).reshape(n_bank, W)
    names = tuple(DETECTORS)
    S = {n: np.array([DETECTORS[n](w, ctx) for w in bank]) for n in names}
    R, n_cal, n_test = 260, 60, 500
    per, comb = {(n, lv): [] for n in names for lv in (0.05, 0.2)}, []
    for _ in range(n_cal):
        idx = rng.permutation(n_bank)
        nul, tst = idx[:R], idx[R:R + n_test]
        P = {n: np.array([conformal_p(np.sort(S[n][nul]), v) for v in S[n][tst]]) for n in names}
        for n in names:
            for lv in (0.05, 0.2):
                per[(n, lv)].append(np.mean(P[n] <= lv))
        comb.append(np.mean(np.minimum(1.0, len(names) * np.min([P[n] for n in names], axis=0)) <= ALPHA))
    for (n, lv), r in per.items():
        r = np.array(r)
        assert r.mean() <= lv + 4 * r.std(ddof=1) / math.sqrt(n_cal) + 1e-9, (n, lv, r.mean())
    assert np.mean(comb) <= ALPHA


def test_single_warden_false_alarm_rate_is_near_nominal_within_calibration_noise_iid(iid_warden):
    fresh = _windows(LogNormalIID().sample(1500 * W, np.random.default_rng(101)))
    res = [iid_warden.test(w) for w in fresh]
    n, R = len(res), iid_warden.n_null
    assert np.mean([r.alarm for r in res]) <= ALPHA + _rate_ci(ALPHA, n, R)
    for name in iid_warden.names:
        p = np.array([r.p_values[name] for r in res])
        for level in (0.05, 0.2, 0.5):
            assert np.mean(p <= level) <= level + _rate_ci(level, n, R) + 0.0, (name, level)


def test_single_warden_false_alarm_rate_on_bursty_honest_traffic(bursty_warden):
    fresh = _windows(BurstyMarkov().sample(1200 * W, np.random.default_rng(201)))
    res = [bursty_warden.test(w) for w in fresh]
    n, R = len(res), bursty_warden.n_null
    assert np.mean([r.alarm for r in res]) <= ALPHA + _rate_ci(ALPHA, n, R)
    for name in bursty_warden.names:
        p = np.array([r.p_values[name] for r in res])
        assert np.mean(p <= 0.1) <= 0.1 + _rate_ci(0.1, n, R), name


def test_naive_level_channel_is_caught_essentially_always(iid_warden):
    ch = LevelChannel(levels=4, t0=0.02, step=0.02)
    n = 300
    x = ch.encode(random_symbols(n * W, 4, np.random.default_rng(102)))
    assert iid_warden.alarm_rate(x) > 0.99
    r = iid_warden.test(x[:W])
    assert "eps_similarity" in r.triggered or "ks" in r.triggered


def test_a_perfectly_matched_quantile_channel_is_undetectable_by_construction(iid_warden):
    """Encoded stream is distributed exactly as honest traffic, so detection rate = false-alarm rate, at any capacity."""
    for bits in (1, 3):
        ch = QuantileChannel(LogNormalIID(), bits)
        rng = np.random.default_rng(103 + bits)
        x = ch.encode(random_symbols(1500 * W, ch.levels, rng), rng)
        rate = iid_warden.alarm_rate(x)
        assert rate <= ALPHA + _rate_ci(ALPHA, 1500, iid_warden.n_null), (bits, rate)


def test_marginal_matching_alone_fails_against_structured_honest_traffic(bursty_warden):
    """Adversary matches the marginal of bursty traffic but not its dependence: structure-sensitive tests see it."""
    ch = QuantileChannel(BurstyMarkov(), bits=2)
    rng = np.random.default_rng(210)
    x = ch.encode(random_symbols(600 * W, ch.levels, rng), rng)
    res = bursty_warden.scan(x)
    assert np.mean([r.alarm for r in res]) > 0.9
    # ... and the *marginal* test alone is blind, as it should be: the marginal really is matched
    ks_p = np.array([r.p_values["ks"] for r in res])
    assert np.mean(ks_p <= 0.05) <= 0.05 + _rate_ci(0.05, len(res), bursty_warden.n_null)
    dependence = [r for r in res if {"autocorr", "cce"} & set(r.triggered)]
    assert len(dependence) / len(res) > 0.9


def test_results_are_deterministic(iid_warden):
    w = LogNormalIID().sample(W, np.random.default_rng(5))
    a, b = iid_warden.test(w), iid_warden.test(w)
    assert a == b
