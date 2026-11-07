"""Synthetic honest traffic. Parameters are illustrative, not measurements of any real server.

Two generators:

* :class:`LogNormalIID`  - i.i.d. lognormal inter-packet delays. Simple, and exactly matchable by an adversary.
* :class:`BurstyMarkov`  - two-state (burst / idle) Markov-modulated lognormal. Has temporal structure that a
  marginal-only adversary destroys.

Use :func:`load_ipd_csv` to run everything on a real timestamp trace instead.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import special

_TINY = 1e-300
_Q_LO, _Q_HI = 1e-16, float(np.nextafter(1.0, 0.0))


@dataclass(frozen=True)
class LogNormalIID:
    """Median 30 ms, log-sd 0.6 by default."""
    mu: float = math.log(0.03)
    sigma: float = 0.6

    def sample(self, n: int, rng: np.random.Generator) -> np.ndarray:
        return np.exp(self.mu + self.sigma * rng.standard_normal(n))

    def cdf(self, x):
        x = np.maximum(np.asarray(x, dtype=float), _TINY)
        return special.ndtr((np.log(x) - self.mu) / self.sigma)

    def ppf(self, q):
        q = np.clip(np.asarray(q, dtype=float), _Q_LO, _Q_HI)
        return np.exp(self.mu + self.sigma * special.ndtri(q))


@dataclass(frozen=True)
class BurstyMarkov:
    """Burst state: median 20 ms; idle state: median 250 ms. Stays in burst w.p. 0.92, in idle w.p. 0.75."""
    mu_b: float = math.log(0.02)
    s_b: float = 0.35
    mu_i: float = math.log(0.25)
    s_i: float = 0.55
    p_bb: float = 0.92
    p_ii: float = 0.75

    def stationary_burst(self) -> float:
        return (1.0 - self.p_ii) / ((1.0 - self.p_bb) + (1.0 - self.p_ii))

    def sample(self, n: int, rng: np.random.Generator) -> np.ndarray:
        u = rng.random(n)
        z = rng.standard_normal(n)
        burst = np.empty(n, dtype=bool)
        state = rng.random() < self.stationary_burst()
        for i in range(n):
            burst[i] = state
            state = (u[i] < self.p_bb) if state else (u[i] >= self.p_ii)
        return np.exp(np.where(burst, self.mu_b + self.s_b * z, self.mu_i + self.s_i * z))

    def cdf(self, x):
        """Stationary marginal CDF: a two-component lognormal mixture."""
        x = np.maximum(np.asarray(x, dtype=float), _TINY)
        lx = np.log(x)
        pb = self.stationary_burst()
        return pb * special.ndtr((lx - self.mu_b) / self.s_b) + (1 - pb) * special.ndtr((lx - self.mu_i) / self.s_i)

    def ppf(self, q):
        """Numerical inverse of :meth:`cdf` (log-grid interpolation, relative error below 1e-6)."""
        lo = min(self.mu_b - 9 * self.s_b, self.mu_i - 9 * self.s_i)
        hi = max(self.mu_b + 9 * self.s_b, self.mu_i + 9 * self.s_i)
        grid = np.linspace(lo, hi, 200_001)
        c = self.cdf(np.exp(grid))
        return np.exp(np.interp(np.clip(np.asarray(q, dtype=float), _Q_LO, _Q_HI), c, grid))


def to_timestamps(ipd, t0: float = 0.0) -> np.ndarray:
    """``n`` inter-packet delays -> ``n + 1`` timestamps starting at ``t0`` (packet 0 is at ``t0``)."""
    d = np.asarray(ipd, dtype=float)
    return np.concatenate([[t0], t0 + np.cumsum(d)])


def to_ipd(timestamps) -> np.ndarray:
    """``n + 1`` non-decreasing timestamps -> ``n`` delays. Exact inverse of :func:`to_timestamps` up to rounding."""
    t = np.asarray(timestamps, dtype=float)
    if t.size < 2 or np.any(np.diff(t) < 0):
        raise ValueError("timestamps must be non-decreasing with at least two entries")
    return np.diff(t)


def load_ipd_csv(path: str, column: int = 0, timestamps: bool = True) -> np.ndarray:
    """Read one numeric column of a CSV and return delays (or the raw column if ``timestamps=False``).

    Leading non-numeric lines are treated as a header and skipped. A non-numeric or short row *after* data
    has started raises ``ValueError`` with its line number instead of silently shortening the trace.
    """
    vals, started = [], False
    with open(path) as fh:
        for lineno, line in enumerate(fh, 1):
            if not line.strip():
                continue
            cells = line.strip().split(",")
            try:
                v = float(cells[column].strip())
            except (ValueError, IndexError):
                if started:
                    raise ValueError(f"{path}:{lineno}: non-numeric or missing value in column {column}")
                continue
            started = True
            vals.append(v)
    arr = np.asarray(vals, dtype=float)
    return to_ipd(arr) if timestamps else arr
