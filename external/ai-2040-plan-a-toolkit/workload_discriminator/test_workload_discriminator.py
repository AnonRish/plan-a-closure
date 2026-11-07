import numpy as np
import pytest

from .traffic_gen import generate_training_session, generate_inference_session, generate_adversarial_regular_inference_session
from .features import extract_features, feature_vector, FEATURE_NAMES
from .classifier import train_and_evaluate, evaluate_adversarial, build_dataset, LABEL_TRAINING, LABEL_INFERENCE


def test_training_session_has_low_timing_variance_on_average():
    rng = np.random.default_rng(42)
    cvs = [extract_features(generate_training_session(rng))["inter_event_cv"] for _ in range(50)]
    assert np.mean(cvs) < 0.2, "training's step cadence should be much more regular than inference's arrivals"


def test_inference_session_has_higher_timing_variance_on_average():
    rng = np.random.default_rng(42)
    train_cvs = [extract_features(generate_training_session(rng))["inter_event_cv"] for _ in range(50)]
    infer_cvs = [extract_features(generate_inference_session(rng))["inter_event_cv"] for _ in range(50)]
    assert np.mean(infer_cvs) > np.mean(train_cvs)


def test_training_session_is_near_symmetric():
    rng = np.random.default_rng(1)
    ratios = [extract_features(generate_training_session(rng))["log_symmetry_ratio"] for _ in range(50)]
    assert np.mean(np.abs(ratios)) < 0.3, "AllReduce-style sync should be close to symmetric (log ratio near 0)"


def test_inference_session_is_asymmetric():
    rng = np.random.default_rng(1)
    ratios = [extract_features(generate_inference_session(rng))["log_symmetry_ratio"] for _ in range(50)]
    assert np.mean(ratios) < -1.0, "prompt-upload / completion-download should be well below symmetric"


def test_adversarial_session_keeps_inference_asymmetry_despite_regular_timing():
    rng = np.random.default_rng(3)
    adv = [extract_features(generate_adversarial_regular_inference_session(rng)) for _ in range(50)]
    normal_train = [extract_features(generate_training_session(rng)) for _ in range(50)]
    # timing looks training-like...
    assert np.mean([a["inter_event_cv"] for a in adv]) < 0.3
    # ...but byte asymmetry still looks inference-like, not training-like
    assert np.mean([a["log_symmetry_ratio"] for a in adv]) < -1.0
    assert np.mean([a["log_symmetry_ratio"] for a in adv]) < np.mean([t["log_symmetry_ratio"] for t in normal_train])


def test_feature_vector_matches_feature_names_order():
    rng = np.random.default_rng(0)
    s = generate_training_session(rng)
    fv = feature_vector(s)
    fd = extract_features(s)
    assert fv == [fd[name] for name in FEATURE_NAMES]


def test_empty_session_does_not_crash():
    class Empty:
        label = "training"
        timestamps = np.array([])
        bytes_sent = np.array([])
        bytes_received = np.array([])
    f = extract_features(Empty())
    assert f["n_events"] == 0


def test_classifier_achieves_strong_held_out_performance():
    _, metrics = train_and_evaluate(seed=0, n_per_class=150)
    assert metrics["accuracy"] > 0.9
    assert metrics["roc_auc"] > 0.9


def test_classifier_labels_are_well_defined():
    assert LABEL_TRAINING == 1 and LABEL_INFERENCE == 0


def test_dataset_is_balanced():
    rng = np.random.default_rng(5)
    _, y, _ = build_dataset(100, rng)
    assert np.sum(y == LABEL_TRAINING) == 100
    assert np.sum(y == LABEL_INFERENCE) == 100


def test_adversarial_evaluation_degrades_but_beats_random():
    clf, _ = train_and_evaluate(seed=0, n_per_class=150)
    adv = evaluate_adversarial(clf, n=150, seed=2)
    assert adv["accuracy"] < 1.0, "the adversarial case should be harder than the held-out case"
    assert adv["accuracy"] > 0.5, "but the full-feature classifier should still substantially beat a coin flip"


def test_coefficients_show_symmetry_ratio_carries_real_weight():
    _, metrics = train_and_evaluate(seed=0, n_per_class=150)
    # log_symmetry_ratio should be a meaningfully-weighted, positive-signed coefficient
    # (higher/less-negative symmetry ratio -> more training-like, label 1)
    assert metrics["coefficients"]["log_symmetry_ratio"] > 0
    assert abs(metrics["coefficients"]["log_symmetry_ratio"]) > 0.5
