"""The false-alarm side of the sampling story, which Appendix A sets aside.

Appendix A prices *detection*. Every audited packet also carries a chance of a
spurious flag if the recomputation check is tolerance-based rather than
bit-exact. At the supplement's 2034 example (33 B H100e pool, 1 % budget,
100 H100e-hour packets) about 2.9e10 packets are audited per year, so tolerating
one spurious alarm a year means a per-packet false-flag rate near 3.5e-11
(about 6.5 sigma if the honest tail were Gaussian). Certifying a rate that low
from clean honest runs takes ln(1/delta) years of that same audited throughput.
These helpers make the arithmetic explicit. Inputs are yours; nothing here is
a claim about any particular verifier.
"""
from __future__ import annotations

import math
from statistics import NormalDist

HOURS_PER_YEAR = 8760.0  # 365 days


def audited_packets_per_year(pool_h100e: float, budget: float, packet_size_h100e_hours: float,
                             hours: float = HOURS_PER_YEAR) -> float:
    """Packets recomputed per ``hours``: pool * budget * hours / packet_size."""
    if pool_h100e < 0 or not (0 <= budget <= 1) or packet_size_h100e_hours <= 0:
        raise ValueError("bad inputs")
    return pool_h100e * budget * hours / packet_size_h100e_hours


def expected_false_alarms(n_audited: float, fpr: float) -> float:
    if n_audited < 0 or not (0 <= fpr <= 1):
        raise ValueError("bad inputs")
    return n_audited * fpr


def max_fpr_for_alarm_budget(n_audited: float, max_alarms: float) -> float:
    """Per-packet false-flag rate that keeps expected false alarms <= ``max_alarms``."""
    if n_audited <= 0 or max_alarms < 0:
        raise ValueError("bad inputs")
    return min(1.0, max_alarms / n_audited)


def gaussian_threshold_sigma(fpr: float) -> float:
    """One-sided z such that a standard-normal null exceeds it with probability ``fpr``.

    Only meaningful if the honest-score tail really is Gaussian; real
    nondeterminism tails are usually heavier, which makes the true threshold
    *higher* for the same fpr.
    """
    if not (0.0 < fpr < 1.0):
        raise ValueError("fpr must be in (0, 1)")
    return -NormalDist().inv_cdf(fpr)


def packets_to_certify_fpr(fpr: float, delta: float = 0.05) -> int:
    """Honest packets needed so that seeing zero exceedances certifies ``fpr`` at level ``delta``.

    Zero-failure bound: ``(1 - fpr)^n <= delta``  (the "rule of three" at delta = 5 %).
    """
    if not (0.0 < fpr < 1.0) or not (0.0 < delta < 1.0):
        raise ValueError("fpr and delta must be in (0, 1)")
    return math.ceil(math.log(delta) / math.log1p(-fpr))


def certifiable_fpr(n_honest_packets: float, delta: float = 0.05) -> float:
    """Smallest per-packet false-flag rate you can certify from ``n`` clean honest packets."""
    if n_honest_packets <= 0 or not (0.0 < delta < 1.0):
        raise ValueError("bad inputs")
    return -math.expm1(math.log(delta) / n_honest_packets)
