"""Window statistics used by the warden. Each maps a window of delays to one number.

References: regularity and epsilon-similarity, Cabuk, Brodley & Shields, *IP covert timing channels:
design and detection* (CCS 2004); corrected conditional entropy, Gianvecchio & Wang, *Detecting covert timing
channels: an entropy-based approach* (CCS 2007), after Porta et al. (2001).
"""
from __future__ import annotations

import zlib
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Context:
    edges: np.ndarray        # interior quantile edges of the honest reference (n_symbols - 1 values)
    ref_sorted: np.ndarray   # sorted honest reference pool, for the KS distance


def quantize(x, edges) -> np.ndarray:
    return np.searchsorted(np.asarray(edges), np.asarray(x, dtype=float), side="right")


def regularity(x, block: int = 20) -> float:
    """Cabuk: std over pairs i<j of |s_i - s_j| / s_i, s_i = std of the i-th block. Low = suspiciously regular."""
    x = np.asarray(x, dtype=float)
    k = x.size // block
    if k < 2:
        raise ValueError("window too short for the block size")
    sig = x[: k * block].reshape(k, block).std(axis=1)
    i, j = np.triu_indices(k, 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        rel = np.abs(sig[i] - sig[j]) / sig[i]
    rel = rel[np.isfinite(rel)]
    return float(rel.std()) if rel.size > 1 else 0.0


def eps_similarity(x, eps: float = 0.05) -> float:
    """Cabuk: fraction of sorted neighbours within a relative gap ``eps``. High = delays cluster at few values."""
    s = np.sort(np.asarray(x, dtype=float))
    if s.size < 2 or np.any(s <= 0):
        raise ValueError("need at least two strictly positive delays")
    return float(np.mean(np.diff(s) / s[:-1] < eps))


def ks_stat(x, ref_sorted) -> float:
    """Exact two-sample Kolmogorov-Smirnov distance between a window and a large sorted reference, O(n log m).

    Both empirical CDFs are right-continuous step functions. On each interval between consecutive distinct window
    values the window's CDF is constant and the reference CDF is monotone, so the supremum is attained at the
    interval's endpoints: only ``n`` searches into the reference are needed, and ties are handled by working
    on distinct values.
    """
    a = np.asarray(x, dtype=float)
    r = np.asarray(ref_sorted, dtype=float)
    u, cnt = np.unique(a, return_counts=True)
    c = np.cumsum(cnt) / a.size                                  # window CDF at each distinct value
    r_right = np.searchsorted(r, u, side="right") / r.size       # reference CDF at u
    r_left = np.searchsorted(r, u, side="left") / r.size         # reference CDF just below u
    d = max(r_left[0], float(np.max(np.abs(c - r_right))))       # first interval (-inf, u_1), and every jump
    if u.size > 1:
        d = max(d, float(np.max(np.abs(c[:-1] - r_left[1:]))))   # right ends of interior intervals
    return float(d)


def cce(x, edges, m_max: int = 6) -> float:
    """Corrected conditional entropy (bits) of the quantised sequence: ``min_m [CE(m) + perc(m) * E(1)]``.

    ``E(m)`` is the Shannon entropy of overlapping length-``m`` patterns, ``CE(m) = E(m) - E(m-1)``, ``perc(m)`` the
    fraction of patterns seen exactly once. Structured (predictable) sequences score low, i.i.d. noise scores
    near ``log2(#symbols)``.
    """
    sym = quantize(x, edges).astype(np.int64)
    n, Q = sym.size, len(edges) + 1
    if n <= m_max + 1:
        raise ValueError("window too short for m_max")
    E, perc = [0.0], [0.0]
    for m in range(1, m_max + 1):
        codes = np.zeros(n - m + 1, dtype=np.int64)
        for j in range(m):
            codes = codes * Q + sym[j: n - m + 1 + j]
        _, counts = np.unique(codes, return_counts=True)
        p = counts / counts.sum()
        E.append(float(-(p * np.log2(p)).sum()))
        perc.append(float((counts == 1).sum() / counts.sum()))
    return float(min((E[m] - E[m - 1]) + perc[m] * E[1] for m in range(1, m_max + 1)))


def compress_ratio(x, edges) -> float:
    """zlib(level 9) size over raw size of the quantised sequence, one byte per symbol."""
    raw = quantize(x, edges).astype(np.uint8).tobytes()
    return len(zlib.compress(raw, 9)) / len(raw)


def lag1_autocorr(x) -> float:
    """Lag-1 autocorrelation of log delays."""
    v = np.log(np.asarray(x, dtype=float))
    v = v - v.mean()
    d = float(np.dot(v, v))
    return float(np.dot(v[:-1], v[1:]) / d) if d > 0 else 0.0


#: name -> f(window, Context) -> float
DETECTORS = {
    "regularity": lambda w, c: regularity(w),
    "eps_similarity": lambda w, c: eps_similarity(w),
    "ks": lambda w, c: ks_stat(w, c.ref_sorted),
    "cce": lambda w, c: cce(w, c.edges),
    "compress": lambda w, c: compress_ratio(w, c.edges),
    "autocorr": lambda w, c: lag1_autocorr(w),
}
