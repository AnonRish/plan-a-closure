#!/usr/bin/env python3
"""H100-equivalent (H100e) conversions from the AI 2040 covert-projects supplement, section 3.3.

Track 3 counts compute in H100e and sets the audit threshold T in H100e, while grid queues,
interconnection filings and datacenter records speak in megawatts. This module holds the
supplement's own MW <-> H100e conversion so the two can be related with every assumption
written down. Every constant below is the supplement's assumption, not a measurement.

    python track3_units.py --h100e 30000 --year 2028.6
    python track3_units.py --facility-mw 1000 --year 2026.5
"""
from __future__ import annotations

import argparse
import json

SOURCE = "https://ai-2040.com/supplements/covert-ai-projects (section 3.3, Quantitative estimates)"

BASELINE_YEAR = 2026.0
US_IT_WATTS_PER_H100E_AT_BASELINE = 833.0  # 2026.0 US IT power per H100e at max utilization
US_EFFICIENCY_PROGRESS_PER_YEAR = 1.37  # average US power-efficiency progress per year, 2026.0-2028.0
CHINA_DOMESTIC_EFFICIENCY_GAP = 3.7  # Chinese domestic power-efficiency gap during the diversion period
DEFAULT_PUE = 1.4  # covert datacenter peak PUE (facility power / IT power)
SMUGGLED_CHIP_YEAR = 2028.6
DECOMMISSIONED_CHIP_YEAR = 2026.5

# The supplement's worked example: a covert datacenter with 1 GW of facility power supports
# about this many H100e. The tests check that the functions below reproduce these.
SUPPLEMENT_1GW_EXAMPLES = {
    "smuggled_us_chips_2028": {"year": SMUGGLED_CHIP_YEAR, "efficiency_gap": 1.0, "stated_h100e": 1_900_000},
    "decommissioned_us_chips": {"year": DECOMMISSIONED_CHIP_YEAR, "efficiency_gap": 1.0, "stated_h100e": 1_000_000},
    "domestic_chips_2028": {
        "year": SMUGGLED_CHIP_YEAR,
        "efficiency_gap": CHINA_DOMESTIC_EFFICIENCY_GAP,
        "stated_h100e": 525_000,
    },
}


def _check(value: float, name: str, *, minimum: float, inclusive: bool = True) -> None:
    ok = value >= minimum if inclusive else value > minimum
    if not ok:
        raise ValueError(f"{name} must be {'>=' if inclusive else '>'} {minimum}, got {value}")


def it_watts_per_h100e(year: float, efficiency_gap: float = 1.0) -> float:
    """IT watts needed per H100e at max utilization in ``year``.

    Starts from the 2026.0 US figure, improves by the yearly efficiency factor, and is
    multiplied by ``efficiency_gap`` for chips less power-efficient than the US frontier.
    """
    _check(efficiency_gap, "efficiency_gap", minimum=0.0, inclusive=False)
    return US_IT_WATTS_PER_H100E_AT_BASELINE / (US_EFFICIENCY_PROGRESS_PER_YEAR ** (year - BASELINE_YEAR)) * efficiency_gap


def h100e_from_it_mw(it_mw: float, year: float, efficiency_gap: float = 1.0) -> float:
    _check(it_mw, "it_mw", minimum=0.0)
    return it_mw * 1e6 / it_watts_per_h100e(year, efficiency_gap)


def it_mw_from_h100e(h100e: float, year: float, efficiency_gap: float = 1.0) -> float:
    _check(h100e, "h100e", minimum=0.0)
    return h100e * it_watts_per_h100e(year, efficiency_gap) / 1e6


def h100e_from_facility_mw(
    facility_mw: float, year: float, pue: float = DEFAULT_PUE, efficiency_gap: float = 1.0
) -> float:
    """H100e a facility with ``facility_mw`` of total power can support."""
    _check(pue, "pue", minimum=1.0)
    return h100e_from_it_mw(facility_mw / pue, year, efficiency_gap)


def facility_mw_from_h100e(
    h100e: float, year: float, pue: float = DEFAULT_PUE, efficiency_gap: float = 1.0
) -> float:
    """Total facility power needed to run ``h100e`` of compute."""
    _check(pue, "pue", minimum=1.0)
    return it_mw_from_h100e(h100e, year, efficiency_gap) * pue


def threshold_record(
    h100e: float, year: float, pue: float = DEFAULT_PUE, efficiency_gap: float = 1.0
) -> dict:
    """A threshold T in H100e together with the conversion assumptions behind its MW equivalent."""
    return {
        "value": h100e,
        "unit": "H100e",
        "year": year,
        "pue": pue,
        "efficiency_gap": efficiency_gap,
        "it_watts_per_h100e": it_watts_per_h100e(year, efficiency_gap),
        "it_mw": it_mw_from_h100e(h100e, year, efficiency_gap),
        "facility_mw": facility_mw_from_h100e(h100e, year, pue, efficiency_gap),
        "source": SOURCE,
        "note": "Supplement assumptions, not measurements.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--h100e", type=float, help="convert this many H100e to MW")
    group.add_argument("--facility-mw", type=float, help="convert this much facility power to H100e")
    ap.add_argument("--year", type=float, required=True, help="chip-generation year, e.g. 2028.6")
    ap.add_argument("--pue", type=float, default=DEFAULT_PUE)
    ap.add_argument("--efficiency-gap", type=float, default=1.0)
    args = ap.parse_args()
    if args.h100e is not None:
        out = threshold_record(args.h100e, args.year, args.pue, args.efficiency_gap)
    else:
        out = {
            "facility_mw": args.facility_mw,
            "year": args.year,
            "pue": args.pue,
            "efficiency_gap": args.efficiency_gap,
            "h100e": h100e_from_facility_mw(args.facility_mw, args.year, args.pue, args.efficiency_gap),
            "source": SOURCE,
        }
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
