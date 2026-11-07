"""
RSA accumulator with membership and non-membership proofs.

An accumulator commits a whole set to one short value, then lets you prove
an element is (or is not) in that set without revealing the rest of it.
This module implements the classic construction:

  * Benaloh & de Mare, "One-Way Accumulators: A Decentralized Alternative
    to Digital Signatures", EUROCRYPT 1993.
  * Barić & Pfitzmann, "Collision-Free Accumulators and Fail-Stop Signature
    Schemes Without Trees", EUROCRYPT 1997 (strengthens the security notion
    to collision-freeness under the strong RSA assumption).
  * Li, Li & Xue, "Universal Accumulators with Efficient Nonmembership
    Proofs", ACNS 2007 (adds the non-membership witness this module uses).

Security depends on the strong RSA assumption in a group of unknown order.
`trusted_setup()` below generates that modulus itself via a fresh RSA
keypair and never stores p, q -- but a real deployment cannot let any
single party run this step honestly-by-assumption; it needs either an
actual trusted third party or a multi-party ceremony, since whoever knows
the factorization of N can forge arbitrary membership proofs. This is a
known, named limitation, not an oversight -- see spec/PROTOCOL.md section
8. A trapdoor-free alternative exists using class groups of imaginary
quadratic order (see e.g. the "Secure Accumulators from Euclidean Rings
without Trusted Setup" line of work); that's real future work for this
repo, not implemented here.

Math, briefly: elements are mapped to distinct large primes (hash-to-prime
below). The accumulator is A = g^(x_1 * x_2 * ... * x_n) mod N. Membership
witness for x_i is g raised to the product of every *other* prime; you
verify by raising the witness to x_i and checking you land back on A.
Non-membership for y (coprime to the accumulated product u, which holds
automatically whenever y differs from every x_i) uses the Bezout identity
a*y + b*u = 1: the witness is (a, b), and verification checks
g^a raised to y, times A^b, lands on g. If y actually equals some x_i, then
gcd(y, u) = y != 1, and the Bezout step has no integer solution -- a
dishonest prover cannot construct a witness at all, not just an unlikely
one. That's the qualitative difference from commitment.py's spot-check
scheme: this is a soundness guarantee, not a detection probability.
"""

import hashlib
import math
import random
from dataclasses import dataclass

from cryptography.hazmat.primitives.asymmetric import rsa

_SMALL_PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47)


def is_probable_prime(n: int, rounds: int = 40) -> bool:
    """Miller-Rabin primality test."""
    if n < 2:
        return False
    for p in _SMALL_PRIMES:
        if n % p == 0:
            return n == p
    r, d = 0, n - 1
    while d % 2 == 0:
        r += 1
        d //= 2
    for _ in range(rounds):
        a = random.randrange(2, n - 1)
        x = pow(a, d, n)
        if x == 1 or x == n - 1:
            continue
        for _ in range(r - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def hash_to_prime(data: bytes, bit_length: int = 128) -> int:
    """Deterministically derive a prime from arbitrary bytes: hash with an
    incrementing counter until the candidate passes primality testing.
    Reference-implementation parameter choice (128 bits) -- a real
    deployment should size this against the formal analysis in the cited
    accumulator literature, not against this docstring."""
    counter = 0
    while True:
        digest = hashlib.sha256(data + counter.to_bytes(8, "big")).digest()
        candidate = int.from_bytes(digest[: bit_length // 8], "big")
        candidate |= (1 << (bit_length - 1)) | 1  # force top bit set and odd
        if is_probable_prime(candidate):
            return candidate
        counter += 1


@dataclass
class AccumulatorSetup:
    N: int
    g: int


def trusted_setup(key_size: int = 2048) -> AccumulatorSetup:
    """Generates N via a fresh RSA keypair (discarding p, q immediately --
    this process never returns them) and picks g as a random quadratic
    residue mod N. See module docstring for the honest caveat about who
    should actually run this in a real deployment."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
    N = key.private_numbers().public_numbers.n
    while True:
        h = random.randrange(2, N - 1)
        if math.gcd(h, N) == 1:
            break
    g = pow(h, 2, N)
    return AccumulatorSetup(N=N, g=g)


def _product(primes: list) -> int:
    u = 1
    for p in primes:
        u *= p
    return u


def accumulate(setup: AccumulatorSetup, primes: list) -> int:
    return pow(setup.g, _product(primes), setup.N)


def membership_witness(setup: AccumulatorSetup, primes: list, index: int) -> int:
    exponent = _product(p for i, p in enumerate(primes) if i != index)
    return pow(setup.g, exponent, setup.N)


def verify_membership(setup: AccumulatorSetup, A: int, prime: int, witness: int) -> bool:
    return pow(witness, prime, setup.N) == A


def _extended_gcd(a: int, b: int):
    """Returns (gcd, x, y) with a*x + b*y = gcd."""
    old_r, r = a, b
    old_s, s = 1, 0
    old_t, t = 0, 1
    while r != 0:
        q = old_r // r
        old_r, r = r, old_r - q * r
        old_s, s = s, old_s - q * s
        old_t, t = t, old_t - q * t
    return old_r, old_s, old_t


def nonmembership_witness(y: int, u: int):
    """u is the product of all accumulated primes (not the accumulator
    value itself). Returns (a, b) with a*y + b*u = 1, or None if y shares a
    factor with u -- which, for prime y, means y is literally one of the
    accumulated primes. In that case no witness can exist; this isn't a
    missing feature, it's the security property."""
    g, a, b = _extended_gcd(y, u)
    if g != 1:
        return None
    return (a, b)


def verify_nonmembership(setup: AccumulatorSetup, A: int, y: int, witness) -> bool:
    if witness is None:
        return False
    a, b = witness
    d = pow(setup.g, a, setup.N)
    lhs = (pow(d, y, setup.N) * pow(A, b, setup.N)) % setup.N
    return lhs == setup.g % setup.N
