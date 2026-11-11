"""Did the energy model drift between calibration and audit? A check on assumption A2, from a trial's own data.

The trial calibrates on reference blocks, then audits. If the GPU's power behaviour changes in between (clocks,
temperature, the VM), audit blocks without hidden load stop looking like calibration blocks, and false alarms follow.
Colab T4 run 3 showed exactly this (docs/DEVIATIONS.md section 3). This report reads a trial folder's raw.npz and
prereg.json and compares the two directly, and reports how far calibration residuals moved from the first third of the
reference blocks to the last. It is a diagnostic: it decides nothing, and the registered analysis does not use it.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .residual import nnls

SHIFT_FLAG, SPREAD_FLAG = 0.5, 1.5   # fixed flags; the report gives the shift's standard error to read them against


def _idle_w(X, E, H):
    m = (X[:, 1] == 0) & (H == 0) & (X[:, 0] > 0)
    return float(np.mean(E[m] / X[m, 0])) if m.sum() >= 5 else None


def _linear(X, E, H):
    """Energy per window = a x seconds + b x units, over loaded windows without hidden energy."""
    m = (X[:, 1] > 0) & (H == 0)
    if m.sum() < 10:
        return None
    (a, b), *_ = np.linalg.lstsq(np.column_stack([X[m, 0], X[m, 1]]), E[m], rcond=None)
    return {"windows": int(m.sum()), "w_per_second": float(a), "j_per_unit": float(b)}


def report(run_dir) -> dict:
    run = Path(run_dir)
    cfg = json.loads((run / "prereg.json").read_text(encoding="utf-8"))["cfg"]
    L = int(cfg["L"])
    z = np.load(run / "raw.npz")
    Xr, Er, Hr = z["ref_X"], z["ref_E"], z["ref_hid"]
    Xa, Ea, Ha = z["aud_X"], z["aud_E"], z["aud_hid"]
    n_a = (len(Ea) // L) * L
    if cfg.get("analysis") == "link":                        # the run's own model: a calibrated curve (link.py)
        from .link import Curve
        curve = Curve.fit(Xr, Er)
        rb = (Er - curve.predict(Xr))[: (len(Er) // L) * L].reshape(-1, L).sum(1)
        ra = (Ea - curve.predict(Xa))[:n_a].reshape(-1, L).sum(1)
    else:
        th = nnls(Xr, Er)                                    # one straight line over the calibration windows
        rb = (Er - Xr @ th)[: (len(Er) // L) * L].reshape(-1, L).sum(1)
        ra = (Ea - Xa @ th)[:n_a].reshape(-1, L).sum(1)
    clean = Ha[:n_a].reshape(-1, L).sum(1) == 0
    sd = float(rb.std()) if rb.size > 1 else float("nan")
    third = rb.size // 3                                      # reference blocks are in time order
    trend = float((rb[-third:].mean() - rb[:third].mean()) / sd) if third >= 5 and sd > 0 else None
    out = {"block_windows": L, "calibration_design": cfg.get("calibration", "sequential"),
           "calibration_trend_sds": trend,
           "calibration": {"blocks": int(rb.size), "idle_power_w": _idle_w(Xr, Er, Hr), "linear": _linear(Xr, Er, Hr),
                           "block_residual_sd_j": sd},
           "audit_without_hidden_energy": {"blocks": int(clean.sum()), "idle_power_w": _idle_w(Xa, Ea, Ha),
                                           "linear": _linear(Xa, Ea, Ha),
                                           "block_residual_mean_j": float(ra[clean].mean()) if clean.any() else None,
                                           "block_residual_sd_j": float(ra[clean].std()) if clean.sum() > 1 else None}}
    if clean.sum() >= 5 and sd > 0:
        a = out["audit_without_hidden_energy"]
        out["mean_shift_in_calibration_sds"] = a["block_residual_mean_j"] / sd
        out["mean_shift_standard_error"] = float(np.sqrt(1.0 / clean.sum() + 1.0 / rb.size))
        out["spread_ratio"] = a["block_residual_sd_j"] / sd
        out["drift_suspected"] = bool(abs(out["mean_shift_in_calibration_sds"]) > SHIFT_FLAG
                                      or out["spread_ratio"] > SPREAD_FLAG)
    else:
        out["mean_shift_in_calibration_sds"] = out["spread_ratio"] = out["drift_suspected"] = None
        out["mean_shift_standard_error"] = None
    return out


def summary_lines(rep: dict) -> list:
    """The lines tier0's SUMMARY.md shows."""
    c, a = rep["calibration"], rep["audit_without_hidden_energy"]
    if rep.get("drift_suspected") is None:
        return [f"- too few audit blocks without hidden energy ({a['blocks']}) to compare with calibration"]
    lines = [f"- audit blocks without hidden energy ({a['blocks']}) against calibration ({c['blocks']}): mean shift "
             f"{rep['mean_shift_in_calibration_sds']:+.2f} calibration SDs (standard error "
             f"{rep.get('mean_shift_standard_error') or float('nan'):.2f}), spread {rep['spread_ratio']:.2f}x; "
             f"drift suspected: {rep['drift_suspected']} (flags at {SHIFT_FLAG} SD and {SPREAD_FLAG}x)"]
    if c["idle_power_w"] is not None and a["idle_power_w"] is not None:
        lines.append(f"- idle power {c['idle_power_w']:.1f} W during calibration, {a['idle_power_w']:.1f} W during audit")
    if c["linear"] and a["linear"]:
        lines.append(f"- energy per unit of work {c['linear']['j_per_unit']:.3f} J during calibration, "
                     f"{a['linear']['j_per_unit']:.3f} J during audit")
    if rep.get("calibration_trend_sds") is not None:
        lines.append(f"- calibration blocks, last third against first third: {rep['calibration_trend_sds']:+.2f} SDs"
                     + ("; reference blocks were interleaved with the audit, so drift reaches both alike"
                        if rep.get("calibration_design") == "interleaved" else ""))
    return lines
