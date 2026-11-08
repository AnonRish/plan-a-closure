"""closure drift: calibration against audit blocks without hidden load (assumption A2), on synthetic trial folders and
on run 3's real data."""
import json
import tarfile
from pathlib import Path

import numpy as np
import pytest

from closure.drift import report, summary_lines

RUN3 = Path(__file__).resolve().parents[1] / "results" / "shakedown-2026-11-08-colab-t4-run3" / "tier0_bundle.tar.gz"


def _trial(tmp_path, audit_idle_w=30.0, audit_j_per_unit=0.4, L=30, blocks=60, seed=0):
    rng = np.random.default_rng(seed)

    def half(idle, jpu, hidden):
        n = L * blocks
        u = rng.choice([0, 30, 70, 100], size=n).astype(float)
        X = np.column_stack([np.ones(n), u, u, u])
        E = idle + jpu * u + rng.normal(0, 0.8, n)
        H = np.zeros(n)
        if hidden:                                          # every other block carries hidden load
            for b in range(0, blocks, 2):
                H[b * L:(b + 1) * L] = 5.0
                E[b * L:(b + 1) * L] += 5.0
        return X, E, H

    Xr, Er, Hr = half(30.0, 0.4, False)
    Xa, Ea, Ha = half(audit_idle_w, audit_j_per_unit, True)
    np.savez(tmp_path / "raw.npz", ref_X=Xr, ref_E=Er, ref_B=Xr[:, 1], ref_t0=np.arange(len(Er)), ref_hid=Hr,
             aud_X=Xa, aud_E=Ea, aud_B=Xa[:, 1], aud_t0=np.arange(len(Ea)), aud_hid=Ha)
    (tmp_path / "prereg.json").write_text(json.dumps({"cfg": {"L": L, "dt": 1.0}}))
    return tmp_path


def test_a_stable_gpu_shows_no_drift(tmp_path):
    r = report(_trial(tmp_path))
    assert r["drift_suspected"] is False and abs(r["mean_shift_in_calibration_sds"]) < 0.5
    assert r["audit_without_hidden_energy"]["blocks"] == 30 and abs(r["calibration"]["idle_power_w"] - 30.0) < 0.3


def test_falling_idle_power_is_flagged(tmp_path):
    r = report(_trial(tmp_path, audit_idle_w=27.5))                 # run 3: about 2.4 W lower during the audit
    assert r["drift_suspected"] is True and r["mean_shift_in_calibration_sds"] < -0.5
    assert any("idle power 30.0 W during calibration, 27.5 W during audit" in x for x in summary_lines(r))


def test_run_3_is_flagged(tmp_path):
    with tarfile.open(RUN3) as tf:
        for name in ("prereg.json", "raw.npz"):
            (tmp_path / name).write_bytes(tf.extractfile(f"tier0-20261108-155308/T1-smoke/{name}").read())
    r = report(tmp_path)
    assert r["drift_suspected"] is True
    assert r["mean_shift_in_calibration_sds"] == pytest.approx(-1.30, abs=0.01)
    assert r["spread_ratio"] == pytest.approx(3.08, abs=0.01)
