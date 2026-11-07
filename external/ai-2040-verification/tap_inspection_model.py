"""
§22, part 2: given N tap installations at some granularity, what inspection
rate does a realistic, bounded inspector budget actually deliver PER TAP,
and what does that mean for the "bypass-and-restore" residual risk the
source material itself flags as unsolved? This section's own self-check
demands that gap be preserved, not solved artificially — everything below
is built toward quantifying it honestly, not closing it.

Reuses §20's own facility-visit cadence (10% of 1,000 facilities/quarter,
i.e. lambda_facility = 0.4/year) rather than inventing a fresh number. The
new parameter this section adds is K: how many individual taps one
facility visit can actually check, which is what turns "the facility got
visited" into "THIS tap got checked."

Two regimes, both computed, both verified by simulation, not just one
asserted:
  - UNSEALED bypass: prover removes/reroutes a tap, operates covertly,
    restores it to an indistinguishable state before anyone looks. Only a
    LIVE catch -- an inspection landing during the bypass window -- catches
    this. This is Johnston et al.'s "intrusion detection" (real-time)
    case, and it's the harder one.
  - SEALED bypass: a tamper-indicating seal breaks the instant the tap is
    disturbed and stays detectably broken (barring seal defeat, its own
    separate difficulty axis -- see write-up) until the next time THAT
    SPECIFIC tap is actually checked. This is Johnston et al.'s "tamper
    detection" (delayed, after-the-fact) case.
"""
import numpy as np
import json
from tap_granularity_model import (
    GRANULARITIES, units_per_facility, racks_per_facility, taps_per_facility,
)

RNG = np.random.default_rng(2226)

# ---- §20's own facility-visit cadence, reused directly ----
FACILITY_VISIT_PROB_PER_QUARTER = 0.10   # §20: 100 of 1,000 facilities/quarter
LAMBDA_FACILITY_PER_YEAR = FACILITY_VISIT_PROB_PER_QUARTER * 4   # 0.4/yr

# ---- new to this section: per-visit tap-checking throughput ----
K_MANUAL = 100      # ~5 min/tap manual check (physical presence + seal-
                      # serial scan + registry cross-check), one
                      # inspector-day budget
K_AUTOMATED = 1000   # illustrative batch/photographic-scan capability --
                      # NOT a claim this exists today; see write-up


def lambda_tap_per_year(taps_per_fac, k_per_visit, lambda_facility=LAMBDA_FACILITY_PER_YEAR):
    t_sample = min(1.0, k_per_visit / taps_per_fac)
    return lambda_facility * t_sample, t_sample


def p_caught_unsealed_formula(lam_per_year, duration_years):
    return 1 - np.exp(-lam_per_year * duration_years)


def p_campaign_caught_formula(lam_per_year, duration_years, n_events):
    p_single = p_caught_unsealed_formula(lam_per_year, duration_years)
    return 1 - (1 - p_single) ** n_events


# ---------------------------------------------------------------------
# Monte Carlo verification -- built from first principles (cumulative
# exponential inter-arrival times = a real Poisson-process construction),
# not the Poisson-count shortcut, which would just be re-deriving the same
# formula through a different door rather than independently checking it.
# ---------------------------------------------------------------------
def _single_event_catch_trials(lam_per_year, duration_years, n_trials, horizon_years, max_arrivals):
    inter_arrival = RNG.exponential(1.0 / lam_per_year, size=(n_trials, max_arrivals))
    arrival_times = np.cumsum(inter_arrival, axis=1)
    starts = RNG.uniform(0, horizon_years - duration_years, size=n_trials)
    ends = starts + duration_years
    hits = (arrival_times >= starts[:, None]) & (arrival_times <= ends[:, None])
    caught = np.any(hits, axis=1)
    # Sanity: was max_arrivals generous enough that no trial's simulated
    # arrivals ran out before reaching the horizon? If the last arrival
    # time is short of the horizon for any trial, that trial's later
    # arrivals were silently truncated and the result would bias low --
    # checked directly, not assumed sufficient.
    sufficient = arrival_times[:, -1].min() >= horizon_years
    return caught, sufficient


