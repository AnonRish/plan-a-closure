import pytest

from fides.accumulator import (
    is_probable_prime,
    hash_to_prime,
    trusted_setup,
    accumulate,
    membership_witness,
    verify_membership,
    nonmembership_witness,
    verify_nonmembership,
    _product,
)

_KNOWN_PRIMES = (2, 3, 5, 7, 11, 97, 7919, 1_000_003)
_KNOWN_COMPOSITES = (0, 1, 4, 6, 100, 7920, 1_000_002, 9973 * 9967)


@pytest.fixture(scope="module")
def setup():
    # 1024 is the library's floor and is not a production security
    # recommendation -- kept small purely to keep the test suite fast.
    # Production sizing is a deployment decision documented in
    # accumulator.py, not this test.
    return trusted_setup(key_size=1024)


def test_miller_rabin_identifies_known_primes():
    for p in _KNOWN_PRIMES:
        assert is_probable_prime(p), p


def test_miller_rabin_identifies_known_composites():
    for c in _KNOWN_COMPOSITES:
        assert not is_probable_prime(c), c


def test_hash_to_prime_is_deterministic_and_actually_prime():
    p1 = hash_to_prime(b"forward_matmul")
    p2 = hash_to_prime(b"forward_matmul")
    assert p1 == p2
    assert is_probable_prime(p1)


def test_hash_to_prime_differs_across_distinct_inputs():
    ops = [b"forward_matmul", b"backward_matmul", b"optimizer_update", b"kv_cache_write"]
    primes = [hash_to_prime(op) for op in ops]
    assert len(set(primes)) == len(primes)


def test_membership_witness_verifies_for_every_accumulated_element(setup):
    primes = [hash_to_prime(f"op-{i}".encode(), bit_length=64) for i in range(6)]
    A = accumulate(setup, primes)
    for i, p in enumerate(primes):
        w = membership_witness(setup, primes, i)
        assert verify_membership(setup, A, p, w)


def test_membership_witness_fails_for_wrong_prime(setup):
    primes = [hash_to_prime(f"op-{i}".encode(), bit_length=64) for i in range(4)]
    A = accumulate(setup, primes)
    w0 = membership_witness(setup, primes, 0)
    wrong_prime = hash_to_prime(b"not-in-the-set", bit_length=64)
    assert not verify_membership(setup, A, wrong_prime, w0)


def test_nonmembership_succeeds_for_a_genuine_nonmember(setup):
    primes = [hash_to_prime(f"op-{i}".encode(), bit_length=64) for i in range(5)]
    A = accumulate(setup, primes)
    u = _product(primes)
    y = hash_to_prime(b"definitely-not-accumulated", bit_length=64)
    witness = nonmembership_witness(y, u)
    assert witness is not None
    assert verify_nonmembership(setup, A, y, witness)


def test_nonmembership_witness_does_not_exist_for_an_actual_member(setup):
    # This is the core soundness property: if y IS one of the accumulated
    # primes, y divides u, gcd(y, u) = y != 1, and no Bezout witness
    # exists. A dishonest prover cannot fabricate one -- the math itself
    # has no solution, not merely an improbable one.
    primes = [hash_to_prime(f"op-{i}".encode(), bit_length=64) for i in range(5)]
    u = _product(primes)
    member = primes[2]
    assert nonmembership_witness(member, u) is None


def test_nonmembership_proof_for_a_member_forged_with_a_wrong_witness_is_rejected(setup):
    primes = [hash_to_prime(f"op-{i}".encode(), bit_length=64) for i in range(5)]
    A = accumulate(setup, primes)
    u = _product(primes)
    member = primes[1]
    # borrow a *different* element's valid non-membership witness and try
    # to pass it off as belonging to `member`
    other_nonmember = hash_to_prime(b"outside-the-set", bit_length=64)
    borrowed_witness = nonmembership_witness(other_nonmember, u)
    assert not verify_nonmembership(setup, A, member, borrowed_witness)


def test_tampered_accumulator_value_is_rejected(setup):
    primes = [hash_to_prime(f"op-{i}".encode(), bit_length=64) for i in range(4)]
    A = accumulate(setup, primes)
    u = _product(primes)
    y = hash_to_prime(b"outside-the-set", bit_length=64)
    witness = nonmembership_witness(y, u)
    assert verify_nonmembership(setup, A, y, witness)
    assert not verify_nonmembership(setup, (A + 1) % setup.N, y, witness)
