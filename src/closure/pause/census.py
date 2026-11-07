"""Global accelerator census: how many pre-pause chips would a thorough census miss? (paper sections 5.4-5.5, Table 5.1.)

Two things go missing: chips that failed and were disposed of without a record, and working chips an owner keeps off the
books. The paper bounds both with deliberately pessimistic anchors; this module makes the chain executable so the anchors
can be replaced by better ones. It also turns the paper's list of documentary sources (section 5.4.1) into a reconciliation
you can run on real record sets: chips that appear in records but not in the declared registry are the first leads."""
from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

# ---- anchors (section 5.5.2): every one is an overestimate of what a cooperating state would miss ------------------------
OUT_OF_DC = 0.10                 # share of chips not in a data center (LBNL: under 10% of US servers)
MISS_DC = 0.06                   # extra share missed by both operator and owner (IRS under-reporting anchor)
UNDECLARED_ON_BOOKS = 0.06       # owner fails to declare, with substantial information reporting
UNRECOVERED_ON_BOOKS = 0.20      # tracing from the seller fails (ATF firearms-trace anchor)
UNDECLARED_OFF_BOOKS = 0.20      # inflated for owners who prefer to keep chips for the black market
UNRECOVERED_OFF_BOOKS = 0.50
FAIL_RATE = {"low": 0.0016, "central": 0.0045, "high": 0.0097}    # replacement rate per year of new hardware (Cui et al.)
HAZARD_RISE = 0.03               # failure rate rises 3 points per year after the warranty
WARRANTY_YEARS = 3.0
UNACCOUNTED_IN_WARRANTY = 0.01   # failed under warranty with no contemporaneous record
UNACCOUNTED_OUT_OF_WARRANTY = 0.10
UNACCOUNTED_OFF_BOOKS = 0.50
KINDS = ("public", "on_books", "off_books", "informal")


def site_miss_fraction(out_of_dc: float = OUT_OF_DC, miss_dc: float = MISS_DC) -> float:
    """Share of chips not findable through a data center. The paper adds the two terms (16%), a conservative reading."""
    return out_of_dc + miss_dc


def missing_fraction(kind: str, out_of_dc: float = OUT_OF_DC, miss_dc: float = MISS_DC) -> float:
    """mu(h): fraction of working chips of holding type h that a thorough census misses (section 5.5.2)."""
    site = site_miss_fraction(out_of_dc, miss_dc)
    if kind == "public":
        return 0.0                                                  # held by large named owners: negligible non-compliance
    if kind == "on_books":
        return site * UNDECLARED_ON_BOOKS * UNRECOVERED_ON_BOOKS    # about 0.19%
    if kind == "off_books":
        return site * UNDECLARED_OFF_BOOKS * UNRECOVERED_OFF_BOOKS  # about 1.6%
    if kind == "informal":
        return UNDECLARED_OFF_BOOKS * UNRECOVERED_OFF_BOOKS        # none sit in data centers: 10%
    raise ValueError(f"unknown holding type {kind!r}")


def cumulative_hazard(age: float, rate: float = FAIL_RATE["central"], rise: float = HAZARD_RISE,
                      warranty: float = WARRANTY_YEARS) -> float:
    """Integral of a failure rate that is `rate` per year until the warranty ends and climbs by `rise` per year after it."""
    return rate * age + 0.5 * rise * max(age - warranty, 0.0) ** 2


def failed_by_vintage(vintages, at_year: float, rate: float = FAIL_RATE["central"], rise: float = HAZARD_RISE,
                      warranty: float = WARRANTY_YEARS) -> tuple:
    """(all failed, failed after warranty) in H100e for chips sold as (sale_year, h100e) pairs, observed at `at_year`."""
    hz = lambda a: cumulative_hazard(a, rate, rise, warranty)
    total = late = 0.0
    for sale_year, h in vintages:
        age = at_year - sale_year
        if age > 0:
            total += h * (1.0 - math.exp(-hz(age)))
        if age > warranty:
            late += h * (math.exp(-hz(warranty)) - math.exp(-hz(age)))
    return total, late


def missing_failed(kind: str, failed_all: float, failed_late: float = 0.0) -> float:
    """Failed chips with no contemporaneous record of failure (warranty return, e-waste certificate, inventory entry)."""
    if kind in ("public", "on_books"):
        return UNACCOUNTED_IN_WARRANTY * (failed_all - failed_late) + UNACCOUNTED_OUT_OF_WARRANTY * failed_late
    if kind == "off_books":
        return UNACCOUNTED_OFF_BOOKS * failed_all
    if kind == "informal":
        return failed_all
    raise ValueError(f"unknown holding type {kind!r}")


@dataclass
class Holding:
    kind: str
    stock: float            # H100e, working and failed
    failed: float
    miss_failed: float      # failed chips with no record

    @property
    def functional(self) -> float:
        return self.stock - self.failed

    @property
    def mu(self) -> float:
        return missing_fraction(self.kind)

    @property
    def miss_functional(self) -> float:
        return self.mu * self.functional

    @property
    def total_missing(self) -> float:
        return self.miss_failed + self.miss_functional


def k_missing(holdings) -> float:
    """K_M(s) = sum over holding types of the chips a thorough census misses."""
    return sum(h.total_missing for h in holdings)


