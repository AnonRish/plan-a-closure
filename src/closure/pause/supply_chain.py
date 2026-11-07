"""Supply-chain chokepoints and who must participate (paper sections 3.1, 3.3.2 and 5.2).

The case that chip production can be governed rests on a few stages that only a handful of firms in a handful of
jurisdictions can perform. A stage is *controlled* by a coalition only if every jurisdiction with a capable supplier is in it:
one supplier outside can serve a defector. This module encodes the stages the paper names and answers three questions: which
stages a given coalition leaves open, which member's departure opens which stage, and which high-value hosts of chips a census
would still miss.

The table is the paper's own reading of its section 5.2 (and footnote 36), not an independent survey. Shares and suppliers are as
of its writing."""
from __future__ import annotations

from dataclasses import dataclass

EU_MEMBERS_NAMED = ("Netherlands", "Germany")        # the paper names these two when it says "European Union"


@dataclass(frozen=True)
class Chokepoint:
    stage: str
    suppliers: tuple
    jurisdictions: tuple           # every jurisdiction with a capable supplier
    concentration: str
    note: str = ""


CHOKEPOINTS = (
    Chokepoint("refined magnet rare earths", ("Chinese refiners",), ("China",), "91% of 2024 supply refined in mainland China"),
    Chokepoint("high-purity quartz", ("Spruce Pine, North Carolina",), ("United States",), "an overwhelmingly large share of world supply",
               "a hurricane there disrupted global silicon supply"),
    Chokepoint("EUV lithography machines", ("ASML",), ("Netherlands",), "monopoly", "about 100,000 parts from 5,000 suppliers"),
    Chokepoint("DUV (ArF immersion) lithography machines", ("ASML", "Nikon", "Yuliangsheng"), ("Netherlands", "Japan", "China"),
               "dominant, one new entrant", "Yuliangsheng reportedly expects 12 machines at 28 nm by end 2026"),
    Chokepoint("EUV optics and precision mirrors", ("Zeiss",), ("Germany",), "sole producer of some components"),
    Chokepoint("EUV coater/developer", ("Tokyo Electron",), ("Japan",), "near-complete monopoly"),
    Chokepoint("leading-edge foundry and advanced packaging", ("TSMC", "Samsung", "SMIC", "TSMC Arizona"),
               ("Taiwan", "South Korea", "China", "United States"), "TSMC leads; others capable but less advanced"),
    Chokepoint("high-bandwidth memory", ("SK hynix",), ("South Korea", "United States"), "significant role in development",
               "the firm is offshoring some capability to the US"),
    Chokepoint("accelerator design", ("NVIDIA", "AMD", "Google", "Amazon", "Huawei", "Cambricon"), ("United States", "China"),
               "over 60% of global AI compute capacity is NVIDIA's", "every chip in Epoch AI's sales data has an American or Chinese designer"),
)

# section 3.1: the initial participants, "jurisdictions that currently enjoy nearly a collective global monopoly" on
# cutting-edge chip manufacturing and frontier training
PARTICIPANTS_3_1 = ("United States", "China", "European Union", "United Kingdom", "Taiwan", "South Korea", "Japan")
# section 3.1: other high-value signatories where many existing chips or compute infrastructure sit
STOCK_HOSTS = ("Singapore", "Malaysia", "Indonesia", "Thailand", "Vietnam", "United Arab Emirates", "Saudi Arabia")
# section 3.3.2: jurisdictions outside the US and China whose resellers and data centres a census must reach
CENSUS_TRANSIT = ("Singapore", "Malaysia", "Taiwan", "United Arab Emirates")


def expand(coalition) -> set:
    c = set(coalition)
    if "European Union" in c:
        c |= set(EU_MEMBERS_NAMED)
    return c


def uncovered(coalition, chokepoints=CHOKEPOINTS) -> list:
    """Stages a coalition does not control, with the outside jurisdictions that can still supply a defector."""
    have = expand(coalition)
    return [{"stage": cp.stage, "outside": sorted(set(cp.jurisdictions) - have), "suppliers": cp.suppliers}
            for cp in chokepoints if not set(cp.jurisdictions) <= have]


def critical_members(coalition, chokepoints=CHOKEPOINTS) -> dict:
    """For each member, the stages that would be left open if it left. An empty list means the table gives it no hardware
    leverage (a member can matter for other reasons: finance, frontier labs, politics)."""
    base = {u["stage"] for u in uncovered(coalition, chokepoints)}
    out = {}
    for m in coalition:
        rest = [x for x in coalition if x != m]
        out[m] = sorted({u["stage"] for u in uncovered(rest, chokepoints)} - base)
    return out


def census_gaps(coalition) -> dict:
    """High-value chip hosts and transit jurisdictions a census would not reach because they are outside the coalition."""
    have = expand(coalition)
    return {"stock_hosts": [j for j in STOCK_HOSTS if j not in have], "census_transit": [j for j in CENSUS_TRANSIT if j not in have]}


def minimum_coalition(chokepoints=CHOKEPOINTS) -> set:
    """Smallest set that controls every listed stage: every jurisdiction with a capable supplier, since one outside is a leak."""
    return {j for cp in chokepoints for j in cp.jurisdictions}
