"""Governing hardware production (paper sections 3.3.4, 5.3 and 6.5.4): wafer mass balance, sampling detection and the
lithography-machine census.

The regime never needs to see inside a fab. It needs the books to close: wafers in, wafers printed on registered machines,
dies out, rejects destroyed under monitoring, consumables used. Whatever does not close is charged to the host state's
ledger as dark compute until it is explained."""
from __future__ import annotations

import math
from dataclasses import dataclass

from .treaty_ledger import Source

# Brown & Khan (2026), as converted by the paper: one ArF-immersion DUV machine at 7 nm multipatterning, state-of-the-art yield
DUV_H100E_PER_MONTH = (24_000.0, 38_000.0)


# ---- sampling detection (section 5.3.2) ------------------------------------------------------------------------------------
def p_detect(n_samples: int, diversion_fraction: float, p_recognize: float) -> float:
    """Probability that sampling n outgoing chips catches at least one illicit one when a fraction is diverted and an
    inspection recognises an illicit chip with probability p_recognize."""
    return 1.0 - (1.0 - diversion_fraction * p_recognize) ** n_samples


def samples_needed(diversion_fraction: float, p_recognize: float, confidence: float) -> int:
    return math.ceil(math.log(1.0 - confidence) / math.log(1.0 - diversion_fraction * p_recognize))


def min_detectable_diversion(n_samples: int, p_recognize: float, confidence: float) -> float:
    """Smallest diverted fraction caught with the given confidence by n samples."""
    return (1.0 - (1.0 - confidence) ** (1.0 / n_samples)) / p_recognize


def months_to_detect(samples_per_year: float, diversion_fraction: float, p_recognize: float, confidence: float = 0.95) -> float:
    return samples_needed(diversion_fraction, p_recognize, confidence) / (samples_per_year / 12.0)


# ---- mass balance (sections 3.3.4 and 5.3.2) -------------------------------------------------------------------------------
@dataclass
class FabPeriod:
    wafers_received: int
    wafers_scrapped: int            # destroyed under witness
    wafer_prints_logged: int        # attested prints from registered lithography machines
    dies_per_wafer: int             # known for a given design on an equally spaced grid
    dies_shipped_licensed: int
    dies_rejected_destroyed: int    # shown to inspectors, destroyed under monitoring
    wip_start: int = 0              # wafers in process at the start and end of the period
    wip_end: int = 0


def reconcile_fab(p: FabPeriod, wafer_tolerance: int = 0, die_tolerance: float = 0.0) -> dict:
    """Close the books for one period.

    unlogged_wafers: wafers that left the blank stock with no logged print and no witnessed scrap: candidates for processing
        on an undeclared lithography machine.
    missing_dies: dies the logged prints must have produced that are neither shipped nor destroyed: diversion candidates.
    A negative missing_dies means more dies shipped than prints allow, which is an inflated count and also a finding."""
    unlogged = p.wafers_received + p.wip_start - p.wip_end - p.wafers_scrapped - p.wafer_prints_logged
    expected = p.wafer_prints_logged * p.dies_per_wafer
    missing = expected - p.dies_shipped_licensed - p.dies_rejected_destroyed
    findings = []
    if unlogged > wafer_tolerance:
        findings.append(f"{unlogged} wafers unaccounted for: possible undeclared lithography")
    if missing > die_tolerance * expected:
        findings.append(f"{missing} dies unaccounted for ({missing / max(expected, 1):.3%} of expected)")
    if missing < -die_tolerance * max(expected, 1):
        findings.append(f"{-missing} more dies shipped than the logged prints can produce")
    if unlogged < -wafer_tolerance:
        findings.append(f"{-unlogged} more wafers printed than were received: records do not reconcile")
    return {"unlogged_wafers": unlogged, "expected_dies": expected, "missing_dies": missing,
            "balanced": not findings, "findings": findings}


def consumable_balance(received: float, used_per_wafer: float, wafers_printed: int, waste_recorded: float = 0.0,
                       inventory_start: float = 0.0, inventory_end: float = 0.0, tolerance: float = 0.02) -> dict:
    """Mass balance of a perishable input such as photoresist. Consumption beyond what logged prints justify is skimming:
    it implies wafers processed somewhere the log does not see."""
    consumed = inventory_start + received - inventory_end - waste_recorded
    expected = used_per_wafer * wafers_printed
    unexplained = consumed - expected
    return {"consumed": consumed, "expected": expected, "unexplained": unexplained,
            "unexplained_wafers": unexplained / used_per_wafer if used_per_wafer else math.nan,
            "balanced": abs(unexplained) <= tolerance * max(expected, 1e-12)}


# ---- custody and lithography census (sections 3.3.4, 5.3.1) ---------------------------------------------------------------
def custody_balance(issued, **accounted) -> dict:
    """Every serial issued (lenses, machines, chips) must end up in exactly one account: installed in a registered machine,
    returned to the vendor, destroyed under witness. Returns what no account holds and what several accounts claim."""
    issued = set(issued)
    seen, double = {}, set()
    for name, serials in accounted.items():
        for s in set(serials):
            if s in seen:
                double.add(s)
            seen[s] = name
    return {"unaccounted": sorted(issued - set(seen)), "unknown": sorted(set(seen) - issued), "double_counted": sorted(double)}


def reconcile_litho(registered, delivered, serviced=()) -> dict:
    """Registered machines against vendor delivery and service records. A machine the vendor delivered or services that
    is not on the register is charged to its host state as continuously producing dark compute (section 3.3.4)."""
    registered, delivered, serviced = set(registered), set(delivered), set(serviced)
    return {"delivered_unregistered": sorted(delivered - registered),
            "registered_without_delivery_record": sorted(registered - delivered),
            "serviced_unregistered": sorted(serviced - registered),
            "dark_candidates": sorted((delivered | serviced) - registered)}


def dark_stock_after(n_machines: int, months: float, h100e_per_machine_month: float = DUV_H100E_PER_MONTH[0]) -> float:
    """Dark compute (H100e) accumulated by n unregistered machines producing for `months` (section 6.5.4)."""
    return n_machines * h100e_per_machine_month * months


def litho_dark_source(n_machines: int, months: float, high: bool = False) -> Source:
    """The ledger line for unregistered lithography: undiscounted, since chips from a covert line are fully usable."""
    rate = DUV_H100E_PER_MONTH[1 if high else 0]
    return Source("unregistered lithography", dark_stock_after(n_machines, months, rate),
                  note=f"{n_machines} machine(s) x {months:g} months at {rate:,.0f} H100e per month")
