"""Compute accounting and declaration reconciliation (Plan A Phase 1 chip tracking, Phase 2 declaration).

Everything is in H100-equivalents (H100e) with explicit uncertainty; nothing here is a claim about real stocks."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from statistics import NormalDist

Z90 = NormalDist().inv_cdf(0.90)           # one-sided 90% == the plan's two-sided 80% interval


@dataclass
class Estimate:
    mean: float
    sd: float
    source: str = ""

    def ci80(self):
        return (self.mean - Z90 * self.sd, self.mean + Z90 * self.sd)


def combine(estimates) -> Estimate:
    """Inverse-variance combination of independent estimates of the same quantity."""
    w = [1.0 / (e.sd ** 2) for e in estimates]
    sw = sum(w)
    return Estimate(sum(wi * e.mean for wi, e in zip(w, estimates)) / sw, math.sqrt(1.0 / sw), "combined")


def undeclared_upper_bound(declared: float, est: Estimate, conf_z: float = Z90) -> float:
    """Largest undeclared stock consistent with the estimate at one-sided 90% (never negative)."""
    return max(0.0, est.mean + conf_z * est.sd - declared)


def reconcile(declared: float, estimates, conf_z: float = Z90) -> dict:
    e = combine(estimates) if len(estimates) > 1 else estimates[0]
    z = (declared - e.mean) / e.sd
    return {"estimate": e, "z_declared_vs_estimate": z, "consistent": abs(z) <= 2.0,
            "undeclared_upper_bound": undeclared_upper_bound(declared, e, conf_z),
            "ci80": e.ci80()}


@dataclass
class Event:
    kind: str          # production | shipment_in | shipment_out | death | import | export
    h100e: float
    sd: float = 0.0
    note: str = ""


@dataclass
class StockLedger:
    """Chip-stock accounting: stock = production + in - out - deaths, uncertainties add in quadrature."""
    owner: str
    opening: Estimate
    events: list = field(default_factory=list)

    def add(self, ev: Event):
        self.events.append(ev)

    def stock(self) -> Estimate:
        sign = {"production": 1, "shipment_in": 1, "import": 1, "shipment_out": -1, "export": -1, "death": -1}
        m = self.opening.mean + sum(sign[e.kind] * e.h100e for e in self.events)
        var = self.opening.sd ** 2 + sum(e.sd ** 2 for e in self.events)
        return Estimate(m, math.sqrt(var), self.owner)


def audit_sample_size(n_sites: int, bad_sites: int, conf: float = 0.99) -> int:
    """Fewest sites to inspect (uniformly at random, without replacement) so that at least one of `bad_sites`
    misdeclared sites is found with probability >= conf. Hypergeometric."""
    if bad_sites <= 0:
        return 0
    miss = 1.0
    for k in range(1, n_sites + 1):
        miss *= (n_sites - bad_sites - (k - 1)) / (n_sites - (k - 1)) if n_sites - bad_sites - (k - 1) > 0 else 0.0
        if 1.0 - miss >= conf:
            return k
    return n_sites


def bucket_intervention(h100e: float, consumer: bool = False) -> str:
    """Plan A Jan 2029 intervention table (cluster size buckets)."""
    if consumer:
        return "intelligence: look for efforts to gather massive quantities of consumer compute"
    if h100e > 10_000:
        return "inference-only retrofit"
    return "reporting for anything above an A100 + random spot checks (powered off during rollout)"


@dataclass
class ChipTierThresholds:
    mem_capacity_tb: float = 10.0       # plan: tier 1 above 10 TB (scale-up domain)
    mem_bw_tbs: float = 1.5             # plan: tier 1 above HBM2 (~1.5 TB/s)
    compute_h100e: float = None         # in the plan's figure only; supply from the figure
    interconnect_gbs: float = None      # in the plan's figure only; supply from the figure


def chip_tier(mem_capacity_tb: float, mem_bw_tbs: float, compute_h100e: float = 0.0, interconnect_gbs: float = 0.0,
              th: ChipTierThresholds = ChipTierThresholds()) -> dict:
    """Tier 1 (subject to the deal) if ANY supplied threshold is exceeded. Thresholds the plan gives only
    graphically are None by default and are then NOT applied: the result says so."""
    hits, skipped = [], []
    for name, val, lim in (("memory capacity", mem_capacity_tb, th.mem_capacity_tb),
                           ("memory bandwidth", mem_bw_tbs, th.mem_bw_tbs),
                           ("compute", compute_h100e, th.compute_h100e),
                           ("interconnect", interconnect_gbs, th.interconnect_gbs)):
        if lim is None:
            skipped.append(name)
        elif val > lim:
            hits.append(name)
    return {"tier": 1 if hits else 0, "exceeded": hits, "thresholds_not_applied": skipped}
