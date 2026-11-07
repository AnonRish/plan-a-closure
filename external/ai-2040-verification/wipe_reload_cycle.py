"""
§19: the actual decision-relevant number isn't "how fast is a data diode"
in isolation, it's the full wipe-then-reload cycle time, since that's what
determines how often §15's memory wipe can realistically run without
unacceptable service disruption. Built on this document's own real §15
measurement (not a fresh assumption) and a properly-ranged data-diode
bandwidth figure (checked against real commercial products, not just one
source's 10-40 Gbps claim).
"""

# §15's own real, measured result (this document): ~715-747 MiB/s single-core
# CPU/DRAM wipe rate. A real deployment parallelizes across many cores/HBM
# channels; modeled here as a tunable speedup factor over the measured
# single-core baseline, not a fresh, unmeasured assumption.
MEASURED_WIPE_MIBPS_SINGLE_CORE = 730  # midpoint of §15's 715-747 range
PARALLELISM_ASSUMPTIONS = {
    "single-core (as directly measured, §15)": 1,
    "16-core parallel (conservative real deployment)": 16,
    "128-way parallel (GPU-HBM-scale, aspirational)": 128,
}

MODEL_SIZE_GB = 140  # 70B params, FP16 — same reference size as the
                       # comparison this section is checking

# Data-diode bandwidth: NOT just the 10-40 Gbps range — checked against
# real commercial products. Most (Waterfall, RSN, Owl Talon One) sit in the
# 1-10 Gbps range; Owl's Talon Torrent PFD platform is the real outlier,
# rated up to 100 Gbps. The honest range is wider on BOTH ends than a
# single 10-40 Gbps figure suggests.
DIODE_BANDWIDTH_GBPS = {
    "typical commercial (1 Gbps)": 1,
    "upper-typical commercial (10 Gbps)": 10,
    "Owl Talon Torrent PFD, real high-end product (100 Gbps)": 100,
}

ARCHITECTURE_B_GBPS = 400  # existing switched fabric, full utilization —
                            # matches this document's own §2/§4 frontend
                            # bandwidth figures in scale

def reload_time_s(size_gb, bandwidth_gbps):
    size_gigabits = size_gb * 8
    return size_gigabits / bandwidth_gbps


def wipe_time_s(capacity_gib, wipe_rate_mibps):
    return (capacity_gib * 1024) / wipe_rate_mibps


if __name__ == "__main__":
    print("=" * 100)
    print("Reload time, Architecture A (data diode) across the REAL commercial bandwidth range")
    print("=" * 100)
    for label, gbps in DIODE_BANDWIDTH_GBPS.items():
        t = reload_time_s(MODEL_SIZE_GB, gbps)
        print(f"  {label:<55} {t:>8.1f}s  ({t/60:.1f} min)")

    t_b = reload_time_s(MODEL_SIZE_GB, ARCHITECTURE_B_GBPS)
    print()
    print(f"Architecture B (400G switched fabric, full utilization): {t_b:.1f}s")

    print()
    print("=" * 100)
    print("Full wipe-then-reload cycle: a hypothetical 1.7TB tray-scale capacity (§15's own")
    print("extrapolation target), at different real parallelism assumptions for the wipe stage")
    print("=" * 100)
    CAPACITY_GIB = 1740.8  # §15's own tray-scale extrapolation figure, GiB

    for wipe_label, factor in PARALLELISM_ASSUMPTIONS.items():
        wipe_rate = MEASURED_WIPE_MIBPS_SINGLE_CORE * factor
        t_wipe = wipe_time_s(CAPACITY_GIB, wipe_rate)
        print(f"\nWipe stage: {wipe_label} -> {wipe_rate:,} MiB/s -> {t_wipe/60:.1f} min")
        for diode_label, gbps in DIODE_BANDWIDTH_GBPS.items():
            t_reload = reload_time_s(MODEL_SIZE_GB, gbps)
            total_a = t_wipe + t_reload
            total_b = t_wipe + t_b
            print(f"  + Architecture A reload ({diode_label:<45}): "
                  f"total cycle = {total_a/60:6.1f} min  "
                  f"(reload is {100*t_reload/total_a:5.1f}% of the cycle)")
        print(f"  + Architecture B reload (400G fabric):{'':<40} "
              f"total cycle = {total_b/60:6.1f} min  "
              f"(reload is {100*t_b/total_b:5.2f}% of the cycle)")
