"""A distribution for 'how much could be hidden', fitted to three published quantiles."""
from __future__ import annotations

import math
import random
from statistics import NormalDist

_N = NormalDist()
Z90 = _N.inv_cdf(0.9)          # 1.2816: the 10th/90th percentile of a standard normal sits at -/+ Z90


class TwoPieceLogNormal:
    """Quantile-matched two-piece lognormal.

    ``Q(p) = p50 * exp(sigma * z_p)`` with ``sigma = sigma_lo`` below the median and ``sigma_hi`` above it, where
    the two sigmas are fixed by the 10th and 90th percentiles.  Both halves carry probability 1/2, so p10, p50
    and p90 are reproduced exactly (a single lognormal can only match two of the three when the interval is
    skewed, as the plan's 0.1%-1.4% around a 0.5% median is).  The density jumps at the median.
    """

    def __init__(self, p10: float, p50: float, p90: float):
        if not (0 < p10 < p50 < p90):
            raise ValueError("need 0 < p10 < p50 < p90")
        self.p10, self.p50, self.p90 = float(p10), float(p50), float(p90)
        self.sigma_lo = math.log(self.p50 / self.p10) / Z90
        self.sigma_hi = math.log(self.p90 / self.p50) / Z90

    def ppf(self, p: float) -> float:
        if not 0.0 < p < 1.0:
            raise ValueError("p must be in (0, 1)")
        s = self.sigma_lo if p < 0.5 else self.sigma_hi
        return self.p50 * math.exp(s * _N.inv_cdf(p))

    def cdf(self, x: float) -> float:
        if x <= 0:
            return 0.0
        s = self.sigma_lo if x < self.p50 else self.sigma_hi
        return _N.cdf(math.log(x / self.p50) / s)

    def pdf(self, x: float) -> float:
        if x <= 0:
            return 0.0
        s = self.sigma_lo if x < self.p50 else self.sigma_hi
        return _N.pdf(math.log(x / self.p50) / s) / (x * s)

    def mean(self) -> float:
        lo, hi = self.sigma_lo, self.sigma_hi
        return self.p50 * (math.exp(lo * lo / 2) * _N.cdf(-lo) + math.exp(hi * hi / 2) * _N.cdf(hi))

    def sample(self, rng: random.Random) -> float:
        u = rng.random()
        while u == 0.0:
            u = rng.random()
        return self.ppf(u)
