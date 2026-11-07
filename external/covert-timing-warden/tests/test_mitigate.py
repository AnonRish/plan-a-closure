import math

import numpy as np
import pytest
from hypothesis import given, settings, strategies as st
from scipy import stats as sst

from covert_timing_warden import capacity as cap
from covert_timing_warden import mitigate as M


# ------------------------------------------------------------------ quantised release
def test_quantizer_hand_cases_including_float_traps():
    q = M.QuantizedRelease(0.01)
    out = q.apply([0.0, 0.004, 0.01, 0.0100001, 0.03, 0.031])
    assert out == pytest.approx([0.0, 0.01, 0.01, 0.02, 0.03, 0.04], abs=1e-12)     # 0.03 / 0.01 = 2.9999999999999996


@settings(max_examples=200, deadline=None)
@given(delta=st.floats(1e-3, 1.0), ts=st.lists(st.floats(0, 1e3), min_size=1, max_size=40))
def test_quantizer_properties(delta, ts):
    ts = np.sort(np.array(ts))
    out = M.QuantizedRelease(delta).apply(ts)
    assert np.all(out >= ts - 1e-6)
    assert np.all(out - ts < delta + 1e-6)                                    # at most one tick of delay
    assert np.all(np.diff(out) >= -1e-12)
    ticks = out / delta
    assert np.allclose(ticks, np.rint(ticks), atol=1e-6)                     # on the grid
    assert np.allclose(M.QuantizedRelease(delta).apply(out), out, atol=1e-9)   # idempotent


@pytest.mark.parametrize("D,delta,lo,hi", [
    (0.3, 0.1, 2.0, 2.0),                                   # 0.3 / 0.1 = 2.9999999999999996 must count as exactly 3
    (3.0, 1.0, 2.0, 2.0),
    (3.5, 1.0, 2.0, math.log2(5)),
    (0.5, 1.0, 0.0, 1.0),                                   # the 1-bit floor of the upper bound
    (0.0, 1.0, 0.0, 0.0),
    (1.0, 1.0, 1.0, 1.0),
])
def test_quantizer_capacity_brackets(D, delta, lo, hi):
    b = M.QuantizedRelease(delta).capacity(D)
    assert (b.lower_bits, b.upper_bits) == (pytest.approx(lo), pytest.approx(hi))


@pytest.mark.parametrize("D", [0.5, 1.0, 1.7, 2.5, 3.0, 3.75])
def test_quantizer_upper_bound_by_brute_force_enumeration(D):
    """Delta = 1. For every arrival phase, count the distinct tick increments an extra delay in [0, D] can produce."""
    phases = np.linspace(0.0, 1.0, 2001, endpoint=False)
    xs = np.linspace(0.0, D, 4001)
    best = 0
    for a in phases:
        inc = np.ceil(a + xs - 1e-9) - math.ceil(a - 1e-9)
        best = max(best, len(np.unique(inc)))
    assert best == math.ceil(D) + 1                          # never exceeded, and attained at phase 0
    assert M.QuantizedRelease(1.0).capacity(D).upper_bits == pytest.approx(math.log2(best))


@pytest.mark.parametrize("q", [1, 2, 7, 31])
def test_quantizer_lower_bound_is_achieved_error_free(q):
    rng = np.random.default_rng(q)
    sym = rng.integers(0, q + 1, 100_000)
    assert np.array_equal(M.lattice_roundtrip_quantizer(sym, 10_000_000), sym)
    assert M.QuantizedRelease(1.0).capacity(float(q)).lower_bits == pytest.approx(math.log2(q + 1))


# ------------------------------------------------------------------ jitter
def test_jitter_adds_uniform_delay_when_arrivals_are_far_apart():
    rng = np.random.default_rng(1)
    w = 0.005
    arrivals = np.arange(100_000) * 1.0
    added = M.UniformJitter(w).apply(arrivals, rng) - arrivals
    assert np.all(added >= 0) and np.all(added < w)
    assert sst.kstest(added / w, "uniform").pvalue > 1e-3
    assert added.mean() == pytest.approx(M.UniformJitter(w).mean_added_latency, abs=5 * w / math.sqrt(12 * added.size))


@settings(max_examples=100, deadline=None)
@given(w=st.floats(1e-4, 0.5), ts=st.lists(st.floats(0, 100), min_size=2, max_size=60), seed=st.integers(0, 10**6))
def test_jitter_output_is_fifo_and_never_earlier(w, ts, seed):
    ts = np.sort(np.array(ts))
    out = M.UniformJitter(w).apply(ts, np.random.default_rng(seed))
    assert np.all(out >= ts)
    assert np.all(np.diff(out) >= 0)


@pytest.mark.parametrize("D,w,lo,hi", [(3.0, 1.0, 2.0, math.log2(5)), (0.5, 1.0, 0.0, math.log2(2.5)), (8.0, 1.0, math.log2(9), math.log2(10))])
def test_jitter_capacity_brackets(D, w, lo, hi):
    b = M.UniformJitter(w).capacity(D)
    assert (b.lower_bits, b.upper_bits) == (pytest.approx(lo), pytest.approx(hi))


