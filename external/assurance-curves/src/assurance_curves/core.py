"""Detection probabilities for random-sampling verification of packet streams.

Setting (AI 2040: Plan A, Verification Plan supplement, Appendix A): a stream of
``N`` reproducible packets, ``n_fake`` of which are unauthorised substitutions.
A verifier recomputes a random subset. This module gives the exact answer and
the Poisson form the supplement uses, so the gap between them is a number you
can read off rather than an assumption.

Everything is computed in log space (``log1p`` / ``expm1``) so tiny detection
probabilities and 8-nines confidences do not round to 0 / 1.
"""
from __future__ import annotations

import math

import numpy as np

#: ln(100). "C * N_fake must exceed about 4.6" for 99 % detection (Appendix A.3).
LN_100 = math.log(100.0)


def _prob(x: float, name: str) -> float:
    x = float(x)
    if math.isnan(x) or not (0.0 <= x <= 1.0):
        raise ValueError(f"{name} must be in [0, 1], got {x!r}")
    return x


def _nonneg(x: float, name: str) -> float:
    x = float(x)
    if math.isnan(x) or x < 0.0:
        raise ValueError(f"{name} must be >= 0, got {x!r}")
    return x


# --------------------------------------------------------------------------- #
# Independent sampling: each packet audited with probability c
# --------------------------------------------------------------------------- #
def p_undetected_exact(c: float, n_fake: float) -> float:
    """P(no fake packet is audited) = (1 - c) ** n_fake  (Appendix A.2, exact form)."""
    c = _prob(c, "c")
    n = _nonneg(n_fake, "n_fake")
    if n == 0.0 or c == 0.0:
        return 1.0
    if c == 1.0:
        return 0.0
    return math.exp(n * math.log1p(-c))


def p_detected_exact(c: float, n_fake: float) -> float:
    """P(at least one fake packet is audited) = 1 - (1 - c) ** n_fake."""
    c = _prob(c, "c")
    n = _nonneg(n_fake, "n_fake")
    if n == 0.0 or c == 0.0:
        return 0.0
    if c == 1.0:
        return 1.0
    return -math.expm1(n * math.log1p(-c))


def p_detected_poisson(n_verified: float, f_fake: float) -> float:
    """Appendix A.2 Poisson form: 1 - exp(-N_verified * F_fake).

    Always <= :func:`p_detected_exact` at the same ``c * n_fake`` because
    ``ln(1 - c) <= -c``: the Poisson form is conservative (it understates
    detection). The gap is largest at large ``c``.
    """
    nv = _nonneg(n_verified, "n_verified")
    f = _prob(f_fake, "f_fake")
    return -math.expm1(-nv * f)


# --------------------------------------------------------------------------- #
# Fixed audit count: n_audited packets drawn without replacement from N
# --------------------------------------------------------------------------- #
#: Longest product evaluated term by term (about 20 ms, 16 MB of temporaries).
_DIRECT_LIMIT = 2_000_000
#: n*F/N at or above this: P(undetected) <= exp(-40) < 2**-57, which rounds to 0 in float64.
_SATURATED = 40.0


def _log_undetected_direct(N: int, a: int, b: int) -> float:
    """ln prod_{i<a} (1 - b/(N-i)), summed in blocks. Requires a + b <= N."""
    total, block = [], 1 << 20
    fN = float(N)
    for start in range(0, a, block):
        i = np.arange(start, min(a, start + block), dtype=np.float64)
        total.append(float(np.sum(np.log1p(-b / (fN - i)))))
    return math.fsum(total)


