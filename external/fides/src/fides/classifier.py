"""
Lightweight classifier separating inference-only epochs from training
epochs using fingerprint features. Intentionally a transparent, thresholded
scoring function rather than a trained ML model: the decision function
itself sits inside the trust boundary (it decides what gets flagged for
human/auditor review), so we want it auditable by inspection rather than
being a black box whose own behavior would need separate verification.
See spec/PROTOCOL.md section 5.
"""

from enum import Enum

from .features import EpochFingerprint


class WorkloadClass(Enum):
    INFERENCE = "inference"
    TRAINING = "training"
    AMBIGUOUS = "ambiguous"


def classify(fp: EpochFingerprint) -> WorkloadClass:
    score = 0
    if fp.backward_ratio > 0.1:
        score += 2
    if fp.has_optimizer_update:
        score += 2
    if fp.kv_cache_present:
        score -= 2
    if fp.backward_ratio < 0.01 and not fp.has_optimizer_update:
        score -= 1

    if score >= 2:
        return WorkloadClass.TRAINING
    if score <= -1:
        return WorkloadClass.INFERENCE
    return WorkloadClass.AMBIGUOUS
