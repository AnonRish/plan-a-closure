"""Units and the physics anchor: turn hidden joules into hidden FLOPs and H100-hours."""
from __future__ import annotations

from dataclasses import dataclass

H100_PEAK_DENSE_BF16 = 989e12  # FLOP/s, convention only (see README)


@dataclass
class EnergyFloor:
    """Lowest measured joules per FLOP on the enrolled chip over clocks, caps, shapes and dtypes.

    Hidden FLOPs <= hidden joules / j_per_flop. Must be *measured* (hw-selftest), never assumed.
    """
    j_per_flop: float
    source: str = "unmeasured-default"


def block_capacity_j(n_gpu: int, p_max_w: float, L: int, dt: float) -> float:
    return n_gpu * p_max_w * L * dt


def hidden_flop_bound(hidden_j: float, floor: EnergyFloor) -> float:
    return hidden_j / floor.j_per_flop


def h100_hours(flop: float, peak: float = H100_PEAK_DENSE_BF16) -> float:
    return flop / (peak * 3600.0)


def apply_slack(hidden_ub_j: float, predicted_j: float, slack_frac: float) -> float:
    """Inflate a bound by the measured efficiency slack of allowed software stacks."""
    return hidden_ub_j + slack_frac * predicted_j
