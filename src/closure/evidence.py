"""Hash-chained evidence log, Ed25519 signing, commit-reveal for the breaker's schedule."""
from __future__ import annotations

import hashlib
import json
import math
import os
import time
from pathlib import Path

import numpy as np
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


def clean(o):
    """Make an object strictly JSON-safe (non-finite floats -> None, numpy -> python)."""
    if isinstance(o, dict):
        return {str(k): clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple, set)):
        return [clean(v) for v in o]
    if isinstance(o, np.ndarray):
        return clean(o.tolist())
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (float, np.floating)):
        return float(o) if math.isfinite(float(o)) else None
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


def canonical(obj) -> bytes:
    return json.dumps(clean(obj), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def array_digest(a) -> str:
    a = np.ascontiguousarray(a)
    return sha256_hex(str(a.dtype).encode() + str(a.shape).encode() + a.tobytes())


class Chain:
    """Append-only JSONL; each entry commits to the previous hash, so edits and gaps are detectable."""

    def __init__(self, path):
        self.path = Path(path)
        self.head, self.n = "0" * 64, 0
        if self.path.exists():
            ok, n, head = Chain.verify(self.path)
            if not ok:
                raise ValueError("existing chain failed verification")
            self.n, self.head = n, head

    def append(self, record: dict) -> str:
        entry = {"i": self.n, "prev": self.head, "ts": time.time(), "record": clean(record)}
        entry["hash"] = sha256_hex(canonical({k: entry[k] for k in ("i", "prev", "ts", "record")}))
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, sort_keys=True) + "\n")
        self.head, self.n = entry["hash"], self.n + 1
        return entry["hash"]

    @staticmethod
    def verify(path):
        prev, n = "0" * 64, 0
        for line in open(path, encoding="utf-8"):
            e = json.loads(line)
            body = {k: e[k] for k in ("i", "prev", "ts", "record")}
            if e["i"] != n or e["prev"] != prev or sha256_hex(canonical(body)) != e["hash"]:
                return False, n, prev
            prev, n = e["hash"], n + 1
        return True, n, prev


class Signer:
    def __init__(self, key: Ed25519PrivateKey = None):
        self.key = key or Ed25519PrivateKey.generate()

    def public_hex(self) -> str:
        return self.key.public_key().public_bytes(serialization.Encoding.Raw,
                                                  serialization.PublicFormat.Raw).hex()

    def sign_hex(self, msg: bytes) -> str:
        return self.key.sign(msg).hex()

    def save(self, path):
        raw = self.key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
                                     serialization.NoEncryption())
        p = Path(path)
        p.write_bytes(raw)
        try:
            os.chmod(p, 0o600)
        except OSError:
            pass

    @classmethod
    def load(cls, path):
        return cls(Ed25519PrivateKey.from_private_bytes(Path(path).read_bytes()))


def verify_sig(pub_hex: str, sig_hex: str, msg: bytes) -> bool:
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub_hex)).verify(bytes.fromhex(sig_hex), msg)
        return True
    except (InvalidSignature, ValueError):
        return False


def commit(obj) -> dict:
    nonce = os.urandom(16).hex()
    return {"commitment": sha256_hex(canonical({"nonce": nonce, "obj": obj})), "nonce": nonce}


def verify_commit(obj, commitment: str, nonce: str) -> bool:
    return sha256_hex(canonical({"nonce": nonce, "obj": obj})) == commitment
