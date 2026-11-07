"""From closure evidence to treaty-ledger entries.

The paper's political discount factors are assumptions: for transitional inference service it takes pi_E = 0.001 by supposing
that 10% of operators evade and each diverts 1%. The closure kit measures what it can actually see: the smallest hidden
energy fraction a cluster audit reliably detects (`closure_gap_fraction`, results.json). That number is a measured ceiling on
what an operator could hide from this audit, so it can stand in for pi_E on the audited share of a fleet, with an explicit
assumption (not a measurement) for the rest.

This is descriptive and post hoc: it is not one of the pre-registered claims, and it inherits every limit of the trial it
reads (a simulated trial says nothing about real hardware; efficiency slack is invisible to an energy audit)."""
from __future__ import annotations

from . import pausegame
from .treaty_ledger import Source
from .units import H100E_FLOPS


DEFAULT_E_FLOOR_J_PER_FLOP = 0.5e-12     # the trial's unmeasured default (TrialConfig.e_floor_j_per_flop)


def closure_discount(results: dict, p_max_w: float = 700.0, e_floor_j_per_flop: float = None) -> dict:
    """Read a closure results.json into a discount for the audited cluster.

    pi_e: the closure gap, the hidden share of the cluster's energy capacity detected reliably (1.0 if the trial never
        reached reliable detection, i.e. no discount earned).
    tau_e: the H100e of work one GPU slot's power could fund at the energy floor, a conservative conversion (>= 1) from
        capacity-energy to H100e, not a utilisation discount."""
    gap = results.get("closure_gap_fraction")
    if e_floor_j_per_flop is None:
        e_floor_j_per_flop = ((results.get("hidden_compute_at_gap_per_week") or {}).get("energy_floor_j_per_flop")
                              or DEFAULT_E_FLOOR_J_PER_FLOP)
    caveats = []
    status = results.get("status", "")
    if "SIM" in str(status).upper():
        caveats.append("trial is SIMULATED: this is a method check, not evidence about any real cluster")
    if gap is None:
        caveats.append("no reliable detection level was reached; no discount earned")
    b = results.get("bound", {}) or {}
    sl = results.get("slack") or {}
    if sl.get("slack_inflated_gap_fraction") is not None and gap is not None:
        gap = max(float(gap), float(sl["slack_inflated_gap_fraction"]))
        caveats.append(f"gap includes the measured efficiency slack (s_max={sl['s_max']:.3g}, {sl.get('source')})")
    elif b.get("coverage_slack_expected_to_fail") is not None:
        caveats.append("an operator with efficiency slack can hide work from an energy audit; the bound excludes that class")
    pi_e = 1.0 if gap is None else min(1.0, float(gap))
    tau_e = p_max_w / (e_floor_j_per_flop * H100E_FLOPS)
    return {"pi_e": pi_e, "tau_e": tau_e, "gap": gap, "e_floor_j_per_flop": e_floor_j_per_flop, "caveats": caveats}


def blended_pi(pi_audited: float, audit_coverage: float, pi_unaudited: float = 0.001) -> float:
    """Discount for a fleet when only a share of it is audited; the unaudited share keeps an assumed discount."""
    return audit_coverage * pi_audited + (1.0 - audit_coverage) * pi_unaudited


def transitional_source(fleet_h100e: float, results: dict, audit_coverage: float, pi_unaudited: float = 0.001,
                        name: str = "transitional service (closure-audited)", **kw) -> Source:
    """A ledger line for training-capable chips in transitional service whose covert discount comes from closure evidence.
    Breakout exposure is unaffected: seizing the fleet is charged at pi = tau = 1."""
    d = closure_discount(results, **kw)
    pi = blended_pi(d["pi_e"], audit_coverage, pi_unaudited)
    tau = (audit_coverage * d["tau_e"] * d["pi_e"] + (1.0 - audit_coverage) * pi_unaudited) / pi if pi > 0 else 1.0
    return Source(name, fleet_h100e, pi_e=pi, tau_e=tau, retires=True,
                  note=f"audited share {audit_coverage:.0%} at closure gap {d['gap']}; rest assumed {pi_unaudited}")


def detection_at(results: dict, intensity: float, adversary: str = "constant", conservative: bool = True):
    """Detection probability per audited block at a hidden-load intensity, from the trial's detection table (the lower
    Clopper-Pearson bound if `conservative`). None if that cell was not measured."""
    cell = (results.get("detection_combined", {}).get(adversary, {}) or {}).get(str(intensity))
    if not cell:
        return None
    return cell["cp95_lower"] if conservative else cell["rate"]


def monitoring_supports_pause(results: dict, payoffs: tuple, delta: float, intensity: float, adversary: str = "constant",
                              false_alarm: float = 0.0) -> dict:
    """Feed the measured per-block detection probability into the repeated-game threshold: is this audit informative
    enough to sustain a pause between players of patience delta?"""
    d = detection_at(results, intensity, adversary)
    if d is None:
        return {"detect": None, "sustainable": None, "note": "no measurement at that intensity"}
    out = pausegame.monitoring_supports_pause(payoffs, delta, d, false_alarm)
    out["detect"] = d
    return out
