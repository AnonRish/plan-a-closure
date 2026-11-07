"""Inference-only hardware: the residual training factor and what a seized fleet could do (paper sections 3.2.1, 4.1, 6.4.4).

A system's *residual training factor* is phi = (bound on its peak training throughput, in H100e) / (its peak licensed
inference rating, in inference-H100e). A fleet of phi = 0.001 chips replacing training-capable ones removes 99.9% of the
fleet's training capacity. Seizing such a fleet in an overt breakout is charged at pi = tau = 1, so phi is what protects
the breakout ledger."""
from __future__ import annotations

import math
from dataclasses import dataclass


def inference_h100e(tokens_per_s: float, cluster_tokens_per_s: float, cluster_h100e: float) -> float:
    """Inference-H100e: peak token throughput relative to a standardised general-purpose cluster, times its H100e (section 3.2.1)."""
    return tokens_per_s / cluster_tokens_per_s * cluster_h100e


def residual_training_factor(training_bound_h100e: float, inference_rating_h100e: float) -> float:
    return training_bound_h100e / inference_rating_h100e


def training_capacity_reduction(phi: float) -> float:
    """Share of a like-for-like training-capable fleet's training capacity removed by replacing it with phi-chips."""
    return 1.0 - phi


@dataclass(frozen=True)
class Rating:
    name: str
    inference_h100e: float
    training_bound_h100e: float

    @property
    def phi(self) -> float:
        return residual_training_factor(self.training_bound_h100e, self.inference_h100e)


def fleet_phi(items) -> float:
    """Average residual training factor of a fleet, weighted by inference-H100e. items: (count, Rating)."""
    num = sum(n * r.training_bound_h100e for n, r in items)
    den = sum(n * r.inference_h100e for n, r in items)
    return num / den


def seized_fleet_exposure(inference_h100e_total: float, phi: float) -> float:
    """Training capacity (H100e) of an inference-only fleet if a state seizes it for a breakout (pi = tau = 1)."""
    return phi * inference_h100e_total


def servable_demand(exposure_budget_h100e: float, phi: float) -> float:
    """Inference demand (inference-H100e) a fleet of residual factor phi can serve inside an overt-breakout budget."""
    return exposure_budget_h100e / phi


def max_phi(inference_h100e_total: float, exposure_budget_h100e: float) -> float:
    """Largest average residual training factor that keeps a fleet serving the given demand inside the budget."""
    return exposure_budget_h100e / inference_h100e_total


def token_oracle_gemm_rate(context_tokens: float, tokens_per_s: float, elements_per_token: float = 1.0) -> float:
    """FLOP/s of general matrix multiplication obtainable through the token interface alone (section 4.1, footnote 39).

    Multiplying an n x k by a k x m matrix needs nk + mk context tokens in and nm tokens out for 2nmk FLOPs; with the
    best square shape n = m = k = sqrt(L e / 3) this is (2/3) * sqrt(L e / 3) * e * r. With one 16-bit element per
    token (e = 1), a billion-token context and a million tokens per second it is about 12 GFLOP/s."""
    s = math.sqrt(context_tokens * elements_per_token / 3.0)
    return (2.0 / 3.0) * s * elements_per_token * tokens_per_s


def machines_to_match(target_flops: float, per_machine_flops: float) -> float:
    return target_flops / per_machine_flops


def inference_speed_as_training_multiple(speed_ratio: float, eta: float = 0.7) -> float:
    """Training-FLOP multiple equivalent to a serial inference speed-up, from Ord's trade-off log(C) + eta*log(T) = const.
    A 50x speed-up is worth about 15x training FLOP; the paper takes beta_E = 10 as the conservative covert target."""
    return speed_ratio ** eta
