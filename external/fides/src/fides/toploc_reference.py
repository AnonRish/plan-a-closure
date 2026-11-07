"""
Polynomial top-k recomputation verification -- a from-scratch
reimplementation of the actual algorithmic core of TOPLOC (Ong et al.,
2025, arXiv:2501.16007; github.com/PrimeIntellect-ai/toploc), read
directly from that repository's toploc/poly.py rather than reconstructed
from the paper's abstract.

recompute.py (elsewhere in this package) built an independent SimHash
scheme "in the spirit of" TOPLOC/DiFR without checking that spirit
against their actual code. On reading toploc/poly.py directly, TOPLOC's
real mechanism turns out to be meaningfully different from
random-hyperplane hashing:

  1. Select the top-k activation values by absolute magnitude (not a
     random projection of all values) -- `flat_view.abs().topk(topk)`.
  2. Fit a polynomial through the (position, value) points over a finite
     field, so k values compress to k polynomial coefficients -- the same
     "k points determine a degree-(k-1) polynomial" idea behind Shamir's
     Secret Sharing.
  3. To verify, the *verifier* independently re-selects its own top-k
     positions from its recomputed activations (it does not trust the
     prover's choice of which positions mattered), evaluates the
     original proof's polynomial at those positions, and compares
     against what it actually recomputed there -- using a *graded*
     floating-point comparison (exponent must match exactly; mantissa
     error is measured, not just thresholded) rather than a single
     pass/fail bit.

This module reimplements steps 1-3 using standard modular Lagrange
interpolation over GF(65537) (the Fermat prime 2^16+1, chosen because it
is the smallest prime exceeding the full range of a 16-bit bfloat16 bit
pattern) and manual IEEE-754 bfloat16 decomposition via `struct`.
Correctness of the interpolation is checked in
test_toploc_reference.py by confirming a fitted polynomial reproduces its
own input points exactly, and against a hand-computable known polynomial.

What this is NOT: it is not bit-compatible with TOPLOC's compiled
implementation. The exact finite-field modulus and bit-packing scheme
live in a C extension (toploc/C/csrc/) this module does not
reverse-engineer -- `pip install toploc` was attempted directly in this
environment and its prebuilt extension failed to load against the
available torch build (a real ABI mismatch, not a hypothetical one; see
spec/PROTOCOL.md section 11). What's reimplemented here is the verified
algorithmic principle, confirmed by reading their actual Python source,
not their exact compiled bytes -- and it should be read as that, not as
"this repo now runs TOPLOC."
"""

import struct
from dataclasses import dataclass

from .accumulator import is_probable_prime

MODULUS = 65537  # Fermat prime F4 = 2**16 + 1
assert is_probable_prime(MODULUS)


def to_bfloat16_bits(value: float) -> int:
    """Truncates a Python float to bfloat16 precision, returning its
    16-bit representation as an unsigned integer -- the top 16 bits of
    the value's IEEE 754 float32 representation, which is exactly what
    bfloat16 is."""
    f32_bits = struct.unpack(">I", struct.pack(">f", value))[0]
    return f32_bits >> 16


def bfloat16_parts(bits16: int):
    """(sign, exponent, mantissa) from a bfloat16 bit pattern."""
    return (bits16 >> 15) & 0x1, (bits16 >> 7) & 0xFF, bits16 & 0x7F


def select_topk_by_magnitude(values: list, k: int) -> list:
    """Indices of the k largest values by absolute magnitude -- TOPLOC's
    actual selection rule, not a random sample."""
    return sorted(range(len(values)), key=lambda i: abs(values[i]), reverse=True)[:k]


def _mod_inverse(a: int, p: int) -> int:
    return pow(a, p - 2, p)


def lagrange_coefficients(points: list, modulus: int = MODULUS) -> list:
    """points: list of (x, y) pairs with distinct x mod `modulus`.
    Returns coefficients [c0, c1, ...] (lowest degree first) of the
    unique degree-(len(points)-1) polynomial passing through them."""
    k = len(points)
    coeffs = [0] * k
    for i in range(k):
        xi, yi = points[i]
        basis = [1]
        denom = 1
        for j in range(k):
            if j == i:
                continue
            xj, _ = points[j]
            new_basis = [0] * (len(basis) + 1)
            for d, c in enumerate(basis):
                new_basis[d] = (new_basis[d] - xj * c) % modulus
                new_basis[d + 1] = (new_basis[d + 1] + c) % modulus
            basis = new_basis
            denom = (denom * ((xi - xj) % modulus)) % modulus
        inv_denom = _mod_inverse(denom, modulus)
        scale = (yi * inv_denom) % modulus
        for d, c in enumerate(basis):
            coeffs[d] = (coeffs[d] + scale * c) % modulus
    return coeffs


def evaluate_polynomial(coeffs: list, x: int, modulus: int = MODULUS) -> int:
    result = 0
    for c in reversed(coeffs):
        result = (result * x + c) % modulus
    return result


@dataclass
class TopKProof:
    coeffs: list  # only the polynomial coefficients -- no indices stored,
                  # matching TOPLOC's real design: the verifier derives
                  # its own top-k positions rather than trusting the
                  # prover's.
    k: int


def build_proof(values: list, k: int) -> TopKProof:
    topk_indices = select_topk_by_magnitude(values, k)
    points = [(idx % MODULUS, to_bfloat16_bits(values[idx])) for idx in topk_indices]
    if len({x for x, _ in points}) != len(points):
        raise ValueError("index collision mod MODULUS for this k -- use fewer points or a larger modulus")
    return TopKProof(coeffs=lagrange_coefficients(points), k=k)


@dataclass
class VerificationResult:
    exponent_matches: int
    exponent_total: int
    mantissa_error_mean: float
    mantissa_error_max: int


def verify_proof(proof: TopKProof, recomputed_values: list) -> VerificationResult:
    verifier_topk_indices = select_topk_by_magnitude(recomputed_values, proof.k)
    exp_matches = 0
    mant_errors = []
    for idx in verifier_topk_indices:
        reconstructed_bits = evaluate_polynomial(proof.coeffs, idx % MODULUS) & 0xFFFF
        actual_bits = to_bfloat16_bits(recomputed_values[idx])
        _, r_exp, r_mant = bfloat16_parts(reconstructed_bits)
        _, a_exp, a_mant = bfloat16_parts(actual_bits)
        if r_exp == a_exp:
            exp_matches += 1
            mant_errors.append(abs(r_mant - a_mant))
    mean_err = (sum(mant_errors) / len(mant_errors)) if mant_errors else float("inf")
    max_err = max(mant_errors) if mant_errors else -1
    return VerificationResult(exp_matches, proof.k, mean_err, max_err)
