"""Anytime-valid monitoring of a stream of per-packet verification flags.

Appendix A gives a fixed-sample detection probability. A deployed verifier does
not stop at a fixed sample size and it has a non-zero honest false-flag rate
(numerical nondeterminism, tolerance thresholds). This module supplies:

* :class:`BernoulliMixtureEProcess` - a test martingale for
  ``H0: flags ~ iid Bernoulli(p0)`` against any larger flag rate. Under H0 it has
  expectation exactly 1 at every time, so by Ville's inequality
  ``P(exists t: E_t >= 1/alpha) <= alpha``: you may look after every packet, and
  stop whenever you like, without inflating the false-alarm rate.
* :func:`e_bh` - e-BH (Wang & Ramdas 2022): FDR control across many clusters
  under *arbitrary* dependence, from their e-values.

The mixture is a finite average of likelihood-ratio martingales, so validity is
exact (not approximate); the grid only affects power.
"""
from __future__ import annotations

import math

import numpy as np


def _logsumexp(a, axis=None):
    a = np.asarray(a, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        m = np.max(a, axis=axis, keepdims=True)
        m = np.where(np.isfinite(m), m, 0.0)
        out = m + np.log(np.sum(np.exp(a - m), axis=axis, keepdims=True))
    if axis is None:
        return float(out.reshape(()))
    return np.squeeze(out, axis=axis)


def _grid(p0: float, n_grid: int, u_min: float, u_max: float):
    if not (0.0 < p0 < 1.0):
        raise ValueError("p0 must be in (0, 1)")
    if n_grid < 2 or not (0.0 < u_min < u_max < 1.0):
        raise ValueError("need n_grid >= 2 and 0 < u_min < u_max < 1")
    u = np.geomspace(u_min, u_max, n_grid)          # log-spaced excess over p0
    p = p0 + (1.0 - p0) * u
    a = np.log(p / p0)                              # log-LR of a flagged packet
    b = np.log1p(-p) - math.log1p(-p0)              # log-LR of an unflagged packet
    return p, a, b


class BernoulliMixtureEProcess:
    """Mixture over alternatives ``p in (p0, 1)`` with log-uniform weight on the excess."""

    def __init__(self, p0: float, n_grid: int = 64, u_min: float = 1e-3, u_max: float = 0.999):
        self.p0 = float(p0)
        self.p, self._a, self._b = _grid(self.p0, n_grid, u_min, u_max)
        self._logw = -math.log(n_grid)
        self._logL = np.zeros(n_grid)
        self.n = 0
        self.k = 0

    def update(self, flags=None, *, n: int | None = None, k: int | None = None):
        """Feed an array of 0/1 flags, or batch counts ``n`` audited / ``k`` flagged."""
        if flags is not None:
            arr = np.asarray(flags).astype(bool).ravel()
            n_, k_ = int(arr.size), int(arr.sum())
        else:
            if n is None or k is None:
                raise ValueError("give flags, or both n and k")
            n_, k_ = int(n), int(k)
        if not (0 <= k_ <= n_):
            raise ValueError("need 0 <= k <= n")
        self._logL += k_ * self._a + (n_ - k_) * self._b
        self.n += n_
        self.k += k_
        return self

    @property
    def log_e(self) -> float:
        return float(_logsumexp(self._logL)) + self._logw

    @property
    def e_value(self) -> float:
        le = self.log_e
        return math.exp(le) if le < 700.0 else math.inf

    def rejects(self, alpha: float) -> bool:
        """True once ``E >= 1/alpha``. Time-uniformly valid at level ``alpha``."""
        if not (0.0 < alpha < 1.0):
            raise ValueError("alpha must be in (0, 1)")
        return self.log_e >= math.log(1.0 / alpha)


def log_e_paths(flags, p0: float, n_grid: int = 64, u_min: float = 1e-3, u_max: float = 0.999):
    """log E_t for many independent flag streams at once. ``flags``: (streams, T) bool."""
    flags = np.asarray(flags).astype(bool)
    if flags.ndim == 1:
        flags = flags[None, :]
    S, T = flags.shape
    _, a, b = _grid(p0, n_grid, u_min, u_max)
    logw = -math.log(n_grid)
    logL = np.zeros((S, n_grid))
    out = np.empty((S, T))
    for t in range(T):
        logL += np.where(flags[:, t][:, None], a[None, :], b[None, :])
        out[:, t] = _logsumexp(logL, axis=1) + logw
    return out


def log_e_from_counts(n, k, p0: float, n_grid: int = 64, u_min: float = 1e-3, u_max: float = 0.999):
    """log E after ``n`` audits with ``k`` flags (``k`` may be an array). Vectorised, O(len(k) * n_grid)."""
    k = np.asarray(k, dtype=float)
    if np.any(k < 0) or np.any(k > n):
        raise ValueError("need 0 <= k <= n")
    _, a, b = _grid(p0, n_grid, u_min, u_max)
    logL = k[..., None] * a + (n - k)[..., None] * b
    return _logsumexp(logL, axis=-1) - math.log(n_grid)


def first_alarm_step(log_e_path, alpha: float) -> np.ndarray:
    """Index (0-based) of the first step with E >= 1/alpha per stream, or -1."""
    p = np.atleast_2d(np.asarray(log_e_path))
    hit = p >= math.log(1.0 / alpha)
    idx = np.where(hit.any(axis=1), hit.argmax(axis=1), -1)
    return idx


def e_bh(e_values, alpha: float) -> np.ndarray:
    """e-BH: reject the ``k*`` largest e-values, ``k* = max{k : e_(k) >= m / (alpha k)}``.

    Controls FDR at ``alpha`` under arbitrary dependence between the e-values
    (Wang & Ramdas, 2022). Returns a boolean rejection mask.
    """
    if not (0.0 < alpha < 1.0):
        raise ValueError("alpha must be in (0, 1)")
    e = np.asarray(e_values, dtype=float)
    m = e.size
    rej = np.zeros(m, dtype=bool)
    if m == 0:
        return rej
    order = np.argsort(-e, kind="stable")
    ks = np.arange(1, m + 1)
    ok = e[order] >= m / (alpha * ks)
    if ok.any():
        kstar = int(np.nonzero(ok)[0].max()) + 1
        rej[order[:kstar]] = True
    return rej
