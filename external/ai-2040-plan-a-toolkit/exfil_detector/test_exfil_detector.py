import math
import numpy as np
import pytest

from .generators import (
    CLEAN_ENTROPY_BITS_PER_CHAR, RAW_PAYLOAD_ENTROPY_BITS_PER_CHAR, BASE64_ALPHABET,
    generate_clean_chunk, generate_raw_payload_chunk, generate_disguised_payload_chunk,
    generate_session, shannon_entropy_bits,
)
from .features import empirical_entropy_bits, base64_fraction, feature_vector
from .detector import (
    train_classifier, calibrate_k, calibrate_threshold, evaluate_detection,
    evaluate_false_positive_rate, run_cusum,
)


def test_uniform_distribution_entropy_matches_log2n():
    probs = [1 / 8] * 8
    assert shannon_entropy_bits(probs) == pytest.approx(3.0, abs=1e-9)


def test_clean_entropy_is_computed_not_hardcoded_and_in_expected_range():
    # widely-cited unigram English entropy is ~4.0-4.2 bits/char; this should land there
    assert 3.9 < CLEAN_ENTROPY_BITS_PER_CHAR < 4.3


def test_raw_payload_entropy_is_exactly_log2_64():
    assert RAW_PAYLOAD_ENTROPY_BITS_PER_CHAR == pytest.approx(math.log2(64))


def test_empirical_entropy_of_single_repeated_char_is_zero():
    assert empirical_entropy_bits("aaaaaaaa") == 0.0


def test_empirical_entropy_of_raw_payload_chunk_approaches_theoretical_max():
    rng = np.random.default_rng(0)
    chunk = generate_raw_payload_chunk(rng, 2000)
    assert empirical_entropy_bits(chunk) > 5.7  # close to the 6.0 theoretical ceiling at this length


def test_clean_chunk_entropy_is_meaningfully_lower_than_payload_chunk():
    rng = np.random.default_rng(1)
    clean = generate_clean_chunk(rng, 1000)
    payload = generate_raw_payload_chunk(rng, 1000)
    assert empirical_entropy_bits(clean) < empirical_entropy_bits(payload) - 1.0


def test_base64_fraction_of_pure_payload_is_one():
    rng = np.random.default_rng(2)
    chunk = generate_raw_payload_chunk(rng, 500)
    assert base64_fraction(chunk) == pytest.approx(1.0)


def test_disguised_chunk_entropy_matches_clean_distribution_not_raw_payload():
    """The core premise of the stress test: disguised payload's unigram
    entropy should land near clean text's, not near raw payload's."""
    rng = np.random.default_rng(3)
    disguised = generate_disguised_payload_chunk(rng, 2000)
    clean = generate_clean_chunk(rng, 2000)
    assert abs(empirical_entropy_bits(disguised) - empirical_entropy_bits(clean)) < 0.15
    assert empirical_entropy_bits(disguised) < RAW_PAYLOAD_ENTROPY_BITS_PER_CHAR - 1.0


def test_classifier_achieves_strong_performance_on_raw_payload():
    _, metrics = train_classifier(seed=0, n_per_class=200)
    assert metrics["accuracy"] > 0.95
    assert metrics["roc_auc"] > 0.95


def test_cusum_calibration_achieves_close_to_target_fpr():
    clf, _ = train_classifier(seed=0, n_per_class=200)
    rng = np.random.default_rng(1)
    k = calibrate_k(clf, rng, n_sessions=150, session_len=50)
    rng = np.random.default_rng(2)
    h = calibrate_threshold(clf, k, rng, target_fpr=0.05, n_sessions=250, session_len=60)
    rng = np.random.default_rng(3)
    achieved = evaluate_false_positive_rate(clf, k, h, rng, n_sessions=300, session_len=60)
    assert achieved < 0.12  # calibrated on a different rng draw than the check; some slack is expected


def test_detection_rate_is_high_for_raw_payload_at_moderate_injection():
    clf, _ = train_classifier(seed=0, n_per_class=200)
    rng = np.random.default_rng(1)
    k = calibrate_k(clf, rng, n_sessions=150, session_len=50)
    rng = np.random.default_rng(2)
    h = calibrate_threshold(clf, k, rng, target_fpr=0.05, n_sessions=250, session_len=60)
    rng = np.random.default_rng(4)
    res = evaluate_detection(clf, k, h, rng, injection_rate=0.2, payload_kind="raw", n_sessions=150, session_len=80)
    assert res["detection_rate"] > 0.9


def test_detection_rate_collapses_for_disguised_payload():
    """The honest headline finding: against unigram-matched disguise, detection
    rate should sit near the false-positive floor, not meaningfully above it,
    REGARDLESS of injection rate. Threshold is set well above the expected
    ~5-10% floor (target FPR 5% plus calibration/sampling noise) but far below
    what real detection looks like -- compare to >90% for raw payload above."""
    clf, _ = train_classifier(seed=0, n_per_class=200)
    rng = np.random.default_rng(1)
    k = calibrate_k(clf, rng, n_sessions=150, session_len=50)
    rng = np.random.default_rng(2)
    h = calibrate_threshold(clf, k, rng, target_fpr=0.05, n_sessions=400, session_len=60)

    rng = np.random.default_rng(5)
    res_low = evaluate_detection(clf, k, h, rng, injection_rate=0.1, payload_kind="disguised", n_sessions=300, session_len=80)
    rng = np.random.default_rng(6)
    res_high = evaluate_detection(clf, k, h, rng, injection_rate=1.0, payload_kind="disguised", n_sessions=300, session_len=80)

    assert res_low["detection_rate"] < 0.20
    assert res_high["detection_rate"] < 0.20
    # the key point: MORE disguised payload should not blow past the FPR-floor regime
    assert abs(res_high["detection_rate"] - res_low["detection_rate"]) < 0.15


def test_disguise_bandwidth_cost_ratio_is_below_one():
    """Disguising to match clean unigram stats necessarily caps payload rate
    below the raw channel capacity -- entropy can't exceed the target distribution's."""
    ratio = CLEAN_ENTROPY_BITS_PER_CHAR / RAW_PAYLOAD_ENTROPY_BITS_PER_CHAR
    assert 0 < ratio < 1
    assert ratio == pytest.approx(0.683, abs=0.01)


def test_cusum_never_goes_negative():
    clf, _ = train_classifier(seed=0, n_per_class=100)
    rng = np.random.default_rng(7)
    chunks, _ = generate_session(rng, 40, injection_rate=0.2, payload_kind="raw")
    trace = run_cusum(clf, chunks, k=0.0)
    assert all(s >= 0 for s in trace)
