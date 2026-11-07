"""
§29: Track 1's actual claim, tested against this document's own prior
math rather than taken on faith: "embedded auditors together with
existing hardware might be able to reach sufficient assurance" -- i.e.,
you don't need §2's passive optical splitter, §3's TEE gateway, or any
of the purpose-built hardware Track 2 (§1-28, this whole document) spent
28 sections on, IF an auditor is embedded closely enough. The claim rests
entirely on CADENCE (how often is someone actually looking) rather than
on exotic hardware. §22 already built the real math connecting cadence to
detection probability -- this file reuses it directly, with one changed
input, rather than inventing new math for what's really the same question
asked with a different auditor-access model.

The honest asymmetry this file does NOT get to erase by reusing good
math: §22's tap taps EVERY packet crossing a physical link, mechanically,
whether or not anyone is watching in that instant, and the passive
splitter has "no logic, no firmware, no state" to compromise (§2). An
embedded human auditor, however frequent, only sees what they're shown or
what they think to look for -- a fundamentally different failure mode
(company-controlled access) that no amount of cadence fixes, named
directly in 29c rather than left for the numbers below to imply away.
"""
import numpy as np
from tap_inspection_model import (
    lambda_tap_per_year, p_caught_unsealed_formula, p_campaign_caught_formula,
    simulate_single_event_catch, simulate_time_to_discovery,
    LAMBDA_FACILITY_PER_YEAR,  # §22's own 0.4/yr, the quarterly-10%-sampled baseline
)

# Track 1: an embedded auditor has STANDING access, not a per-visit budget
# -- K isn't the constraint the way it was for §22's touring inspector, so
# it's set effectively unlimited here (K_effective >> any realistic
# taps-per-facility count, so t_sample saturates to 1.0 regardless of
# granularity). What varies instead is how CONTINUOUSLY that access is
# actually exercised.
K_EMBEDDED = 1_000_000

EMBEDDED_CADENCES = {
    "Track 2 baseline (§22, quarterly 10%-sampled international regime)": LAMBDA_FACILITY_PER_YEAR,
    "Track 1, monthly embedded review": 12.0,
    "Track 1, weekly embedded review": 52.0,
    "Track 1, daily embedded presence": 365.0,
}


if __name__ == "__main__":
    print("=" * 96)
    print("1. Same Poisson-process math §22 already built and verified, one input changed:")
    print("   auditor cadence (lambda), not tap hardware granularity")
    print("=" * 96)
    DURATIONS = {"1 week": 7 / 365, "1 month": 30 / 365, "1 quarter": 91 / 365}
    print(f"{'regime':<70}{'lambda/yr':<12}" + "".join(f"{d:<12}" for d in DURATIONS))
    for label, lam in EMBEDDED_CADENCES.items():
        row = [p_caught_unsealed_formula(lam, d) for d in DURATIONS.values()]
        print(f"{label:<70}{lam:<12.2f}" + "".join(f"{v:<12.4f}" for v in row))

    print()
    print("=" * 96)
    print("2. Sealed-bypass expected time-to-discovery -- verified against real simulation,")
    print("   not just the formula")
    print("=" * 96)
    print(f"{'regime':<70}{'formula (days)':<18}{'monte carlo (days)'}")
    for label, lam in EMBEDDED_CADENCES.items():
        formula_years = 1.0 / lam
        mc_years = simulate_time_to_discovery(lam)
        print(f"{label:<70}{formula_years*365:<18.1f}{mc_years*365:.1f}")

    print()
    print("The claim holds up quantitatively, as far as cadence alone goes: going from §22's")
    print("quarterly-sampled 0.4/yr to even monthly embedded review (12/yr, a real, achievable")
    print("cadence for a single company's own auditor, not a fleet-wide sampling regime) cuts")
    print("expected discovery time by roughly 30x, with no new hardware at all. Daily presence")
    print("cuts it by roughly 900x. This is exactly why the source material's claim is plausible,")
    print("not just aspirational -- it's the same math this document already trusted in §22,")
    print("landing very differently once the input reflects Track 1's actual access model.")

    print()
    print("=" * 96)
    print("3. What cadence does NOT fix -- the honest limit on this whole comparison")
    print("=" * 96)
    print("Every number above assumes the auditor's cadence translates directly into a real")
    print("chance of catching a real bypass event, exactly the way §22's touring inspector")
    print("checking a physical tap's seal did. That assumption holds for §22's case because a")
    print("passive tap has no discretion about what it sees -- it mechanically mirrors every")
    print("packet, full stop. An embedded human auditor has discretion, by construction: they")
    print("see what they're shown, or what they think to check. Daily presence with restricted,")
    print("company-controlled access is not the same claim as daily presence with the kind of")
    print("access §2's splitter has by physical design -- and nothing in the Poisson-process math")
    print("above can tell the difference between those two cases, because it was never built to.")
