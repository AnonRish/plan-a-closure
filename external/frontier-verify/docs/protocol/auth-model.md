# Authentication and Authorization Model

## Authentication: API keys

`frontier_verify/api/auth.py`. Every mutating endpoint and every endpoint
that reads potentially sensitive stored state requires an `X-Api-Key`
header matching a key configured in `FV_API_KEYS`. Missing or invalid key
-> `401`. `FV_API_KEYS` unset or malformed -> `500`, refusing to
authenticate rather than silently running open.

## Authorization: roles, added in Phase 3

Phase 2 shipped authentication only -- any valid key could do anything any
other valid key could do. Phase 3 replaces that flat model with four
roles, each mapped directly onto an actor `docs/trust-model.md` names, not
an arbitrary permission grid:

| Role | Can do | Cannot do |
|---|---|---|
| `PROVER` | Submit attestations/evidence, trigger `/v1/inferences/verify`, read its own submissions' structural validity | Define policies, rotate/revoke keys |
| `POLICY_AUTHORITY` | Register and read policies | Submit evidence, trigger verification, manage keys |
| `ADMINISTRATOR` | Rotate and revoke verifier keys, check key status | Submit evidence, define policy |
| `AUDITOR` | Read verification records, check evidence/attestation validity, check key status | Submit anything, define policy, manage keys |

**Why `PROVER` and `POLICY_AUTHORITY` are separate roles, specifically**:
a prover that could also define the policy its own evidence gets checked
against could simply write a policy that always passes. This is the one
role separation in this table that maps to an actual attack, not just
tidiness -- see `docs/trust-model.md`.

`FV_API_KEYS` format: comma-separated `key:ROLE1|ROLE2|...` pairs:

```bash
export FV_API_KEYS="sk_prover_abc:PROVER,sk_policy_def:POLICY_AUTHORITY,sk_admin_ghi:ADMINISTRATOR|AUDITOR"
```

A bare key with no role suffix is rejected outright at request time
(`500`, not silently granted every permission) -- there is no implicit
default role, because a default that happened to mean "everything" would
just silently recreate the Phase 2 gap this exists to close.

## What's deliberately NOT behind auth, and why

`POST /v1/receipts/verify`, `GET /v1/verifier/public-key`, `GET
/v1/verifier/public-key/{key_id}`, `GET /health`, `GET /ready`. The
receipt-verification and public-key endpoints are unauthenticated on
purpose: the entire design goal of a receipt
(`docs/receipt-specification.md`) is that ANY relying party can check it,
without even an account, let alone a specific role. Gating this behind
auth would directly contradict that goal. The genuinely independent path
remains fully offline anyway -- `fv receipt verify` and
`tools/standalone-verifier/` need no API access, credentialed or not.

## What real per-resource authorization would still need (NOT_IMPLEMENTED)

Role-based endpoint gating is coarser than real authorization. Today, any
key holding `PROVER` can read `GET /v1/verifications/{id}` for **any**
verification ID, not only ones tied to evidence it submitted itself --
there is no concept of "which prover owns this evidence" anywhere in the
data model. Building that requires: a notion of prover identity distinct
from "holds a key with the PROVER role" (multiple provers currently share
the undifferentiated PROVER role), and checking resource ownership on
every read, not just role membership. This is a materially bigger feature
than the role model above and is not implemented.

## Why API keys, not mTLS/OIDC, for now

Unchanged reasoning from Phase 2: API keys identify "someone who has a
valid key," not a specific, auditable service identity with its own
lifecycle. mTLS is the standard answer for service-to-service
authentication in exactly this deployment shape (prover infrastructure
calling a verifier over an untrusted network) and remains the natural next
step, not attempted this phase.

## Secrets handling

Keys are read from environment variables, never from source or a
committed file. `generate_api_key()` produces cryptographically random
key material for operators to distribute out of band -- there is no
in-repo default key, and none should ever be added. Assigning roles is
the operator's responsibility when constructing `FV_API_KEYS`; nothing in
this repository picks roles for you.
