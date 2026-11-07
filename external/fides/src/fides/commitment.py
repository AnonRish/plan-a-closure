"""
BLAKE3-based Merkle commitment over an ExecutionEpoch's kernel events --
this module is the actual "packet-hashing tap" referenced in the AI 2040
verification SITREP (https://amododesign.com/ai-verification/plan-a-sitrep/),
listed there under "New tap types and bandwidth limits" as NOT STARTED:

    "Sampling or packet-hashing taps, and ways to cut the capture
    bandwidth the recomputation side needs."

The idea: instead of mirroring 100% of a datacenter's raw traffic to an
external recomputation server (the "Recomputation servers (capture)"
workstream, which the SITREP grades active-but-bandwidth-hungry), a tap
can commit locally to every packet immediately and cheaply, and only
transmit full raw packet contents for the small sampled subset an auditor
actually asks for. BLAKE3 is used because:

  1. It's a tree hash by construction, so Merkle proofs over event chunks
     fall out of the hash function almost for free.
  2. It saturates modern SIMD/AES-NI-class hardware throughput, which
     matters because the committing agent has to keep up with live
     traffic on the same device that's serving production workloads.

This is the local-commitment half of the scheme; attestation.py adds the
device signature and spot-check reveal/audit flow on top.
"""

import struct
from dataclasses import dataclass

import blake3

from .trace import KernelEvent

_OP_CODES = {
    "forward_matmul": 0,
    "forward_attention": 1,
    "backward_matmul": 2,
    "backward_attention": 3,
    "optimizer_update": 4,
    "allreduce_grad": 5,
    "allreduce_activation": 6,
    "kv_cache_write": 7,
    "kv_cache_reset": 8,
}
_OP_CODE_TO_NAME = {v: k for k, v in _OP_CODES.items()}

_EVENT_STRUCT = "<BQQQQQ"  # op_code, timestamp_ns, duration_ns, bytes_read, bytes_written, flops


def _event_bytes(event: KernelEvent) -> bytes:
    """Deterministic serialization of a KernelEvent. Deliberately avoids
    Python's built-in hash() for the op code, since str/enum hashing is
    randomized per-process (PYTHONHASHSEED) and would make commitments
    non-reproducible across runs -- exactly the kind of bug a real
    verifier and prover would disagree about."""
    op_code = _OP_CODES[event.op.value]
    return struct.pack(
        _EVENT_STRUCT,
        op_code,
        event.timestamp_ns,
        event.duration_ns,
        event.bytes_read,
        event.bytes_written,
        event.flops,
    )


def decode_event(data: bytes):
    op_code, ts, dur, br, bw, fl = struct.unpack(_EVENT_STRUCT, data)
    return _OP_CODE_TO_NAME[op_code], ts, dur, br, bw, fl


def _hash_leaf(data: bytes) -> bytes:
    return blake3.blake3(b"\x00" + data).digest()


def _hash_node(left: bytes, right: bytes) -> bytes:
    return blake3.blake3(b"\x01" + left + right).digest()


def _build_levels(leaves: list) -> list:
    level = [_hash_leaf(l) for l in leaves]
    levels = [level]
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            if i + 1 < len(level):
                nxt.append(_hash_node(level[i], level[i + 1]))
            else:
                nxt.append(_hash_node(level[i], level[i]))  # duplicate the odd one out
        levels.append(nxt)
        level = nxt
    return levels


def merkle_root(leaves: list) -> bytes:
    if not leaves:
        return blake3.blake3(b"").digest()
    return _build_levels(leaves)[-1][0]


@dataclass
class MerkleProof:
    leaf_index: int
    siblings: list  # list of (hash: bytes, sibling_is_right: bool)


def prove(leaves: list, index: int) -> MerkleProof:
    levels = _build_levels(leaves)
    siblings = []
    idx = index
    for level in levels[:-1]:
        if idx % 2 == 0:
            sib_idx = idx + 1 if idx + 1 < len(level) else idx
            siblings.append((level[sib_idx], True))
        else:
            siblings.append((level[idx - 1], False))
        idx //= 2
    return MerkleProof(index, siblings)


def verify(leaf_data: bytes, proof: MerkleProof, root: bytes) -> bool:
    h = _hash_leaf(leaf_data)
    for sib, is_right in proof.siblings:
        h = _hash_node(h, sib) if is_right else _hash_node(sib, h)
    return h == root
