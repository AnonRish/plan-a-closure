"""Ed25519 signing and independent verification for receipts.

Uses the `cryptography` package (pyca/cryptography), not a hand-rolled
signature scheme. This is real cryptography with a real adversarial test
suite (see tests/security/test_receipt_tamper.py: tampering with any single
field after signing must and does flip verify_receipt() to False).

What this DOES prove: the receipt's contents are exactly what the holder of
`verifier_key_id`'s private key signed, and nothing has been altered since.

What this does NOT prove: that the evidence referenced by the receipt's
digests was truthful when it was submitted. See docs/threat-model.md,
question B -- receipts protect integrity in transit/storage, not the
truthfulness of what was reported.
"""
from __future__ import annotations

import base64

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from frontier_verify.core.canonical import canonicalize
from frontier_verify.receipts.models import Receipt


def generate_keypair() -> tuple[Ed25519PrivateKey, Ed25519PublicKey]:
    sk = Ed25519PrivateKey.generate()
    return sk, sk.public_key()


def sign_receipt(receipt: Receipt, private_key: Ed25519PrivateKey) -> Receipt:
    payload = canonicalize(receipt.unsigned_payload())
    signature = private_key.sign(payload)
    return receipt.model_copy(update={"signature": base64.b64encode(signature).decode("ascii")})


def verify_receipt(receipt: Receipt, public_key: Ed25519PublicKey) -> bool:
    """Pure, offline, independent verification. Takes only a raw public key
    and the receipt -- no network call, no trust in whoever handed you the
    receipt. This is the function docs/receipt-specification.md means when
    it says a receipt is independently verifiable."""
    if receipt.signature is None:
        return False
    payload = canonicalize(receipt.unsigned_payload())
    try:
        signature_bytes = base64.b64decode(receipt.signature)
    except Exception:  # noqa: BLE001 -- deliberate: a verifier fed adversarial or
        # corrupted input must resolve to "not valid", never raise. See
        # tests/security/test_receipt_tamper.py::test_corrupted_signature_fails_verification.
        return False
    try:
        public_key.verify(signature_bytes, payload)
        return True
    except InvalidSignature:
        return False
    except (ValueError, TypeError):
        # Malformed/wrong-length signature bytes can raise something other
        # than InvalidSignature before a mismatch is even checked. A
        # verifier that raises on adversarial input instead of returning
        # False is itself a bug -- this function's job is to answer
        # "valid or not", not to assume well-formed input.
        return False


def public_key_to_hex(pk: Ed25519PublicKey) -> str:
    raw = pk.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return raw.hex()


def public_key_from_hex(hex_str: str) -> Ed25519PublicKey:
    return Ed25519PublicKey.from_public_bytes(bytes.fromhex(hex_str))


def private_key_to_hex(sk: Ed25519PrivateKey) -> str:
    raw = sk.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return raw.hex()


def private_key_from_hex(hex_str: str) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(bytes.fromhex(hex_str))
