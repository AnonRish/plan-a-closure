#!/usr/bin/env python3
"""Transparent Track 3 sampling-bound calculator.

This is a research model, not a treaty certificate.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


def _log_cdf(k: int, n: int, p: float, log_comb: list[float]) -> float:
    """log P[X <= k] for X ~ Binomial(n, p), computed in log space."""
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        return -math.inf  # k < n here, so the CDF is 0
    lp, lq = math.log(p), math.log1p(-p)
    terms = [log_comb[i] + i * lp + (n - i) * lq for i in range(k + 1)]
    m = max(terms)
    return m + math.log(sum(math.exp(t - m) for t in terms))


def one_sided_failure_upper_bound(k: int, n: int, delta: float) -> float:
    """Return a one-sided binomial upper confidence bound.

    For k failures out of n trials, solve for p in:
        P[X <= k | X~Binomial(n,p)] = delta
    using binary search. This is the conservative Clopper-Pearson-style
    upper bound for the failure probability. The CDF is evaluated in log
    space, so cases where C(n, k) exceeds float range (for example n=100,000
    with k=100) no longer overflow.
    """
    if n <= 0:
        raise ValueError("n must be > 0")
    if not 0 <= k <= n:
        raise ValueError("k must satisfy 0 <= k <= n")
    if not 0 < delta < 1:
        raise ValueError("delta must be between 0 and 1")

    if k == n:
        return 1.0

    lg_n1 = math.lgamma(n + 1)
    log_comb = [lg_n1 - math.lgamma(i + 1) - math.lgamma(n - i + 1) for i in range(k + 1)]
    log_delta = math.log(delta)

    lo, hi = 0.0, 1.0
    for _ in range(100):
        mid = (lo + hi) / 2
        # CDF decreases as p increases.
        if _log_cdf(k, n, mid, log_comb) > log_delta:
            lo = mid
        else:
            hi = mid
    return hi


def zero_failure_reference_bound(tail_units: float, n: int, delta: float) -> float:
    if tail_units < 0:
        raise ValueError("tail_units must be >= 0")
    if n <= 0:
        raise ValueError("n must be > 0")
    if not 0 < delta < 1:
        raise ValueError("delta must be between 0 and 1")
    return tail_units * math.log(1.0 / delta) / n


def certificate_model(tail_units: float, n: int, failures: int, delta: float) -> dict:
    upper_failure_rate = one_sided_failure_upper_bound(failures, n, delta)
    upper_compute = tail_units * upper_failure_rate
    reference_zero_fail = (
        zero_failure_reference_bound(tail_units, n, delta)
        if failures == 0
        else None
    )
    return {
        "schema_version": 1,
        "model": "Track3-tail-sampling-upper-bound",
        "status": "RESEARCH_MODEL_ONLY",
        "inputs": {
            "tail_compute_units": tail_units,
            "sample_size_n": n,
            "observed_failures_k": failures,
            "confidence_delta": delta,
            "confidence_level": 1.0 - delta,
        },
        "outputs": {
            "upper_failure_rate": upper_failure_rate,
            "upper_bound_untraced_compute_units": upper_compute,
            "zero_failure_reference_bound": reference_zero_fail,
        },
        "assumptions": [
            "The tail population is genuinely closed and its size is known.",
            "Sampling is random with a declared sampling frame and reproducible seed.",
            "The audited unit is representative of the tail population under the stated sampling design.",
            "A failure is defined before sampling and cannot be reclassified after observing the outcome.",
        ],
        "limitations": [
            "This is not a treaty certificate.",
            "The calculator does not validate ownership, physical location, serial numbers, or inspection records.",
            "Finite-population corrections, stratified designs, cluster sampling, and weighting require explicit extensions.",
            "The zero-failure reference formula is included for transparency and matches the approximate form discussed in the AI 2040 Appendix B material; the failure-aware bound uses the explicit binomial model above.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tail-units", type=float, required=True)
    ap.add_argument("--sample-size", type=int, required=True)
    ap.add_argument("--failures", type=int, default=0)
    ap.add_argument("--delta", type=float, default=0.05)
    ap.add_argument("--write-json", type=Path)
    args = ap.parse_args()

    obj = certificate_model(args.tail_units, args.sample_size, args.failures, args.delta)
    obj["input_hash"] = hashlib.sha256(
        json.dumps(obj["inputs"], sort_keys=True).encode("utf-8")
    ).hexdigest()

    output = json.dumps(obj, indent=2) + "\n"
    if args.write_json:
        args.write_json.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
