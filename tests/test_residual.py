import numpy as np
import pytest

from closure import residual as R
from closure.energy import apply_slack
from closure.sim import HiddenSpec, SimConfig, SimSource
from closure.trial import TrialConfig, collect, fit_channels

CFG = TrialConfig(L=300, n_ref_blocks=600, n_audit_blocks=0)


def _blocks(src, n, spec=None):
    parts = [src.run_block(CFG.L, spec) for _ in range(n)]
    return {k: np.concatenate([p[k] for p in parts]) for k in ("X", "E", "busy", "hidden_j")}


def test_nnls_recovers_nonnegative_coefficients():
    rng = np.random.default_rng(0)
    X = rng.uniform(0, 1, (5000, 3)) * np.array([1, 100, 1e4])
    y = X @ np.array([5.0, 0.0, 2e-3]) + rng.normal(0, 0.1, 5000)
    th = R.nnls(X, y)
    assert np.all(th >= 0) and np.allclose(th, [5.0, 0.0, 2e-3], atol=[0.05, 0.01, 2e-5])
    y2 = X @ np.array([5.0, -3.0, 2e-3])          # negative truth is clipped, never negative
    assert np.all(R.nnls(X, y2) >= 0)


def test_null_false_positive_rate_is_not_above_nominal():
    rates = []
    for seed in range(4):
        src = SimSource(SimConfig(), seed=500 + seed)
        ref = collect(src, CFG, CFG.n_ref_blocks)
        cal, _ = fit_channels(ref, CFG)
        aud = _blocks(src, 1500)
        rates.append(R.audit(cal, aud["X"], aud["E"], alpha=0.01).flagged.mean())
    assert np.mean(rates) <= 0.015 and max(rates) <= 0.04


def test_detects_constant_hidden_load_and_bound_covers_truth():
    src = SimSource(SimConfig(), seed=11)
    ref = collect(src, CFG, CFG.n_ref_blocks)
    cal, _ = fit_channels(ref, CFG)
    aud = _blocks(src, 400, HiddenSpec("constant", 0.05))
    r = R.audit(cal, aud["X"], aud["E"], alpha=0.001)
    hid = aud["hidden_j"].reshape(-1, CFG.L).sum(1)
    assert r.flagged.mean() >= 0.99
    assert (r.hidden_ub >= hid).mean() >= 0.98
    assert np.median(r.hidden_ub / hid) < 1.6        # the bound is reasonably tight


def test_tiny_hidden_load_is_not_detected_so_no_free_claims():
    src = SimSource(SimConfig(), seed=12)
    ref = collect(src, CFG, CFG.n_ref_blocks)
    cal, _ = fit_channels(ref, CFG)
    aud = _blocks(src, 300, HiddenSpec("constant", 0.0005))
    assert R.audit(cal, aud["X"], aud["E"], alpha=0.001).flagged.mean() < 0.5


def test_efficiency_slack_evades_energy_and_slack_margin_restores_coverage():
    """Honest negative result: an energy-neutral attacker is invisible to the residual test.
    The bound only holds once measured slack is added (apply_slack)."""
    src = SimSource(SimConfig(), seed=13)
    ref = collect(src, CFG, CFG.n_ref_blocks)
    cal, _ = fit_channels(ref, CFG)
    aud = _blocks(src, 300, HiddenSpec("slack", 0.10))
    r = R.audit(cal, aud["X"], aud["E"], alpha=0.001)
    hid = aud["hidden_j"].reshape(-1, CFG.L).sum(1)
    assert r.flagged.mean() < 0.05
    assert (r.hidden_ub >= hid).mean() < 0.2
    padded = np.array([apply_slack(h, p, 0.10) for h, p in zip(r.hidden_ub, r.pred)])
    assert (padded >= hid).mean() >= 0.98


def test_min_detectable_and_power_curve_are_consistent():
    src = SimSource(SimConfig(), seed=14)
    ref = collect(src, CFG, CFG.n_ref_blocks)
    cal, _ = fit_channels(ref, CFG)
    for reg in range(cal.n_regimes):
        h = R.min_detectable(cal, reg, alpha=0.001, beta=0.05)
        assert R.detection_power(cal, reg, [h * 1.02], alpha=0.001)[0] >= 0.94
        assert R.detection_power(cal, reg, [0.0], alpha=0.001)[0] < 0.01


def test_underdetermined_calibration_is_rejected():
    src = SimSource(SimConfig(), seed=15)
    ref = collect(src, TrialConfig(L=30), 20)
    with pytest.raises(ValueError):
        R.fit(ref["X"], ref["E"], L=30, n_regimes=3)
