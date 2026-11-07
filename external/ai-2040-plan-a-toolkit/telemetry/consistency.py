
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Interval:
    low:float
    high:float
    def __post_init__(self):
        if self.low<0 or self.high<self.low: raise ValueError("invalid interval")

@dataclass(frozen=True)
class TelemetryClaim:
    expected_h100e_hours:Interval
    observed_h100e_hours:Interval
    expected_energy_kwh:Interval
    observed_energy_kwh:Interval

def consistency(claim:TelemetryClaim)->dict:
    compute_ok=not (claim.observed_h100e_hours.high<claim.expected_h100e_hours.low or claim.observed_h100e_hours.low>claim.expected_h100e_hours.high)
    energy_ok=not (claim.observed_energy_kwh.high<claim.expected_energy_kwh.low or claim.observed_energy_kwh.low>claim.expected_energy_kwh.high)
    return {
        "status":"CONSISTENT" if compute_ok and energy_ok else "INCONSISTENT",
        "compute_overlap":compute_ok,
        "energy_overlap":energy_ok,
        "note":"consistency telemetry is auxiliary evidence and is not by itself proof of workload identity",
    }
