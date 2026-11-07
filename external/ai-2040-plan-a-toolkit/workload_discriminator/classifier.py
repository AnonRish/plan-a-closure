"""
classifier.py

Trains a logistic regression classifier (interpretable by construction --
an auditor can read the coefficients, not just trust a score) on the
synthetic dataset, evaluates it normally, and separately stress-tests it
against traffic deliberately built to fool one feature at a time.
"""

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score, confusion_matrix

from .traffic_gen import (
    generate_training_session, generate_inference_session,
    generate_adversarial_regular_inference_session,
)
from .features import feature_vector, FEATURE_NAMES

LABEL_TRAINING, LABEL_INFERENCE = 1, 0  # 1 = training workload, 0 = inference workload


def build_dataset(n_per_class, rng):
    sessions = []
    for _ in range(n_per_class):
        sessions.append(generate_training_session(rng))
        sessions.append(generate_inference_session(rng))
    X = np.array([feature_vector(s) for s in sessions])
    y = np.array([LABEL_TRAINING if s.label == "training" else LABEL_INFERENCE for s in sessions])
    return X, y, sessions


def train_and_evaluate(seed=0, n_per_class=300, test_size=0.3):
    rng = np.random.default_rng(seed)
    X, y, _ = build_dataset(n_per_class, rng)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=seed, stratify=y)

    clf = LogisticRegression()
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1]

    precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average="binary", pos_label=LABEL_TRAINING)
    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "roc_auc": float(roc_auc_score(y_test, y_prob)),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "coefficients": dict(zip(FEATURE_NAMES, clf.coef_[0].tolist())),
        "intercept": float(clf.intercept_[0]),
    }
    return clf, metrics


def evaluate_adversarial(clf, n=300, seed=1):
    """All sessions here are genuinely inference workloads, timed to look training-regular."""
    rng = np.random.default_rng(seed)
    sessions = [generate_adversarial_regular_inference_session(rng) for _ in range(n)]
    X = np.array([feature_vector(s) for s in sessions])
    y_true = np.full(n, LABEL_INFERENCE)
    y_pred = clf.predict(X)
    return {
        "n": n,
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "misclassified_as_training": int(np.sum(y_pred == LABEL_TRAINING)),
    }


def evaluate_timing_only_baseline(seed=0, n_per_class=300, test_size=0.3):
    """A classifier using ONLY inter_event_cv -- to show why relying on timing alone is weaker."""
    rng = np.random.default_rng(seed)
    X, y, _ = build_dataset(n_per_class, rng)
    X = X[:, [0]]  # inter_event_cv only
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=seed, stratify=y)
    clf = LogisticRegression()
    clf.fit(X_train, y_train)

    rng_adv = np.random.default_rng(seed + 1)
    adv_sessions = [generate_adversarial_regular_inference_session(rng_adv) for _ in range(300)]
    X_adv = np.array([[feature_vector(s)[0]] for s in adv_sessions])
    y_adv_pred = clf.predict(X_adv)
    return {
        "held_out_accuracy": float(accuracy_score(y_test, clf.predict(X_test))),
        "adversarial_accuracy": float(accuracy_score(np.full(len(adv_sessions), LABEL_INFERENCE), y_adv_pred)),
    }
