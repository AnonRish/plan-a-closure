"""Content-addressed storage.

Evidence identity (its digest) is separate from where its bytes happen to
live. A receipt references a digest, not a database row or a file path --
so an Evidence object can move between storage backends, or be archived
and retrieved years later by a different system, without invalidating
anything that referenced it. See docs/architecture.md, "Evidence
Portability" -- that claim is only real if something in the repo actually
enforces it; this module is that something.

MATURITY: EXPERIMENTAL. Real, tested, filesystem-backed persistence that
verifies integrity on every read -- re-hashes the stored bytes and compares
against the digest used as the storage key, raising IntegrityError on
mismatch rather than silently returning corrupted or tampered data (see
tests/conformance/test_content_addressed.py's corruption test). This
replaces Phase 1's in-memory-dict MOCK for evidence storage. It is NOT the
PostgreSQL + object storage design docs/architecture.md describes for a
real deployment -- see docs/protocol-roadmap.md.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from frontier_verify.core.canonical import canonicalize
from frontier_verify.core.canonical import digest as compute_digest


class IntegrityError(Exception):
    """Stored bytes don't hash to the digest used as their own key -- the
    storage layer itself has been tampered with or corrupted."""


class ContentAddressedStore:
    def __init__(self, base_dir: os.PathLike[str] | str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, digest: str) -> Path:
        # Security review finding (Phase 3): no current code path passes
        # an attacker-controlled string directly here (digests always
        # flow through an internal index populated by this project's own
        # put() calls first -- confirmed by inspection of every caller in
        # frontier_verify/api/main.py). Validating the shape anyway is
        # cheap defense-in-depth against a future caller that DOES pass
        # untrusted input directly, and turns a potential path-traversal
        # bug into an immediate, loud ValueError instead.
        if len(digest) != 64 or not all(c in "0123456789abcdef" for c in digest):
            raise ValueError(f"not a valid sha256 hex digest: {digest!r}")
        # Two-level fan-out (first 2 hex chars) so no single directory
        # listing ever has to hold tens of thousands of entries -- the
        # same layout git and most CAS systems use, for the same reason.
        shard = self.base_dir / digest[:2]
        shard.mkdir(exist_ok=True)
        return shard / f"{digest}.json"

    def put(self, obj: dict[str, Any]) -> str:
        """Canonicalize obj, persist it, return its digest -- the digest
        IS the object's identity and its storage key."""
        raw = canonicalize(obj)
        digest = compute_digest(obj)
        self._path_for(digest).write_bytes(raw)
        return digest

    def get(self, digest: str) -> dict[str, Any]:
        path = self._path_for(digest)
        if not path.exists():
            raise KeyError(f"no object stored under digest {digest}")
        raw = path.read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        if actual != digest:
            raise IntegrityError(
                f"object stored under {digest} now hashes to {actual} -- "
                f"storage has been tampered with or corrupted since it was "
                f"written"
            )
        return json.loads(raw)

    def exists(self, digest: str) -> bool:
        return self._path_for(digest).exists()
