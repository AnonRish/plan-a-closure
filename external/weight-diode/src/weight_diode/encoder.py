"""Sender side: erasure-code a file, build the Merkle tree over every coded symbol, sign the manifest, emit a carousel."""
from __future__ import annotations

import hashlib

import numpy as np

from .format import (Manifest, pack_manifest_packet, pack_symbol_packet, sign_manifest, symbol_leaf)
from .merkle import MerkleTree
from .rs import CauchyRS


class Encoder:
    """Reference implementation: the whole file and its tree are held in memory (see README, limits)."""

    def __init__(self, data: bytes, signing_key, *, symbol_size: int = 1024, k: int = 32, r: int = 8,
                 serial: int = 0, label: str = "", _lie_about_hash: bool = False):
        self.rs = CauchyRS(k, r)
        self.k, self.r, self.n, self.S = k, r, k + r, symbol_size
        self.n_blocks = Manifest.blocks_for(len(data), k, symbol_size)
        buf = np.zeros(self.n_blocks * k * symbol_size, dtype=np.uint8)
        buf[:len(data)] = np.frombuffer(data, dtype=np.uint8)
        blocks = buf.reshape(self.n_blocks, k, symbol_size)
        self.coded = np.empty((self.n_blocks, self.n, symbol_size), dtype=np.uint8)
        for b in range(self.n_blocks):
            self.coded[b, :k] = blocks[b]
            if r:
                self.coded[b, k:] = self.rs.encode(blocks[b])
        leaves = [symbol_leaf(b, j, self.coded[b, j].tobytes()) for b in range(self.n_blocks) for j in range(self.n)]
        self.tree = MerkleTree(leaves)
        digest = hashlib.sha256(data if not _lie_about_hash else data + b"x").hexdigest()
        self.manifest = Manifest(serial, label, len(data), digest, symbol_size, k, r, self.n_blocks, self.tree.root.hex())
        self.manifest_bytes = self.manifest.to_bytes()
        self.signature = sign_manifest(self.manifest_bytes, signing_key)
        self.manifest_packet = pack_manifest_packet(self.manifest_bytes, self.signature)
        self.manifest_id = self.manifest.manifest_id

    def symbol_packet(self, block: int, index: int) -> bytes:
        return pack_symbol_packet(self.manifest_id, block, index, self.coded[block, index].tobytes(),
                                  self.tree.proof(block * self.n + index))

    def one_pass(self, interleave: bool = True, offset: int = 0):
        """Every coded symbol once. Interleaved order sends symbol ``j`` of every block before symbol ``j + 1``,
        so a burst of L consecutive lost packets costs each block at most ``ceil(L / n_blocks)`` symbols."""
        order = [(b, (j + offset) % self.n) for j in range(self.n) for b in range(self.n_blocks)] if interleave else \
                [(b, (j + offset) % self.n) for b in range(self.n_blocks) for j in range(self.n)]
        for b, j in order:
            yield self.symbol_packet(b, j)

    def stream(self, passes: int = 1, interleave: bool = True, manifest_every: int = 32, rotate: bool = True,
               preamble: int = 3):
        """A carousel. Each pass starts with ``preamble`` copies of the manifest (a receiver discards symbols that arrive
        before it has an accepted manifest, so losing the only copy would cost a whole burst of symbols), then the
        symbols, with the manifest repeated every ``manifest_every`` packets so a receiver can join at any time."""
        count = 0
        for p in range(passes):
            for _ in range(preamble):
                yield self.manifest_packet
            for pkt in self.one_pass(interleave, offset=(p * 37) % self.n if rotate else 0):
                yield pkt
                count += 1
                if manifest_every and count % manifest_every == 0:
                    yield self.manifest_packet

    def wire_bytes_per_pass(self) -> int:
        """Exact bytes of one pass of symbol datagrams (headers, payloads and proofs), no manifests."""
        from .format import HDR, SYM
        from .merkle import total_proof_length
        N = self.n_blocks * self.n
        return N * (HDR.size + SYM.size + self.S) + 32 * total_proof_length(N)
