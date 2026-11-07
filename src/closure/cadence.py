"""Training-cadence detector: telemetry-based workload classification as defence in depth (hardwired pause, section 3.3.3).

Synchronous training repeats the same iteration (forward, backward, optimizer step, all-reduce) at a steady period, which
shows as a sharp line in the power spectrum; inference serving is driven by request arrivals and shows none. Kimpson,
Baker and Graham ("Detecting AI Training in Datacentre Power", arXiv 2610.30182) track that cadence in facility power and
need a meter at 2 Hz or faster. This detector is deliberately simple and auditable: the largest periodogram peak in a band
of plausible iteration periods, divided by the band's median, with the threshold set by a conformal quantile of the same
statistic on null traces (declared inference), so its false-alarm rate comes from calibration, not from an assumption.

Defence in depth, not a bound. Work whose iteration length varies a lot (the strongest evasion Kimpson et al. found, at a
compute cost) smears the line, and a white-box adversary can shape telemetry against any fixed classifier (Rahman and
Tajdari, arXiv 2606.19262). Closure's energy accounting does not depend on this detector for that reason.
The synthetic traces here are for tests and rehearsal only; they say nothing about any real cluster.
"""
from __future__ import annotations

import numpy as np

from .conformal import upper_conformal_quantile

MIN_RATE_HZ = 2.0


def _uniform(t, p):
    t, p = np.asarray(t, float), np.asarray(p, float)
    o = np.argsort(t)
    t, p = t[o], p[o]
    dt = float(np.median(np.diff(t)))
    grid = np.arange(t[0], t[-1], dt)
    return np.interp(grid, t, p), dt


def statistic(t, p, min_period_s: float = 1.0, max_period_s: float = 120.0) -> dict:
    """Peak-to-median periodogram ratio over periods in [min_period_s, max_period_s] (at least three cycles must fit)."""
    if len(t) < 16:
        return {"stat": None, "period_s": None, "note": "too few samples"}
    x, dt = _uniform(t, p)
    fs = 1.0 / dt
    if fs < MIN_RATE_HZ * 0.999:
        return {"stat": None, "period_s": None,
                "note": f"sampled at {fs:.3g} Hz: the cadence detector needs {MIN_RATE_HZ:g} Hz or faster"}
    span = len(x) * dt
    hi_period = min(max_period_s, span / 3.0)
    n = len(x)
    k = np.arange(n)
    x = x - np.polyval(np.polyfit(k, x, 1), k)               # remove level and slow drift
    spec = np.abs(np.fft.rfft(x * np.hanning(n))) ** 2
    f = np.fft.rfftfreq(n, dt)
    band = (f >= 1.0 / hi_period) & (f <= min(1.0 / min_period_s, fs / 2.0))
    if band.sum() < 8:
        return {"stat": None, "period_s": None, "note": "trace too short for the period band"}
    pb, fb = spec[band], f[band]
    med = float(np.median(pb))
    i = int(np.argmax(pb))
    return {"stat": float(pb[i] / med) if med > 0 else float("inf"), "period_s": float(1.0 / fb[i]), "note": ""}


def calibrate(null_traces, alpha: float = 0.05, **kw) -> dict:
    """Threshold with P(null statistic > threshold) <= alpha for a fresh exchangeable null trace."""
    stats = [statistic(t, p, **kw)["stat"] for t, p in null_traces]
    stats = [s for s in stats if s is not None]
    thr = upper_conformal_quantile(stats, alpha)
    return {"threshold": thr, "alpha": alpha, "n_null": len(stats),
            "note": "" if np.isfinite(thr) else f"need at least {int(np.ceil(1 / alpha)) - 1} usable null traces for alpha={alpha}"}


def detect(t, p, threshold: float, **kw) -> dict:
    s = statistic(t, p, **kw)
    return {**s, "threshold": threshold, "flagged": bool(s["stat"] is not None and s["stat"] > threshold)}


def synthetic_training(duration_s: float = 600.0, fs: float = 4.0, period_s: float = 8.0, jitter: float = 0.02,
                       p_idle: float = 120.0, p_busy: float = 650.0, duty: float = 0.8, noise_w: float = 20.0, seed: int = 0):
    """Synchronous training on one node: each iteration is a busy compute phase, then a lower communication phase.
    `jitter` is the relative spread of iteration length (large values model the 'vary the work per iteration' evasion)."""
    rng = np.random.default_rng(seed)
    t = np.arange(0.0, duration_s, 1.0 / fs)
    p = np.full_like(t, p_idle + 0.3 * (p_busy - p_idle))
    tt = float(rng.uniform(0, period_s))
    while tt < duration_s:
        length = max(0.2 * period_s, period_s * (1.0 + jitter * rng.standard_normal()))
        p[(t >= tt) & (t < tt + duty * length)] = p_busy
        tt += length
    return t, p + noise_w * rng.standard_normal(len(t))


def synthetic_inference(duration_s: float = 600.0, fs: float = 4.0, rate_hz: float = 3.0, mean_service_s: float = 0.6,
                        p_idle: float = 120.0, p_per_request: float = 90.0, p_max: float = 700.0, noise_w: float = 20.0,
                        seed: int = 0):
    """Inference serving: Poisson arrivals, exponential service times, power rising with requests in flight."""
    rng = np.random.default_rng(seed)
    t = np.arange(0.0, duration_s, 1.0 / fs)
    load = np.zeros_like(t)
    n = rng.poisson(rate_hz * duration_s)
    for a, s in zip(rng.uniform(0, duration_s, n), rng.exponential(mean_service_s, n)):
        load[(t >= a) & (t < a + s)] += 1.0
    return t, np.minimum(p_max, p_idle + p_per_request * load) + noise_w * rng.standard_normal(len(t))
