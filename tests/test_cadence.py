"""Training-cadence detector: defence in depth (hardwired pause 3.3.3), calibrated on null traces."""
import json

import numpy as np

from closure import cadence as C
from closure.cli import main

NULL = [C.synthetic_inference(duration_s=300, seed=100 + i) for i in range(40)]


def test_training_is_flagged_and_inference_false_alarms_stay_near_alpha():
    cal = C.calibrate(NULL, alpha=0.05)
    assert np.isfinite(cal["threshold"]) and cal["n_null"] == 40
    hits = [C.detect(*C.synthetic_training(duration_s=300, seed=s), cal["threshold"]) for s in range(20)]
    assert np.mean([h["flagged"] for h in hits]) >= 0.95
    assert all(abs(h["period_s"] - 8.0) < 1.0 or abs(h["period_s"] - 4.0) < 0.5 for h in hits)    # fundamental or 2nd harmonic
    fresh = [C.detect(*C.synthetic_inference(duration_s=300, seed=500 + s), cal["threshold"])["flagged"] for s in range(100)]
    assert np.mean(fresh) <= 0.10                                     # alpha = 0.05 plus binomial noise on 100 traces


def test_varying_the_work_per_iteration_weakens_the_line():
    cal = C.calibrate(NULL, alpha=0.05)

    def rate(jitter):
        return np.mean([C.detect(*C.synthetic_training(duration_s=300, jitter=jitter, seed=s), cal["threshold"])["flagged"]
                        for s in range(30)])
    steady, varied = rate(0.02), rate(0.6)
    assert steady >= 0.95 and varied < steady                         # the evasion Kimpson et al. found, in miniature


def test_the_detector_refuses_traces_sampled_below_two_hertz_and_too_short_calibrations():
    r = C.statistic(*C.synthetic_training(duration_s=300, fs=1.0))
    assert r["stat"] is None and "2 Hz" in r["note"]
    cal = C.calibrate(NULL[:10], alpha=0.05)
    assert not np.isfinite(cal["threshold"]) and "null traces" in cal["note"]


def _csv(path, t, p):
    path.write_text("timestamp_s,power_w\n" + "\n".join(f"{a:.3f},{b:.3f}" for a, b in zip(t, p)))
    return str(path)


def test_cadence_check_cli(tmp_path, capsys):
    nulls = ",".join(_csv(tmp_path / f"n{i}.csv", *C.synthetic_inference(duration_s=300, seed=200 + i)) for i in range(20))
    train = _csv(tmp_path / "train.csv", *C.synthetic_training(duration_s=300, seed=3))
    assert main(["cadence-check", "--csv", train, "--null", nulls]) == 1          # flagged
    out = json.loads(capsys.readouterr().out)
    assert out["flagged"] and out["calibration"]["n_null"] == 20
    infer = _csv(tmp_path / "inf.csv", *C.synthetic_inference(duration_s=300, seed=999))
    assert main(["cadence-check", "--csv", infer]) == 0
    assert "uncalibrated" in json.loads(capsys.readouterr().out)["note"]
