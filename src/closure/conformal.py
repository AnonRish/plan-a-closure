"""One-sided residual-test helpers: conformal (distribution-free), Gaussian, exact binomial."""
from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np


def z_upper(alpha: float) -> float:
    return NormalDist().inv_cdf(1.0 - alpha)


def _betacf(a: float, b: float, x: float) -> float:
    fp, qab, qap, qam = 1e-300, a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > fp else fp)
    h = d
    for m in range(1, 400):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = d if abs(d) > fp else fp
        c = 1.0 + aa / c
        c = c if abs(c) > fp else fp
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = d if abs(d) > fp else fp
        c = 1.0 + aa / c
        c = c if abs(c) > fp else fp
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 3e-14:
            break
    return h


def betainc_reg(a: float, b: float, x: float) -> float:
    """Regularised incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def t_upper(alpha: float, nu: float) -> float:
    """Exact Student-t upper-tail quantile (bisection on the incomplete-beta tail), any nu > 0."""
    nu = max(float(nu), 0.5)
    lo, hi = 0.0, 1.0
    while 0.5 * betainc_reg(nu / 2.0, 0.5, nu / (nu + hi * hi)) > alpha and hi < 1e12:
        hi *= 2.0
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        if 0.5 * betainc_reg(nu / 2.0, 0.5, nu / (nu + mid * mid)) > alpha:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def conformal_p(null, score: float) -> float:
    null = np.asarray(null, float)
    return float((1 + np.sum(null >= score)) / (len(null) + 1))


def upper_conformal_quantile(null, alpha: float) -> float:
    """t with P(N > t) <= alpha for a fresh exchangeable draw N (inf if too few samples)."""
    s = np.sort(np.asarray(null, float))
    n = len(s)
    j = int(math.floor(alpha * (n + 1)))
    return math.inf if j < 1 else float(s[n - j])


def lower_conformal_quantile(null, alpha: float) -> float:
    """q with P(N < q) <= alpha (-inf if too few samples)."""
    s = np.sort(np.asarray(null, float))
    n = len(s)
    j = int(math.floor(alpha * (n + 1)))
    return -math.inf if j < 1 else float(s[j - 1])


def jarque_bera_p(x) -> float:
    """Normality diagnostic; p = exp(-JB/2) is the exact chi-square(2) tail."""
    x = np.asarray(x, float)
    n = len(x)
    if n < 8:
        return 0.0
    m = x - x.mean()
    s2 = float(np.mean(m ** 2))
    if s2 <= 0:
        return 0.0
    skew = float(np.mean(m ** 3) / s2 ** 1.5)
    kurt = float(np.mean(m ** 4) / s2 ** 2)
    jb = n / 6.0 * (skew ** 2 + (kurt - 3.0) ** 2 / 4.0)
    return float(math.exp(-jb / 2.0))


def _binom_cdf(k: int, n: int, p: float) -> float:
    if k < 0:
        return 0.0
    if k >= n:
        return 1.0
    if p <= 0:
        return 1.0
    if p >= 1:
        return 0.0
    lg = math.lgamma
    lp, lq = math.log(p), math.log1p(-p)
    s = 0.0
    for i in range(k + 1):
        s += math.exp(lg(n + 1) - lg(i + 1) - lg(n - i + 1) + i * lp + (n - i) * lq)
    return min(1.0, s)


def cp_upper(k: int, n: int, conf: float = 0.95) -> float:
    """Exact (Clopper-Pearson) one-sided upper confidence bound for a binomial rate."""
    if n <= 0:
        return 1.0
    if k >= n:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(50):
        mid = (lo + hi) / 2
        if _binom_cdf(k, n, mid) > 1 - conf:
            lo = mid
        else:
            hi = mid
    return hi


def cp_lower(k: int, n: int, conf: float = 0.95) -> float:
    """Exact one-sided lower confidence bound for a binomial rate."""
    if n <= 0 or k <= 0:
        return 0.0
    lo, hi = 0.0, 1.0
    for _ in range(50):
        mid = (lo + hi) / 2
        if _binom_cdf(k - 1, n, mid) > conf:
            lo = mid
        else:
            hi = mid
    return lo
