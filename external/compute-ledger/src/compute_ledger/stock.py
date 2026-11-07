"""Annual stock roll-forward with chip survival.

S(t+1) = f * S(t) + P(t): the stock on Jan 1 decays by the survival factor f over the year and the year's
production is added in full.  f = 2**(-1/half_life); ``None`` means no retirement (a pure running sum).
"""
from __future__ import annotations

from typing import List, Optional, Sequence


def survival_factor(half_life_years: Optional[float]) -> float:
    if half_life_years is None:
        return 1.0
    if half_life_years <= 0:
        raise ValueError("half-life must be positive")
    return 2.0 ** (-1.0 / half_life_years)


def roll_forward(stock0: float, production: Sequence[float], half_life_years: Optional[float]) -> List[float]:
    """Returns the Jan-1 stocks after each year of production (length == len(production))."""
    if stock0 < 0 or any(p < 0 for p in production):
        raise ValueError("stock and production must be non-negative")
    f = survival_factor(half_life_years)
    out, s = [], float(stock0)
    for p in production:
        s = f * s + p
        out.append(s)
    return out


def implied_survival(stock_t: float, production: float, stock_next: float) -> float:
    """The survival factor that would make one published step S(t+1) = f*S(t) + P(t) exact."""
    if stock_t <= 0:
        raise ValueError("need a positive opening stock")
    return (stock_next - production) / stock_t
