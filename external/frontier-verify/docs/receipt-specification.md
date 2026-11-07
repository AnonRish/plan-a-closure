# Receipt Specification

## Fields

Defined in `frontier_verify/receipts/models.py`, JSON Schema in
`schemas/receipt.schema.json`.

| Field | Meaning |
|---|---|
| `receipt_version` | Schema version of the receipt itself (currently `0.1.0`) |
| `verification_id` | Ties the receipt back to a specific verification event |
| `created_at` | When the verifier issued this receipt |
| `verifier_key_id` | Which key signed it (see Key management, below) |
| `model_identity_digest`, `runtime_identity_digest`, `hardware_evidence_digest` | Digests of the evidence that was evaluated -- not the evidence itself, so a receipt doesn't leak the full evidence bundle to anyone who only holds the receipt |
| `policy_id`, `policy_version` | Which policy the evidence was checked against |
| `assurance_level` | See `assurance-model.md` -- currently always `L0` or `L1` |
| `result` | Boolean pass/fail |
| `limitations` | A list of plain-language caveats the *issuing verifier* attaches to this specific receipt (see below -- this is not boilerplate) |
| `signature` | Base64-encoded Ed25519 signature over every other field |

## Signing and independent verification

`frontier_verify/receipts/signing.py`:

- `sign_receipt(receipt, private_key)` -- canonicalizes
  `receipt.unsigned_payload()` (every field except `signature`) and signs
  the resulting bytes with Ed25519 (via `pyca/cryptography`, not a
  hand-rolled scheme).
- `verify_receipt(receipt, public_key)` -- takes **only** a public key and
  the receipt. No network call, no database lookup, no trust in whoever
  handed you the receipt. This is what "independently verifiable" means in
  this repository: it's a property of one function's signature, not a
  marketing claim.

Both the CLI (`fv receipt verify receipt.json --public-key-hex <hex>`) and
the SDK (`VerifierClient.verify_receipt(receipt,
verifier_public_key_hex=...)`) expose this offline path directly. The SDK
also has a weaker fallback -- asking the server's own
`/v1/receipts/verify` endpoint -- documented in its own docstring as weaker
precisely because it reintroduces trust in the server.

`tests/security/test_receipt_tamper.py` attacks five different fields
individually (result, assurance_level, policy_id, wrong public key,
corrupted signature bytes) and confirms all five are caught. This was also
exercised live against a running server in this session, not just in
pytest -- see the delivery notes for the transcript.

## What a receipt does NOT prove

Every receipt Phase 1 issues carries `limitations` entries stating, in
plain language, that no independent recomputation happened, no network
evidence was collected, hardware evidence may be mock, and -- critically --
that the receipt attests the evidence satisfied the named policy's checks,
**not** that the evidence was truthful when submitted. This is generated
per-receipt in `frontier_verify/api/main.py`, not written once in this
document and then forgotten; if the checks a policy performs change, the
limitations list is the place that needs to change with them.

## Key management: Phase 1 vs. Phase 2 vs. a real deployment

Phase 1's verifier key was generated in-process, in memory, at server
startup -- no rotation, no way to verify an old receipt after a
hypothetical rotation, and no key-id-based lookup.

**Phase 2 changes this concretely**: a real `KeyProvider` interface backs
the verifier (`LocalFileKeyProvider` by default), supporting real rotation
via `POST /v1/verifier/rotate-key`, with old receipts staying verifiable
afterward because lookup happens by the receipt's own `verifier_key_id`,
not "whatever's current" -- proven by
`tests/integration/test_api_end_to_end.py::test_receipt_survives_key_rotation`.
Full details, including what's still missing (revocation, expiration,
HSM/KMS backing) and the real interface problem with signing-inside-a-device
backends, live in `docs/protocol/key-management.md` -- this section
doesn't duplicate that document, it points to it.

`fv init` still generates a *separate*, CLI-local demo keypair for local
experimentation -- it is not the same key the API server's `KeyProvider`
uses, and the two should not be confused.
