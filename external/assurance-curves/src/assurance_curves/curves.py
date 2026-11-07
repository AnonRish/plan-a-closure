"""Assurance curves (Appendix A.3): coverage vs. confidence at a verification budget.

*Coverage*   = 1 - F*      : fraction of the workload we claim is legitimate.
*Confidence* = 1 - exp(-N_verified * F*) : probability an actual violation of
size >= F* is caught.

Work in ``F*`` (the tolerated fake fraction) rather than in coverage where you
can: ``1 - coverage`` cancels catastrophically near 8 nines.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

_LN10 = float(np.log(10.0))


def confidence_for_fraction(n_verified, f_star):
    """1 - exp(-n_verified * f_star), elementwise, precision-safe for small products."""
    nv = np.asarray(n_verified, dtype=float)
    f = np.asarray(f_star, dtype=float)
    if np.any(nv < 0) or np.any(f < 0) or np.any(f > 1):
        raise ValueError("n_verified must be >= 0 and f_star in [0, 1]")
    return -np.expm1(-nv * f)


def nines_for_fraction(n_verified, f_star):
    """Nines of confidence at tolerated fraction ``f_star``: exactly ``n_verified*f_star/ln 10``."""
    nv = np.asarray(n_verified, dtype=float)
    f = np.asarray(f_star, dtype=float)
    return nv * f / _LN10


def fraction_for_confidence(n_verified, confidence):
    """Largest fake fraction F* that can hide with probability <= 1 - confidence."""
    nv = np.asarray(n_verified, dtype=float)
    conf = np.asarray(confidence, dtype=float)
    if np.any(nv <= 0):
        raise ValueError("n_verified must be > 0")
    if np.any(conf < 0) or np.any(conf >= 1):
        raise ValueError("confidence must be in [0, 1)")
    return np.minimum(1.0, -np.log1p(-conf) / nv)


def coverage_for_confidence(n_verified, confidence):
    """Coverage 1 - F* that is certifiable at ``confidence`` with ``n_verified`` audits."""
    return 1.0 - fraction_for_confidence(n_verified, confidence)


@dataclass(frozen=True)
class AssuranceCurve:
    n_verified: float
    f_star: np.ndarray
    coverage: np.ndarray
    confidence: np.ndarray
    nines: np.ndarray

    def as_rows(self):
        return [
            {"f_star": float(f), "coverage": float(c), "confidence": float(p), "nines": float(k)}
            for f, c, p, k in zip(self.f_star, self.coverage, self.confidence, self.nines)
        ]


def assurance_curve(n_verified: float, f_star=None, n_points: int = 25) -> AssuranceCurve:
    """Confidence as a function of tolerated fake fraction, log-spaced by default.

    Default range spans the fractions at which confidence runs from ~1 % to ~8 nines.
    """
    nv = float(n_verified)
    if nv <= 0:
        raise ValueError("n_verified must be > 0")
    if f_star is None:
        lo, hi = 0.01 / nv, min(1.0, 18.42 / nv)  # 1 % .. 8 nines
        f_star = np.geomspace(lo, hi, n_points)
    f = np.asarray(f_star, dtype=float)
    return AssuranceCurve(
        n_verified=nv,
        f_star=f,
        coverage=1.0 - f,
        confidence=confidence_for_fraction(nv, f),
        nines=nines_for_fraction(nv, f),
    )
