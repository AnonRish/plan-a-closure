"""Local filesystem key storage.

MATURITY: EXPERIMENTAL. Real key generation, storage, lookup, rotation,
AND revocation -- not a placeholder. But "the private key is a plaintext
hex file on disk" is exactly the risk profile a KMS/HSM exists to remove
(see kms_provider.py). Use this for local development and CI, not a real
verifier deployment. See docs/protocol/key-management.md.

Layout under `base_dir`:
    <key_id>.sk.hex     -- private key, hex-encoded raw bytes
    <key_id>.pk.hex     -- public key, hex-encoded raw bytes
    <key_id>.revoked    -- present iff key_id has been revoked; contents
                           are "<reason>" for a human/audit trail
    CURRENT             -- plain text file containing the current key_id
"""
from __future__ import annotations

import os
import time
import uuid
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from frontier_verify.keys.provider import KeyProvider, KeyStatus
from frontier_verify.receipts.signing import (
    generate_keypair,
    private_key_from_hex,
    private_key_to_hex,
    public_key_from_hex,
    public_key_to_hex,
)


def _new_key_id() -> str:
    return f"fv-{int(time.time())}-{uuid.uuid4().hex[:8]}"


class RevokedKeyError(Exception):
    """Raised by get_signing_key() when asked (implicitly, via the
    current key) to sign with a key that has been revoked. A revoked key
    must never sign anything new -- that's the entire point of revoking
    it -- even though its OLD signatures must remain checkable (see
    get_public_key(), unaffected by revocation)."""


class LocalFileKeyProvider(KeyProvider):
    def __init__(self, base_dir: os.PathLike | str):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        if not self._current_file.exists():
            self.rotate()

    @property
    def _current_file(self) -> Path:
        return self.base_dir / "CURRENT"

    def _revoked_file(self, key_id: str) -> Path:
        return self.base_dir / f"{key_id}.revoked"

    def current_key_id(self) -> str:
        return self._current_file.read_text().strip()

    def get_signing_key(self, key_id: str | None = None) -> tuple[str, Ed25519PrivateKey]:
        resolved_id = key_id or self.current_key_id()
        if self.key_status(resolved_id) == KeyStatus.REVOKED:
            raise RevokedKeyError(
                f"key_id={resolved_id!r} is REVOKED and must not sign anything new. "
                f"If this is the current key, rotate() to a fresh one first."
            )
        sk_path = self.base_dir / f"{resolved_id}.sk.hex"
        if not sk_path.exists():
            raise KeyError(f"no private key on file for key_id={resolved_id!r}")
        return resolved_id, private_key_from_hex(sk_path.read_text().strip())

    def get_public_key(self, key_id: str) -> Ed25519PublicKey:
        """Deliberately UNAFFECTED by revocation status -- a verifier
        checking an old receipt against a since-revoked key still needs
        the public key to determine whether the signature was genuine at
        all. Revocation changes whether it's TRUSTED, not whether it's
        checkable. See key_status() and
        docs/protocol/key-management.md."""
        pk_path = self.base_dir / f"{key_id}.pk.hex"
        if not pk_path.exists():
            raise KeyError(f"no public key on file for key_id={key_id!r}")
        return public_key_from_hex(pk_path.read_text().strip())

    def rotate(self) -> str:
        key_id = _new_key_id()
        sk, pk = generate_keypair()
        sk_path = self.base_dir / f"{key_id}.sk.hex"
        sk_path.write_text(private_key_to_hex(sk))
        # Security review finding (Phase 3): write_text() alone leaves the
        # private key world-readable under the default umask (-rw-r--r--).
        # "Plaintext file on disk" is already a documented limitation of
        # this provider (see module docstring), but world-readable is
        # strictly worse than necessary even for a local-development store.
        os.chmod(sk_path, 0o600)
        (self.base_dir / f"{key_id}.pk.hex").write_text(public_key_to_hex(pk))
        self._current_file.write_text(key_id)
        return key_id

    def revoke(self, key_id: str, reason: str) -> None:
        if not (self.base_dir / f"{key_id}.pk.hex").exists():
            raise KeyError(f"cannot revoke unknown key_id={key_id!r}")
        self._revoked_file(key_id).write_text(reason)

    def key_status(self, key_id: str) -> KeyStatus:
        if not (self.base_dir / f"{key_id}.pk.hex").exists():
            raise KeyError(f"unknown key_id={key_id!r}")
        if self._revoked_file(key_id).exists():
            return KeyStatus.REVOKED
        if key_id == self.current_key_id():
            return KeyStatus.ACTIVE
        return KeyStatus.ROTATED

    def revocation_reason(self, key_id: str) -> str | None:
        path = self._revoked_file(key_id)
        return path.read_text() if path.exists() else None

    def list_key_ids(self) -> list[str]:
        """All key_ids this provider has ever issued, current or not --
        needed by an auditor who wants to enumerate what a verifier could
        possibly have signed with, historically."""
        return sorted(p.name.removesuffix(".pk.hex") for p in self.base_dir.glob("*.pk.hex"))
