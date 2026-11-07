"""
Quantitative security analysis of the spot-check audit scheme.

detection_probability() is the exact finite-population answer: the
verifier samples m of n committed events uniformly at random, without
replacement, *after* the prover has already committed (so the prover
cannot predict which indices will be checked). If a declared-inference
epoch actually contains k "bad" (training-signal) events, the probability
that a single audit catches at least one of them follows from the
hypergeometric distribution:

    P(catch >= 1) = 1 - C(n-k, m) / C(n, m)

poisson_detection_probability() is the large-population approximation used
in the field: the AI 2040 verification supplement's own appendix
(https://ai-2040.com/supplements/verification-plan#a2-detection-by-random-sampling)
derives P(detected) = 1 - exp(-N_verified * F_fake) for a per-packet audit
probability C, independently converging on the same result as
Rinberg et al., 2025, "Verifying LLM Inference to Detect Model Weight
Exfiltration" (arXiv:2511.02620). test_security.py checks that our exact
hypergeometric formula and this Poisson approximation agree in the regime
where both apply, as a sanity check that this implementation's math
matches the field's, not just this repo's own assumptions.

repeated_detection_probability() captures the point that actually matters
operationally: a single epoch's catch probability can be well under 100%
and the scheme is still strong, because a device has to sustain its lie
across every epoch it operates, and per-epoch failure probabilities
compound fast.
"""

from math import comb, exp
import random


def detection_probability(n: int, k: int, m: int) -> float:
    """Exact hypergeometric probability of sampling at least one of k
    marked items out of n total, when drawing m without replacement."""
    if n <= 0 or k <= 0 or m <= 0:
        return 0.0
    if m > n:
        raise ValueError("sample size m cannot exceed population size n")
    if n - k < m:
        return 1.0
    return 1 - (comb(n - k, m) / comb(n, m))


def poisson_detection_probability(n_verified: float, f_fake: float) -> float:
    """Large-population approximation: P(detected) = 1 - exp(-N_verified * F_fake),
    matching the AI 2040 verification-plan appendix and Rinberg et al. (2025)."""
    if n_verified < 0 or not (0.0 <= f_fake <= 1.0):
        raise ValueError("n_verified must be >= 0 and f_fake must be a probability in [0, 1]")
    return 1 - exp(-n_verified * f_fake)


def repeated_detection_probability(p_single: float, epochs: int) -> float:
    """Probability of being caught at least once across `epochs`
    independent audits, each with per-epoch catch probability p_single."""
    if not (0.0 <= p_single <= 1.0):
        raise ValueError("p_single must be a probability in [0, 1]")
    if epochs < 0:
        raise ValueError("epochs must be >= 0")
    return 1 - (1 - p_single) ** epochs


def monte_carlo_detection_rate(n: int, k: int, m: int, trials: int = 20000, seed: int = 0) -> float:
    """Empirical check of detection_probability() by direct simulation."""
    rng = random.Random(seed)
    bad = set(range(k))
    caught = 0
    population = range(n)
    for _ in range(trials):
        sample = rng.sample(population, m)
        if bad.intersection(sample):
            caught += 1
    return caught / trials
