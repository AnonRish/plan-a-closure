"""
§22, part 1: installation granularity as a dial — how many physical tap
points get INSTALLED, which is a different question from §14's "how finely
does a fixed evidence stream get sampled." §8 named this dial explicitly
("fleet-wide down to per-server down to per-GPU") without building it.
This is where it actually gets built.

Reuses §20's own corrected fleet numbers rather than inventing fresh ones:
imports max_supportable_gpus() directly from power_envelope.py so this
section's reference facility size is guaranteed identical to §20's, not a
retyped copy of a number from prose that could silently drift.
"""
import json
from power_envelope import max_supportable_gpus

# ---- §20's own numbers, imported directly rather than retyped ----
GPUS_PER_FACILITY = max_supportable_gpus(5)   # §20: max GPUs a 5MW
                                                # intertie supports at
                                                # PUE 1.15 -> 5702
GPUS_PER_INFERENCE_UNIT = 8                    # HGX H100 8-GPU baseboard,
                                                # §20's own NVIDIA datasheet
                                                # citation

# ---- new to this section ----
UNITS_PER_RACK = 6   # stated assumption, not a measured figure: an
                       # air-cooled 42U-class rack housing six 8-GPU
                       # HGX-class nodes (each node itself spans several
                       # rack units once PSUs, NICs, and cooling headroom
                       # are counted). A liquid-cooled, rack-scale design
                       # (NVL72-class) would collapse the rack and server
                       # granularities in this model down to nearly the
                       # same tap count; this model doesn't separately
                       # represent that design point.

GRANULARITIES = ["facility", "rack", "server"]


def units_per_facility():
    return GPUS_PER_FACILITY / GPUS_PER_INFERENCE_UNIT


def racks_per_facility(units_per_fac):
    return units_per_fac / UNITS_PER_RACK


def taps_per_facility(units_per_fac, racks_per_fac):
    """How many physical tap points exist at each granularity, for ONE
    reference facility. facility=1 (a single aggregation-point tap covers
    everything); rack=one tap per rack; server=one tap per inference unit."""
    return {"facility": 1.0, "rack": racks_per_fac, "server": units_per_fac}


if __name__ == "__main__":
    units_fac = units_per_facility()
    racks_fac = racks_per_facility(units_fac)
    per_fac = taps_per_facility(units_fac, racks_fac)

    print("=" * 92)
    print(f"Reference facility (§20's own max_supportable_gpus(5)): {GPUS_PER_FACILITY:,} GPUs")
    print(f"  / {GPUS_PER_INFERENCE_UNIT} GPUs per inference unit = {units_fac:,.2f} inference units")
    print(f"  / {UNITS_PER_RACK} units per rack (stated assumption) = {racks_fac:,.2f} racks")
    print("=" * 92)
    for g in GRANULARITIES:
        print(f"  {g:<10} -> {per_fac[g]:>10,.2f} taps / facility")

    print()
    print("=" * 92)
    print("Fleet-wide tap count, swept across facility count")
    print("=" * 92)
    FLEET_SIZES = [100, 300, 1000]   # §20's own 1,000-facility reference is
                                       # the upper end; smaller counts stand
                                       # in for an earlier-stage regime with
                                       # fewer participating facilities
    header = f"{'facilities':<12}" + "".join(f"{g:<16}" for g in GRANULARITIES)
    print(header)
    fleet_sweep = {}
    for n_fac in FLEET_SIZES:
        row = {g: per_fac[g] * n_fac for g in GRANULARITIES}
        fleet_sweep[n_fac] = row
        print(f"{n_fac:<12}" + "".join(f"{row[g]:<16,.0f}" for g in GRANULARITIES))

    lo = fleet_sweep[FLEET_SIZES[0]]["facility"]
    hi = fleet_sweep[FLEET_SIZES[-1]]["server"]
    print()
    print(f"Range spanned: {lo:,.0f} (facility-level, {FLEET_SIZES[0]} facilities) "
          f"to {hi:,.0f} (server-level, {FLEET_SIZES[-1]} facilities) — "
          f"low hundreds through high hundred-thousands.")

    with open("tap_granularity_model.json", "w") as f:
        json.dump(
            {
                "gpus_per_facility": GPUS_PER_FACILITY,
                "gpus_per_inference_unit": GPUS_PER_INFERENCE_UNIT,
                "units_per_rack_assumption": UNITS_PER_RACK,
                "units_per_facility": units_fac,
                "racks_per_facility": racks_fac,
                "taps_per_facility": per_fac,
                "fleet_sweep": fleet_sweep,
            },
            f,
            indent=2,
        )
    print("\nwritten: tap_granularity_model.json")
