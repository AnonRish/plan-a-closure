"""
Device identity: Ed25519 keypairs used to sign commitment roots, so a
revealed/audited commitment can be tied to a specific device rather than
an anonymous submission. In a real deployment the private key would live
in hardware (a TPM/secure-enclave-class root of trust on the tap itself,
per the "Hardening the trusted parts themselves" open problem on the
verification get-involved page); this reference implementation keeps
everything in-process for demonstration and testing.
"""

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature


class DeviceIdentity:
    def __init__(self, private_key: Ed25519PrivateKey = None):
        self._sk = private_key or Ed25519PrivateKey.generate()

    @property
    def public_bytes(self) -> bytes:
        return self._sk.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    def sign(self, message: bytes) -> bytes:
        return self._sk.sign(message)


def verify_signature(public_bytes: bytes, message: bytes, signature: bytes) -> bool:
    pubkey = Ed25519PublicKey.from_public_bytes(public_bytes)
    try:
        pubkey.verify(signature, message)
        return True
    except InvalidSignature:
        return False
