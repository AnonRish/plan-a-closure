import pytest

from fides.commitment import merkle_root, prove, verify, _event_bytes, decode_event
from fides.trace import KernelEvent, KernelOp


def _make_leaves(n):
    return [f"leaf-{i}".encode() for i in range(n)]


@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 7, 8, 13, 16, 33])
def test_all_leaves_verify_against_root(n):
    leaves = _make_leaves(n)
    root = merkle_root(leaves)
    for i in range(n):
        proof = prove(leaves, i)
        assert verify(leaves[i], proof, root), f"leaf {i} of {n} failed to verify"


def test_tampered_leaf_fails_verification():
    leaves = _make_leaves(6)
    root = merkle_root(leaves)
    proof = prove(leaves, 2)
    assert not verify(b"tampered-data", proof, root)


def test_tampered_proof_fails_verification():
    leaves = _make_leaves(9)
    root = merkle_root(leaves)
    proof = prove(leaves, 4)
    proof.siblings[0] = (b"\x00" * 32, proof.siblings[0][1])
    assert not verify(leaves[4], proof, root)


def test_different_leaf_sets_produce_different_roots():
    assert merkle_root(_make_leaves(5)) != merkle_root(_make_leaves(6))


def test_event_roundtrip_through_bytes():
    ev = KernelEvent(KernelOp.FORWARD_MATMUL, 1000, 500, 200, 300, 4_000_000)
    op, ts, dur, br, bw, fl = decode_event(_event_bytes(ev))
    assert op == "forward_matmul"
    assert (ts, dur, br, bw, fl) == (1000, 500, 200, 300, 4_000_000)


def test_event_serialization_is_deterministic_across_calls():
    # Regression test: an earlier draft used Python's str hash() for the
    # op code, which is randomized per-process (PYTHONHASHSEED) and would
    # make two honest parties compute different commitments for the same
    # trace. This pins deterministic struct-based encoding instead.
    ev = KernelEvent(KernelOp.BACKWARD_ATTENTION, 42, 7, 1, 2, 3)
    assert _event_bytes(ev) == _event_bytes(ev)
    assert len(_event_bytes(ev)) == 41  # 1 (op code) + 5 * 8 (uint64 fields)
