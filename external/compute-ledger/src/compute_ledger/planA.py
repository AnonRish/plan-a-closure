"""Reproduce the AI 2040 Plan A compute figures (289M world stock, ownership, locations, 0.5% hidden) from their inputs.

Every published number lives in data/plan_a_2029.json with its provenance.  Tolerances come from the rounding of
the published inputs (half a unit in the last printed digit), propagated through the arithmetic, not from the size
of the result being compared.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from importlib import resources
from typing import List, Optional

from . import stock as st
from . import units
from .distributions import TwoPieceLogNormal


def load() -> dict:
    with resources.files("compute_ledger").joinpath("data/plan_a_2029.json").open() as f:
        return json.load(f)


@dataclass
class Check:
    name: str
    computed: float
    published: Optional[float]
    tol: float
    unit: str = "H100e"
    expect_match: bool = True        # False: the check passes when the computed value does NOT match
    note: str = ""

    @property
    def diff(self) -> Optional[float]:
        return None if self.published is None else self.computed - self.published

    @property
    def ok(self) -> bool:
        if self.published is None:
            return True                                  # informational
        within = abs(self.computed - self.published) <= self.tol
        return within if self.expect_match else not within


def _years(d: dict) -> List[str]:
    return sorted(d)


def printed_halfwidth(x: float) -> float:
    """Half a unit in the last printed decimal of ``x`` (0.1 -> 0.05, 0.32 -> 0.005, 12.0 -> 0.05); used for percentages."""
    text = repr(float(x))
    decimals = len(text.split(".")[1]) if "." in text and "e" not in text else 0
    return 0.5 * 10 ** (-decimals)


def reproduce(data: Optional[dict] = None) -> List[Check]:
    d = data or load()
    out: List[Check] = []

    # 1. world stock from the production series -------------------------------------------------------------
    w = d["world_stock_series"]
    years = _years(w["production"])
    prod = [w["production"][y] for y in years]
    s0 = w["jan1"][years[0]]
    hl = w["survival_half_life_years"]
    published = w["jan1"][str(int(years[-1]) + 1)]
    f = st.survival_factor(hl)
    hw = w["rounding_halfwidth"]
    coeff = f ** len(prod) + sum(f ** k for k in range(len(prod)))      # worst-case rounding propagation
    tol = hw * coeff + hw + 0.2e6                                       # + allowance: the half-life is itself "~15 years"
    decay = st.roll_forward(s0, prod, hl)
    out.append(Check("world stock, Jan 1 2029, from 2025-28 production with a 15-year half-life", decay[-1], published, tol,
                     note="rounding of the published inputs (%.2fM) plus 0.2M for the approximate half-life" % ((hw * coeff + hw) / 1e6)))
    for i, y in enumerate(years[:-1]):
        nxt = w["jan1"][str(int(y) + 1)]
        out.append(Check("world stock, Jan 1 %d (decay model)" % (int(y) + 1), decay[i], nxt, hw * (f ** (i + 1) + sum(f ** k for k in range(i + 1))) + hw + 0.2e6))
    cum = st.roll_forward(s0, prod, None)
    out.append(Check("same, as a pure running sum (no retirement)", cum[-1], published, tol, expect_match=False,
                     note="the published series does not follow a running sum: this check passes when it does not match"))

    # 2. China ------------------------------------------------------------------------------------------------
    c = d["china"]
    cy = _years(c["stock_end_of_year"])
    chw = c["rounding_halfwidth"]
    prev = c["stock_end_of_year"][cy[0]]
    for y in cy[1:]:
        out.append(Check("China stock end-%s = end-%d stock + added" % (y, int(y) - 1), prev + c["added_per_year"][y],
                         c["stock_end_of_year"][y], 3 * chw))
        prev = c["stock_end_of_year"][y]
    ch = c["channels_2028"]
    out.append(Check("China 2028 additions: sum of the four channels", sum(ch.values()), c["added_per_year"]["2028"], 5 * chw))

    # 3. ownership ----------------------------------------------------------------------------------------------
    o = d["owners"]
    world = w["jan1"]["2029"]
    china = c["stock_end_of_year"]["2028"]
    rest = world - china
    derived = {"China": china, "US": rest * o["us_share_of_non_china"], "RoW": rest * (1 - o["us_share_of_non_china"])}
    for k in ("US", "China", "RoW"):
        # printed precision of the figure (0.5M) plus the rounding of the two inputs it is derived from (0.1M)
        out.append(Check("%s stock from the 85/15 rule" % k, derived[k], o["published"][k], o["rounding_halfwidth"] + 0.1e6))
        share = 100 * derived[k] / world
        out.append(Check("%s share of world (%%)" % k, share, o["published_share_pct"][k], 0.5, unit="%"))
    out.append(Check("published ownership sums to the published world total", sum(o["published"].values()), o["published_world_total"], 0.0))

    # 4. locations ----------------------------------------------------------------------------------------------
    L = d["locations"]
    den = L["share_denominator"]
    bins = L["datacenter_bins"]
    parts = [(b["label"], b["h100e"], b["share_pct"], b["halfwidth"]) for b in bins]
    parts.append(("in-transit", L["in_transit"]["h100e"], L["in_transit"]["share_pct"], L["in_transit"]["halfwidth"]))
    parts.append(("AI consumer", L["ai_consumer"]["h100e"], L["ai_consumer"]["share_pct"], L["ai_consumer"]["halfwidth"]))
    for name, v, pct, hwid in parts:
        pp_tol = 100 * hwid / den + printed_halfwidth(pct)
        out.append(Check("share of world in %s (%%)" % name, 100 * v / den, pct, pp_tol, unit="%"))
    total_loc = sum(v for _, v, _, _ in parts)
    rss = math.sqrt(sum(h * h for _, _, _, h in parts))
    out.append(Check("datacenter bins + in-transit + AI consumer = world stock", total_loc, den, rss,
                     note="tolerance is the root-sum-square of the rounding of the eight published parts"))
    dc = sum(b["h100e"] for b in bins)
    big = sum(b["h100e"] for b in bins if b["label"] in ("10M+", "1M-10M", "100K-1M", "10K-100K"))
    out.append(Check("share of datacenter compute in sites of 10K H100e or more (%)", 100 * big / dc, None, 0.0, unit="%",
                     note="informational: the plan describes this as about 99%"))
    out.append(Check("number of datacenters", float(sum(b["sites"] for b in bins)), 2850.0, 60.0, unit="sites",
                     note="the supplement says about 2,850 sites by 2029 (1,000 growing 30% a year)"))

    # 5. hidden compute -----------------------------------------------------------------------------------------
    h = d["hidden_compute"]
    out.append(Check("hidden compute: median / world stock (%)", 100 * h["median_h100e"] / world, h["published_world_fraction_pct"], 0.05, unit="%"))
    lo_f, hi_f = h["ci80_fraction_of_ai_relevant"]
    out.append(Check("hidden compute: 80% interval upper end (H100e)", hi_f * world, 4.0e6, 0.1e6,
                     note="1.4% of the world stock; the plan calls this about 4M"))
    dist = TwoPieceLogNormal(lo_f * world, h["median_h100e"], hi_f * world)
    out.append(Check("fitted hidden-compute distribution reproduces its median", dist.ppf(0.5), h["median_h100e"], 1.0))
    out.append(Check("fitted hidden-compute distribution reproduces its 90th percentile", dist.ppf(0.9), hi_f * world, 1.0))

    # 6. units --------------------------------------------------------------------------------------------------
    t = d["tpp"]
    out.append(Check("AI-relevance floor in H100e", units.h100e_from_tpp(t["ai_floor"]), 0.25, 0.01, unit="H100e/chip"))
    out.append(Check("B200 in H100e", units.h100e_from_tpp(t["b200"]), 2.3, 0.05, unit="H100e/chip"))
    out.append(Check("H100 TPP / defined H100 TPP", float(t["h100"]), units.H100_TPP, 0.0, unit="TPP"))
    return out
