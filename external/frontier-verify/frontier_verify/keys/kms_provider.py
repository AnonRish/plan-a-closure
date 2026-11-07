"""KMS, HSM, and cloud-KMS-backed key providers.

STATUS: NOT IMPLEMENTED. Every class here raises NotImplementedError on
first use, same pattern as frontier_verify.attestations.nvidia_provider --
fix the interface now, implement against a real backend when one is
actually wired up and testable. This environment has no HSM, no on-prem
KMS, and no cloud credentials, so implementing any of these now would mean
either faking a backend that doesn't exist or writing untestable code
against an SDK API from memory. Both are exactly what section 4 of the
original Phase 1 brief (non-fabrication) and this document's own section
12 ("Do NOT pretend to provide enterprise HSM integration unless actually
implemented") prohibit.

What a real implementation of each needs, concretely:

- HsmKeyProvider: a PKCS#11 or vendor SDK session against a real HSM;
  signing happens INSIDE the device, so get_signing_key() as currently
  shaped (return the raw private key object) is the wrong interface for
  this backend -- an HSM-backed provider should expose a `sign(key_id,
  message: bytes) -> bytes` method instead and never hand back private key
  material at all. That's a real, non-cosmetic interface change, not just
  a new subclass -- see docs/protocol/key-management.md for why
  KeyProvider.get_signing_key() as written is Phase 2's known limit here,
  not this stub's bug.
- KmsKeyProvider (on-prem/generic KMS, e.g. via a REST or gRPC KMS API):
  same signing-happens-remotely shape as HSM.
- CloudKmsKeyProvider (AWS KMS / GCP Cloud KMS / Azure Key Vault): same
  shape again, plus real cloud credentials and a live account to test
  against, which this environment does not have.
"""
from __future__ import annotations

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from frontier_verify.keys.provider import KeyProvider, KeyStatus

_NOT_IMPLEMENTED_MSG = (
    "{name} is not implemented -- this environment has no {backend} to "
    "build or test against. Implementing this against a real backend also "
    "requires changing the signing interface (see this module's "
    "docstring) since a real {backend} never exposes raw private key "
    "material. See docs/protocol/key-management.md."
)


class HsmKeyProvider(KeyProvider):
    def current_key_id(self) -> str:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG.format(name="HsmKeyProvider", backend="HSM"))

    def get_signing_key(self, key_id: str | None = None) -> tuple[str, Ed25519PrivateKey]:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG.format(name="HsmKeyProvider", backend="HSM"))

    def get_public_key(self, key_id: str) -> Ed25519PublicKey:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG.format(name="HsmKeyProvider", backend="HSM"))

    def rotate(self) -> str:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG.format(name="HsmKeyProvider", backend="HSM"))

    def revoke(self, key_id: str, reason: str) -> None:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG.format(name="HsmKeyProvider", backend="HSM"))

    def key_status(self, key_id: str) -> KeyStatus:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG.format(name="HsmKeyProvider", backend="HSM"))


class KmsKeyProvider(KeyProvider):
    def current_key_id(self) -> str:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG.format(name="KmsKeyProvider", backend="KMS"))

    def get_signing_key(self, key_id: str | None = None) -> tuple[str, Ed25519PrivateKey]:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG.format(name="KmsKeyProvider", backend="KMS"))

    def get_public_key(self, key_id: str) -> Ed25519PublicKey:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG.format(name="KmsKeyProvider", backend="KMS"))

    def rotate(self) -> str:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG.format(name="KmsKeyProvider", backend="KMS"))

    def revoke(self, key_id: str, reason: str) -> None:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG.format(name="KmsKeyProvider", backend="KMS"))

    def key_status(self, key_id: str) -> KeyStatus:
        raise NotImplementedError(_NOT_IMPLEMENTED_MSG.format(name="KmsKeyProvider", backend="KMS"))


class CloudKmsKeyProvider(KeyProvider):
    def current_key_id(self) -> str:
        raise NotImplementedError(
            _NOT_IMPLEMENTED_MSG.format(name="CloudKmsKeyProvider", backend="cloud KMS account")
        )

    def get_signing_key(self, key_id: str | None = None) -> tuple[str, Ed25519PrivateKey]:
        raise NotImplementedError(
            _NOT_IMPLEMENTED_MSG.format(name="CloudKmsKeyProvider", backend="cloud KMS account")
        )

    def get_public_key(self, key_id: str) -> Ed25519PublicKey:
        raise NotImplementedError(
            _NOT_IMPLEMENTED_MSG.format(name="CloudKmsKeyProvider", backend="cloud KMS account")
        )

    def rotate(self) -> str:
        raise NotImplementedError(
            _NOT_IMPLEMENTED_MSG.format(name="CloudKmsKeyProvider", backend="cloud KMS account")
        )

    def revoke(self, key_id: str, reason: str) -> None:
        raise NotImplementedError(
            _NOT_IMPLEMENTED_MSG.format(name="CloudKmsKeyProvider", backend="cloud KMS account")
        )

    def key_status(self, key_id: str) -> KeyStatus:
        raise NotImplementedError(
            _NOT_IMPLEMENTED_MSG.format(name="CloudKmsKeyProvider", backend="cloud KMS account")
        )
