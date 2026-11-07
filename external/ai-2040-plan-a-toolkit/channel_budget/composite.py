from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class CapacityInterval:
    low_bits_per_second:float
    high_bits_per_second:float
    def __post_init__(self):
        if self.low_bits_per_second<0 or self.high_bits_per_second<self.low_bits_per_second: raise ValueError("invalid interval")

@dataclass(frozen=True)
class ChannelBudget:
    timing:CapacityInterval
    header:CapacityInterval
    payload:CapacityInterval

def compose_budget(b:ChannelBudget)->dict:
    total=CapacityInterval(b.timing.low_bits_per_second+b.header.low_bits_per_second+b.payload.low_bits_per_second,b.timing.high_bits_per_second+b.header.high_bits_per_second+b.payload.high_bits_per_second)
    return {"status":"PASS","combined_capacity_bits_per_second":{"low":total.low_bits_per_second,"high":total.high_bits_per_second},"note":"additive upper bound; not a Shannon-capacity proof"}
