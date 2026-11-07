import math

import numpy as np
import pytest
from hypothesis import given, settings, strategies as st
from scipy import special, stats

from covert_timing_warden import capacity as cap


def bsc(p):
    return np.array([[1 - p, p], [p, 1 - p]])


@pytest.mark.parametrize("p", [0.0, 0.01, 0.11, 0.25, 0.5])
def test_bsc_matches_closed_form_and_bracket_contains_it(p):
    r = cap.blahut_arimoto(bsc(p))
    assert r.converged
    assert r.lower_bits <= cap.bsc_capacity(p) + 1e-9 <= r.upper_bits + 2e-9
    assert r.bits == pytest.approx(cap.bsc_capacity(p), abs=1e-8)


@pytest.mark.parametrize("e", [0.0, 0.2, 0.9])
def test_bec_matches_closed_form(e):
    P = np.array([[1 - e, e, 0], [0, e, 1 - e]])
    assert cap.blahut_arimoto(P).bits == pytest.approx(cap.bec_capacity(e), abs=1e-8)


@pytest.mark.parametrize("p", [0.1, 0.5, 0.75, 0.95])
def test_z_channel_asymmetric_optimum(p):
    P = np.array([[1.0, 0.0], [p, 1 - p]])
    r = cap.blahut_arimoto(P)
    assert r.converged
    assert r.bits == pytest.approx(cap.z_channel_capacity(p), abs=1e-7)
    assert r.p_opt[1] < 0.5 - 1e-3            # optimum is *not* uniform: the noisy input is used less than half the time


def test_z_channel_known_value():
    assert cap.z_channel_capacity(0.5) == pytest.approx(math.log2(1.25), abs=1e-15)   # 0.3219...


@pytest.mark.parametrize("M", [1, 2, 7, 64])
def test_noiseless_channel_capacity_is_log_m(M):
    assert cap.blahut_arimoto(np.eye(M)).bits == pytest.approx(math.log2(M), abs=1e-9)


def test_useless_channel_has_zero_capacity():
    P = np.tile([0.3, 0.7], (5, 1))
    assert cap.blahut_arimoto(P).upper_bits == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize("m,k", [(1, 1), (3, 2), (4, 3), (8, 4), (5, 1)])
def test_discrete_uniform_noise_channel_matches_log2_one_plus_ratio(m, k):
    """Inputs on a grid of m*k+1 cells, noise uniform over k consecutive cells: C = log2(1 + m) (D/w = m)."""
    J = m * k
    P = np.zeros((J + 1, J + k))
    for j in range(J + 1):
        P[j, j:j + k] = 1.0 / k
    r = cap.blahut_arimoto(P, tol_bits=1e-8)
    assert r.converged
    assert r.lower_bits - 1e-8 <= cap.uniform_noise_capacity_integer_ratio(m) <= r.upper_bits + 1e-8
    assert r.bits == pytest.approx(math.log2(1 + m), abs=1e-7)


def _fine_grid_capacity(h, w=1.0, D=3.0):
    xs = np.arange(0, D + h / 2, h)
    edges = np.arange(-h / 2, D + w + 1.5 * h, h)
    P = cap.additive_noise_channel(xs, edges, lambda z: np.clip(z / w, 0, 1))
    return cap.blahut_arimoto(P, tol_bits=1e-8).bits


def test_continuous_uniform_noise_limit_is_approached_linearly_in_the_grid_step():
    """D/w = 3, continuous capacity log2(1 + 3) = 2. Measured: 2 - C = 0.149, 0.0748, 0.0374 at h = 0.2, 0.1, 0.05."""
    c = {h: _fine_grid_capacity(h) for h in (0.2, 0.1, 0.05)}
    assert c[0.2] < c[0.1] < c[0.05] < 2.0                       # monotone from below
    assert (2 - c[0.1]) / (2 - c[0.05]) == pytest.approx(2.0, rel=0.02)     # error halves when h halves
    assert 2 * c[0.05] - c[0.1] == pytest.approx(2.0, abs=1e-3)  # Richardson extrapolation lands on log2(1+3)


def test_pam_awgn_mutual_information_limits():
    assert cap.pam_awgn_mutual_information([0, 1], 1e-3) == pytest.approx(1.0, abs=1e-6)          # high SNR: log2 M
    assert cap.pam_awgn_mutual_information(np.arange(8.0), 0.02) == pytest.approx(3.0, abs=1e-6)
    assert cap.pam_awgn_mutual_information([0, 1], 50.0) < 1e-3                                  # low SNR
    # binary antipodal at sigma = 1 (0 dB): 0.4859441541 from independent mpmath quadrature (my first constant, 0.48642, was misremembered)
    assert cap.pam_awgn_mutual_information([-1, 1], 1.0) == pytest.approx(0.4859441541, abs=1e-8)