def p_detected_hypergeometric(n_total: int, n_fake: int, n_audited: int) -> float:
    """P(catch >= 1 fake) when exactly ``n_audited`` of ``n_total`` packets are audited.

    ``1 - C(N - F, n) / C(N, n)``. The supplement notes (A.1) that real audits
    sample without replacement; this is that case. It is never lower than the
    independent-sampling answer at ``c = n_audited / n_total`` (property-tested).

    Evaluation. ``C(N-F, n) / C(N, n) = prod_{i<n} (1 - F/(N-i))`` and, by the
    symmetry of the hypergeometric distribution, equals the same product with
    ``n`` and ``F`` swapped. The shorter product (``min(n, F)`` terms, at most
    2e6) is summed exactly with ``log1p``; a log-gamma difference is *not* used
    because it loses about 1e-16 * N ln N of absolute accuracy in the exponent
    (relative error 9e-5 at N = 1.9e9, see VERIFICATION_LOG.md, entry 3).
    When both ``n`` and ``F`` exceed 2e6 and the answer is not saturated, then
    ``N >= 1e11`` and ``n/N, F/N <= 2e-5``, and the sum of the smooth terms
    ``g(i) = log1p(-F/(N-i))`` is evaluated by an expansion about the midpoint
    ``m = (n-1)/2``:  ``n g(m) + g''(m) n (n^2 - 1) / 24``.  The first omitted term
    is about ``(n F / N) (n / N)^4 / 80``, below 1e-19 wherever this branch runs.
    ``n * F / N >= 40`` returns exactly 1.0 (true value is within 2**-57 of 1).
    """
    N, F, n = int(n_total), int(n_fake), int(n_audited)
    if N < 0 or F < 0 or n < 0 or F > N or n > N:
        raise ValueError("need 0 <= n_fake <= n_total and 0 <= n_audited <= n_total")
    if F == 0 or n == 0:
        return 0.0
    if n > N - F:  # pigeonhole: cannot avoid every fake
        return 1.0
    if n * F >= _SATURATED * N:
        return 1.0
    m = min(n, F)
    if m <= _DIRECT_LIMIT:
        L = _log_undetected_direct(N, n, F) if n <= F else _log_undetected_direct(N, F, n)
    else:
        u = N - (n - 1) / 2.0
        g0 = math.log1p(-F / u)
        g2 = -F * (2.0 * u - F) / (u * u * (u - F) ** 2)      # g''(m)
        L = n * g0 + g2 * n * (n * n - 1.0) / 24.0
    return -math.expm1(L)


# --------------------------------------------------------------------------- #
# Inverting the formulas
# --------------------------------------------------------------------------- #
def fake_packets_for_confidence(c: float, confidence: float, *, model: str = "exact") -> float:
    """Real-valued number of fake packets at which detection reaches ``confidence``.

    ``model="exact"``  -> ln(1-conf) / ln(1-c)
    ``model="poisson"``-> -ln(1-conf) / c        (the supplement's "4.6 / C")
    """
    c = _prob(c, "c")
    conf = _prob(confidence, "confidence")
    if conf == 0.0:
        return 0.0
    if c == 0.0:
        return math.inf
    if conf == 1.0:
        return 1.0 if c == 1.0 else math.inf
    if model == "poisson":
        return -math.log1p(-conf) / c
    if model == "exact":
        if c == 1.0:
            return 1.0
        return math.log1p(-conf) / math.log1p(-c)
    raise ValueError("model must be 'exact' or 'poisson'")


def min_fake_packets_exact(c: float, confidence: float) -> int:
    """Smallest integer ``n`` with ``1 - (1-c)^n >= confidence``."""
    x = fake_packets_for_confidence(c, confidence, model="exact")
    if math.isinf(x):
        raise ValueError("confidence unreachable: budget is 0, or confidence is 1 with c < 1")
    n = max(1, math.ceil(x)) if confidence > 0 else 0
    if n == 0:
        return 0
    # floating-point guard so the result is exactly minimal
    while p_detected_exact(c, n) < confidence:
        n += 1
    while n > 1 and p_detected_exact(c, n - 1) >= confidence:
        n -= 1
    return n


def required_budget(n_fake: float, confidence: float, *, model: str = "exact") -> float:
    """Recomputation budget ``c`` needed to catch ``n_fake`` fakes at ``confidence``."""
    n = _nonneg(n_fake, "n_fake")
    conf = _prob(confidence, "confidence")
    if n == 0.0:
        raise ValueError("n_fake must be > 0")
    if conf == 0.0:
        return 0.0
    if conf == 1.0:
        return 1.0
    if model == "poisson":
        return min(1.0, -math.log1p(-conf) / n)
    if model == "exact":
        return -math.expm1(math.log1p(-conf) / n)
    raise ValueError("model must be 'exact' or 'poisson'")


def nines(confidence: float) -> float:
    """Number of nines: 0.99 -> 2, 0.99999 -> 5. ``inf`` for confidence 1."""
    conf = _prob(confidence, "confidence")
    if conf == 1.0:
        return math.inf
    return -math.log1p(-conf) / math.log(10.0)


def confidence_from_nines(k: float) -> float:
    """Inverse of :func:`nines` (``-expm1`` keeps precision for small ``k``)."""
    k = _nonneg(k, "nines")
    return -math.expm1(-k * math.log(10.0))
