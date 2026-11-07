import numpy as np

from closure import repro as P


def test_variant_kernel_is_batch_dependent_invariant_is_not():
    mv = P.measure_reproducibility(P.ToyLM(kernel="variant"), n_requests=60)
    mi = P.measure_reproducibility(P.ToyLM(kernel="invariant"), n_requests=60)
    assert mv["bitwise_equal_rate"] < 0.5 and mv["max_abs_diff"] > 0
    assert mi["bitwise_equal_rate"] == 1.0 and mi["max_abs_diff"] == 0.0


def test_tolerance_calibration_controls_false_alarms():
    v = P.ToyLM(kernel="variant")
    tol = P.conformal_tolerance(P.measure_reproducibility(v, n_requests=300, seed=0)["diffs"], alpha=0.01)
    fresh = P.measure_reproducibility(v, n_requests=300, seed=99)["diffs"]
    assert (fresh > tol).mean() <= 0.03
    assert 0 < tol < 1e-4                                                      # honest spread is tiny
    assert P.detection_rate(v, v.perturbed("lora", 0.0), tol) <= 0.03          # identical model, other batch: no alarm


def test_substitution_detection_curve_is_monotone():
    ref = P.ToyLM(kernel="variant")
    tol = P.conformal_tolerance(P.measure_reproducibility(ref, n_requests=300, seed=0)["diffs"], alpha=0.01)
    curve = P.detection_curve(ref, "lora", [0.0, 1e-6, 1e-4, 1e-2, 1e-1], tol)
    rates = [r for _, r in curve]
    assert all(b >= a - 0.02 for a, b in zip(rates, rates[1:]))
    assert rates[0] <= 0.03 and rates[-1] >= 0.99
    q = P.detection_curve(ref, "quant", [1e-4, 1e-1], tol)
    assert q[-1][1] >= 0.99
