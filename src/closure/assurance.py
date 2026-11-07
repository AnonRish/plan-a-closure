"""Plan A's assurance curve and the composition of independent verification layers.

Assurance curve (Appendix A.3): coverage = 1 - F*, confidence = 1 - exp(-N_ver * F*)."""
from __future__ import annotations

import math

H100_TDP_W = 700.0
GRANULARITY_H100E = {2030: 4000.0, 2032: 400.0, 2034: 100.0}   # per-server, per-shelf, per-GPU taps (plan figure)


def nines(conf: float) -> float:
    return min(15.0, -math.log10(max(1e-300, 1.0 - conf)))   # float64 resolution: cap the display at 15 nines


def confidence_at_coverage(n_ver: float, coverage: float) -> float:
    return 1.0 - math.exp(-n_ver * (1.0 - coverage))


def coverage_at_confidence(n_ver: float, conf: float) -> float:
    return 1.0 - (-math.log(1.0 - conf)) / n_ver


def assurance_curve(n_ver: float, coverages=(0.0, 0.9, 0.99, 0.999, 0.9999)) -> list:
    return [(c, confidence_at_coverage(n_ver, c)) for c in coverages]


def n_verified(budget_c: float, packet_h100e_hours: float, pool_h100e_hours: float) -> float:
    """N_ver = C * N_packets = C * pool / packet size."""
    return budget_c * pool_h100e_hours / packet_h100e_hours


def recompute_detection(budget_c: float, hidden_h100e_hours: float, packet_h100e_hours: float) -> float:
    return 1.0 - math.exp(-budget_c * hidden_h100e_hours / packet_h100e_hours)


def detection_time_hours(budget_c: float, packet_h100e_hours: float, deployment_h100e: float, conf: float = 0.99) -> float:
    w = -math.log(1.0 - conf) * packet_h100e_hours / budget_c
    return w / deployment_h100e


def h100e_hours_to_joules(h100e_hours: float, watts: float = H100_TDP_W) -> float:
    return h100e_hours * 3600.0 * watts


def compose(probs, rho: float = 0.0) -> float:
    """Detection probability of several layers. rho=0: independent. rho=1: perfectly correlated (best layer only).
    The interpolation is a sensitivity heuristic, not a derivation: always report rho=0 AND rho=1."""
    probs = [min(max(p, 0.0), 1.0) for p in probs]
    miss_ind = math.prod(1.0 - p for p in probs)
    miss_cor = 1.0 - max(probs) if probs else 1.0
    return 1.0 - (miss_ind ** (1.0 - rho)) * (miss_cor ** rho)


def end_to_end(hidden_h100e_hours: float, packet_h100e_hours: float, budget_c: float, closure_p: float = 0.0,
               state_p: float = 0.0, rho: float = 0.0) -> dict:
    p_rec = recompute_detection(budget_c, hidden_h100e_hours, packet_h100e_hours)
    layers = {"recompute": p_rec, "closure": closure_p, "state": state_p}
    return {"layers": layers, "independent": compose(list(layers.values()), 0.0),
            "correlated": compose(list(layers.values()), 1.0), "assumed_rho": rho,
            "assumed": compose(list(layers.values()), rho)}
