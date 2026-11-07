"""RFC 6962 / RFC 9162 Merkle tree over SHA-256 (leaf prefix 0x00, node prefix 0x01), with inclusion proofs.

Built bottom-up: adjacent nodes are paired and an unpaired last node is carried up unchanged. This is the tree
RFC 6962 defines recursively (split at the largest power of two below ``n``); the tests check the two agree for
every size up to 200 and reproduce the published Certificate Transparency test roots.
"""
from __future__ import annotations

import hashlib


def _h(b: bytes) -> bytes:
    return hashlib.sha256(b).digest()


def leaf_hash(data: bytes) -> bytes:
    return _h(b"\x00" + data)


def node_hash(left: bytes, right: bytes) -> bytes:
    return _h(b"\x01" + left + right)


EMPTY_ROOT = _h(b"")


def mth_recursive(leaf_hashes: list) -> bytes:
    """The RFC 6962 definition, kept only as a test oracle."""
    n = len(leaf_hashes)
    if n == 0:
        return EMPTY_ROOT
    if n == 1:
        return leaf_hashes[0]
    k = 1
    while k * 2 < n:
        k *= 2
    return node_hash(mth_recursive(leaf_hashes[:k]), mth_recursive(leaf_hashes[k:]))


def _path_shape(index: int, size: int):
    """Yield ('L'|'R') for each proof element needed by leaf ``index`` in a tree of ``size`` leaves.

    'L': the sibling is on the left; 'R': on the right. Levels where the node is carried up unpaired yield nothing.
    """
    while size > 1:
        if index % 2 == 1:
            yield "L"
        elif index + 1 < size:
            yield "R"
        index //= 2
        size = (size + 1) // 2


def proof_length(index: int, size: int) -> int:
    if not (0 <= index < size):
        raise ValueError("index out of range")
    return sum(1 for _ in _path_shape(index, size))


def max_proof_length(size: int) -> int:
    """Longest proof in a ``size``-leaf tree: the depth of the deepest leaf, ``ceil(log2 size)``."""
    if size < 1:
        raise ValueError("size must be >= 1")
    return (size - 1).bit_length()


def total_proof_length(size: int) -> int:
    """Sum of ``proof_length(i, size)`` over every leaf, in O(log size).

    A leaf's proof has one element per ancestor split, so the total is the external path length ``E(n)`` of the RFC 6962
    tree: ``E(1) = 0`` and ``E(n) = E(k) + E(n - k) + n`` with ``k`` the largest power of two below ``n``, where a perfect
    subtree of ``2^m`` leaves contributes ``m * 2^m``. (A linear scan over 1.2 billion leaves, which is what a 1 TB file
    needs, never finishes; see VERIFICATION_LOG.md.)
    """
    if size < 1:
        raise ValueError("size must be >= 1")
    total, n = 0, size
    while n > 1:
        k = 1 << ((n - 1).bit_length() - 1)              # largest power of two strictly below n
        total += k * (k.bit_length() - 1) + n            # perfect left subtree + one sibling element for each of n leaves
        n -= k
    return total


class MerkleTree:
    def __init__(self, leaf_hashes: list):
        if not leaf_hashes:
            raise ValueError("empty tree")
        self.levels = [list(leaf_hashes)]
        while len(self.levels[-1]) > 1:
            cur, nxt = self.levels[-1], []
            for i in range(0, len(cur) - 1, 2):
                nxt.append(node_hash(cur[i], cur[i + 1]))
            if len(cur) % 2:
                nxt.append(cur[-1])
            self.levels.append(nxt)
        self.size = len(leaf_hashes)
        self.root = self.levels[-1][0]

    def proof(self, index: int) -> list:
        if not (0 <= index < self.size):
            raise ValueError("index out of range")
        out, i = [], index
        for level in self.levels[:-1]:
            if i % 2 == 1:
                out.append(level[i - 1])
            elif i + 1 < len(level):
                out.append(level[i + 1])
            i //= 2
        return out


def verify_inclusion(leaf: bytes, index: int, size: int, proof: list, root: bytes) -> bool:
    """True iff ``proof`` shows ``leaf`` at ``index`` of a ``size``-leaf tree with the given ``root``. Never raises."""
    try:
        if not (0 <= index < size) or len(proof) != proof_length(index, size):
            return False
        h, it = leaf, iter(proof)
        for side in _path_shape(index, size):
            sib = next(it)
            h = node_hash(sib, h) if side == "L" else node_hash(h, sib)
        return h == root
    except Exception:
        return False
