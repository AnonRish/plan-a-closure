"""
LSH-based recomputation verification -- a reference construction in the
spirit of "Inference reproducibility workarounds" and "Recomputation
algorithms" (SITREP items 5 and 8, both graded Active elsewhere via
TOPLOC and DiFR). This module does not reproduce either published
algorithm -- their code is open source and cited in README.md, not ported
here, since duplicating already-active work isn't closing a gap. This is
an independent, from-scratch construction built on classical
locality-sensitive hashing (Charikar, 2002, "Similarity Estimation
Techniques from Rounding Algorithms" -- SimHash), demonstrating the same
underlying idea: a compact fingerprint of a model's intermediate
activations that (a) is cheap to compute and compare, (b) is stable under
the small numerical noise that legitimate hardware/kernel-order
differences introduce, and (c) changes sharply if the actual computation
differed (wrong model, wrong weights, fabricated output).

`generate_activation_vector` stands in for a real model's intermediate
activations -- this repo has no model or GPU to produce real ones.
Everything downstream of that (the hashing, the tolerance analysis, the
red-teaming in test_recompute.py, addressing item 10) is real, tested,
general-purpose SimHash math that applies unchanged to real activation
vectors.

Item 9 ("Frontier recomputation algorithms") asks for algorithms that
evolve with new architectures. This isn't solved here either -- but
test_recompute.py's
test_scheme_generalizes_across_different_configurations demonstrates the
mechanism isn't hardcoded to one vector shape, which is the minimum bar
for "could plausibly adapt."
"""

import random
from dataclasses import dataclass


def simhash_projection_matrix(dim: int, n_bits: int, seed: int) -> list:
    rng = random.Random(seed)
    return [[rng.gauss(0, 1) for _ in range(dim)] for _ in range(n_bits)]


def simhash(vector: list, projections: list) -> int:
    bits = 0
    for i, plane in enumerate(projections):
        dot = sum(v * p for v, p in zip(vector, plane))
        if dot >= 0:
            bits |= (1 << i)
    return bits


def hamming_distance(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def generate_activation_vector(dim: int, seed: int) -> list:
    rng = random.Random(seed)
    return [rng.gauss(0, 1) for _ in range(dim)]


def perturb(vector: list, noise_scale: float, seed: int) -> list:
    """Small numerical noise -- stands in for legitimate hardware/kernel-
    order differences between an honest recomputation and the original
    run."""
    rng = random.Random(seed)
    return [v + rng.gauss(0, noise_scale) for v in vector]


def fabricate(dim: int, seed: int) -> list:
    """An unrelated vector -- stands in for a dishonest party submitting
    output from a different (e.g. cheaper) model while claiming it came
    from the correct one."""
    return generate_activation_vector(dim, seed)


@dataclass
class RecomputationFingerprint:
    bits: int
    n_bits: int


class RecomputationVerifier:
    def __init__(self, dim: int, n_bits: int = 256, seed: int = 0):
        self.dim = dim
        self.n_bits = n_bits
        self.projections = simhash_projection_matrix(dim, n_bits, seed)

    def fingerprint(self, activation_vector: list) -> RecomputationFingerprint:
        return RecomputationFingerprint(simhash(activation_vector, self.projections), self.n_bits)

    def verify(self, claimed: RecomputationFingerprint, recomputed_vector: list, max_hamming_fraction: float = 0.1) -> bool:
        recomputed_fp = self.fingerprint(recomputed_vector)
        dist = hamming_distance(claimed.bits, recomputed_fp.bits)
        return dist <= max_hamming_fraction * self.n_bits
