"""Catching a rogue internal deployment (Verification Plan, 2034 section).

Model. Every packet represents ``packet_size`` H100e-hours of work. A rogue
deployment of ``size`` H100e that runs for ``hours`` hours produces
``size * hours / packet_size`` unauthorised packets. A verifier that recomputes
each packet independently with probability ``budget`` catches it with
``1 - (1 - budget) ** n_fake``.

The fluid (real-valued) packet count is used, so answers are smooth in ``size``
and ``hours``; the supplement's own worked numbers are fluid too.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .core import fake_packets_for_confidence, p_detected_exact


@dataclass(frozen=True)
class RogueDeploymentModel:
    budget: float               # C: fraction of packets recomputed
    packet_size: float          # H100e-hours of work per packet

    def __post_init__(self):
        if not (0.0 < self.budget <= 1.0):
            raise ValueError("budget must be in (0, 1]")
        if self.packet_size <= 0:
            raise ValueError("packet_size must be > 0")

    # -- forward ----------------------------------------------------------- #
    def fake_packets(self, size_h100e: float, hours: float) -> float:
        if size_h100e < 0 or hours < 0:
            raise ValueError("size and hours must be >= 0")
        return size_h100e * hours / self.packet_size

    def p_detect(self, size_h100e: float, hours: float) -> float:
        """P(detected within ``hours``) for a rogue deployment of ``size_h100e``."""
        return p_detected_exact(self.budget, self.fake_packets(size_h100e, hours))

    # -- inverse ----------------------------------------------------------- #
    def h100e_hours_to_detect(self, confidence: float, *, model: str = "exact") -> float:
        """Unapproved H100e-hours after which detection reaches ``confidence``."""
        return fake_packets_for_confidence(self.budget, confidence, model=model) * self.packet_size

    def hours_to_detect(self, size_h100e: float, confidence: float, *, model: str = "exact") -> float:
        if size_h100e <= 0:
            return math.inf
        return self.h100e_hours_to_detect(confidence, model=model) / size_h100e

    # -- cost -------------------------------------------------------------- #
    def recompute_capacity_h100e(self, pool_h100e: float) -> float:
        """Continuous recomputation capacity the verifier must own: budget * pool.

        A 1 % budget on a 33 B H100e pool is 330 M H100e of *trusted* recompute,
        larger than the entire 2029 world stock. Detection maths does not care;
        the bill does.
        """
        if pool_h100e < 0:
            raise ValueError("pool must be >= 0")
        return self.budget * pool_h100e


#: Logging granularity levels from the 2030/2032/2034 figure: H100e per tap.
TAP_LEVELS_H100E = {
    "per-server (2030)": 4000.0,
    "per-shelf (2032)": 400.0,
    "per-GPU (2034)": 100.0,
}


def _size_key(s: float) -> str:
    return str(int(s)) if float(s).is_integer() else f"{s:g}"


def granularity_table(budget: float, confidence: float, rogue_sizes, *,
                      hours_per_packet: float = 1.0, model: str = "poisson"):
    """Hours to detect each rogue size at each tap granularity.

    Packet size = H100e per tap * hours per packet (one packet per tap-hour by
    default, as in the supplement's 2034 example).
    """
    rows = []
    for label, h100e_per_tap in TAP_LEVELS_H100E.items():
        m = RogueDeploymentModel(budget, h100e_per_tap * hours_per_packet)
        rows.append({
            "granularity": label,
            "packet_size_h100e_hours": m.packet_size,
            **{f"hours_to_detect_{_size_key(s)}_h100e": m.hours_to_detect(s, confidence, model=model)
               for s in rogue_sizes},
        })
    return rows
