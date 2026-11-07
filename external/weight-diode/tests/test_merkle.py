import hashlib
import os
import random

import pytest
from hypothesis import given, settings, strategies as st

from weight_diode.merkle import (EMPTY_ROOT, MerkleTree, leaf_hash, mth_recursive, node_hash, proof_length,
                                 total_proof_length, max_proof_length, verify_inclusion)

# RFC 6962 / Certificate Transparency test roots for the leaves below, sizes 0..8. These hex strings were written down from
# memory *before* the implementation was run against them (see VERIFICATION_LOG.md); all nine matched.
CT_LEAVES = [b"", b"\x00", b"\x10", b"\x20\x21", b"\x30\x31", b"\x40\x41\x42\x43", bytes(range(0x50, 0x58)), bytes(range(0x60, 0x70))]
CT_ROOTS = {
    0: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    1: "6e340b9cffb37a989ca544e6bb780a2c78901d3fb33738768511a30617afa01d",
    2: "fac54203e7cc696cf0dfcb42c92a1d9dbaf70ad9e621f4bd8d98662f00e3c125",
    3: "aeb6bcfe274b70a14fb067a5e5578264db0fa9b51af5e0ba159158f329e06e77",
    4: "d37ee418976dd95753c1c73862b9398fa2a2cf9b4ff0fdfe8b30cd95209614b7",
    5: "4e3bbb1f7b478dcfe71fb631631519a3bca12c9aefca1612bfce4c13a86264d4",
    6: "76e67dadbcdf1e10e1b74ddc608abd2f98dfb16fbce75277b5232a127f2087ef",
    7: "ddb89be403809e325750d3d263cd78929c2942b7942a34b77e122c9594a74c8c",
    8: "5dc9da79a70659a9ad559cb701ded9a2ab9d823aad2f4960cfe370eff4604328",
}


def _tree(entries):
    return MerkleTree([leaf_hash(e) for e in entries])


def test_certificate_transparency_known_answer_roots():
    assert EMPTY_ROOT.hex() == CT_ROOTS[0] == hashlib.sha256(b"").hexdigest()
    for n in range(1, 9):
        assert _tree(CT_LEAVES[:n]).root.hex() == CT_ROOTS[n], n
        assert mth_recursive([leaf_hash(e) for e in CT_LEAVES[:n]]).hex() == CT_ROOTS[n], n


def test_bottom_up_construction_equals_the_recursive_rfc_definition_for_every_size_to_200():
    rng = random.Random(0)
    for n in range(1, 201):
        leaves = [hashlib.sha256(rng.randbytes(8)).digest() for _ in range(n)]
        assert MerkleTree(leaves).root == mth_recursive(leaves), n


def test_every_inclusion_proof_verifies_and_has_the_derived_length():
    for n in range(1, 71):
        entries = [bytes([i % 251]) * (i % 5) + i.to_bytes(2, "big") for i in range(n)]
        t = _tree(entries)
        for i in range(n):
            p = t.proof(i)
            assert len(p) == proof_length(i, n)
            assert verify_inclusion(leaf_hash(entries[i]), i, n, p, t.root), (n, i)


def test_any_single_bit_flip_in_any_proof_element_is_rejected():
    entries = [os.urandom(9) for _ in range(29)]
    t = _tree(entries)
    rng = random.Random(1)
    for i in range(29):
        p = t.proof(i)
        for j in range(len(p)):
            for _ in range(6):
                bad = bytearray(p[j])
                bad[rng.randrange(32)] ^= 1 << rng.randrange(8)
                q = list(p)
                q[j] = bytes(bad)
                assert not verify_inclusion(leaf_hash(entries[i]), i, 29, q, t.root)


def test_wrong_leaf_index_size_length_or_root_is_rejected():
    entries = [bytes([i]) for i in range(13)]
    t = _tree(entries)
    lf, p = leaf_hash(entries[5]), t.proof(5)
    assert verify_inclusion(lf, 5, 13, p, t.root)
    assert not verify_inclusion(leaf_hash(b"other"), 5, 13, p, t.root)         # wrong leaf
    assert not verify_inclusion(lf, 4, 13, p, t.root)                          # neighbouring index
    assert not verify_inclusion(lf, 5, 8, p, t.root)                           # size with a different path length
    assert not verify_inclusion(lf, 5, 30, p, t.root)
    assert not verify_inclusion(lf, 5, 13, p[:-1], t.root)                     # truncated
    assert not verify_inclusion(lf, 5, 13, p + [p[0]], t.root)                 # extended
    assert not verify_inclusion(lf, 5, 13, p, _tree(entries[:12]).root)        # different tree
    assert not verify_inclusion(lf, 13, 13, p, t.root) and not verify_inclusion(lf, -1, 13, p, t.root)


