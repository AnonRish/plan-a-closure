"""Inference-only retrofit logistics (Plan A, Feb 2029): how fast can taps be installed?

One tap per inference unit of `racks_per_unit` racks is the reading under which the plan's own numbers close:
China's 20,000 taps cover 40% of the US's 200,000 racks in month 1, and +10,000 taps/month reach 80% by month 3."""
from __future__ import annotations

import math


def units_needed(racks: int, racks_per_unit: int = 4) -> int:
    return math.ceil(racks / racks_per_unit)


def schedule(racks_to_cover: int, tap_stock: int, taps_per_month: int, months: int = 6,
             racks_per_unit: int = 4, taps_per_unit: int = 1, install_cap_units_per_month=None) -> list:
    """Cumulative fraction of the counterparty's racks under inference-only verification per month.
    Month 1 uses the existing stock; purchases arrive from month 2."""
    need = units_needed(racks_to_cover, racks_per_unit)
    done, out = 0, []
    for m in range(1, months + 1):
        taps = tap_stock + taps_per_month * (m - 1)
        avail = taps // taps_per_unit
        target = min(need, avail)
        if install_cap_units_per_month is not None:
            target = min(target, done + install_cap_units_per_month)
        done = max(done, target)
        out.append((m, done, done / need))
    return out


def proportional(schedule_a: list, schedule_b: list) -> list:
    """The plan's 'proportional schedule determined by the slower side's achievable pace'."""
    return [(m, min(fa, fb)) for (m, _, fa), (_, _, fb) in zip(schedule_a, schedule_b)]