def test_blahut_arimoto_capacity_dominates_uniform_input_mi_on_gaussian_channel():
    levels = np.arange(4.0)
    sigma = 0.55
    edges = np.linspace(-6 * sigma, 3 + 6 * sigma, 500)
    P = cap.additive_noise_channel(levels, edges, lambda z: special.ndtr(z / sigma))
    r = cap.blahut_arimoto(P, tol_bits=1e-9)
    mi_uniform = cap.pam_awgn_mutual_information(levels, sigma)
    assert r.converged
    assert r.upper_bits >= mi_uniform - 5e-4          # capacity >= MI of any input (edges quantise, so allow a hair)
    assert r.lower_bits <= math.log2(4) + 1e-9


@settings(max_examples=60, deadline=None)
@given(nx=st.integers(2, 6), ny=st.integers(2, 6), seed=st.integers(0, 10**6))
def test_random_channels_bracket_and_bounds(nx, ny, seed):
    rng = np.random.default_rng(seed)
    P = rng.dirichlet(np.ones(ny) * 0.4, size=nx)
    r = cap.blahut_arimoto(P, tol_bits=1e-9)
    assert r.converged
    assert 0 <= r.lower_bits <= r.upper_bits + 1e-12
    assert r.upper_bits - r.lower_bits < 2e-9
    assert r.upper_bits <= math.log2(min(nx, ny)) + 1e-9
    # any input distribution gives a lower bound
    pu = np.full(nx, 1 / nx)
    q = pu @ P
    mi_u = float(np.sum(pu[:, None] * P * np.log2(np.where(P > 0, P / q[None, :], 1.0))))
    assert r.lower_bits >= mi_u - 1e-9


def test_input_validation():
    with pytest.raises(ValueError):
        cap.blahut_arimoto([[0.5, 0.6]])
    with pytest.raises(ValueError):
        cap.blahut_arimoto([[-0.1, 1.1]])
    with pytest.raises(ValueError):
        cap.blahut_arimoto([1.0, 0.0])


def test_single_input_row_has_zero_capacity():
    assert cap.blahut_arimoto([[0.2, 0.8]]).bits == 0.0


@pytest.mark.parametrize("p", [0.05, 0.2, 0.4])
def test_plugin_mi_estimator_recovers_bsc_capacity_without_bias(p):
    """Over 24 seeds the mean error must vanish; a single-seed check at 2.2 sigma was flaky (see VERIFICATION_LOG)."""
    errs = []
    for seed in range(24):
        rng = np.random.default_rng(1000 + seed)
        n = 200_000
        xs = rng.integers(0, 2, n)
        ys = xs ^ (rng.random(n) < p)
        errs.append(cap.mutual_information_plugin(xs, ys) - cap.bsc_capacity(p))
    errs = np.array(errs)
    assert abs(errs.mean()) < 5 * errs.std(ddof=1) / math.sqrt(errs.size) + 1e-6
    assert errs.std(ddof=1) < 4e-3


def test_plugin_mi_bias_matches_the_chi_square_prediction_and_the_correction_removes_it():
    """Independent 16x16 samples: naive bias is (kx-1)(ky-1)/(2 n ln2) = 0.0081 bits, sd 0.0008 (chi-square)."""
    rng = np.random.default_rng(4)
    n, k = 20_000, 16
    naive_vals, corrected_vals = [], []
    for _ in range(20):
        xs, ys = rng.integers(0, k, n), rng.integers(0, k, n)
        naive_vals.append(cap.mutual_information_plugin(xs, ys, miller_madow=False))
        corrected_vals.append(cap.mutual_information_plugin(xs, ys))
    predicted = (k - 1) ** 2 / (2 * n * math.log(2))
    assert np.mean(naive_vals) == pytest.approx(predicted, rel=0.05)
    assert abs(np.mean(corrected_vals)) < 3e-4


def test_accelerated_and_plain_blahut_arimoto_agree():
    rng = np.random.default_rng(9)
    for _ in range(25):
        nx, ny = rng.integers(2, 9), rng.integers(2, 9)
        P = rng.dirichlet(np.ones(ny) * 0.5, size=nx)
        a = cap.blahut_arimoto(P, tol_bits=1e-10, accelerate=True)
        b = cap.blahut_arimoto(P, tol_bits=1e-10, accelerate=False)
        assert a.converged and b.converged
        assert max(a.lower_bits, b.lower_bits) <= min(a.upper_bits, b.upper_bits) + 1e-9     # brackets overlap
        assert a.bits == pytest.approx(b.bits, abs=3e-10)


def test_acceleration_reduces_iterations_on_a_degenerate_channel():
    m, k = 3, 2
    P = np.zeros((m * k + 1, m * k + k))
    for j in range(m * k + 1):
        P[j, j:j + k] = 1.0 / k
    fast = cap.blahut_arimoto(P, tol_bits=1e-9, accelerate=True)
    slow = cap.blahut_arimoto(P, tol_bits=1e-9, accelerate=False)
    assert fast.converged and slow.converged
    assert fast.iterations < 0.6 * slow.iterations
