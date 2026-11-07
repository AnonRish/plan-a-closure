"""Covert timing channels, from trivially detectable to undetectable-by-construction."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


def random_symbols(n: int, levels: int, rng: np.random.Generator) -> np.ndarray:
    """Uniform i.i.d. symbols: the worst case for the defender (encrypted payload)."""
    return rng.integers(0, levels, n)


@dataclass(frozen=True)
class LevelChannel:
    """Naive channel: the sender *replaces* each honest delay by ``t0 + k * step``.

    Detectable by construction (a few discrete delay values); included because it is what most
    published detectors were designed against.
    """
    levels: int
    t0: float
    step: float

    @property
    def bits_per_packet(self) -> float:
        return math.log2(self.levels)

    def encode(self, symbols) -> np.ndarray:
        s = np.asarray(symbols)
        if s.size and (s.min() < 0 or s.max() >= self.levels):
            raise ValueError("symbols out of range")
        return self.t0 + self.step * s.astype(float)

    def decode(self, ipd) -> np.ndarray:
        k = np.rint((np.asarray(ipd, dtype=float) - self.t0) / self.step)
        return np.clip(k, 0, self.levels - 1).astype(int)


@dataclass(frozen=True)
class QuantileChannel:
    """Encode ``bits`` bits per packet in *which quantile* of a public honest distribution the delay falls in.

    With ``K = 2**bits`` and uniform i.i.d. message symbols ``k``, the delay ``ppf((k + u) / K)`` with
    ``u ~ U[0,1)`` has *exactly* the honest marginal distribution ``dist``. If honest delays are i.i.d.
    from ``dist`` the whole stream is distributed exactly like honest traffic, so no statistical test,
    however clever, can beat chance: capacity is limited by receiver noise, not by detection.
    If honest traffic has temporal structure that ``dist`` (a marginal) does not capture, the structure is
    lost and structure-sensitive tests can see it.
    """
    dist: object      # needs .cdf and .ppf
    bits: int = 2

    @property
    def levels(self) -> int:
        return 1 << self.bits

    def encode(self, symbols, rng: np.random.Generator) -> np.ndarray:
        s = np.asarray(symbols)
        if s.size and (s.min() < 0 or s.max() >= self.levels):
            raise ValueError("symbols out of range")
        return self.dist.ppf((s + rng.random(s.size)) / self.levels)

    def decode(self, ipd) -> np.ndarray:
        k = np.floor(self.levels * self.dist.cdf(np.asarray(ipd, dtype=float)))
        return np.clip(k, 0, self.levels - 1).astype(int)
