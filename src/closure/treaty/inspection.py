"""Random-sample inspection of a chip registry (Scher and Thiergart 2024: owners register chips and locations;
international inspectors check a random sample of declared chips by their unique identifiers).

If D of N declared chips are missing (diverted, swapped, or never there) and inspectors check n chosen uniformly
without replacement, a violation is found with probability 1 - C(N - D, n) / C(N, n) (hypergeometric). That fixes
how many chips each inspection must check for a given assurance, and how the assurance builds up over repeated
inspections. The sample is drawn from a commit-reveal seed (beacon.py), so the inspected party cannot predict it.
"""
from __future__ import annotations

import math

from . import beacon


def _log_comb(n: int, k: int) -> float:
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


def detection_probability(n_declared: int, n_missing: int, sample: int) -> float:
    """P(at least one missing chip is in a uniform sample of `sample` of `n_declared`)."""
    N, D, n = int(n_declared), int(n_missing), int(sample)
    if not (0 <= D <= N and 0 <= n <= N):
        raise ValueError("need 0 <= missing <= declared and 0 <= sample <= declared")
    if D == 0 or n == 0:
        return 0.0
    if n > N - D:
        return 1.0
    return 1.0 - math.exp(_log_comb(N - D, n) - _log_comb(N, n))


def sample_size(n_declared: int, n_missing: int, assurance: float) -> int:
    """Smallest sample that finds at least one of n_missing missing chips with probability >= assurance."""
    lo, hi = 0, int(n_declared)
    if detection_probability(n_declared, n_missing, hi) < assurance:
        raise ValueError("even inspecting every chip does not reach that assurance (no chip is missing?)")
    while lo < hi:
        mid = (lo + hi) // 2
        if detection_probability(n_declared, n_missing, mid) >= assurance:
            hi = mid
        else:
            lo = mid + 1
    return lo


def repeated_detection(n_declared: int, n_missing: int, sample: int, inspections: int) -> float:
    """Probability that at least one of `inspections` independent samples finds a missing chip (the chips stay
    missing between inspections)."""
    miss = 1.0 - detection_probability(n_declared, n_missing, sample)
    return 1.0 - miss ** int(inspections)


def plan_sample(seed: bytes, declared_ids: list, sample: int, round_label: str) -> list:
    """The chips to inspect this round, from the parties' joint seed: reproducible by anyone, unpredictable before
    the reveal."""
    return beacon.draw(seed, list(declared_ids), int(sample), label=f"inspection:{round_label}")


def inspect(declared_ids: list, found_ids: set, sample_ids: list) -> dict:
    """Reconcile one round: which sampled chips were not found where the registry says they are."""
    missing = sorted(i for i in sample_ids if i not in found_ids)
    return {"declared": len(declared_ids), "sampled": len(sample_ids), "missing": missing, "violation": bool(missing)}
