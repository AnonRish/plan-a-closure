"""Why a pause can be an equilibrium (paper sections 2.3 and 8.4.3): payoffs, patience and monitoring.

Symmetric two-player game over {pause, race}. R: both pause. T: race while the other pauses. S: pause while the other
races. P: both race. A Prisoner's Dilemma has T > R > P > S and no pause equilibrium; a Stag Hunt has R > T >= P > S and two.
In the repeated game, cooperation is sustained by a trigger strategy if players are patient enough and defection is
detected often enough: monitoring quality enters the threshold directly, which is the paper's argument for informative, timely
verification."""
from __future__ import annotations

ACTIONS = ("pause", "race")


def _u(T, R, P, S):
    return {("pause", "pause"): R, ("race", "pause"): T, ("pause", "race"): S, ("race", "race"): P}


def classify(T: float, R: float, P: float, S: float) -> str:
    if T > R > P > S:
        return "prisoners_dilemma"
    if R > T >= P > S:
        return "stag_hunt"
    if T > R > S > P:
        return "chicken"
    if R > T and S > P:
        return "harmony"
    return "other"


def pure_equilibria(T: float, R: float, P: float, S: float) -> list:
    u = _u(T, R, P, S)
    eq = []
    for a in ACTIONS:
        for b in ACTIONS:
            row_ok = all(u[(a, b)] >= u[(x, b)] for x in ACTIONS)
            col_ok = all(u[(b, a)] >= u[(x, a)] for x in ACTIONS)   # column player's payoff mirrors by symmetry
            if row_ok and col_ok:
                eq.append((a, b))
    return eq


def grim_threshold(T: float, R: float, P: float) -> float:
    """Smallest discount factor that sustains cooperation under grim trigger with perfect monitoring: (T-R)/(T-P)."""
    return (T - R) / (T - P)


def threshold_with_detection(T: float, R: float, P: float, detect: float) -> float:
    """Same when a defection is noticed (and punished for ever) only with probability `detect` each period, no false alarms:
    (T-R) / (T-R + detect*(R-P)). Equal to the grim threshold at detect = 1; tends to 1 as detection vanishes."""
    return (T - R) / (T - R + detect * (R - P))


def values(T: float, R: float, P: float, delta: float, detect: float, false_alarm: float = 0.0) -> tuple:
    """(value of cooperating, value of defecting every period) under a grim trigger that fires on a signal. The signal fires
    with probability `detect` after a defection and `false_alarm` after cooperation."""
    punish = delta * P / (1.0 - delta)
    v_c = (R + false_alarm * punish) / (1.0 - delta * (1.0 - false_alarm))
    v_d = (T + detect * punish) / (1.0 - delta * (1.0 - detect))
    return v_c, v_d


def sustainable(T: float, R: float, P: float, delta: float, detect: float, false_alarm: float = 0.0) -> bool:
    v_c, v_d = values(T, R, P, delta, detect, false_alarm)
    return v_c >= v_d


def patience_threshold(T: float, R: float, P: float, detect: float, false_alarm: float = 0.0, tol: float = 1e-10):
    """Smallest discount factor that sustains cooperation, by bisection; None if no patience is enough (detect <= false alarm)."""
    hi = 1.0 - 1e-9
    if not sustainable(T, R, P, hi, detect, false_alarm):
        return None
    lo = 1e-9
    while hi - lo > tol:
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if sustainable(T, R, P, mid, detect, false_alarm) else (mid, hi)
    return hi


def min_detection(T: float, R: float, P: float, delta: float, false_alarm: float = 0.0, tol: float = 1e-10):
    """Smallest per-period detection probability that sustains cooperation at this patience; None if even certain detection
    is not enough."""
    if not sustainable(T, R, P, delta, 1.0, false_alarm):
        return None
    lo, hi = false_alarm, 1.0
    while hi - lo > tol:
        mid = (lo + hi) / 2
        lo, hi = (lo, mid) if sustainable(T, R, P, delta, mid, false_alarm) else (mid, hi)
    return hi


def monitoring_supports_pause(payoffs: tuple, delta: float, detect: float, false_alarm: float = 0.0) -> dict:
    """payoffs = (T, R, P, S). Does this verification regime (per-period detection, false-alarm rates) sustain a pause between
    players of this patience?"""
    T, R, P, S = payoffs
    return {"game": classify(T, R, P, S), "pure_equilibria": pure_equilibria(T, R, P, S),
            "sustainable": sustainable(T, R, P, delta, detect, false_alarm),
            "patience_needed": patience_threshold(T, R, P, detect, false_alarm),
            "detection_needed": min_detection(T, R, P, delta, false_alarm)}
