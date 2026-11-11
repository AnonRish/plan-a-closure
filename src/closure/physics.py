"""What the GPU did during a finished trial, read off raw.npz: a diagnostic, never a criterion.

The analysis asks one question of a block (is there more energy or busy time than the verified work explains?). This
module asks the plain questions underneath it, per requested load level: how much work a second, how many watts, how
busy; and what a hidden load of each label did to those three. It is how runs 4 and 5 were understood
(docs/DEVIATIONS.md sections 4 and 5): power that flattens under the limit, and hidden work that displaces verified
work on a full GPU instead of adding energy.

Since 0.8.0 raw.npz records the load level each window asked for. For earlier hardware runs the levels are regenerated
from the trial's seed, which fixes them (hw/source.py draws them from one generator in time order), and the result is
checked against the work actually done before it is used.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .sim import LEVELS

MIN_WINDOWS = 20      # a cell of the hidden-load table is reported once it has this many windows


def _regenerated_levels(seed: int, n: int) -> np.ndarray:
    rng, lev, level, hold = np.random.default_rng(seed), np.empty(n), 0.5, 0
    for i in range(n):
        if hold <= 0:
            level, hold = float(rng.choice(LEVELS)), int(rng.integers(30, 181))
        hold -= 1
        lev[i] = level
    return lev


def windows(run) -> tuple:
    """(cfg, W, note): every window of the run in time order. W holds, per window: src (warm, ref or aud), blk, t,
    dur, units, E, B, hid (the hidden energy label), lev (requested load level), hs (counted hidden seconds, or NaN),
    kind and frac (the hidden load scheduled for its block)."""
    run = Path(run)
    cfg = json.loads((run / "prereg.json").read_text())["cfg"]
    sched = json.loads((run / "schedule_reveal.json").read_text())["schedule"]
    z = np.load(run / "raw.npz")
    L, parts = int(cfg["L"]), []
    for name in ("warm", "ref", "aud"):
        if f"{name}_E" not in z.files:
            continue
        n = len(z[f"{name}_E"])
        nan = np.full(n, np.nan)
        parts.append({"src": np.full(n, name), "blk": np.arange(n) // L, "t": z[f"{name}_t0"],
                      "dur": z[f"{name}_X"][:, 0], "units": z[f"{name}_X"][:, 1], "E": z[f"{name}_E"],
                      "B": z[f"{name}_B"], "hid": z[f"{name}_hid"],
                      "lev": z[f"{name}_lev"] if f"{name}_lev" in z.files else nan,
                      "hs": z[f"{name}_hs"] if f"{name}_hs" in z.files else nan})
    W = {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}
    order = np.argsort(W["t"], kind="stable")
    W = {k: v[order] for k, v in W.items()}
    note = "load levels as recorded"
    if np.isnan(W["lev"]).any():
        if not str(cfg.get("status", "")).startswith("HARDWARE"):
            raise ValueError("this run did not record its load levels, and only a hardware run's can be regenerated")
        W["lev"] = _regenerated_levels(int(cfg["seed"]), len(order))
        idle = W["lev"] == 0
        means = [float(W["units"][W["lev"] == lv].mean()) for lv in LEVELS if (W["lev"] == lv).any()]
        slack = 0.05 * max(means)                       # a full GPU does the same work at 90% and at 100%
        if (idle.any() and float(np.mean(W["units"][idle] > 0)) > 0.02) or any(b < a - slack for a, b in zip(means, means[1:])):
            raise ValueError("the load levels regenerated from the seed do not match the work done")
        note = "load levels regenerated from the trial's seed (recorded since 0.8.0) and checked against the work done"
    kind, frac = np.array(["none"] * len(order), dtype=object), np.zeros(len(order))
    for i in np.where(W["src"] == "aud")[0]:
        s = sched[int(W["blk"][i])]
        if s is not None:
            kind[i], frac[i] = s["kind"], float(s["frac"])
    W["kind"], W["frac"] = kind, frac
    return cfg, W, note


def report(run) -> dict:
    cfg, W, note = windows(run)
    cap_w = float(cfg["n_gpu"]) * float(cfg["p_max_w"])
    per_s = lambda v, m: float(v[m].sum() / W["dur"][m].sum())      # noqa: E731
    clean = W["hid"] == 0
    levels, base = [], {}
    for lv in LEVELS:
        m = clean & (W["lev"] == lv)
        if not m.any():
            continue
        u, w, b = per_s(W["units"], m), per_s(W["E"], m), per_s(W["B"], m)
        base[lv] = (u, w, b)
        levels.append({"level": lv, "windows": int(m.sum()), "units_per_s": u, "watts": w, "busy_share": b,
                       "busy_ms_per_unit": (1e3 * b / u if u >= 0.5 else None),
                       "joules_per_unit_above_idle": None})
    if levels and levels[0]["level"] == 0:
        for row in levels[1:]:
            if row["units_per_s"] >= 0.5:
                row["joules_per_unit_above_idle"] = (row["watts"] - levels[0]["watts"]) / row["units_per_s"]
    # a hidden load that is on for the whole window (constant and dilute; duty and idle_gap switch within a block)
    steady = (W["hid"] > 0) & np.isin(W["kind"], ["constant", "dilute"])
    effect = []
    for fr in sorted(set(W["frac"]) - {0.0}):
        for lv in LEVELS:
            m = steady & (W["lev"] == lv) & np.isclose(W["frac"], fr)
            if m.sum() < MIN_WINDOWS or lv not in base:
                continue
            u, w, b = per_s(W["units"], m), per_s(W["E"], m), per_s(W["B"], m)
            row = {"label_fraction": fr, "label_watts": fr * cap_w, "level": lv, "windows": int(m.sum()),
                   "units_per_s_change": u - base[lv][0], "watts_added": w - base[lv][1],
                   "busy_share_added": b - base[lv][2]}
            if not np.isnan(W["hs"][m]).any():
                row["hidden_busy_share_counted"] = per_s(W["hs"], m)
            effect.append(row)
    return {"status": cfg.get("status"), "levels_source": note, "capacity_w": cap_w,
            "windows": {k: int((W["src"] == k).sum()) for k in ("warm", "ref", "aud")},
            "by_level": levels, "hidden_load_effect": effect,
            "hidden_load_on_an_idle_gpu": [r for r in effect if r["level"] == 0]}


def summary_lines(rep: dict) -> list:
    """Markdown for SUMMARY.md: the level table, and what each hidden label drew on an idle GPU against its label."""
    L = ["| requested level | windows | units of work a second | watts | busy share | busy ms per unit |",
         "| --- | --- | --- | --- | --- | --- |"]
    for r in rep["by_level"]:
        ms = "" if r["busy_ms_per_unit"] is None else f"{r['busy_ms_per_unit']:.2f}"
        L.append(f"| {r['level']:g} | {r['windows']} | {r['units_per_s']:.1f} | {r['watts']:.1f} | "
                 f"{r['busy_share']:.3f} | {ms} |")
    L.append("")
    solo = rep["hidden_load_on_an_idle_gpu"]
    if solo:
        L.append("- hidden load on an otherwise idle GPU, watts added against the label: "
                 + "; ".join(f"{r['label_fraction']:.0%} label ({r['label_watts']:.1f} W): {r['watts_added']:+.1f} W"
                             for r in solo))
    full = [r for r in rep["hidden_load_effect"] if r["level"] == max(x["level"] for x in rep["hidden_load_effect"])]
    if full:
        L.append(f"- the same loads at requested level {full[0]['level']:g}, watts added and verified work displaced: "
                 + "; ".join(f"{r['label_fraction']:.0%} label: {r['watts_added']:+.1f} W, "
                             f"{r['units_per_s_change']:+.1f} units a second" for r in full))
    L.append(f"- {rep['levels_source']}")
    return L
