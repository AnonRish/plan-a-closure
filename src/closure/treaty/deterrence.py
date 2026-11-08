"""When does verification deter a covert programme? Payoffs from the proposals' penalty ladders, detection from
measurements. Each model has a closed form and a simulation the tests check it against.

1. Per period. A covert programme gains G in each period it goes undetected; detection (probability p per period)
   costs C once (sanctions, embargo: the middle-powers ladder) and ends it. Starting it has value
   ((1 - p) G - p C) / (1 - d (1 - p)) for discount d, which is <= 0 exactly when p >= G / (G + C), whatever d.
2. Winner-take-all. The asi-prevention paper's point (and MIRI's "Threat of Sabotage"): a programme that finishes
   (T undetected periods, e.g. the days covert compute needs to reach a threshold run) is worth W, far more than any
   one period's gain. Without discounting it does not pay iff (1 - p)^T W <= (1 - (1 - p)^T) C, so verification must
   catch it before it finishes with probability at least W / (W + C): 99% if winning is worth 100 times the penalty.
3. Sustained hidden load against a sequential test. One block's test (the trial's f95) is not the whole story: a load
   that shifts every block's standardized residual by delta is caught by a one-sided CUSUM. Siegmund's approximation
   gives the average run length; a verifier that tolerates one false alarm in Y years sets the threshold from it.
   Per-block residuals are taken as independent; drift and model mismatch do not average out, so the systematic floor
   the trial measures (assumption A2) bounds what any sequential test can see.
"""
from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np

SIEGMUND_SHIFT = 1.166          # b = h + 2 x 0.583 for a Gaussian CUSUM (Siegmund 1985)
YEAR_S = 365.25 * 86400.0


# ---- 1. per period ---------------------------------------------------------------------------------------------
def per_period_threshold(gain: float, penalty: float) -> float:
    """Smallest per-period detection probability at which a covert programme does not pay: G / (G + C)."""
    return float(gain) / (float(gain) + float(penalty))


def per_period_value(p: float, gain: float, penalty: float, discount: float = 0.99) -> float:
    """Value of starting the programme: ((1 - p) G - p C) / (1 - d (1 - p))."""
    q = 1.0 - float(p)
    return (q * gain - float(p) * penalty) / (1.0 - discount * q)


# ---- 2. winner-take-all ----------------------------------------------------------------------------------------
def race_value(p: float, periods: int, prize: float, penalty: float, discount: float = 1.0) -> float:
    """Value of a programme that needs `periods` undetected periods to win `prize`; detection in any period costs
    `penalty` and ends it: d^T (1-p)^T W - C sum_{k=1..T} d^(k-1) (1-p)^(k-1) p."""
    q, d, T = 1.0 - float(p), float(discount), int(periods)
    caught = (1.0 - q ** T) if d == 1.0 else float(p) * (1.0 - (d * q) ** T) / (1.0 - d * q)
    return (d * q) ** T * prize - penalty * caught


def required_cumulative_detection(prize: float, penalty: float) -> float:
    """W / (W + C): how likely verification must be to catch the programme before it finishes (no discounting)."""
    return float(prize) / (float(prize) + float(penalty))


def race_threshold(periods: int, prize: float, penalty: float, discount: float = 1.0) -> float:
    """Smallest per-period detection probability at which the race does not pay.
    Without discounting: 1 - (C / (W + C))^(1/T); with discounting, by bisection (race_value falls as p rises)."""
    if discount == 1.0:
        return 1.0 - (penalty / (prize + penalty)) ** (1.0 / int(periods))
    lo, hi = 0.0, 1.0
    if race_value(lo, periods, prize, penalty, discount) <= 0:
        return 0.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if race_value(mid, periods, prize, penalty, discount) > 0:
            lo = mid
        else:
            hi = mid
    return hi


def simulate_race(p: float, periods: int, prize: float, penalty: float, n: int = 200_000, seed: int = 0) -> float:
    """Mean payoff of the race over n simulated programmes (no discounting)."""
    rng = np.random.default_rng(seed)
    first = rng.geometric(p, size=n) if p > 0 else np.full(n, np.iinfo(np.int64).max)   # period of first detection
    return float(np.mean(np.where(first > periods, prize, -penalty)))


