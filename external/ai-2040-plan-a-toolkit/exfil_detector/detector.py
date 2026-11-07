"""
detector.py

Two layers:

1. A per-chunk logistic regression on (empirical_entropy, base64_fraction)
   -- same interpretable-by-construction choice as the workload discriminator.

2. A CUSUM (cumulative sum) sequential detector on top of the classifier's
   per-chunk log-odds. CUSUM (Page, 1954) is the standard tool for exactly
   this shape of problem -- detecting a shift in a running stream, not just
   classifying one sample -- and it's what lets the detector accumulate
   weak evidence across many outputs instead of needing any single output
   to be a smoking gun. S_t = max(0, S_{t-1} + llr_t - k); flag when S_t
   crosses a threshold h. k is calibrated on clean data so the statistic
   drifts down under normal conditions and only grows when payload evidence
   actually appears; h is calibrated for a target false-positive rate.
"""

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score

from .generators import generate_session
from .features import feature_vector, FEATURE_NAMES

EPS = 1e-9


def build_chunk_dataset(rng, n_per_class, payload_kind="raw", chunk_length=180):
    from .generators import generate_clean_chunk, generate_raw_payload_chunk, generate_disguised_payload_chunk
    gen_payload = generate_raw_payload_chunk if payload_kind == "raw" else generate_disguised_payload_chunk
    X, y = [], []
    for _ in range(n_per_class):
        X.append(feature_vector(generate_clean_chunk(rng, chunk_length))); y.append(0)
        X.append(feature_vector(gen_payload(rng, chunk_length))); y.append(1)
    return np.array(X), np.array(y)


def train_classifier(seed=0, n_per_class=400, chunk_length=180):
    rng = np.random.default_rng(seed)
    X, y = build_chunk_dataset(rng, n_per_class, payload_kind="raw", chunk_length=chunk_length)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=seed, stratify=y)
    clf = LogisticRegression()
    clf.fit(X_train, y_train)
    y_prob = clf.predict_proba(X_test)[:, 1]
    metrics = {
        "accuracy": float(accuracy_score(y_test, clf.predict(X_test))),
        "roc_auc": float(roc_auc_score(y_test, y_prob)),
        "coefficients": dict(zip(FEATURE_NAMES, clf.coef_[0].tolist())),
    }
    return clf, metrics


def chunk_log_odds(clf, chunk: str) -> float:
    p = clf.predict_proba([feature_vector(chunk)])[0, 1]
    p = min(max(p, EPS), 1 - EPS)
    return float(np.log(p / (1 - p)))


def calibrate_k(clf, rng, n_sessions=200, session_len=60, chunk_length=180):
    """k = mean per-chunk log-odds on pure-clean sessions, so clean evidence
    drifts the CUSUM statistic down on average."""
    llrs = []
    for _ in range(n_sessions):
        chunks, _ = generate_session(rng, session_len, injection_rate=0.0, payload_kind=None, chunk_length=chunk_length)
        llrs.extend(chunk_log_odds(clf, c) for c in chunks)
    return float(np.mean(llrs))


def run_cusum(clf, chunks, k):
    """Returns the list of S_t values (len == len(chunks))."""
    s = 0.0
    trace = []
    for c in chunks:
        s = max(0.0, s + chunk_log_odds(clf, c) - k)
        trace.append(s)
    return trace


def calibrate_threshold(clf, k, rng, target_fpr=0.05, n_sessions=300, session_len=80, chunk_length=180, search_max=200.0, steps=4000):
    """Find the smallest threshold h such that at most target_fpr fraction of
    pure-clean sessions ever cross h within session_len outputs."""
    max_traces = []
    for _ in range(n_sessions):
        chunks, _ = generate_session(rng, session_len, injection_rate=0.0, payload_kind=None, chunk_length=chunk_length)
        trace = run_cusum(clf, chunks, k)
        max_traces.append(max(trace))
    max_traces = np.array(sorted(max_traces))
    idx = int(np.ceil((1 - target_fpr) * len(max_traces))) - 1
    idx = min(max(idx, 0), len(max_traces) - 1)
    return float(max_traces[idx])


def evaluate_detection(clf, k, h, rng, injection_rate, payload_kind, n_sessions=300, session_len=80, chunk_length=180):
    """For sessions with the given injection_rate/payload_kind: fraction
    flagged within session_len outputs, and mean outputs-to-flag among those."""
    flagged, latencies = 0, []
    for _ in range(n_sessions):
        chunks, _ = generate_session(rng, session_len, injection_rate, payload_kind, chunk_length)
        trace = run_cusum(clf, chunks, k)
        cross = next((i + 1 for i, s in enumerate(trace) if s >= h), None)
        if cross is not None:
            flagged += 1
            latencies.append(cross)
    return {
        "detection_rate": flagged / n_sessions,
        "mean_outputs_to_detect": float(np.mean(latencies)) if latencies else None,
        "n_sessions": n_sessions,
    }


def evaluate_false_positive_rate(clf, k, h, rng, n_sessions=300, session_len=80, chunk_length=180):
    return evaluate_detection(clf, k, h, rng, injection_rate=0.0, payload_kind=None,
                               n_sessions=n_sessions, session_len=session_len, chunk_length=chunk_length)["detection_rate"]
