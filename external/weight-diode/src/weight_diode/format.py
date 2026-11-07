"""Wire format, manifest, and signing.

Datagram header (16 bytes, big endian): ``magic "WDIO" | version u8 | type u8 | flags u8 | reserved u8 | manifest_id 8B``.
``manifest_id`` is ``SHA-256(manifest bytes)[:8]``, a routing hint only; nothing is trusted because of it.

* type 0 (manifest): ``u16 length | manifest JSON | 64-byte Ed25519 signature``
* type 1 (symbol):   ``u32 block | u16 index | payload (symbol_size bytes) | Merkle proof (32 bytes each)``
  The proof length is *derived* from (leaf position, tree size), never read from the packet.

A symbol's leaf is ``SHA-256(0x00 || u32 block || u16 index || payload)``, at tree position ``block * n + index``.
"""
from __future__ import annotations

import hashlib
import json
import math
import struct
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .merkle import leaf_hash, proof_length

MAGIC = b"WDIO"
VERSION = 1
T_MANIFEST, T_SYMBOL = 0, 1
HDR = struct.Struct(">4sBBBB8s")
SYM = struct.Struct(">IH")
SIG_DOMAIN = b"weight-diode/v1/manifest\x00"
MAX_MANIFEST = 1200


class FormatError(ValueError):
    pass


def symbol_leaf(block: int, index: int, payload: bytes) -> bytes:
    return leaf_hash(SYM.pack(block, index) + payload)


@dataclass(frozen=True)
class Manifest:
    serial: int
    label: str
    file_size: int
    file_sha256: str
    symbol_size: int
    k: int
    r: int
    n_blocks: int
    root: str
    version: int = 1

    @property
    def n(self) -> int:
        return self.k + self.r

    @property
    def tree_size(self) -> int:
        return self.n_blocks * self.n

    def to_bytes(self) -> bytes:
        d = {"v": self.version, "serial": self.serial, "label": self.label, "file_size": self.file_size,
             "file_sha256": self.file_sha256, "symbol_size": self.symbol_size, "k": self.k, "r": self.r,
             "n_blocks": self.n_blocks, "root": self.root}
        return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()

    @property
    def manifest_id(self) -> bytes:
        return hashlib.sha256(self.to_bytes()).digest()[:8]

    @staticmethod
    def blocks_for(file_size: int, k: int, symbol_size: int) -> int:
        return max(1, math.ceil(file_size / (k * symbol_size)))

    @classmethod
    def from_bytes(cls, b: bytes) -> "Manifest":
        try:
            d = json.loads(b.decode("utf-8"))
        except Exception as e:
            raise FormatError(f"manifest is not valid JSON: {e}")
        keys = {"v", "serial", "label", "file_size", "file_sha256", "symbol_size", "k", "r", "n_blocks", "root"}
        if not isinstance(d, dict) or set(d) != keys:
            raise FormatError("manifest has missing or unexpected fields")
        ints = ("v", "serial", "file_size", "symbol_size", "k", "r", "n_blocks")
        for f in ints:
            if type(d[f]) is not int:
                raise FormatError(f"{f} must be an integer")
        if d["v"] != 1:
            raise FormatError("unsupported manifest version")
        if not (isinstance(d["label"], str) and len(d["label"]) <= 64 and d["label"].isprintable()):
            raise FormatError("bad label")
        for f in ("file_sha256", "root"):
            if not (isinstance(d[f], str) and len(d[f]) == 64 and all(c in "0123456789abcdef" for c in d[f])):
                raise FormatError(f"{f} must be 64 lowercase hex characters")
        if d["serial"] < 0 or d["file_size"] < 0:
            raise FormatError("negative serial or size")
        if not (1 <= d["symbol_size"] <= 60_000):
            raise FormatError("symbol_size out of range")
        if not (1 <= d["k"] and 0 <= d["r"] and d["k"] + d["r"] <= 256):
            raise FormatError("k, r out of range")
        if d["n_blocks"] != cls.blocks_for(d["file_size"], d["k"], d["symbol_size"]):
            raise FormatError("n_blocks inconsistent with file_size")
        return cls(d["serial"], d["label"], d["file_size"], d["file_sha256"], d["symbol_size"], d["k"], d["r"],
                   d["n_blocks"], d["root"], d["v"])


def sign_manifest(m_bytes: bytes, key: Ed25519PrivateKey) -> bytes:
    return key.sign(SIG_DOMAIN + m_bytes)


def verify_manifest_signature(m_bytes: bytes, sig: bytes, keys) -> bool:
    for k in keys:
        try:
            k.verify(sig, SIG_DOMAIN + m_bytes)
            return True
        except (InvalidSignature, Exception):
            continue
    return False


def public_key_from_bytes(raw: bytes) -> Ed25519PublicKey:
    return Ed25519PublicKey.from_public_bytes(raw)


def pack_manifest_packet(m_bytes: bytes, sig: bytes) -> bytes:
    if len(m_bytes) > MAX_MANIFEST or len(sig) != 64:
        raise FormatError("manifest too large or bad signature length")
    mid = hashlib.sha256(m_bytes).digest()[:8]
    return HDR.pack(MAGIC, VERSION, T_MANIFEST, 0, 0, mid) + struct.pack(">H", len(m_bytes)) + m_bytes + sig


def pack_symbol_packet(manifest_id: bytes, block: int, index: int, payload: bytes, proof: list) -> bytes:
    return HDR.pack(MAGIC, VERSION, T_SYMBOL, 0, 0, manifest_id) + SYM.pack(block, index) + payload + b"".join(proof)


@dataclass(frozen=True)
class ManifestPacket:
    manifest_id: bytes
    manifest_bytes: bytes
    signature: bytes


@dataclass(frozen=True)
class SymbolPacket:
    manifest_id: bytes
    block: int
    index: int
    payload: bytes
    proof: list


def parse_header(datagram: bytes):
    if len(datagram) < HDR.size:
        raise FormatError("short datagram")
    magic, ver, typ, _flags, _res, mid = HDR.unpack_from(datagram)
    if magic != MAGIC or ver != VERSION:
        raise FormatError("bad magic or version")
    return typ, mid, datagram[HDR.size:]


def parse_manifest_packet(mid: bytes, body: bytes) -> ManifestPacket:
    if len(body) < 2:
        raise FormatError("short manifest packet")
    (ln,) = struct.unpack_from(">H", body)
    if ln > MAX_MANIFEST or len(body) != 2 + ln + 64:
        raise FormatError("manifest length mismatch")
    return ManifestPacket(mid, body[2:2 + ln], body[2 + ln:])


def parse_symbol_packet(mid: bytes, body: bytes, manifest: Manifest) -> SymbolPacket:
    if len(body) < SYM.size:
        raise FormatError("short symbol packet")
    block, index = SYM.unpack_from(body)
    if block >= manifest.n_blocks or index >= manifest.n:
        raise FormatError("symbol position out of range")
    plen = proof_length(block * manifest.n + index, manifest.tree_size)
    if len(body) != SYM.size + manifest.symbol_size + 32 * plen:
        raise FormatError("symbol packet length mismatch")
    payload = body[SYM.size:SYM.size + manifest.symbol_size]
    rest = body[SYM.size + manifest.symbol_size:]
    return SymbolPacket(mid, block, index, payload, [rest[i:i + 32] for i in range(0, len(rest), 32)])