@settings(max_examples=100, deadline=None)
@given(D=st.floats(0, 100), unit=st.floats(0.01, 10))
def test_every_bracket_is_ordered(D, unit):
    for mit in (M.QuantizedRelease(unit), M.UniformJitter(unit), M.FixedSchedule(unit)):
        b = mit.capacity(D)
        assert 0 <= b.lower_bits <= b.upper_bits + 1e-12


@pytest.mark.parametrize("m,w_ns", [(1, 1000), (3, 1000), (7, 4096), (15, 1_000_000)])
def test_jitter_lower_bound_is_achieved_error_free_with_shared_clock(m, w_ns):
    rng = np.random.default_rng(m)
    sym = rng.integers(0, m + 1, 200_000)
    assert np.array_equal(M.lattice_roundtrip_jitter(sym, w_ns, w_ns, rng), sym)
    assert np.array_equal(M.lattice_roundtrip_jitter(sym, w_ns, w_ns // 2, rng), sym)     # less jitter than spacing
    assert M.UniformJitter(1.0).capacity(float(m)).lower_bits == pytest.approx(math.log2(m + 1))


def test_negative_control_decoder_fails_when_jitter_exceeds_spacing():
    """Same decoder, jitter of twice the spacing (bypassing the guard): errors must appear, or the test above is vacuous."""
    rng = np.random.default_rng(0)
    s = 1000
    sym = rng.integers(0, 4, 50_000)
    request = s * np.cumsum(sym)
    released = np.maximum.accumulate(request + rng.integers(0, 2 * s, sym.size))
    decoded = np.diff(np.concatenate([[0], released // s]))
    assert np.mean(decoded != sym) > 0.1
    with pytest.raises(ValueError):
        M.lattice_roundtrip_jitter(sym, s, 2 * s, rng)


def _tri_cdf(z, w):
    z = np.asarray(z, float)
    return np.where(z <= -w, 0.0, np.where(z <= 0, (z + w) ** 2 / (2 * w * w), np.where(z < w, 1 - (w - z) ** 2 / (2 * w * w), 1.0)))


@pytest.mark.parametrize("m", [1, 2, 4])
def test_naive_per_ipd_bound_undercounts_what_the_lattice_scheme_achieves(m):
    h, w = 0.1, 1.0
    xs = np.arange(0, m * w + h / 2, h)
    edges = np.arange(-w - h / 2, m * w + w + 1.5 * h, h)
    naive = cap.blahut_arimoto(cap.additive_noise_channel(xs, edges, lambda z: _tri_cdf(z, w)), tol_bits=1e-7).upper_bits
    achieved = M.UniformJitter(w).capacity(m * w).lower_bits
    assert naive < 0.8 * achieved            # measured: misses 36 %, 29 %, 24 % at D/w = 1, 2, 4


def _block2_matrix(m, k):
    """Two packets, known start, Y1 = X1 + N1, Y2 = X1 + X2 + N2, N ~ U[0, 1]; grid 1/k, output bins aligned to the noise."""
    h = 1.0 / k
    xs = np.arange(0, m * k + 1) * h
    f = lambda z: np.clip(z, 0, 1)
    chan = lambda inp, edges: np.diff(f(edges[None, :] - inp[:, None]), axis=1)
    P1 = chan(xs, np.arange(0, (m + 1) * k + 1) * h)
    P2 = chan(np.arange(0, 2 * m * k + 1) * h, np.arange(0, (2 * m + 1) * k + 1) * h)
    nx = xs.size
    Pj = np.zeros((nx * nx, P1.shape[1] * P2.shape[1]))
    for i in range(nx):
        for j in range(nx):
            Pj[i * nx + j] = np.outer(P1[i], P2[i + j]).ravel()
    return Pj


@pytest.mark.parametrize("m", [1, 2, 3])
def test_two_packet_block_channel_matches_lattice_when_bins_are_aligned(m):
    r = M_cap(_block2_matrix(m, 1))
    assert r.lower_bits / 2 == pytest.approx(math.log2(1 + m), abs=1e-6)


@pytest.mark.parametrize("m,k", [(1, 4), (2, 4)])
def test_two_packet_block_capacity_sits_strictly_inside_the_bracket(m, k):
    """Finer grids beat the lattice rate (the bracket's lower end is not the capacity) but never the proven upper bound."""
    r = M_cap(_block2_matrix(m, k))
    per_packet = r.lower_bits / 2
    b = M.UniformJitter(1.0).capacity(float(m))
    assert per_packet > b.lower_bits + 0.03
    assert per_packet < b.upper_bits - 0.1


def M_cap(P):
    return cap.blahut_arimoto(P, tol_bits=1e-7, max_iter=50_000)


# ------------------------------------------------------------------ fixed schedule
def test_fixed_schedule_hand_case():
    fs = M.FixedSchedule(1.0)
    arr = [0.2, 0.3, 0.4, 5.0]
    assert fs.release_times(arr) == pytest.approx([1, 2, 3, 5])
    assert fs.latency(arr) == pytest.approx([0.8, 1.7, 2.6, 0.0])


def test_fixed_schedule_observable_stream_is_independent_of_arrivals():
    """Whatever the arrivals, real packets occupy distinct scheduled ticks and dummies fill the rest: the observer's
    view is the whole tick grid in every case."""
    fs = M.FixedSchedule(0.02)
    rng = np.random.default_rng(3)
    horizon, n_ticks = 10.0, 500
    grid = np.arange(1, n_ticks + 1)
    processes = {
        "uniform": np.sort(rng.random(100) * 9.0),
        "bursty": np.sort(np.concatenate([rng.random(50) * 0.5, 8.0 + rng.random(50) * 0.5])),
        "single burst": np.full(100, 4.0),
    }
    views = []
    for name, arr in processes.items():
        rel = fs.release_times(arr)
        ticks = np.rint(rel / 0.02).astype(int)
        assert rel.max() <= horizon, name                                   # nothing spills past the horizon
        assert np.all(np.isin(ticks, grid)) and len(np.unique(ticks)) == ticks.size, name
        dummies = np.setdiff1d(grid, ticks)                                 # every other tick carries a dummy
        views.append(np.sort(np.concatenate([ticks, dummies])))
    for v in views:
        assert np.array_equal(v, grid)                                      # identical observer view in all cases
    assert np.array_equal(np.rint(fs.observable(horizon) / 0.02).astype(int), grid)
    assert fs.capacity().lower_bits == fs.capacity().upper_bits == 0.0


def test_fixed_schedule_latency_is_uniform_over_one_period_when_uncongested():
    fs = M.FixedSchedule(0.02)
    n = 100_000
    rng = np.random.default_rng(4)
    arr = np.arange(n) * 0.02 + 0.02 * rng.random(n) * (1 - 1e-9) + 1e-12   # one arrival per tick interval
    lat = fs.latency(arr)
    assert sst.kstest(lat / 0.02, "uniform").pvalue > 1e-3
    assert lat.mean() == pytest.approx(0.01, abs=5 * 0.02 / math.sqrt(12 * n))


def test_fixed_schedule_congestion_and_stability():
    fs = M.FixedSchedule(1.0)
    rng = np.random.default_rng(5)
    def mean_latency(rate, n=40_000):
        arr = np.cumsum(rng.exponential(1.0 / rate, n))
        return fs.latency(arr).mean()
    assert fs.is_stable(0.5) and not fs.is_stable(1.0) and not fs.is_stable(2.0)
    l1, l2, l3 = mean_latency(0.1), mean_latency(0.5), mean_latency(0.9)
    assert l1 < l2 < l3 and l1 == pytest.approx(0.55, abs=0.05)
    over = fs.latency(np.cumsum(rng.exponential(0.5, 20_000)))                 # 2 packets per period: unstable
    assert over[-100:].mean() > 50 * over[:100].mean()


@settings(max_examples=100, deadline=None)
@given(period=st.floats(0.01, 2.0), ts=st.lists(st.floats(0, 100), min_size=1, max_size=50))
def test_fixed_schedule_properties(period, ts):
    ts = np.sort(np.array(ts))
    rel = M.FixedSchedule(period).release_times(ts)
    assert np.all(rel >= ts - 1e-6)
    assert np.all(np.diff(rel) > 0) or rel.size == 1
    assert np.allclose(rel / period, np.rint(rel / period), atol=1e-6)


def test_input_validation():
    with pytest.raises(ValueError):
        M.FixedSchedule(1.0).release_times([2.0, 1.0])
    with pytest.raises(ValueError):
        M.QuantizedRelease(1.0).capacity(-1.0)
    with pytest.raises(ValueError):
        M.UniformJitter(0.0).capacity(1.0)
    with pytest.raises(ValueError):
        M.lattice_roundtrip_quantizer([1], 0)


# ------------------------------------------------------------------ exfiltration arithmetic
def test_exfiltration_time():
    # 1 TB of weights = 8e12 bits; 6 bits/packet, 50 packets/s, 1,000 concurrent streams
    assert M.exfiltration_seconds(8e12, 6, 50, 1000) == pytest.approx(8e12 / 300_000)
    assert M.exfiltration_seconds(8e12, 6, 50, 1000) / 86400 == pytest.approx(308.6, abs=0.1)
    assert math.isinf(M.exfiltration_seconds(8e12, 0.0, 50, 1000))
    assert M.exfiltration_seconds(0, 1, 1) == 0.0
    with pytest.raises(ValueError):
        M.exfiltration_seconds(-1, 1, 1)
