"""Receiver side. A state machine over datagrams with **no way to transmit**: it has no socket, and no method returns bytes
to send. Everything it learns comes from the one-way stream; nothing is acknowledged, requested or retried.

What it enforces, in order, before any symbol is believed: a manifest must parse strictly, fit the configured limits,
carry a valid Ed25519 signature from a trusted key, be on the whitelist of approved file hashes (if one is configured) and
not roll back below ``min_serial``. Every symbol must then prove membership in the signed Merkle root at its exact position.
At the end the assembled file must match the signed SHA-256, or nothing is released.
"""
from __future__ import annotations

import hashlib
from collections import Counter, OrderedDict

import numpy as np

from .format import (FormatError, Manifest, T_MANIFEST, T_SYMBOL, parse_header, parse_manifest_packet,
                     parse_symbol_packet, symbol_leaf, verify_manifest_signature)
from .merkle import verify_inclusion
from .rs import CauchyRS

# event kinds returned by Receiver.feed
MANIFEST_ACCEPTED = "manifest_accepted"
MANIFEST_DUPLICATE = "manifest_duplicate"
MANIFEST_INVALID = "manifest_rejected_invalid"
MANIFEST_SIGNATURE = "manifest_rejected_signature"
MANIFEST_WHITELIST = "manifest_rejected_whitelist"
MANIFEST_SERIAL = "manifest_rejected_serial"
MANIFEST_LIMITS = "manifest_rejected_limits"
SYMBOL_ACCEPTED = "symbol_accepted"
SYMBOL_DUPLICATE = "symbol_duplicate"
SYMBOL_BAD_PROOF = "symbol_rejected_proof"
SYMBOL_NO_SESSION = "symbol_no_session"
SYMBOL_MALFORMED = "symbol_malformed"
MALFORMED = "malformed"
COMPLETE = "complete"
FILE_HASH_MISMATCH = "file_hash_mismatch"


class _Session:
    def __init__(self, manifest: Manifest):
        self.m = manifest
        self.rs = CauchyRS(manifest.k, manifest.r)
        self.root = bytes.fromhex(manifest.root)
        self.pending: dict = {}
        self.decoded: dict = {}
        self.status = "receiving"
        self.data: bytes | None = None


class Receiver:
    def __init__(self, trusted_keys, whitelist=None, min_serial: int = 0, max_file_size: int = 1 << 40,
                 max_tree_size: int = 1 << 26, max_sessions: int = 4):
        self.trusted_keys = list(trusted_keys)
        self.whitelist = None if whitelist is None else {w.lower() for w in whitelist}
        self.min_serial, self.max_file_size, self.max_tree_size, self.max_sessions = min_serial, max_file_size, max_tree_size, max_sessions
        self.sessions: dict = {}
        self._rejected: OrderedDict = OrderedDict()
        self.stats: Counter = Counter()

    # ------------------------------------------------------------------ public
    def feed(self, datagram: bytes) -> str:
        ev = self._feed(datagram)
        self.stats[ev] += 1
        return ev

    def progress(self, manifest_id: bytes):
        s = self.sessions[manifest_id]
        return len(s.decoded), s.m.n_blocks

    def result(self, manifest_id: bytes):
        s = self.sessions.get(manifest_id)
        return s.data if s is not None and s.status == "complete" else None

    def completed_ids(self) -> list:
        return [mid for mid, s in self.sessions.items() if s.status == "complete"]

    # ------------------------------------------------------------------ internals
    def _feed(self, datagram: bytes) -> str:
        try:
            typ, mid, body = parse_header(bytes(datagram))
            if typ == T_MANIFEST:
                return self._manifest(mid, body)
            if typ == T_SYMBOL:
                return self._symbol(mid, body)
        except FormatError:
            return MALFORMED
        return MALFORMED

    def _remember_rejected(self, key: tuple) -> None:
        self._rejected[key] = True
        while len(self._rejected) > 1024:
            self._rejected.popitem(last=False)

    def _manifest(self, mid: bytes, body: bytes) -> str:
        if mid in self.sessions:
            return MANIFEST_DUPLICATE
        mp = parse_manifest_packet(mid, body)
        if hashlib.sha256(mp.manifest_bytes).digest()[:8] != mid:
            return MANIFEST_INVALID                          # header id is only a hint; never cached under an unproven id
        # Two kinds of verdict, cached under different keys. A verdict that depends on the manifest bytes alone (structure,
        # limits, whitelist, serial) is cached by id. A signature verdict depends on the (bytes, signature) pair, so it is
        # cached by both: a corrupted copy of a genuine manifest shares its id but must only ever block itself.
        bytes_key = (mid, b"")
        sig_key = (mid, hashlib.sha256(mp.signature).digest()[:8])
        if bytes_key in self._rejected or sig_key in self._rejected:
            return MANIFEST_DUPLICATE
        try:
            m = Manifest.from_bytes(mp.manifest_bytes)
        except FormatError:
            self._remember_rejected(bytes_key)
            return MANIFEST_INVALID
        if m.file_size > self.max_file_size or m.tree_size > self.max_tree_size:
            self._remember_rejected(bytes_key)
            return MANIFEST_LIMITS
        if not verify_manifest_signature(mp.manifest_bytes, mp.signature, self.trusted_keys):
            self._remember_rejected(sig_key)
            return MANIFEST_SIGNATURE
        if self.whitelist is not None and m.file_sha256 not in self.whitelist:
            self._remember_rejected(bytes_key)               # reached only with a valid signature, so the verdict is about the bytes
            return MANIFEST_WHITELIST
        if m.serial < self.min_serial:
            self._remember_rejected(bytes_key)
            return MANIFEST_SERIAL
        if len(self.sessions) >= self.max_sessions:
            return MANIFEST_LIMITS
        self.sessions[mid] = _Session(m)
        return MANIFEST_ACCEPTED

    def _symbol(self, mid: bytes, body: bytes) -> str:
        s = self.sessions.get(mid)
        if s is None:
            return SYMBOL_NO_SESSION
        if s.status != "receiving":
            return SYMBOL_DUPLICATE
        try:
            sp = parse_symbol_packet(mid, body, s.m)
        except FormatError:
            return SYMBOL_MALFORMED
        if sp.block in s.decoded or sp.index in s.pending.get(sp.block, {}):
            return SYMBOL_DUPLICATE
        leaf = symbol_leaf(sp.block, sp.index, sp.payload)
        if not verify_inclusion(leaf, sp.block * s.m.n + sp.index, s.m.tree_size, sp.proof, s.root):
            return SYMBOL_BAD_PROOF
        pend = s.pending.setdefault(sp.block, {})
        pend[sp.index] = sp.payload
        if len(pend) >= s.m.k:
            s.decoded[sp.block] = s.rs.decode(pend)
            del s.pending[sp.block]
            if len(s.decoded) == s.m.n_blocks:
                return self._finalize(s)
        return SYMBOL_ACCEPTED

    def _finalize(self, s: _Session) -> str:
        raw = b"".join(s.decoded[b].tobytes() for b in range(s.m.n_blocks))[:s.m.file_size]
        if hashlib.sha256(raw).hexdigest() != s.m.file_sha256:
            s.status = "failed"
            return FILE_HASH_MISMATCH                      # nothing is released
        s.status, s.data = "complete", raw
        return COMPLETE