def simulate_single_event_catch(lam_per_year, duration_years, n_trials=100_000, horizon_years=25):
    max_arrivals = int(lam_per_year * horizon_years * 4) + 50
    caught, sufficient = _single_event_catch_trials(lam_per_year, duration_years, n_trials, horizon_years, max_arrivals)
    return caught.mean(), sufficient


def simulate_campaign_catch(lam_per_year, duration_years, n_events, n_trials=50_000, horizon_years=25):
    max_arrivals = int(lam_per_year * horizon_years * 4) + 50
    caught_any = np.zeros(n_trials, dtype=bool)
    all_sufficient = True
    for _ in range(n_events):
        caught, sufficient = _single_event_catch_trials(lam_per_year, duration_years, n_trials, horizon_years, max_arrivals)
        caught_any |= caught
        all_sufficient &= sufficient
    return caught_any.mean(), all_sufficient


def simulate_time_to_discovery(lam_per_year, n_trials=200_000):
    """SEALED case: the seal breaks at bypass-start; by the memoryless
    property of a Poisson process, time to the next inspection from ANY
    starting point is Exponential(lambda) -- this IS the first-principles
    construction (waiting time to the first arrival of a freshly-started
    Poisson process), not a shortcut."""
    return RNG.exponential(1.0 / lam_per_year, size=n_trials).mean()


