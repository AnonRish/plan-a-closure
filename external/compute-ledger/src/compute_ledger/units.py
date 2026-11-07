"""H100-equivalents: compute measured in Total Processing Performance (TPP) relative to an H100."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

H100_TPP = 15_800.0        # the plan's definition of one H100e ("~15,800 TPP")
AI_FLOOR_TPP = 4_000.0     # AI-relevance floor on compute, set just below an A100


def h100e_from_tpp(tpp: float) -> float:
    return tpp / H100_TPP


def tpp_from_h100e(h100e: float) -> float:
    return h100e * H100_TPP


@dataclass(frozen=True)
class ChipSpec:
    tpp: float
    memory_bandwidth_tbps: float
    memory_capacity_gb: float
    nic_gbps: float


FLOORS = ChipSpec(AI_FLOOR_TPP, 1.0, 32.0, 100.0)


def ai_relevant(chip: ChipSpec, floors: ChipSpec = FLOORS) -> bool:
    """A chip is AI-relevant only if it clears all four floors (compute, memory bandwidth, memory capacity, NIC)."""
    return (chip.tpp >= floors.tpp and chip.memory_bandwidth_tbps >= floors.memory_bandwidth_tbps
            and chip.memory_capacity_gb >= floors.memory_capacity_gb and chip.nic_gbps >= floors.nic_gbps)


def failing_floors(chip: ChipSpec, floors: ChipSpec = FLOORS) -> Dict[str, bool]:
    return {"tpp": chip.tpp < floors.tpp, "memory_bandwidth": chip.memory_bandwidth_tbps < floors.memory_bandwidth_tbps,
            "memory_capacity": chip.memory_capacity_gb < floors.memory_capacity_gb, "nic": chip.nic_gbps < floors.nic_gbps}
