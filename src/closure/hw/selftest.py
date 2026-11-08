"""`closure hw-selftest`: does this GPU's energy track the verified work, and did the load levels change that work?

Five load levels, `windows` one-second windows each; energy per window is fitted to the counted work by non-negative
least squares. Pass: r2 > 0.9 (pre-registered), idle power above zero, and the load levels did different amounts of work
(25% load under 80% of the units of 100% load; amendment v0.3, docs/PREREGISTRATION.md). Without the last check a
saturated load generator (every level running flat out, the first T4 run) can only fail by accident of the fit, and a
fit through two clusters of points could pass while the trial behind it measures nothing.
"""
from __future__ import annotations

import numpy as np

from ..residual import nnls
from ..sim import FEATURES

LEVELS = (0.0, 0.25, 0.5, 0.75, 1.0)
R2_MIN = 0.9
DISTINCT_MAX = 0.8


def _key(level: float) -> str:
    return f"{float(level):g}"


def report(rows, unit: dict = None) -> dict:
    """rows: (level, x, energy_j) per window, x = [duration_s, prefill_units, decode_units, steps]; unit: the load
    generator's describe(), used only to explain a failure."""
    lv = np.array([float(r[0]) for r in rows])
    X = np.array([np.asarray(r[1], float) for r in rows])
    y = np.array([float(r[2]) for r in rows])
    th = nnls(X, y)
    res = y - X @ th
    sst = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - float(np.sum(res ** 2)) / sst if sst > 0 else float("nan")
    idle = lv == 0.0
    idle_w = float(np.mean(y[idle] / X[idle, 0])) if idle.any() else float("nan")
    per = {}
    for level in sorted(set(lv.tolist())):
        m = lv == level
        per[_key(level)] = {"windows": int(m.sum()), "units_per_window": float(X[m, 1].mean()),
                            "power_w": float(np.mean(y[m] / X[m, 0]))}
    lo, hi = per.get(_key(0.25)), per.get(_key(1.0))
    ratio = lo["units_per_window"] / hi["units_per_window"] if (lo and hi and hi["units_per_window"] > 0) else None
    distinct = ratio is not None and ratio < DISTINCT_MAX
    out = {"windows": len(rows), "r2": r2, "residual_sd_j": float(res.std()), "idle_power_w": idle_w,
           "theta": dict(zip(FEATURES, th.tolist())), "per_level": per, "work_ratio_25_to_100": ratio,
           "levels_distinct": bool(distinct), "pass": bool(r2 > R2_MIN and idle_w > 0 and distinct)}
    if not out["pass"]:
        out["diagnosis"] = diagnose(out, unit)
    return out


def diagnose(out: dict, unit: dict = None) -> str:
    """One plain sentence or two on why the self-test failed, from its own numbers."""
    per = out.get("per_level", {})
    lo, hi = per.get(_key(0.25)), per.get(_key(1.0))
    if not hi or hi["units_per_window"] <= 0:
        return ("no verified work was counted at 100% load: the load generator did not run (look for a worker error "
                "in this log)")
    if not out.get("levels_distinct"):
        s = (f"the load levels did not change the work done: 25% load ran {lo['units_per_window']:.1f} units per window "
             f"and 100% load {hi['units_per_window']:.1f}, at {lo['power_w']:.0f} W and {hi['power_w']:.0f} W. ")
        if unit and unit.get("unit_s") is not None and unit.get("slot_s"):
            s += (f"One unit of work takes {1e3 * unit['unit_s']:.0f} ms against a {1e3 * unit['slot_s']:.0f} ms slot, "
                  "so every level above zero runs flat out. ")
        else:
            s += "A unit of work that takes longer than a slot makes every level above zero run flat out. "
        return s + "Energy cannot be checked against work that does not vary: let the unit size itself (the default) " \
                   "or pass a smaller --dim."
    if not out.get("idle_power_w", 0) > 0:
        return "idle power is not above zero: the energy counter is not advancing"
    return (f"energy did not track the counted work (r2 {out['r2']:.3f}, needs > {R2_MIN}) although the load levels "
            "differed: look in per_level for a level whose power does not rise with its units (power capping, clock "
            "changes, another process on the GPU, a noisy meter)")
