"""
Order-independent packet verification -- a narrow software-only slice of
SITREP item 7 ("Network reproducibility", not started, flagged by Amodo
as possibly needing firmware/hardware work too). This module doesn't make
the network stack itself bit-reproducible (that needs firmware-level
changes out of this repo's reach); it solves a narrower, explicitly
floated adjacent problem: verify a logical message was delivered
completely and correctly from a set of packets, regardless of the order
they arrived in or how they were fragmented -- content-addressing instead
of requiring bit-exact packet-level replay.

Each chunk is committed together with its logical index, so the Merkle
root (reusing commitment.py's BLAKE3 tree) depends on both content and
position -- a chunk delivered out of order, dropped, duplicated into the
wrong slot, or tampered with all produce a verification failure, while
the *arrival* order of packets carrying those chunks is irrelevant.
"""

from dataclasses import dataclass

from .commitment import merkle_root


def chunk_message(message: bytes, chunk_size: int = 256) -> list:
    return [message[i:i + chunk_size] for i in range(0, len(message), chunk_size)]


def _indexed_leaf(index: int, chunk: bytes) -> bytes:
    return index.to_bytes(4, "big") + chunk


@dataclass
class PacketCommitment:
    root: bytes
    n_chunks: int
    message_length: int


def commit_message(message: bytes, chunk_size: int = 256) -> PacketCommitment:
    chunks = chunk_message(message, chunk_size)
    leaves = [_indexed_leaf(i, c) for i, c in enumerate(chunks)]
    return PacketCommitment(merkle_root(leaves), len(chunks), len(message))


def reconstruct_and_verify(commitment: PacketCommitment, received_packets: dict, chunk_size: int = 256) -> bool:
    """received_packets: dict mapping index -> chunk bytes, in any order
    and with possible gaps or duplicates. Returns True only if every
    expected index is present exactly once and the reconstructed
    message's commitment matches the original."""
    if set(received_packets.keys()) != set(range(commitment.n_chunks)):
        return False
    ordered_chunks = [received_packets[i] for i in range(commitment.n_chunks)]
    reconstructed = b"".join(ordered_chunks)
    if len(reconstructed) != commitment.message_length:
        return False
    leaves = [_indexed_leaf(i, c) for i, c in enumerate(ordered_chunks)]
    return merkle_root(leaves) == commitment.root
