# Key Management

## The interface

`frontier_verify/keys/provider.py` defines `KeyProvider`:

```
current_key_id() -> str
get_signing_key(key_id: str | None) -> (key_id, private_key)
get_public_key(key_id: str) -> public_key
rotate() -> new_key_id
```

## Why lookup-by-id and not just "the current key"

Phase 1 had exactly one keypair, generated once, held in memory. There was
no rotation because rotation would have been meaningless -- with no way to
look up a NON-current key, rotating would have permanently broken every
receipt issued before the rotation.

Phase 2 fixes this by making `verifier_key_id` (already a field on every
`Receipt` since Phase 1) the actual lookup key: `GET
/v1/verifier/public-key/{key_id}` and `KeyProvider.get_public_key(key_id)`
both take a specific ID, not "whatever's current." `POST
/v1/receipts/verify` uses this: when no explicit public key is supplied,
it looks up the key by the RECEIPT'S OWN `verifier_key_id` field against
the verifier's own trusted local key store -- not against anything the
caller supplies. That distinction matters: an attacker can put any
`verifier_key_id` they want in a forged receipt, but the verifier will
check the signature against ITS OWN recorded key for that ID, not
whatever the attacker hoped it would use. If the attacker doesn't hold the
matching private key, the signature check fails regardless of which
`key_id` they claimed. This is the same principle as JWT `kid`-based key
lookup done correctly: the lookup table is trusted and local, never
attacker-suppliable.

`tests/integration/test_api_end_to_end.py::test_receipt_survives_key_rotation`
proves this concretely: it rotates the key mid-test and confirms a receipt
signed BEFORE rotation still verifies correctly afterward, alongside a new
receipt signed with the new key -- both looked up automatically by their
own `verifier_key_id`.

## Implementations

| Provider | File | Status |
|---|---|---|
| `LocalFileKeyProvider` | `frontier_verify/keys/local_provider.py` | EXPERIMENTAL -- real generation, storage, lookup, rotation |
| `HsmKeyProvider` | `frontier_verify/keys/kms_provider.py` | NOT_IMPLEMENTED |
| `KmsKeyProvider` | `frontier_verify/keys/kms_provider.py` | NOT_IMPLEMENTED |
| `CloudKmsKeyProvider` | `frontier_verify/keys/kms_provider.py` | NOT_IMPLEMENTED |

### `LocalFileKeyProvider`

Ed25519 keys as hex-encoded files in a directory: `<key_id>.sk.hex` /
`<key_id>.pk.hex`, plus a `CURRENT` file naming the active key. Real
generation, real rotation, real lookup-by-id. The private key sits in a
plaintext file on disk -- fine for local development and CI, not
acceptable for anything else. Use for local development only.

**Data location**: `FV_KEY_DIR` env var if set, otherwise a fresh
temporary directory created once per process. The default does **not**
survive a process restart -- an explicit, honest choice (see
`frontier_verify/api/store.py`'s identical reasoning for `FV_DATA_DIR`),
not an oversight. Set `FV_KEY_DIR` to a real path for persistence.

### `HsmKeyProvider`, `KmsKeyProvider`, `CloudKmsKeyProvider`

All three raise `NotImplementedError` unconditionally. This environment
has no HSM, no on-prem KMS, and no cloud credentials to build or test
against -- implementing any of these now would mean either faking a
backend that doesn't exist, or writing untested code against a remembered
SDK shape, both of which the project's non-fabrication rule prohibits.

There is also a real interface problem worth flagging before anyone
starts: `KeyProvider.get_signing_key()` as currently shaped returns a raw
`Ed25519PrivateKey` object. **A real HSM or KMS never hands back private
key material at all** -- signing happens inside the device or service. A
correct HSM/KMS-backed provider needs a different method shape, something
like `sign(key_id: str, message: bytes) -> bytes`, with the private key
never leaving the backend. Implementing `HsmKeyProvider` against the
CURRENT `KeyProvider` interface would be implementing it against the wrong
interface. Fixing this is real design work for whoever picks this up next
-- not a trivial fill-in-the-blank the way `LocalFileKeyProvider` was.

## What's still missing even for `LocalFileKeyProvider`

- **Revocation**: rotating creates a new current key but never marks an
  old one as compromised/untrusted. There's no way today to say "key
  `fv-...` is rotated out AND should be treated as compromised, reject
  anything relying on it retroactively" versus "key `fv-...` is rotated
  out but was never compromised, old receipts remain fully trustworthy."
  Both cases currently look identical to a verifier. NOT_IMPLEMENTED.
- **Expiration**: keys have no validity window. NOT_IMPLEMENTED.
- **Multi-verifier trust stores**: an auditor trusting more than one
  independent verifier has no standard way to configure which key IDs
  from which verifiers it accepts. NOT_IMPLEMENTED -- see
  `docs/adoption-strategy.md` and `docs/protocol-roadmap.md`, Phase 4.
