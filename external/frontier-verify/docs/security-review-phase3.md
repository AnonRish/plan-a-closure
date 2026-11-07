# Security Review (Phase 3)

A dedicated pass over auth, authorization, keys, revocation, evidence,
canonicalization, receipt signing, replay, storage, verifier independence,
API, and network boundaries, per section 24. Two real findings, both
fixed and regression-tested; everything else reviewed and found already
covered by existing tests or already documented as a known, unfixed gap.

## Findings, fixed this phase

1. **Private key files were world-readable.**
   `LocalFileKeyProvider.rotate()` wrote key material via `write_text()`
   alone, leaving `-rw-r--r--` permissions under the default umask.
   Fixed: `os.chmod(sk_path, 0o600)` immediately after writing.
   Regression test:
   `tests/unit/test_key_revocation.py::test_private_key_file_permissions_are_restrictive`
   -- fails against the pre-fix code, not a speculative check.
2. **No digest-format validation in `ContentAddressedStore._path_for()`.**
   No current caller passes an attacker-controlled digest directly (every
   digest reaching this method flows through an internal index this
   project populates itself first -- confirmed by inspection of every
   caller), so this was not an exploitable path today. Fixed anyway as
   cheap defense-in-depth: a digest that isn't 64 lowercase hex
   characters now raises `ValueError` immediately rather than silently
   constructing a path. Regression test:
   `tests/conformance/test_content_addressed.py::test_malformed_digest_is_rejected_defensively`,
   including a literal `../../../etc/passwd` case.

## Reviewed, already covered

- **Timing-safe key comparison**: `frontier_verify/api/auth.py` uses
  `hmac.compare_digest` for every API key check, confirmed by direct
  inspection, not assumed.
- **No hardcoded secrets in source**: searched for common patterns
  (`api_key =`, `secret =`, `password =` followed by literal strings) --
  none found outside test fixtures and documentation examples.
- **Private key material never appears in API responses**: confirmed by
  inspection of every response model in `frontier_verify/api/main.py` --
  none references `private_key` or signing key material; only public keys
  and key IDs cross the API boundary.
- **Blind exception handling**: three instances exist in the codebase
  (`frontier_verify/emitters/async_queue.py`,
  `frontier_verify/receipts/signing.py`, `cli/fv/main.py`), all already
  carry `# noqa: BLE001` comments explaining the specific reason each is
  deliberate (isolating a background worker, handling adversarial
  signature input, reporting a subprocess failure honestly) -- reviewed
  individually, not blanket-approved.
- **Receipt tamper detection**: unchanged from Phase 1/2, still covers 5
  distinct tamper vectors (`tests/security/test_receipt_tamper.py`).
- **Authorization boundaries**: newly built this phase, tested
  adversarially (`tests/unit/test_authorization.py`, 12 tests confirming
  restriction, not just permission).

## Reviewed, found to be already-documented, unfixed gaps (not new findings)

- `LocalFileKeyProvider` storing private keys as plaintext files at all
  (permissions fix above narrows exposure, doesn't remove the underlying
  gap) -- `docs/protocol/key-management.md`.
- No per-resource ownership in authorization (a `PROVER` can read any
  verification record its role permits, not only its own) --
  `docs/protocol/auth-model.md`.
- No key expiration, no HSM/KMS backing -- `docs/protocol/key-management.md`.
- Evidence freshness defeatable by a prover lying about its own clock --
  `docs/threat-model.md`, question I.

## What this review did NOT cover

Anything requiring real infrastructure this project doesn't have: network
boundary testing against a real deployment topology, real load/DoS
testing, dependency vulnerability scanning against a live threat feed (ran
no SBOM/CVE scan this phase -- a real gap, not attempted). A security
review of code that has never been deployed anywhere real is inherently
partial; this document does not claim otherwise.
