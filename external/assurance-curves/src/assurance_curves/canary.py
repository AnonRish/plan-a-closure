"""Auditing the auditor: canary packets against a recomputation server that lies.

A compromised recomputation server can suppress alarms. The verifier
injects ``m`` *canaries* - packets it knows are wrong - indistinguishable from
real traffic. A server that suppresses each alarm with probability ``q`` lets a
canary through with probability ``q``. Catching suppression is the same
sampling math as catching fakes, with the roles swapped.

Assumption that carries all the weight: the server cannot tell a canary from a
real fake. If it can, canaries prove nothing.
"""
from __future__ import annotations

from .core import min_fake_packets_exact, p_detected_exact, required_budget


def p_catch_suppression(q: float, m: int) -> float:
    """P(at least one of ``m`` canaries goes unflagged) for a server suppressing at rate ``q``."""
    return p_detected_exact(q, m)


def canaries_needed(q_min: float, confidence: float) -> int:
    """Canaries needed to catch a server suppressing at rate >= ``q_min`` with ``confidence``."""
    return min_fake_packets_exact(q_min, confidence)


def max_undetected_suppression(m: int, confidence: float) -> float:
    """After ``m`` canaries all flagged: any suppression rate >= this would have been caught w.p. >= ``confidence``."""
    if m <= 0:
        return 1.0
    return required_budget(m, confidence)


def p_detected_with_suppression(c: float, q: float, n_fake: float) -> float:
    """Detection probability when each audited fake is flagged with probability ``1 - q``."""
    return p_detected_exact(c * (1.0 - q), n_fake)


def guaranteed_detection(c: float, m_clean_canaries: int, canary_confidence: float, n_fake: float) -> float:
    """Lower bound on detection given ``m`` clean canaries; holds except with prob <= ``1 - canary_confidence``."""
    q_max = max_undetected_suppression(m_clean_canaries, canary_confidence)
    return p_detected_with_suppression(c, q_max, n_fake)
