"""Declared versus estimated: how much of an owner's true stock could be undeclared?

Model.  The owner declares a stock D (taken as exact: it is the audited figure).  The true stock is T = D + H
with H >= 0 the undeclared part.  An independent estimate E of T has Gaussian error, E ~ Normal(T, s^2), where s
comes from the estimate's stated central interval.  With a prior p(H) on the undeclared part,

    p(H | E)  ~  p(H) * Normal(E; D + H, s^2)          for H >= 0.

The posterior is computed on a fine grid (no sampling), so every number is deterministic.  With a flat prior
it is a Normal(E - D, s^2) truncated to H >= 0; with a half-normal prior it is again a truncated normal.  Both
closed forms are used by the tests as independent references.
"""
from __future__ import annotations

import bisect
import math
import random
from dataclasses import dataclass
from statistics import NormalDist
from typing import List, Optional, Sequence

from .distributions import TwoPieceLogNormal

_N = NormalDist()


@dataclass(frozen=True)
class Estimate:
    """An independent estimate of an owner's true stock, given as a central ``level`` interval [lo, hi]."""
    lo: float
    hi: float
    level: float = 0.8

    def __post_init__(self):
        if not (self.hi > self.lo > 0) or not (0 < self.level < 1):
            raise ValueError("need 0 < lo < hi and 0 < level < 1")

    @property
    def center(self) -> float:
        return (self.lo + self.hi) / 2

    @property
    def sigma(self) -> float:
        return (self.hi - self.lo) / (2 * _N.inv_cdf(0.5 + self.level / 2))


class Prior:
    """Prior density (up to a constant) of the undeclared stock H >= 0."""

    def pdf(self, h: float) -> float:
        raise NotImplementedError

    def upper(self) -> float:
        return 0.0


class Flat(Prior):
    def pdf(self, h: float) -> float:
        return 1.0


class HalfNormal(Prior):
    def __init__(self, tau: float):
        if tau <= 0:
            raise ValueError("tau must be positive")
        self.tau = tau

    def pdf(self, h: float) -> float:
        return math.exp(-0.5 * (h / self.tau) ** 2)


class Fitted(Prior):
    """A prior given by a :class:`TwoPieceLogNormal` (for instance the plan's published hidden-compute quantiles)."""

    def __init__(self, dist: TwoPieceLogNormal):
        self.dist = dist

    def pdf(self, h: float) -> float:
        return self.dist.pdf(h)

    def upper(self) -> float:
        return self.dist.ppf(0.999999)


@dataclass
class Posterior:
    grid: List[float]
    pdf: List[float]
    cdf: List[float]

    def quantile(self, p: float) -> float:
        if not 0.0 <= p <= 1.0:
            raise ValueError("p must be in [0, 1]")
        i = bisect.bisect_left(self.cdf, p)
        if i <= 0:
            return self.grid[0]
        if i >= len(self.grid):
            return self.grid[-1]
        c0, c1 = self.cdf[i - 1], self.cdf[i]
        t = 0.0 if c1 == c0 else (p - c0) / (c1 - c0)
        return self.grid[i - 1] + t * (self.grid[i] - self.grid[i - 1])

    @property
    def median(self) -> float:
        return self.quantile(0.5)

    @property
    def mean(self) -> float:
        g, f = self.grid, self.pdf
        return sum(0.5 * (g[i] * f[i] + g[i + 1] * f[i + 1]) * (g[i + 1] - g[i]) for i in range(len(g) - 1))

    def prob_exceeds(self, x: float) -> float:
        if x <= self.grid[0]:
            return 1.0
        if x >= self.grid[-1]:
            return 0.0
        i = bisect.bisect_left(self.grid, x)
        g0, g1 = self.grid[i - 1], self.grid[i]
        c = self.cdf[i - 1] + (self.cdf[i] - self.cdf[i - 1]) * (x - g0) / (g1 - g0)
        return 1.0 - c

    def sample(self, rng: random.Random) -> float:
        return self.quantile(rng.random())


def posterior_hidden(declared: float, estimate: Estimate, prior: Optional[Prior] = None, n: int = 40001) -> Posterior:
    if declared <= 0:
        raise ValueError("declared stock must be positive")
    prior = prior or Flat()
    s = estimate.sigma
    m = estimate.center - declared                     # where the likelihood is centred (can be negative)
    hmax = max(m, 0.0) + 12 * s
    hmax = max(hmax, prior.upper())
    step = hmax / (n - 1)
    grid = [i * step for i in range(n)]
    logw = []
    for h in grid:
        p = prior.pdf(h)
        logw.append(-0.5 * ((h - m) / s) ** 2 + (math.log(p) if p > 0 else -math.inf))
    top = max(logw)
    w = [math.exp(l - top) if l > -math.inf else 0.0 for l in logw]
    cum = [0.0]
    for i in range(n - 1):
        cum.append(cum[-1] + 0.5 * (w[i] + w[i + 1]) * step)
    total = cum[-1]
    return Posterior(grid, [x / total for x in w], [c / total for c in cum])


@dataclass
class Consistency:
    z: float                 # how many sigma the estimate's centre sits above the declaration
    p_if_complete: float     # P(estimate centre this high or higher | the declaration is complete)


def consistency(declared: float, estimate: Estimate) -> Consistency:
    z = (estimate.center - declared) / estimate.sigma
    return Consistency(z, 1.0 - _N.cdf(z))


def sum_quantiles(posteriors: Sequence[Posterior], qs: Sequence[float] = (0.1, 0.5, 0.9), n: int = 200_000,
                  seed: int = 1) -> List[float]:
    """Quantiles of the sum of independent undeclared stocks (Monte Carlo from the exact posteriors)."""
    rng = random.Random(seed)
    totals = sorted(sum(p.sample(rng) for p in posteriors) for _ in range(n))
    return [totals[min(n - 1, int(q * n))] for q in qs]
