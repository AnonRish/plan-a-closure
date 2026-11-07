"""Phases, ramp-up time and licence auctions of the transition (paper sections 1.1, 3.4 and 4.4)."""
from __future__ import annotations

import math
from dataclasses import dataclass

PHASES = {0: "pre-pause market", 1: "design and production set-up", 2: "managed substitution",
          3: "inference-only primary operation"}


def classify_phase(pause_agreed: bool, high_volume_inference_only_production: bool, inference_only_share: float,
                   majority: float = 0.5) -> int:
    """Phase 0 before an agreement; 1 from the agreement; 2 once high-volume inference-only production starts; 3 once most
    inference is served by inference-only chips."""
    if not pause_agreed:
        return 0
    if inference_only_share > majority:
        return 3
    return 2 if high_volume_inference_only_production else 1


# Phase 1 for OpenAI's Jalapeno inference chip (section 4.4); the last stage is the paper's own estimate, not a measurement
JALAPENO_MONTHS = {"design_to_tapeout": 13, "tapeout_to_first_silicon": 6, "first_silicon_to_production": 7}

# Table 4.1: months of chip design programmes, from scratch and derivative
TABLE_4_1 = [("Google TPU v1", 15, "scratch"), ("Groq TSP", 36, "scratch"), ("Cerebras WSE-1", 48, "scratch"),
             ("Etched first generation", 36, "scratch"), ("Taalas HC1", 30, "scratch"), ("OpenAI Jalapeno", 26, "scratch"),
             ("Nvidia data-centre GPU generation", 24, "derivative"), ("Cerebras WSE-2", 20, "derivative"),
             ("Cerebras WSE-3", 35, "derivative"), ("Taalas HC1, new model on existing platform", 2, "derivative")]


def phase1_months(design_to_tapeout: float, tapeout_to_first_silicon: float, first_silicon_to_production: float) -> float:
    return design_to_tapeout + tapeout_to_first_silicon + first_silicon_to_production


def phase2_months(training_capable_h100e: float, monthly_inference_only_h100e: float) -> float:
    """Months to displace the training-capable stock at a constant monthly rate of inference-only installation."""
    return training_capable_h100e / monthly_inference_only_h100e


def phase2_months_growing(training_capable_h100e: float, monthly0: float, monthly_growth: float) -> float:
    """Same, when the monthly installation rate itself grows by `monthly_growth` per month (geometric series)."""
    if monthly_growth <= 0:
        return phase2_months(training_capable_h100e, monthly0)
    return math.log1p(training_capable_h100e * monthly_growth / monthly0) / math.log1p(monthly_growth)


def transition_years(phase1: float, phase2: float) -> float:
    return (phase1 + phase2) / 12.0


def reallocation_gain(training_share: float) -> float:
    """Multiple of inference capacity gained when the compute that went to training (e.g. 62% for two leading labs) is
    reallocated to inference."""
    return 1.0 / (1.0 - training_share)


def demand_catches_up_years(supply_multiple: float, demand_growth_per_year: float = 10.0) -> float:
    """Years until demand growing at the given factor per year has used up a one-off supply multiple (the reallocation gain).
    Arithmetic on two of the paper's inputs, not a forecast."""
    return math.log(supply_multiple) / math.log(demand_growth_per_year)


# ---- licence auctions (section 3.4.3) ------------------------------------------------------------------------------------
@dataclass
class Bid:
    bidder: str
    quantity: float     # H100e of training-capable inference licence
    price: float


def cap_schedule(initial_cap: float, installed_inference_only_per_period: list) -> list:
    """Licence cap per auction: the initial cap less the inference-only capacity installed so far, never below zero."""
    caps, installed = [], 0.0
    for x in installed_inference_only_per_period:
        caps.append(max(initial_cap - installed, 0.0))
        installed += x
    return caps


def clear_auction(bids: list, cap: float) -> dict:
    """Uniform-price clearing: highest bids first until the cap is exhausted; every winner pays the lowest accepted price."""
    allocations, remaining, clearing = {}, cap, 0.0
    for b in sorted(bids, key=lambda x: -x.price):
        if remaining <= 0:
            break
        q = min(b.quantity, remaining)
        allocations[b.bidder] = allocations.get(b.bidder, 0.0) + q
        remaining -= q
        clearing = b.price
    return {"allocations": allocations, "clearing_price": clearing, "licensed": cap - remaining, "unallocated": remaining}


def trade_in_due(previous: dict, new_allocations: dict) -> dict:
    """Licences expire at the next auction: whatever an operator held and did not win again must be traded in."""
    return {k: previous[k] - new_allocations.get(k, 0.0) for k in previous if previous[k] > new_allocations.get(k, 0.0)}
