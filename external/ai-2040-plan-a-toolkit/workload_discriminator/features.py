"""
features.py

Three features, each independently motivated and each individually
explainable to a non-specialist auditor -- which matters, because a
classification an auditor can't get an explanation for isn't something
they can act on or defend.

inter_event_cv     -- coefficient of variation of inter-event timing.
                       Low = regular cadence (training's step time).
                       High = irregular arrivals (inference's request stream).

log_symmetry_ratio -- log(total bytes sent / total bytes received).
                       Near 0 = symmetric (training's AllReduce).
                       Very negative = upload << download (inference's
                       short-prompt-long-completion pattern).

burst_size_cv      -- coefficient of variation of per-event total bytes.
                       Low = same-size exchange every time (training, same
                       model's gradients each step). High = size varies a
                       lot per exchange (inference, different queries).
"""

import numpy as np

FEATURE_NAMES = ["inter_event_cv", "log_symmetry_ratio", "burst_size_cv"]


def extract_features(session) -> dict:
    ts = np.asarray(session.timestamps)
    sent = np.asarray(session.bytes_sent)
    received = np.asarray(session.bytes_received)

    intervals = np.diff(np.concatenate([[0.0], ts]))
    intervals = intervals[intervals > 0]
    inter_event_cv = float(np.std(intervals) / (np.mean(intervals) + 1e-9)) if len(intervals) else 0.0

    total_sent, total_received = float(np.sum(sent)), float(np.sum(received))
    log_symmetry_ratio = float(np.log((total_sent + 1e-9) / (total_received + 1e-9)))

    burst_totals = sent + received
    burst_size_cv = float(np.std(burst_totals) / (np.mean(burst_totals) + 1e-9)) if len(burst_totals) else 0.0

    return {
        "inter_event_cv": inter_event_cv,
        "log_symmetry_ratio": log_symmetry_ratio,
        "burst_size_cv": burst_size_cv,
        "n_events": int(len(ts)),
        "duration_s": float(ts[-1]) if len(ts) else 0.0,
    }


def feature_vector(session):
    f = extract_features(session)
    return [f[name] for name in FEATURE_NAMES]
