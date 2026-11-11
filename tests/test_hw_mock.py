import numpy as np
import pytest

from closure.hw.source import FakeHardware, HwSource
from closure.sim import HiddenSpec
from closure.trial import TrialConfig, run_trial


def _src(seed=1):
    fh = FakeHardware(seed=seed)
    return fh, HwSource(fh, fh, dt=1.0, n_gpu=8, time_fn=fh.now, sleep_fn=fh.sleep, seed=seed)


def test_hwsource_runs_the_same_pipeline_on_fake_hardware(tmp_path):
    fh, src = _src()
    cfg = TrialConfig(status="HARDWARE-MOCK", L=30, n_ref_blocks=60, n_audit_blocks=60, n_regimes=1, alpha=0.01,
                      classes=("constant", "idle_gap", "duty", "dilute"), intensities=(0.05, 0.2))
    res = run_trial(src, cfg, tmp_path)
    z = np.load(tmp_path / "raw.npz")
    assert np.allclose(z["ref_X"][:, 0], 1.0, atol=1e-6)            # measured window duration
    assert z["ref_E"].min() > 0 and (np.diff(z["ref_t0"]) > 0).all()
    d = res["detection_combined"]["constant"]["0.2"]
    assert d["n"] > 0 and d["rate"] >= 0.8
    assert res["status"] == "HARDWARE-MOCK"


def test_hidden_load_raises_measured_energy_on_fake_hardware():
    fh, src = _src(2)
    src.force_level = 0.3                                             # room to spare: the hidden load simply adds
    base = src.run_block(60, None)["E"].mean()
    fh2, src2 = _src(2)
    src2.force_level = 0.3
    hid = src2.run_block(60, HiddenSpec("constant", 0.2))["E"].mean()
    assert hid - base > 0.15 * 5600                                   # ~20% of the 5.6 kW cap, W per 1 s window


def test_a_full_fake_gpu_gives_way_to_hidden_load_and_reports_the_ground_truth():
    """When verified and hidden work do not fit in the second, the verified work is what gives way: fewer units, the
    same busy time. The block also carries the truth the bounds are checked against (never a regressor)."""
    fh, src = _src(3)
    src.force_level = 1.0
    full = src.run_block(30, None)
    fh2, src2 = _src(3)
    src2.force_level = 1.0
    both = src2.run_block(30, HiddenSpec("constant", 0.2))
    assert both["X"][:, 1].mean() < 0.85 * full["X"][:, 1].mean()                    # verified units displaced
    assert abs(both["busy"].mean() - full["busy"].mean()) < 0.02                      # still as busy as it can be
    assert (both["level"] == 1.0).all() and full["hidden_s"].sum() == 0
    hb = 0.2 * 5600 / 4640
    assert both["hidden_s"].mean() == pytest.approx(FakeHardware.SENSOR_FULL * hb, rel=1e-6)


def test_slack_class_is_refused_on_real_hardware_paths():
    _, src = _src(3)
    with pytest.raises(NotImplementedError):
        src.run_block(5, HiddenSpec("slack", 0.1))