def test_verify_never_raises_on_garbage():
    for args in [(b"x", 0, 1, [b"y"], b"z"), (b"x", 0, 0, [], b""), (b"x", 1 << 70, 1 << 71, [b"a"] * 3, b"r"),
                 (b"x", 0, 5, [None, 5], b"r"), (None, "a", "b", 3, None)]:
        assert verify_inclusion(*args) is False


def test_domain_separation_a_root_cannot_pose_as_a_leaf():
    a, b = leaf_hash(b"a"), leaf_hash(b"b")
    assert leaf_hash(a + b) != node_hash(a, b)                                  # second-preimage attack on tree shape fails
    t2 = MerkleTree([a, b])
    assert not verify_inclusion(leaf_hash(a + b), 0, 1, [], t2.root)


def test_empty_tree_is_refused_and_single_leaf_root_is_the_leaf():
    with pytest.raises(ValueError):
        MerkleTree([])
    t = _tree([b"only"])
    assert t.root == leaf_hash(b"only") and t.proof(0) == [] and proof_length(0, 1) == 0
    with pytest.raises(ValueError):
        t.proof(1)
    with pytest.raises(ValueError):
        proof_length(3, 3)


@settings(max_examples=100, deadline=None)
@given(n=st.integers(1, 300), seed=st.integers(0, 10**6))
def test_random_trees_property(n, seed):
    rng = random.Random(seed)
    entries = [rng.randbytes(rng.randint(0, 30)) for _ in range(n)]
    t = _tree(entries)
    i = rng.randrange(n)
    assert verify_inclusion(leaf_hash(entries[i]), i, n, t.proof(i), t.root)
    j = (i + 1 + rng.randrange(n - 1)) % n if n > 1 else i
    if j != i and entries[j] != entries[i]:
        assert not verify_inclusion(leaf_hash(entries[i]), j, n, t.proof(i), t.root)


def test_agrees_with_an_independent_third_party_implementation():
    pm = pytest.importorskip("pymerkle")
    rng = random.Random(3)
    checked = 0
    for n in list(range(1, 100)) + [255, 256, 257, 511]:
        entries = [rng.randbytes(rng.randint(0, 20)) for _ in range(n)]
        theirs = pm.InmemoryTree(algorithm="sha256")
        for e in entries:
            theirs.append_entry(e)
        mine = _tree(entries)
        assert theirs.get_state() == mine.root, n
        for i in (range(n) if n < 100 else rng.sample(range(n), 10)):
            p = theirs.prove_inclusion(i + 1, n)               # pymerkle counts leaves from 1; its path starts with the leaf
            assert list(p.path)[0] == leaf_hash(entries[i])
            assert list(p.path)[1:] == mine.proof(i), (n, i)
            checked += 1
    assert checked == sum(range(1, 100)) + 4 * 10       # 4,950 exhaustive + 40 sampled


def test_a_proof_does_not_authenticate_the_tree_size_so_the_protocol_takes_it_from_the_signed_manifest():
    """RFC 6962 audit paths only fix the path *shape*. A proof from a 13-leaf tree verifies under every claimed size whose
    shape for that index is identical (9 to 16 here). Harmless for weight-diode because the wire format carries no size
    field: the receiver uses ``manifest.tree_size``, which the signature covers. This test documents the dependency."""
    entries = [bytes([i]) for i in range(13)]
    t = _tree(entries)
    p, lf = t.proof(5), leaf_hash(entries[5])
    accepted = [n for n in range(6, 40) if verify_inclusion(lf, 5, n, p, t.root)]
    assert accepted == list(range(9, 17))
    assert all(proof_length(5, n) == len(p) for n in accepted)


def test_total_proof_length_closed_form_equals_the_brute_force_sum():
    for n in range(1, 600):
        assert total_proof_length(n) == sum(proof_length(i, n) for i in range(n)), n
    for n in (1023, 1024, 1025, 4097, 50_000, 65_537):
        assert total_proof_length(n) == sum(proof_length(i, n) for i in range(n)), n
    assert total_proof_length(2 ** 30) == 30 * 2 ** 30                                   # perfect tree: every leaf at depth 30
    with pytest.raises(ValueError):
        total_proof_length(0)


@settings(max_examples=200, deadline=None)
@given(n=st.integers(1, 20_000))
def test_total_proof_length_property(n):
    assert total_proof_length(n) == sum(proof_length(i, n) for i in range(0, n))


def test_total_proof_length_is_fast_at_terabyte_scale():
    import time
    t0 = time.perf_counter()
    v = total_proof_length(1_220_703_125 * 1)                                           # about 1 TB at 1 KiB symbols with k=32, r=8
    assert time.perf_counter() - t0 < 0.01 and v > 1_220_703_125 * 30


def test_max_proof_length_is_the_depth_of_the_deepest_leaf():
    for n in range(1, 700):
        assert max_proof_length(n) == max(proof_length(i, n) for i in range(n)), n
    assert max_proof_length(1) == 0 and max_proof_length(2) == 1 and max_proof_length(1 << 28) == 28
    with pytest.raises(ValueError):
        max_proof_length(0)