def split_residual(residual: float, diverted_stock: float = 0.0, informal_share: float = 0.01, off_books_share: float = 0.10,
                   month_inventory_half: float = 27.5e3 / 2) -> dict:
    """Split the stock that is not publicly identifiable into holding types (section 5.5.1): `informal_share` held by
    individuals, `off_books_share` of the diverted stock off the books, the rest on the books, and half of one month of
    diversion inventory counted as informal in each state."""
    off = off_books_share * diverted_stock
    informal = informal_share * residual + month_inventory_half
    return {"on_books": residual - informal_share * residual - off, "off_books": off, "informal": informal}


# Table 5.1 inputs at the precision of the paper's calculation supplement (H100e), year-end 2026
TABLE_5_1 = {
    "United States": [Holding("public", 33_081e3, 174.95e3, 3.78e3), Holding("on_books", 2_114e3, 16.14e3, 0.52e3),
                      Holding("informal", 35e3, 0.16e3, 0.16e3)],
    "China": [Holding("public", 732e3, 5.87e3, 0.20e3), Holding("on_books", 2_256e3, 16.92e3, 0.96e3),
              Holding("off_books", 99e3, 0.66e3, 0.33e3), Holding("informal", 38e3, 0.18e3, 0.18e3)],
}


def table_5_1() -> dict:
    """Per-state rows and totals (H100e): the structure of the paper's Table 5.1."""
    out = {}
    for state, hs in TABLE_5_1.items():
        out[state] = {"rows": [{"kind": h.kind, "stock": h.stock, "failed": h.failed, "failed_missing": h.miss_failed,
                                "functional": h.functional, "mu": h.mu, "functional_missing": h.miss_functional,
                                "total_missing": h.total_missing} for h in hs],
                      "stock": sum(h.stock for h in hs), "failed": sum(h.failed for h in hs),
                      "failed_missing": sum(h.miss_failed for h in hs),
                      "functional_missing": sum(h.miss_functional for h in hs), "K_M": k_missing(hs)}
    return out


# ---- dark-compute scenarios (section 6.4.3) -------------------------------------------------------------------------------
DARK_SCENARIOS = {
    "high": {"extra": {"United States": 0.2, "China": 0.2}, "pi": 0.5,
             "story": "cooperating states stash at most 20% of the missing amount and others credit half of it to them"},
    "low": {"extra": {"United States": 4.0, "China": 9.0}, "pi": 1.0,
            "story": "grudging cooperation: 5x (US) and 10x (China) the missing amount is held back, no discount"},
    "non_deniable": {"k0": {"United States": 300e3, "China": 1_000_000.0}, "pi": 1.0,
                     "story": "talks broke down: China conceals its whole pre-pause diverted stock, the US 300k"},
}


def dark_compute(k_m: float, state: str, scenario: str) -> dict:
    """K_0 and the political discount pi for dark compute under a cooperation scenario."""
    s = DARK_SCENARIOS[scenario]
    k0 = s["k0"][state] if "k0" in s else (1.0 + s["extra"][state]) * k_m
    return {"k0": k0, "pi": s["pi"], "scenario": scenario}


def buyback_budget(n_accelerators: float, avg_price: float, margin: float = 2.0) -> float:
    """Cost of buying back every accelerator at `margin` times its purchase price (section 5.4.2: 25M at about $20k is $500B,
    and doubling it still leaves a $1T budget below a quarter of US pandemic relief)."""
    return n_accelerators * avg_price * margin


# ---- documentary evidence (section 5.4.1) ---------------------------------------------------------------------------------
EVIDENCE_SOURCES = ("tax_deduction", "manufacturing_records", "vendor_sales", "resale", "customs", "datacenter_inventory_rental",
                    "public_tenders", "power_bills", "diversion_reseller_records", "purchase_financing", "loan_collateral",
                    "warranty_returns", "decommissioning")


def reconcile(declared, sources: dict) -> dict:
    """Reconcile a declared registry against independent record sets (serial numbers).

    documented_undeclared: in some record, not declared -> first leads for dark compute.
    declared_undocumented: declared, in no record -> possible ghost registrations, or records not yet collected.
    n_sources: how many independent sources mention each chip; f1/f2 are the singletons/doubletons used by chao1_unseen."""
    declared = set(declared)
    seen = Counter()
    for recs in sources.values():
        for serial in set(recs):
            seen[serial] += 1
    documented = set(seen)
    freq = Counter(seen.values())
    return {"documented_undeclared": sorted(documented - declared), "declared_undocumented": sorted(declared - documented),
            "coverage_by_source": {k: len(set(v) & declared) / max(len(declared), 1) for k, v in sources.items()},
            "n_sources": dict(seen), "f1": freq.get(1, 0), "f2": freq.get(2, 0), "n_documented": len(documented)}


def chao1_unseen(f1: int, f2: int) -> float:
    """Chao's bias-corrected lower bound on the number of chips appearing in NO source, from the number seen in exactly
    one (f1) and exactly two (f2) sources. NOT in the paper. Assumes a closed population and sources that miss chips
    independently; shared blind spots (every source missing shell-company diversion) make it a floor, not an estimate."""
    return f1 * (f1 - 1) / (2.0 * (f2 + 1))


def lincoln_petersen(n1: int, n2: int, both: int) -> float:
    """Chapman's two-list estimate of the total population. NOT in the paper; same independence caveat as chao1_unseen."""
    return (n1 + 1) * (n2 + 1) / (both + 1) - 1
