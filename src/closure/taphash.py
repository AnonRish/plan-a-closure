"""Hashing tap: commit to the traffic instead of copying it (Plan A SITREP, "new tap types and bandwidth limits").

Following Cankaya's system overview (MIRI Technical Governance Team, June 2026), the tap hashes payload bytes over
fixed-size groups, blind to message boundaries, and emits only the digests and a Merkle root. The prover keeps its own
copy of the traffic and recomputes the same digests; a mismatch locates tampering to a group. After the commitment the
verifier draws random groups from a nonce it reveals only then; the prover answers with each group's bytes and Merkle
path, and the recomputation server re-runs the work those bytes carry. The tap's output falls from a full copy to
32 bytes per group.

Software protocol only. A hashing tap is a device (an FPGA or SmartNIC behind a passive optical split); this module is the
logic such a device and its verifier would run, tested on pcap captures. Each leaf binds its group index, and an unpaired
node is carried up the tree rather than duplicated, so groups cannot be reordered or the tree padded unseen.
"""
from __future__ import annotations

import hashlib
import hmac
import math

from .traffic import iter_pcap

DIGEST_BYTES = 32


def _leaf(index: int, data: bytes) -> bytes:
    return hashlib.sha256(b"closure-taphash-leaf" + int(index).to_bytes(8, "big") + bytes(data)).digest()


def _node(a: bytes, b: bytes) -> bytes:
    return hashlib.sha256(b"closure-taphash-node" + a + b).digest()


def group_digests(stream, group_bytes: int = 65536) -> list:
    """Digests of consecutive fixed-size groups of a byte stream (bytes, or an iterable of byte chunks); the last group may
    be short."""
    if group_bytes <= 0:
        raise ValueError("group_bytes must be positive")
    out, buf = [], bytearray()
    for c in ([stream] if isinstance(stream, (bytes, bytearray, memoryview)) else stream):
        buf += bytes(c)
        while len(buf) >= group_bytes:
            out.append(_leaf(len(out), bytes(buf[:group_bytes])))
            del buf[:group_bytes]
    if buf:
        out.append(_leaf(len(out), bytes(buf)))
    return out


def _levels(leaves) -> list:
    levels = [list(leaves)]
    while len(levels[-1]) > 1:
        cur = levels[-1]
        nxt = [_node(cur[i], cur[i + 1]) for i in range(0, len(cur) - 1, 2)]
        if len(cur) % 2:
            nxt.append(cur[-1])                       # carried up, never duplicated
        levels.append(nxt)
    return levels


def merkle_root(leaves) -> bytes:
    leaves = list(leaves)
    return _levels(leaves)[-1][0] if leaves else hashlib.sha256(b"closure-taphash-empty").digest()


def merkle_proof(leaves, i: int) -> list:
    """Sibling path from leaf i to the root: a list of (sibling digest, sibling_is_left)."""
    if not 0 <= i < len(leaves):
        raise IndexError(i)
    path = []
    for cur in _levels(leaves)[:-1]:
        sib = i ^ 1
        if sib < len(cur):
            path.append((cur[sib], sib < i))
        i //= 2
    return path


def verify_proof(index: int, data: bytes, proof, root: bytes) -> bool:
    """Does group `index`, holding `data`, belong to the committed root?"""
    h = _leaf(index, data)
    for sib, sib_left in proof:
        h = _node(sib, h) if sib_left else _node(h, sib)
    return hmac.compare_digest(h, root)


def flow_name(p) -> str:
    """One direction of a flow: proto|src:sport>dst:dport."""
    return f"{p.proto}|{p.src}:{p.sport}>{p.dst}:{p.dport}"


def commit_pcap(src, group_bytes: int = 65536) -> dict:
    """Stream a capture once and commit to each direction's payload bytes: {flow: {digests, root, payload_bytes,
    declared_bytes, group_bytes}}. declared > payload means the snaplen cut payloads: capture with `tcpdump -s 0`."""
    state = {}
    for p, pay in iter_pcap(src, with_payload=True):
        st = state.setdefault(flow_name(p), {"buf": bytearray(), "digests": [], "n": 0, "declared": 0})
        st["buf"] += pay
        st["n"] += len(pay)
        st["declared"] += p.payload_len
        while len(st["buf"]) >= group_bytes:
            st["digests"].append(_leaf(len(st["digests"]), bytes(st["buf"][:group_bytes])))
            del st["buf"][:group_bytes]
    out = {}
    for k, st in state.items():
        if st["buf"]:
            st["digests"].append(_leaf(len(st["digests"]), bytes(st["buf"])))
        out[k] = {"digests": st["digests"], "root": merkle_root(st["digests"]), "payload_bytes": st["n"],
                  "declared_bytes": st["declared"], "group_bytes": group_bytes}
    return out


def mismatched_groups(tap_digests, prover_digests) -> list:
    """Group indices where the tap's and the prover's digests disagree, including groups only one side has."""
    n = max(len(tap_digests), len(prover_digests))
    return [i for i in range(n) if i >= len(tap_digests) or i >= len(prover_digests)
            or not hmac.compare_digest(tap_digests[i], prover_digests[i])]


def challenge_indices(nonce: bytes, root: bytes, n_groups: int, k: int) -> list:
    """k distinct groups derived from a verifier nonce revealed after the commitment, so neither side picks them."""
    k, out, ctr = min(int(k), int(n_groups)), [], 0
    while len(out) < k:
        h = hashlib.sha256(b"closure-taphash-challenge" + nonce + root + ctr.to_bytes(8, "big")).digest()
        i = int.from_bytes(h[:8], "big") % n_groups
        if i not in out:
            out.append(i)
        ctr += 1
    return out


def detection_probability(n_groups: int, n_bad: int, k: int) -> float:
    """P(at least one of k distinct random groups is among n_bad tampered ones) = 1 - C(n - b, k) / C(n, k)."""
    n, b, k = int(n_groups), int(n_bad), min(int(k), int(n_groups))
    if b <= 0 or k <= 0:
        return 0.0
    if k > n - b:
        return 1.0
    miss = 1.0
    for j in range(k):
        miss *= (n - b - j) / (n - j)
    return 1.0 - miss


def samples_needed(frac_bad: float, confidence: float) -> int:
    """Challenged groups that catch tampering of a fraction frac_bad with the given confidence (sampling with replacement,
    so an upper bound on what sampling without replacement needs)."""
    if not 0 < frac_bad < 1 or not 0 < confidence < 1:
        raise ValueError("frac_bad and confidence must lie in (0, 1)")
    return math.ceil(math.log(1 - confidence) / math.log(1 - frac_bad))


def bandwidth_reduction(group_bytes: int) -> float:
    """Captured bytes per byte the tap must emit."""
    return group_bytes / DIGEST_BYTES
