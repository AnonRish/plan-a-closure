import math
import zlib

import numpy as np
import pytest
from scipy import special, stats as sst

from covert_timing_warden import stats as S
from covert_timing_warden.channels import LevelChannel, QuantileChannel, random_symbols
from covert_timing_warden.traffic import BurstyMarkov, LogNormalIID, load_ipd_csv, to_ipd, to_timestamps

RNG = lambda s=0: np.random.default_rng(s)


# ------------------------------------------------------------------ traffic
def test_lognormal_sampler_matches_its_cdf_and_ppf_inverts_it():
    d = LogNormalIID()
    x = d.sample(200_000, RNG(1))
    assert sst.kstest(x, d.cdf).pvalue > 1e-3
    q = np.linspace(0.001, 0.999, 999)
    assert d.cdf(d.ppf(q)) == pytest.approx(q, abs=1e-12)
    assert np.median(x) == pytest.approx(0.03, rel=0.01)


def test_bursty_sampler_marginal_matches_stationary_mixture_cdf():
    d = BurstyMarkov()
    x = d.sample(300_000, RNG(2))
    # dependent samples: compare the *empirical CDF* at fixed points; se inflated by the chain's correlation
    for pt in (0.01, 0.02, 0.05, 0.1, 0.3, 0.6):
        assert np.mean(x <= pt) == pytest.approx(float(d.cdf(pt)), abs=0.006)
    q = np.linspace(0.01, 0.99, 99)
    assert d.cdf(d.ppf(q)) == pytest.approx(q, abs=1e-6)
    assert d.stationary_burst() == pytest.approx(0.25 / 0.33)      # (1 - p_ii) / ((1 - p_bb) + (1 - p_ii))


def test_bursty_traffic_has_positive_lag1_autocorrelation_but_iid_does_not():
    assert S.lag1_autocorr(BurstyMarkov().sample(100_000, RNG(3))) > 0.3
    assert abs(S.lag1_autocorr(LogNormalIID().sample(100_000, RNG(3)))) < 0.02


def test_timestamp_round_trip_is_exact_and_lengths_are_n_and_n_plus_one(tmp_path):
    ipd = LogNormalIID().sample(50, RNG(4))
    ts = to_timestamps(ipd)
    assert ts.size == 51 and ts[0] == 0.0
    assert to_ipd(ts) == pytest.approx(ipd, rel=1e-12)
    assert to_timestamps(ipd, t0=100.0)[0] == 100.0
    with pytest.raises(ValueError):
        to_ipd([1.0, 0.5])


def test_csv_loader_skips_header_but_refuses_to_shorten_a_trace_silently(tmp_path):
    ipd = LogNormalIID().sample(50, RNG(4))
    good = tmp_path / "good.csv"
    good.write_text("time_s,other\n" + "\n".join(f"{float(t)!r},x" for t in to_timestamps(ipd)) + "\n")
    assert load_ipd_csv(str(good)) == pytest.approx(ipd, rel=1e-9)
    assert load_ipd_csv(str(good), timestamps=False).size == 51
    bad = tmp_path / "bad.csv"
    bad.write_text("t\n0.0\n0.1\noops\n0.3\n")
    with pytest.raises(ValueError, match=r"bad.csv:4"):
        load_ipd_csv(str(bad))


# ------------------------------------------------------------------ channels
def test_level_channel_round_trip_and_range_checks():
    ch = LevelChannel(levels=4, t0=0.05, step=0.02)
    s = random_symbols(1000, 4, RNG(5))
    assert np.array_equal(ch.decode(ch.encode(s)), s)
    assert ch.bits_per_packet == 2.0
    with pytest.raises(ValueError):
        ch.encode([4])


@pytest.mark.parametrize("dist", [LogNormalIID(), BurstyMarkov()])
@pytest.mark.parametrize("bits", [1, 2, 4])
def test_quantile_channel_round_trips_without_noise_and_has_exactly_the_honest_marginal(dist, bits):
    ch = QuantileChannel(dist, bits)
    s = random_symbols(100_000, ch.levels, RNG(6))
    x = ch.encode(s, RNG(7))
    assert np.mean(ch.decode(x) == s) > 0.999
    # the marginal of the encoded stream is the honest marginal: KS against the honest cdf
    assert sst.kstest(x, dist.cdf).pvalue > 1e-3


