"""KeyProvider: the contract a verifier's key backend must implement.

Phase 1 hardcoded a single in-memory keypair generated at process start.
Phase 2 fixed rotation (this interface's rotate()/get_public_key(key_id)).
Phase 3 fixes the remaining gap Phase 2's own docs flagged explicitly:
rotation and revocation are DIFFERENT operations with different meanings,
and Phase 2 only had the former. Rotating a key is routine hygiene -- the
old key remains fully trustworthy for receipts it already signed.
Revoking a key means "distrust this retroactively, including receipts
already signed with it" -- a materially different, stronger claim. Before
this phase, both looked identical to a verifier: neither was
distinguishable from "not current anymore."

See docs/protocol/key-management.md.
"""
from __future__ import annotations

import abc
from enum import Enum

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


class KeyStatus(str, Enum):
    ACTIVE = "ACTIVE"    # the current signing key
    ROTATED = "ROTATED"  # rotated out, but NOT revoked -- still fully trusted for receipts it signed
    REVOKED = "REVOKED"  # explicitly distrusted, retroactively -- see revoke()


class KeyProvider(abc.ABC):
    @abc.abstractmethod
    def current_key_id(self) -> str:
        """The key_id that should sign new receipts right now."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_signing_key(self, key_id: str | None = None) -> tuple[str, Ed25519PrivateKey]:
        """Returns (key_id, private_key) for signing. Defaults to the
        current key when key_id is None."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_public_key(self, key_id: str) -> Ed25519PublicKey:
        """Look up the public key for a SPECIFIC key_id -- including old,
        rotated-out ones. This is what makes old receipts stay verifiable
        after rotation: the caller looks up by the key_id embedded in the
        receipt, not by "whatever's current." See
        docs/protocol/key-management.md, "Why lookup-by-id and not just
        'the current key'."""
        raise NotImplementedError

    @abc.abstractmethod
    def rotate(self) -> str:
        """Generate a new key, make it current, and return its key_id.
        Prior keys must remain retrievable via get_public_key()."""
        raise NotImplementedError

    @abc.abstractmethod
    def revoke(self, key_id: str, reason: str) -> None:
        """Mark key_id as REVOKED -- distinct from rotation. The public
        key must remain retrievable via get_public_key() (a verifier
        still needs to check whether a receipt signed with a revoked key
        was AT LEAST cryptographically genuine, even though it's no
        longer currently trusted -- see
        docs/protocol/key-management.md, "VALID_AT_ISSUANCE vs
        CURRENTLY_TRUSTED"). Revoking the CURRENT key does not
        automatically rotate to a new one -- callers must rotate
        separately, since auto-rotating on revocation would hide the
        fact that a compromise just happened."""
        raise NotImplementedError

    @abc.abstractmethod
    def key_status(self, key_id: str) -> KeyStatus:
        """ACTIVE, ROTATED, or REVOKED. Raises KeyError for an unknown
        key_id -- distinct from any of the three known states."""
        raise NotImplementedError
