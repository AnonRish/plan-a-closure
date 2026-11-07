"""
§30: Track 3 -- the source material's own reframe is the actual starting
point, not "detect all undeclared compute" (an unbounded, arguably
intractable goal) but "Problem 2: verifying that unknown compute is
INCONSEQUENTIAL" -- the same bound-it-don't-eliminate-it move this
document has made repeatedly (§1's completeness scope, §4's hash-only
commitment, §12's bit-capacity bound, §17's residual-capacity target),
now confirmed as the source material's own chosen frame for its hardest
remaining problem, not an invention of this document's own to make an
intractable question feel smaller than it is.

Two real, checkable pieces this section can actually verify rather than
just cite: the fab-concentration argument for why new covert chip supply
should be near-zero, and a size-vs-detectability bound built on §20's own
already-tested power-envelope machinery plus a real, demonstrated (not
hypothetical) satellite thermal-detection capability.
"""
from power_envelope import required_facility_mw, PUE, EFFECTIVE_W_PER_GPU

# ---- Part 1: the fab-concentration claim, verified rather than trusted ----
def fraction_of_cumulative_capacity_built_in_last_n_years(growth_rate, total_years, n_recent_years):
    """If new fab capacity added per year grows at `growth_rate`x annually
    (the source's own cited 3x/yr figure), what fraction of ALL cumulative
    capacity ever built was added in just the most recent n_recent_years?
    Geometric growth means this is dominated by the most recent terms --
    computed directly, not asserted from the shape of exponential growth
    alone."""
    yearly_added = [growth_rate ** t for t in range(total_years + 1)]
    cumulative_total = sum(yearly_added)
    cumulative_recent = sum(yearly_added[-n_recent_years:])
    return cumulative_recent / cumulative_total


# ---- Part 2: covert-datacenter size vs. a REAL demonstrated detection capability ----
# SatVu (UK, real company) published a satellite thermal image in Dec 2025
# clearly resolving the waste-heat signature of a real, named 700MW
# datacenter (the Riot Platforms Bitcoin-mining facility, Rockdale, TX) at
# 3.5m / 11.5ft resolution, from orbit -- a demonstrated capability, not a
# hypothetical one. Used here as a real anchor point, not an assumption.
DEMONSTRATED_DETECTED_FACILITY_MW = 700.0
DEMONSTRATED_DETECTION_RESOLUTION_M = 3.5


def covert_facility_mw(n_gpus):
    return required_facility_mw(n_gpus)


if __name__ == "__main__":
    print("=" * 92)
    print("1. Verifying the source material's own fab-concentration claim")
    print('   ("every 2 years 90% of the fabs are new fabs", given 3x/yr production growth)')
    print("=" * 92)
    frac = fraction_of_cumulative_capacity_built_in_last_n_years(growth_rate=3, total_years=20, n_recent_years=2)
    print(f"  Computed fraction of cumulative capacity built in the most recent 2 years,")
    print(f"  under sustained 3x/yr growth: {frac:.4f} ({frac*100:.1f}%)")
    print(f"  Source's claim: ~90%. Computed: {frac*100:.1f}%. Holds, and for a clean reason:")
    print(f"  under any growth rate g, the fraction from the last n years converges to")
    print(f"  1 - g^(-n) regardless of how many total years are modeled -- verified below")
    print(f"  by checking convergence rather than trusting one number:")
    for total_years in [5, 10, 20, 40]:
        f = fraction_of_cumulative_capacity_built_in_last_n_years(3, total_years, 2)
        print(f"    total_years={total_years:<4} -> fraction={f:.4f}")
    theoretical = 1 - 3 ** -2
    print(f"  Closed form 1 - 3^-2 = {theoretical:.4f} -- matches, confirming this is a real")
    print(f"  property of sustained exponential growth, not an artifact of the year range chosen.")

    print()
    print("=" * 92)
    print("2. Covert-datacenter power draw vs. a REAL demonstrated satellite detection capability")
    print("=" * 92)
    print(f"  Real anchor: SatVu (Dec 2025) published a satellite thermal image clearly resolving")
    print(f"  a real, named {DEMONSTRATED_DETECTED_FACILITY_MW:.0f}MW datacenter's waste-heat signature at")
    print(f"  {DEMONSTRATED_DETECTION_RESOLUTION_M}m resolution, from orbit. Not hypothetical -- already done.")
    print()
    print(f"  {'covert size (GPUs)':<22}{'required facility draw (MW)':<30}{'vs. the 700MW demonstrated case'}")
    for n_gpus in [500, 5_000, 5_702, 50_000, 100_000, 500_000]:
        mw = covert_facility_mw(n_gpus)
        ratio = mw / DEMONSTRATED_DETECTED_FACILITY_MW
        print(f"  {n_gpus:<22,}{mw:<30.2f}{ratio:.3f}x")

    print()
    print("  A covert operation at §20's own reference-facility scale (5,702 GPUs) draws about")
    print(f"  {covert_facility_mw(5702):.1f}MW -- roughly {DEMONSTRATED_DETECTED_FACILITY_MW/covert_facility_mw(5702):.0f}x SMALLER than the real facility SatVu already")
    print("  resolved clearly from orbit. That's not evidence such a facility WOULD stay hidden --")
    print("  a smaller absolute heat signature is a real, physical constraint on the OTHER side of")
    print("  this problem too, not an assumption. It's evidence the actual detection question isn't")
    print("  'can waste heat ever be seen from orbit' (already demonstrated, yes) -- it's 'at what")
    print("  scale does an AI-specific covert facility's signature clear a REAL sensor's real noise")
    print("  floor,' which needs the sensor's own sensitivity spec, not just its best-case resolution")
    print("  figure, and this document doesn't have access to that number. Stated as the actual gap,")
    print("  not glossed into false confidence either direction.")

    print()
    print("=" * 92)
    print("3. Connecting to the source's own quantified estimate")
    print("=" * 92)
    print("  Source estimate: median ~0.5% of world AI-relevant compute (80% CI 0.1-1.4%) as dark")
    print("  compute at deal start. World compute referenced elsewhere in this document's own")
    print("  citations (§28's context) runs to roughly 930M H100e by the scenario's own numbers.")
    world_h100e = 930_000_000
    for pct, label in [(0.001, "0.1% (CI low)"), (0.005, "0.5% (median)"), (0.014, "1.4% (CI high)")]:
        n = world_h100e * pct
        mw = covert_facility_mw(int(n))
        print(f"  {label:<16} -> ~{n:,.0f} H100e -> ~{mw:,.0f}MW if concentrated in ONE facility")
    print()
    print("  Even the 80th-percentile estimate, concentrated into a single hypothetical facility,")
    print("  draws power on the order of the SatVu-demonstrated case above -- and the source's own")
    print("  point is that this dark compute is very unlikely to BE concentrated that way (spread")
    print("  across many smaller, harder-to-individually-resolve sites is the more likely shape),")
    print("  which is exactly why 'bound it, don't eliminate it' is the honest frame here: the")
    print("  quantity is estimated small enough, on the source's own numbers, to not change the")
    print("  deal's basic viability, not proven to be zero.")