if __name__ == "__main__":
    units_fac = units_per_facility()
    racks_fac = racks_per_facility(units_fac)
    per_fac = taps_per_facility(units_fac, racks_fac)

    print("=" * 96)
    print(f"Per-tap inspection rate at K={K_MANUAL} (manual) vs K={K_AUTOMATED} (automated/batch scan)")
    print("=" * 96)
    print(f"{'granularity':<12}{'taps/facility':<16}{'t_sample(K=100)':<18}{'lambda_tap(K=100)/yr':<22}{'t_sample(K=1000)':<19}{'lambda_tap(K=1000)/yr'}")
    lambda_results = {}
    for g in GRANULARITIES:
        lam_manual, t_manual = lambda_tap_per_year(per_fac[g], K_MANUAL)
        lam_auto, t_auto = lambda_tap_per_year(per_fac[g], K_AUTOMATED)
        lambda_results[g] = {"manual": {"t_sample": t_manual, "lambda": lam_manual},
                              "automated": {"t_sample": t_auto, "lambda": lam_auto}}
        print(f"{g:<12}{per_fac[g]:<16,.1f}{t_manual:<18.3f}{lam_manual:<22.4f}{t_auto:<19.3f}{lam_auto:.4f}")

    print()
    print("=" * 96)
    print("Single-event P(caught) at K=100 -- formula vs. Monte Carlo (real arrival-process simulation)")
    print("=" * 96)
    DURATIONS = {"1 day": 1/365, "1 week": 7/365, "1 month": 30/365, "1 quarter": 91/365}
    print(f"{'granularity':<12}{'duration':<12}{'formula':<12}{'monte_carlo':<14}{'sim_valid'}")
    single_event_results = {}
    for g in GRANULARITIES:
        lam = lambda_results[g]["manual"]["lambda"]
        for dname, d in DURATIONS.items():
            formula = p_caught_unsealed_formula(lam, d)
            mc, valid = simulate_single_event_catch(lam, d)
            single_event_results.setdefault(g, {})[dname] = {"formula": formula, "monte_carlo": mc, "sim_valid": bool(valid)}
            print(f"{g:<12}{dname:<12}{formula:<12.4f}{mc:<14.4f}{valid}")

    print()
    print("=" * 96)
    print("Campaign-level: N_events(M, granularity) and P(campaign ever caught), d=1 month, K=100")
    print("=" * 96)
    M_VALUES = [1, 6, 60]
    M_VALUES_LABELS = {1: "1 unit", 6: "6 units (~1 rack)", 60: "60 units (~10 racks)"}
    D_CAMPAIGN = 30 / 365
    print(f"{'M':<24}{'granularity':<12}{'N_events':<10}{'P_caught(formula)':<20}{'P_caught(MC, small-N only)'}")
    campaign_results = {}
    for M in M_VALUES:
        for g in GRANULARITIES:
            if g == "facility":
                # one tap covers the entire facility -- bypassing it exposes
                # everything up to and including the whole facility in a
                # single event, regardless of how much of that the prover
                # actually intends to use
                n_events = 1
            else:
                units_per_tap = per_fac["server"] / per_fac[g]  # rack->6, server->1
                n_events = min(int(np.ceil(M / units_per_tap)), int(np.ceil(per_fac[g])))
            lam = lambda_results[g]["manual"]["lambda"]
            formula = p_campaign_caught_formula(lam, D_CAMPAIGN, n_events)
            mc_str = "-"
            if n_events <= 20:  # only Monte-Carlo-verify at tractable N_events;
                                 # larger N_events reported analytically, per
                                 # the write-up's own honesty about what was
                                 # simulated vs. extrapolated
                mc, valid = simulate_campaign_catch(lam, D_CAMPAIGN, n_events, n_trials=20_000)
                mc_str = f"{mc:.4f}" + ("" if valid else " (!)")
            campaign_results.setdefault(M, {})[g] = {"n_events": n_events, "formula": formula, "monte_carlo": mc_str}
            print(f"{M_VALUES_LABELS[M]:<24}{g:<12}{n_events:<10}{formula:<20.4f}{mc_str}")

    # whole-facility campaign, analytic only (N_events too large to MC at full scale)
    print()
    whole_facility_results = {}
    for g in GRANULARITIES:
        M_whole = per_fac["server"]
        n_events = 1 if g == "facility" else int(np.ceil(per_fac[g]))
        lam = lambda_results[g]["manual"]["lambda"]
        formula = p_campaign_caught_formula(lam, D_CAMPAIGN, n_events)
        whole_facility_results[g] = {"n_events": n_events, "formula": formula}
        print(f"whole facility (~{M_whole:.0f} units){'':<3}{g:<12}{n_events:<10}{formula:<20.4f}(analytic only, N_events too large to Monte Carlo)")

    print()
    print("=" * 96)
    print("SEALED case: expected time-to-discovery (years), formula vs. Monte Carlo")
    print("=" * 96)
    print(f"{'granularity':<12}{'K':<20}{'1/lambda (formula)':<22}{'monte_carlo'}")
    discovery_results = {}
    for g in GRANULARITIES:
        for k_label, lam in [("manual(K=100)", lambda_results[g]["manual"]["lambda"]),
                               ("automated(K=1000)", lambda_results[g]["automated"]["lambda"])]:
            formula = 1.0 / lam
            mc = simulate_time_to_discovery(lam)
            discovery_results.setdefault(g, {})[k_label] = {"formula": formula, "monte_carlo": mc}
            print(f"{g:<12}{k_label:<20}{formula:<22.3f}{mc:.3f}")

    with open("tap_inspection_model.json", "w") as f:
        json.dump(
            {
                "lambda_facility_per_year": LAMBDA_FACILITY_PER_YEAR,
                "K_manual": K_MANUAL,
                "K_automated": K_AUTOMATED,
                "lambda_by_granularity": lambda_results,
                "single_event_catch": single_event_results,
                "campaign_catch": campaign_results,
                "whole_facility_campaign": whole_facility_results,
                "time_to_discovery": discovery_results,
            },
            f,
            indent=2,
        )
    print("\nwritten: tap_inspection_model.json")
