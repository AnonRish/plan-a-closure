"""Why run 3's smoke trial had 3 false alarms in 23 null blocks: the GPU's power behaviour drifted within the hour.

Reads T1-smoke/raw.npz (every one-second window of the trial: verified-work features X, energy E, busy time B, start
time, hidden energy) straight from tier0_bundle.tar.gz (the repository ignores loose .npz files), and
extracted/probe.json, and prints the numbers quoted in docs/DEVIATIONS.md section 3.
Run from the repository root:  python results/shakedown-2026-11-08-colab-t4-run3/drift.py
"""
import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
from closure.residual import nnls  # noqa: E402
from closure.tier0 import _trial_clock_args  # noqa: E402

BUNDLE = HERE / "tier0_bundle.tar.gz"
SHA256 = "58a273addfd4419ea39c1fc99a025ed4c21dd0514323ecd2d2311ed2aff0e042"
if hashlib.sha256(BUNDLE.read_bytes()).hexdigest() != SHA256:
    sys.exit(f"{BUNDLE} is not the bundle the run returned")
with tarfile.open(BUNDLE) as tf:
    z = np.load(io.BytesIO(tf.extractfile("tier0-20261108-155308/T1-smoke/raw.npz").read()))
L = 30                                           # windows per block in the smoke profile
X = np.concatenate([z["ref_X"], z["aud_X"]])
E = np.concatenate([z["ref_E"], z["aud_E"]])
B = np.concatenate([z["ref_B"], z["aud_B"]])
H = np.concatenate([z["ref_hid"], z["aud_hid"]])
t = np.concatenate([z["ref_t0"], z["aud_t0"]])
t = t - t[0]
n_ref = len(z["ref_E"])
units = X[:, 1]
out = {"calibration_minutes": [0.0, float(t[n_ref - 1] / 60)], "audit_minutes": [float(t[n_ref] / 60), float(t[-1] / 60)]}

idle = (units == 0) & (H == 0)
out["idle_power_w_by_20_min"] = {f"{lo}-{lo + 20}": float(E[idle & (t >= 60 * lo) & (t < 60 * (lo + 20))].mean())
                                 for lo in (0, 20, 40)}
mid = (units >= 20) & (units < 80) & (H == 0)
out["mid_load_energy_per_unit_by_half_hour"] = {}
for lo in (0, 30):
    m = mid & (t >= 60 * lo) & (t < 60 * (lo + 30))
    slope, icpt = np.polyfit(units[m], E[m], 1)
    out["mid_load_energy_per_unit_by_half_hour"][f"{lo}-{lo + 30}"] = {"windows": int(m.sum()),
                                                                        "j_per_unit": float(slope),
                                                                        "intercept_j": float(icpt)}
full = (units >= 80) & (H == 0)
out["full_load_by_10_min"] = {}
for lo in range(0, 60, 10):
    m = full & (t >= 60 * lo) & (t < 60 * (lo + 10))
    if m.sum() > 5:
        out["full_load_by_10_min"][f"{lo}-{lo + 10}"] = {
            "windows": int(m.sum()), "units_per_window": float(units[m].mean()), "energy_j": float(E[m].mean()),
            "units_per_busy_second": float((units[m] / np.maximum(B[m], 1e-9)).mean())}

# Fit on the calibration half (as the trial does, here one NNLS over windows), then look at audit blocks with no
# hidden energy: their residuals should look like the calibration's.
th = nnls(X[:n_ref], E[:n_ref])
rb = (E[:n_ref] - X[:n_ref] @ th).reshape(-1, L).sum(1)
ra = (E[n_ref:] - X[n_ref:] @ th).reshape(-1, L).sum(1)
clean = H[n_ref:].reshape(-1, L).sum(1) == 0
half = int(clean.sum()) // 2
out["block_residuals_j"] = {
    "calibration": {"blocks": int(rb.size), "mean": float(rb.mean()), "sd": float(rb.std()),
                    "skew": float(((rb - rb.mean()) ** 3).mean() / rb.std() ** 3)},
    "audit_without_hidden_energy": {"blocks": int(clean.sum()), "mean": float(ra[clean].mean()),
                                    "sd": float(ra[clean].std()), "mean_first_half": float(ra[clean][:half].mean()),
                                    "mean_second_half": float(ra[clean][half:].mean())}}

probe = json.loads((HERE / "extracted" / "probe.json").read_text())
ref = next(v for v in probe["variants"] if v["kind"] == "reference")
out["probe_reference_sm_mhz_by_level"] = {str(lv["level"]): lv["sm_mhz"] for lv in ref["levels"]}
out["probe_locked_clocks_at_top_level"] = {
    v["name"]: {"sm_mhz": v["levels"][-1]["sm_mhz"], "power_w": v["levels"][-1]["power_w_mean"],
                "feasible": v["levels"][-1]["feasible"]}
    for v in probe["variants"] if v["kind"] == "clock_cap"}
out["tier0_would_lock_the_trial_at"] = _trial_clock_args(HERE / "extracted" / "probe.json")
print(json.dumps(out, indent=2))