# ---- 3. sequential detection -----------------------------------------------------------------------------------
def cusum_arl(mu: float, k: float, h: float) -> float:
    """Siegmund's approximation to the average run length of C_t = max(0, C_{t-1} + z_t - k), alarm when C_t > h,
    with z_t ~ N(mu, 1): D = mu - k, b = h + 1.166, ARL = (exp(-2Db) + 2Db - 1) / (2 D^2), or b^2 when D = 0."""
    D, b = float(mu) - float(k), float(h) + SIEGMUND_SHIFT
    if abs(D) < 1e-12:
        return b * b
    return (math.exp(-2.0 * D * b) + 2.0 * D * b - 1.0) / (2.0 * D * D)


def cusum_h_for_arl0(k: float, arl0: float) -> float:
    """The threshold h that gives an in-control average run length of arl0 (mu = 0)."""
    lo, hi = 0.0, 1.0
    while cusum_arl(0.0, k, hi) < arl0:
        hi *= 2.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if cusum_arl(0.0, k, mid) < arl0:
            lo = mid
        else:
            hi = mid
    return hi


def detection_delay_blocks(delta: float, arl0: float) -> tuple:
    """(h, expected blocks to alarm) for a CUSUM tuned to a shift of delta standard deviations (k = delta / 2),
    with one false alarm per arl0 blocks on average."""
    k = 0.5 * float(delta)
    h = cusum_h_for_arl0(k, arl0)
    return h, cusum_arl(delta, k, h)


def simulate_cusum(mu: float, k: float, h: float, runs: int = 4000, max_t: int = 200_000, seed: int = 0) -> float:
    """Mean run length of the CUSUM over simulated N(mu, 1) streams (runs still going at max_t count as max_t)."""
    rng = np.random.default_rng(seed)
    c = np.zeros(runs)
    t_alarm = np.full(runs, float(max_t))
    alive = np.ones(runs, bool)
    t, chunk = 0, 256
    while alive.any() and t < max_t:
        z = rng.standard_normal((chunk, int(alive.sum()))) + mu
        idx = np.flatnonzero(alive)
        cc = c[idx]
        done = np.zeros(idx.size, bool)
        for j in range(chunk):
            cc = np.maximum(0.0, cc + z[j] - k)
            hit = (cc > h) & ~done
            t_alarm[idx[hit]] = t + j + 1
            done |= hit
        c[idx] = cc
        alive[idx[done]] = False
        t += chunk
    return float(t_alarm.mean())


def sigma_from_min_detectable(md_fraction: float, alpha: float = 0.01, beta: float = 0.05) -> float:
    """Per-block residual SD (as a share of block capacity) implied by a minimum detectable fraction at (alpha, beta),
    for Gaussian residuals: md = (z_(1-alpha) + z_(1-beta)) x sigma."""
    z = NormalDist().inv_cdf
    return float(md_fraction) / (z(1.0 - alpha) + z(1.0 - beta))


def race_against_detection(fraction: float, sigma_fraction: float, block_s: float, threshold_flop: float,
                           fleet_gpus: float, p_max_w: float, e_floor_j_per_flop: float,
                           false_alarm_every_years: float = 10.0) -> dict:
    """A covert programme runs hidden load at `fraction` of capacity on every GPU of a fleet. Which comes first: a
    CUSUM tuned to that load (one false alarm per `false_alarm_every_years`), or the hidden work reaching
    `threshold_flop`? The adversary does not announce its fraction, so a verifier needs a bank of CUSUMs; tuning to
    the true fraction is the best case for the verifier."""
    delta = float(fraction) / float(sigma_fraction)
    arl0 = false_alarm_every_years * YEAR_S / float(block_s)
    h, arl1 = detection_delay_blocks(delta, arl0)
    flop_per_block = float(fraction) * fleet_gpus * p_max_w * block_s / e_floor_j_per_flop
    to_threshold = float(threshold_flop) / flop_per_block
    return {"fraction": float(fraction), "delta_sd": delta, "arl0_blocks": arl0, "cusum_h": h,
            "expected_detection_blocks": arl1, "expected_detection_days": arl1 * block_s / 86400.0,
            "blocks_to_threshold": to_threshold, "days_to_threshold": to_threshold * block_s / 86400.0,
            "hidden_flop_before_detection": arl1 * flop_per_block, "detected_first": bool(arl1 < to_threshold)}
