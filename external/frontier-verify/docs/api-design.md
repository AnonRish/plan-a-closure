# API Design

Base implementation: `frontier_verify/api/main.py` (FastAPI, OpenAPI
generated automatically at `/openapi.json` when the server is running).

## Endpoint status

| Endpoint | Status | Notes |
|---|---|---|
| `GET /health` | Implemented | Trivial liveness check, unauthenticated |
| `GET /ready` | Implemented | Trivial readiness check, unauthenticated |
| `GET /v1/verifier/public-key` | Implemented | Current key only, unauthenticated (must be publicly fetchable) |
| `GET /v1/verifier/public-key/{key_id}` | Implemented (Phase 2) | Fetch a SPECIFIC, possibly rotated-out key -- required for verifying old receipts after rotation, unauthenticated |
| `POST /v1/verifier/rotate-key` | Implemented (Phase 2) | **`ADMINISTRATOR` role required.** Real key rotation via `LocalFileKeyProvider` -- see `docs/protocol/key-management.md` |
| `POST /v1/verifier/revoke-key` | Implemented (Phase 3) | **`ADMINISTRATOR` role required.** Distinct from rotation -- see `docs/protocol/key-management.md`, "VALID_AT_ISSUANCE vs CURRENTLY_TRUSTED" |
| `GET /v1/verifier/keys/{key_id}/status` | Implemented (Phase 3) | **`ADMINISTRATOR` or `AUDITOR` role required.** Returns `ACTIVE`/`ROTATED`/`REVOKED` plus revocation reason if any |
| `GET /v1/verifier/audit-log` | Implemented (Phase 4) | **`ADMINISTRATOR` or `AUDITOR` role required.** Attributed record of every rotate-key/revoke-key call -- closes the gap found in `docs/reviews/external-review.md` finding #1 |
| `POST /v1/attestations` | Implemented | **`PROVER` role required (Phase 3, was any valid key in Phase 2).** Stores a `HardwareEvidence` payload via content-addressed storage, returns its digest |
| `POST /v1/attestations/verify` | Implemented (narrow) | **`PROVER` or `AUDITOR` role required.** Checks schema validity and the `mock` flag only -- explicitly does **not** validate a real hardware signature chain, and says so in its own response `note` field |
| `POST /v1/evidence` | Implemented | **`PROVER` role required.** Stores an `Evidence` bundle. Phase 2: returns `409` if `evidence_id` was already used for DIFFERENT content -- no silent overwrite |
| `POST /v1/evidence/verify` | Implemented (narrow) | **`PROVER` or `AUDITOR` role required.** Structural validity + digest only |
| `POST /v1/inferences/verify` | Implemented | **`PROVER` role required.** Runs the policy evaluator; issues a signed receipt iff the evaluation passes, using the current key from `KeyProvider` |
| `POST /v1/receipts/verify` | Implemented | **Deliberately unauthenticated** -- the whole point of a receipt is that anyone can check it. Phase 2: looks up the key by the receipt's own `verifier_key_id` when no explicit key is supplied, so old receipts verify correctly after rotation |
| `POST /v1/policies/validate` | Implemented | **`POLICY_AUTHORITY` role required (Phase 3 -- deliberately separate from `PROVER`, see `docs/trust-model.md`).** Structural validation + storage |
| `GET /v1/policies/{id}` | Implemented | **Any valid role.** Low sensitivity -- knowing what a policy requires is not itself sensitive |
| `GET /v1/verifications/{id}` | Implemented | **`PROVER` or `AUDITOR` role required.** Returns the evaluator result and the receipt (if one was issued). No per-resource ownership check yet -- see `docs/protocol/auth-model.md` |
| `POST /v1/recomputation` | **501** | Honest stub -- Phase 6 in the roadmap, not implemented. Unauthenticated (nothing sensitive behind a fixed 501) |
| `POST /v1/recomputation/check` | **501** | Same |

Every "Implemented" row above has at least one automated test exercising
it (`tests/integration/`, `tests/adversarial/`), and the full set was also
driven live over real HTTP against a running `uvicorn` process in this
session -- see the delivery notes.

## Deliberately absent from Phase 3

- **Per-resource authorization** (Phase 3 built ROLE-based authorization,
  not per-resource -- a `PROVER` can read `GET /v1/verifications/{id}` for
  ANY verification, not only ones tied to evidence it submitted itself).
  See `docs/protocol/auth-model.md`.
- **mTLS / OIDC** -- API keys are the floor, not the target; see
  `docs/protocol/auth-model.md` for why.
- **gRPC** -- REST only. Listed as "where useful" in the source spec
  (section 15), not required by anything this project has built yet.
- **Async job semantics, idempotency keys beyond evidence_id collision
  detection, retries, version negotiation** -- real requirements for a
  production API, still not built.
- **Rate limiting, request size limits** -- still absent, still a real gap
  before any deployment outside a fully trusted network.
- **Key expiration** -- rotation and revocation both exist now
  (`docs/protocol/key-management.md`); time-based expiration does not.

## OpenAPI

Since the schema is generated directly from the FastAPI app object, it's
always in sync with the actual routes -- there's no separate hand-maintained
spec to drift out of date. Get it via `GET /openapi.json` on a running
server, or:

```bash
python3 -c "from frontier_verify.api.main import app; import json; print(json.dumps(app.openapi(), indent=2))"
```
