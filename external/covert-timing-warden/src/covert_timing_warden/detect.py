"""Distribution-free detection: conformal p-values from honest reference windows.

Validity is marginal over the choice of null windows. For one fixed warden with ``R`` null windows the realised
false-alarm rate at level ``a`` fluctuates around ``a`` with standard deviation about ``sqrt(a (1 - a) / (R + 2))``
(measured: 0.0197 at R = 520, a = 0.2); average over calibrations and it is at most ``a``.

The warden cuts an honest reference into a *pool* (quantile edges, KS reference) and a stream of *null windows*.
For each statistic the p-value of a new window is the rank of its statistic among the null windows,

    p = min(1, 2 * min( (1 + #{null <= s}) / (R + 1), (1 + #{null >= s}) / (R + 1) )),

which is super-uniform under the null whenever the new window is exchangeable with the null windows (finite-sample
exact, no distributional assumption). The combined p-value is Bonferroni over detectors. Exchangeability is the
whole assumption: honest traffic that drifts, or a reference from a different server, voids it.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .stats import DETECTORS, Context


def min_reference_windows(alpha: float, n_detectors: int) -> int:
    """Fewest null windows for which the combined p-value can reach ``alpha`` at all: ``2 k / (R + 1) <= alpha``."""
    if not (0.0 < alpha < 1.0) or n_detectors < 1:
        raise ValueError("need 0 < alpha < 1 and at least one detector")
    return math.ceil(2 * n_detectors / alpha - 1)


def conformal_p(null_sorted, value: float) -> float:
    """Two-sided conformal p-value of ``value`` among the ascending null statistics ``null_sorted``.

    Ties count against the alarm (both tails are inclusive), so the p-value stays super-uniform.
    """
    null_sorted = np.asarray(null_sorted)
    R = null_sorted.size
    p_lo = (1 + np.searchsorted(null_sorted, value, side="right")) / (R + 1)
    p_hi = (1 + R - np.searchsorted(null_sorted, value, side="left")) / (R + 1)
    return float(min(1.0, 2.0 * min(p_lo, p_hi)))


@dataclass(frozen=True)
class WardenResult:
    stats: dict
    p_values: dict
    p_combined: float
    alarm: bool
    triggered: tuple      # detectors whose own p-value is <= alpha / k


class Warden:
    def __init__(self, reference, window: int = 200, n_symbols: int = 8, alpha: float = 0.01, detectors=None):
        names = tuple(detectors) if detectors is not None else tuple(DETECTORS)
        unknown = set(names) - set(DETECTORS)
        if unknown:
            raise ValueError(f"unknown detectors: {sorted(unknown)}")
        ref = np.asarray(reference, dtype=float)
        if ref.ndim != 1 or np.any(ref <= 0) or not np.all(np.isfinite(ref)):
            raise ValueError("reference must be a 1-D array of finite, strictly positive delays")
        half = ref.size // 2
        pool, null_stream = ref[:half], ref[half:]
        R = null_stream.size // window
        need = min_reference_windows(alpha, len(names))
        if R < need:
            raise ValueError(
                f"reference too short: {R} null windows of {window}, but alpha={alpha} with {len(names)} detectors "
                f"needs at least {need} (a warden that can never alarm is worse than none)")
        self.window, self.alpha, self.names = int(window), float(alpha), names
        self.ctx = Context(np.quantile(pool, np.linspace(0, 1, n_symbols + 1)[1:-1]), np.sort(pool))
        wins = null_stream[: R * window].reshape(R, window)
        self._null = {n: np.sort([DETECTORS[n](w, self.ctx) for w in wins]) for n in names}
        self.n_null = R

    def stats(self, window) -> dict:
        w = np.asarray(window, dtype=float)
        if w.shape != (self.window,):
            raise ValueError(f"window must have exactly {self.window} delays")
        return {n: float(DETECTORS[n](w, self.ctx)) for n in self.names}

    def p_values(self, window) -> dict:
        return self._p_from_stats(self.stats(window))

    def test(self, window, alpha: float | None = None) -> WardenResult:
        alpha = self.alpha if alpha is None else float(alpha)
        s = self.stats(window)
        p = self._p_from_stats(s)
        k = len(self.names)
        pc = float(min(1.0, k * min(p.values())))
        return WardenResult(s, p, pc, pc <= alpha, tuple(n for n, v in p.items() if v <= alpha / k))

    def _p_from_stats(self, s: dict) -> dict:
        return {n: conformal_p(self._null[n], v) for n, v in s.items()}

    def scan(self, stream, alpha: float | None = None) -> list:
        x = np.asarray(stream, dtype=float)
        n = x.size // self.window
        return [self.test(x[i * self.window:(i + 1) * self.window], alpha) for i in range(n)]

    def alarm_rate(self, stream, alpha: float | None = None) -> float:
        res = self.scan(stream, alpha)
        return float(np.mean([r.alarm for r in res])) if res else 0.0