def test_level_channel_symbol_error_rate_matches_q_function_theory_under_gaussian_jitter():
    """M-PAM with nearest-level decoding: SER = 2 (1 - 1/M) Q(step / (2 sigma)) for equiprobable symbols."""
    M, step, sigma = 4, 0.02, 0.006
    ch = LevelChannel(M, t0=0.1, step=step)
    n = 600_000
    s = random_symbols(n, M, RNG(8))
    obs = ch.encode(s) + sigma * RNG(9).standard_normal(n)
    ser = np.mean(ch.decode(obs) != s)
    theory = 2 * (1 - 1 / M) * sst.norm.sf(step / (2 * sigma))
    se = math.sqrt(theory * (1 - theory) / n)
    assert abs(ser - theory) < 5 * se


# ------------------------------------------------------------------ statistics: known answers
EDGES8 = LogNormalIID().ppf(np.linspace(0, 1, 9)[1:-1])


def test_cce_known_answers():
    n = 4000
    iid = LogNormalIID().sample(n, RNG(10))
    # log2(8) = 3 bits, minus the plug-in entropy bias at m = 3 (the minimising pattern length):
    # ((8^3 - 1) - (8^2 - 1)) / (2 n ln 2) = 0.081 bits, so 2.919. Measured over 12 seeds: 2.9174 +- 0.0035.
    assert S.cce(iid, EDGES8) == pytest.approx(2.919, abs=0.012)
    periodic = np.tile(LogNormalIID().ppf([0.05, 0.3, 0.6, 0.9]), n // 4)
    assert S.cce(periodic, EDGES8) < 0.05
    assert S.cce(np.full(n, 0.03), EDGES8) == pytest.approx(0.0, abs=1e-12)
    first_order_markov = np.array([0.03, 0.03, 0.09, 0.03] * (n // 4))     # deterministic pattern of period 4
    assert S.cce(first_order_markov, EDGES8) < 0.05


def test_cce_low_for_bursty_traffic_high_for_iid_with_same_marginal():
    b = BurstyMarkov()
    edges = b.ppf(np.linspace(0, 1, 9)[1:-1])
    real = b.sample(20_000, RNG(11))
    shuffled = RNG(12).permutation(real)                                   # same marginal, structure destroyed
    assert S.cce(real, edges) < S.cce(shuffled, edges) - 0.15


def test_regularity_separates_constant_variance_from_bursty():
    rng = RNG(13)
    steady = 0.03 + 0.005 * rng.standard_normal(200)
    bursty = BurstyMarkov().sample(200, rng)
    assert S.regularity(steady) < S.regularity(bursty)
    assert S.regularity(np.full(200, 0.03)) == 0.0
    with pytest.raises(ValueError):
        S.regularity(np.ones(30))


def test_eps_similarity_known_answers():
    x = np.array([1.0, 1.01, 1.02, 2.0, 2.01, 5.0])
    # sorted relative gaps: .01, .0099, .96, .005, 1.49 -> 3 of 5 below 0.05
    assert S.eps_similarity(x, 0.05) == pytest.approx(3 / 5)
    assert S.eps_similarity(np.geomspace(1, 100, 50), 0.05) == 0.0
    with pytest.raises(ValueError):
        S.eps_similarity([1.0, -1.0])


def test_ks_stat_matches_scipy_including_ties_and_disjoint_supports():
    rng = RNG(14)
    a, b = rng.normal(size=300), rng.normal(0.4, 1, size=5000)
    assert S.ks_stat(a, np.sort(b)) == pytest.approx(sst.ks_2samp(a, b).statistic, abs=1e-12)
    for _ in range(200):                                        # heavy ties, tiny alphabets, shared values
        na, nb = int(rng.integers(1, 40)), int(rng.integers(1, 60))
        xa, xb = rng.integers(0, 6, na).astype(float), rng.integers(0, 6, nb).astype(float)
        assert S.ks_stat(xa, np.sort(xb)) == pytest.approx(sst.ks_2samp(xa, xb).statistic, abs=1e-12)
    assert S.ks_stat([10.0, 11.0], np.array([1.0, 2.0, 3.0])) == 1.0                  # disjoint
    assert S.ks_stat([2.0], np.array([2.0])) == 0.0


def test_compress_ratio_orders_structure():
    edges = EDGES8
    periodic = np.tile(LogNormalIID().ppf([0.05, 0.3, 0.6, 0.9]), 500)
    noise = LogNormalIID().sample(2000, RNG(15))
    assert S.compress_ratio(periodic, edges) < 0.1 < S.compress_ratio(noise, edges)
    assert 0 < S.compress_ratio(noise, edges) < 1.2


def test_lag1_autocorr_of_a_known_ar1_process():
    rng = RNG(16)
    phi, n = 0.7, 200_000
    e = rng.standard_normal(n)
    z = np.empty(n)
    z[0] = e[0]
    for i in range(1, n):
        z[i] = phi * z[i - 1] + e[i]
    assert S.lag1_autocorr(np.exp(z)) == pytest.approx(phi, abs=0.01)
