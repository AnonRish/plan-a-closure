"""Channel capacity for timing-channel models, with bounds you can check.

:func:`blahut_arimoto` returns a *bracket* ``[lower, upper]`` on the capacity of
a discrete memoryless channel, both in bits, from the classical Blahut (1972)
bounds ``ln sum_x p_x c_x <= C <= ln max_x c_x`` with
``c_x = exp D(P(.|x) || q)``. A result is only reported as converged when the
bracket is narrower than the tolerance, so "the capacity is X" always comes
with a certificate about *this matrix*. Whether the matrix models the real
channel is a separate question; see :mod:`covert_timing_warden.mitigate`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

LN2 = math.log(2.0)


@dataclass(frozen=True)
class Capacity:
    lower_bits: float
    upper_bits: float
    p_opt: np.ndarray
    iterations: int
    converged: bool

    @property
    def bits(self) -> float:
        """Midpoint of the bracket (use ``lower_bits`` for an achievable rate, ``upper_bits`` for a bound)."""
        return 0.5 * (self.lower_bits + self.upper_bits)


def _check_channel(P) -> np.ndarray:
    P = np.asarray(P, dtype=float)
    if P.ndim != 2 or P.shape[0] < 1 or P.shape[1] < 1:
        raise ValueError("channel matrix must be 2-D with at least one row and column")
    if not np.all(np.isfinite(P)) or np.any(P < 0):
        raise ValueError("channel matrix must be finite and non-negative")
    if not np.allclose(P.sum(axis=1), 1.0, atol=1e-9):
        raise ValueError("each row of the channel matrix must sum to 1")
    return P


def blahut_arimoto(P, tol_bits: float = 1e-9, max_iter: int = 200_000, p0=None, accelerate: bool = True) -> Capacity:
    """Capacity (bits) of the discrete memoryless channel ``P[x, y] = P(y | x)``.

    ``accelerate`` over-relaxes the update, ``p <- p * exp(s * D)`` with ``s`` growing by 10 % per step (cap 64)
    and resetting to 1 whenever the lower bound drops. The bracket is computed from the current ``p`` at every
    step whatever the update rule, so acceleration can change speed but never the validity of the certificate.
    Channels whose optimal input is not unique (e.g. lattice-noise channels) converge sublinearly under plain
    BA: measured 100k to 200k+ iterations for 1e-9 bits, 2.5 to 4x fewer with acceleration.
    """
    P = _check_channel(P)
    nx = P.shape[0]
    if nx == 1:
        return Capacity(0.0, 0.0, np.ones(1), 0, True)
    p = np.full(nx, 1.0 / nx) if p0 is None else np.asarray(p0, dtype=float) / np.sum(p0)
    logP = np.log(np.where(P > 0, P, 1.0))
    pos = P > 0
    tol = tol_bits * LN2
    lower = upper = 0.0
    converged = False
    it = 0
    step, prev_lower = 1.0, -math.inf
    for it in range(1, max_iter + 1):
        q = p @ P
        logq = np.log(np.where(q > 0, q, 1.0))
        D = np.where(pos, P * (logP - logq[None, :]), 0.0).sum(axis=1)   # nats
        dmax = float(D.max())
        lower = dmax + math.log(float(np.sum(p * np.exp(D - dmax))))    # ln sum p_x e^{D_x}, overflow-safe
        upper = dmax
        if upper - lower < tol:
            converged = True
            break
        if accelerate:
            step = 1.0 if lower < prev_lower - 1e-15 else min(step * 1.1, 64.0)
            prev_lower = lower
        p = p * np.exp(step * (D - dmax))
        p = np.maximum(p / p.sum(), 1e-300)
        p /= p.sum()
    return Capacity(max(lower, 0.0) / LN2, upper / LN2, p, it, converged)


# --------------------------------------------------------------------------- #
# Closed forms used as ground truth in the tests
# --------------------------------------------------------------------------- #
def h2(p: float) -> float:
    """Binary entropy in bits."""
    if not (0.0 <= p <= 1.0):
        raise ValueError("p must be in [0, 1]")
    if p in (0.0, 1.0):
        return 0.0
    return -(p * math.log2(p) + (1 - p) * math.log2(1 - p))


def bsc_capacity(p: float) -> float:
    return 1.0 - h2(p)


def bec_capacity(erasure: float) -> float:
    if not (0.0 <= erasure <= 1.0):
        raise ValueError("erasure must be in [0, 1]")
    return 1.0 - erasure


def z_channel_capacity(p: float) -> float:
    """Input 0 is always received as 0; input 1 is received as 0 with probability ``p``."""
    if not (0.0 <= p <= 1.0):
        raise ValueError("p must be in [0, 1]")
    if p == 1.0:
        return 0.0
    if p == 0.0:
        return 1.0
    return math.log2(1.0 + (1.0 - p) * p ** (p / (1.0 - p)))


def uniform_noise_capacity_integer_ratio(m: int) -> float:
    """Capacity of ``Y = X + U[0, w]``, ``X in [0, m w]`` for integer ``m``: ``log2(1 + m)``.

    Upper bound: ``h(Y) <= log2((m+1) w)`` and ``h(N) = log2 w``. Achieved by uniform
    input on the lattice ``{0, w, ..., m w}``, which makes ``Y`` uniform on ``[0, (m+1) w]``.
    """
    if int(m) != m or m < 0:
        raise ValueError("m must be a non-negative integer")
    return math.log2(1 + m)


# --------------------------------------------------------------------------- #
# Numerical helpers
# --------------------------------------------------------------------------- #
def pam_awgn_mutual_information(levels, sigma: float, probs=None, grid: int = 200_001) -> float:
    """I(X; X + N) in bits, X discrete on ``levels``, N ~ Normal(0, sigma^2); by trapezoid integration of h(Y)."""
    x = np.asarray(levels, dtype=float)
    p = np.full(x.size, 1.0 / x.size) if probs is None else np.asarray(probs, dtype=float)
    if sigma <= 0 or not np.isclose(p.sum(), 1.0):
        raise ValueError("need sigma > 0 and probabilities summing to 1")
    y = np.linspace(x.min() - 12 * sigma, x.max() + 12 * sigma, grid)
    py = np.zeros_like(y)
    for xi, pi in zip(x, p):
        py += pi * np.exp(-0.5 * ((y - xi) / sigma) ** 2) / (sigma * math.sqrt(2 * math.pi))
    integrand = np.where(py > 0, -py * np.log2(np.where(py > 0, py, 1.0)), 0.0)
    h_y = float(np.trapezoid(integrand, y))
    h_n = 0.5 * math.log2(2 * math.pi * math.e * sigma**2)
    return h_y - h_n


def additive_noise_channel(x_grid, y_edges, noise_cdf) -> np.ndarray:
    """``P(y_k | x_j) = F(edge_{k+1} - x_j) - F(edge_k - x_j)``; tail mass folded into the end bins."""
    x = np.asarray(x_grid, dtype=float)
    e = np.asarray(y_edges, dtype=float)
    F = noise_cdf(e[None, :] - x[:, None])
    P = np.diff(F, axis=1)
    P[:, 0] += F[:, 0]
    P[:, -1] += 1.0 - F[:, -1]
    return P


def mutual_information_plugin(x, y, miller_madow: bool = True) -> float:
    """Plug-in I(X;Y) in bits from paired integer-coded samples, optionally Miller-Madow corrected."""
    x = np.asarray(x)
    y = np.asarray(y)
    if x.shape != y.shape or x.ndim != 1 or x.size == 0:
        raise ValueError("x and y must be 1-D arrays of equal, non-zero length")
    n = x.size
    _, xi = np.unique(x, return_inverse=True)
    _, yi = np.unique(y, return_inverse=True)
    kx, ky = xi.max() + 1, yi.max() + 1
    joint = np.bincount(xi * ky + yi, minlength=kx * ky).reshape(kx, ky).astype(float)
    pxy = joint / n
    px, py = pxy.sum(axis=1), pxy.sum(axis=0)
    nz = pxy > 0
    mi = float(np.sum(pxy[nz] * np.log(pxy[nz] / (px[:, None] * py[None, :])[nz])))
    if miller_madow:
        mi -= (int(nz.sum()) - int((px > 0).sum()) - int((py > 0).sum()) + 1) / (2.0 * n)
    return mi / LN2
