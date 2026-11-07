# Changelog

All notable changes to this project are documented here.

## [0.4.0] -- Phase 4

### Added
- `docs/releases/phase-3-baseline.md` + real git tag `v0.3.0-phase3-baseline`,
  freezing the state before this phase's work began.
- Multi-verifier quorum experiment (`frontier_verify/quorum/`), tested
  against three genuinely isolated subprocess-based verifier instances --
  found and fixed a real false-independence bug in the process (an
  earlier in-process module-reload approach silently shared storage
  across "independent" instances via Python's module cache).
- A real (if tiny) numerical recomputation kernel
  (`frontier_verify/recomputation/numpy_kernel.py`) -- genuine matrix
  multiplication and a ReLU non-linearity, replacing the pure hash-based
  toy function used through Phase 3. Cross-process bit-reproducibility
  measured empirically, not assumed.
- Reproducible build verification: found builds were NOT bit-reproducible
  by default (traced to the auto-generated RECORD file's build-time
  timestamp), then confirmed `SOURCE_DATE_EPOCH` fixes it -- both
  measured, not asserted (`docs/research/reproducible-builds.md`).
- Audit logging for administrative actions (`frontier_verify/audit/`),
  closing a gap found via this phase's own self-critique: with multiple
  credentials able to hold the `ADMINISTRATOR` role, nothing recorded
  which one performed a given rotation or revocation. First version used
  a key prefix and its own test caught the bug (two human-named keys
  sharing a prefix were indistinguishable) -- fixed to use a one-way hash
  fingerprint instead.
- `docs/research/verifier-trust.md`: honest evaluation of 11 proposed
  trust mitigations, with real evidence behind the ones actually built.
- `docs/ai2040-gap-analysis-phase4.md`: GREEN/YELLOW/RED rollup --
  0 GREEN, 6 YELLOW, 19 RED, with an explanation of why zero GREEN is
  the correct result, not a scoring failure.
- `docs/reviews/external-review.md`: honestly states no independent
  review has occurred (and explains why fabricating one would be
  dishonest), provides a real review-readiness package, and includes
  clearly-labeled adversarial self-critique -- explicitly not a
  substitute for the real thing.
- `examples/external-validation/`: five real signed receipts (one valid,
  four deliberately broken in different ways) that anyone can verify
  without installing this package, pinned as a permanent regression test.
- `examples/hardware/nvidia/confirm_evidence_shape.py`: a real, tested
  diagnostic tool for whoever gets real NVIDIA hardware access, resolving
  the `evidences` vs. `evidence_list` question found in Phase 3's
  research.
- `docs/hardware/nvidia-validation-report.md`: an honest, unexecuted
  template -- every field says `UNVERIFIED` or `NOT RUN` because that is
  the truth.

### Explicitly NOT added, and why
No fabricated hardware validation results. No simulated "external
reviewer" persona presented as independent. No fake Triton execution. No
claim that any AI-2040 workstream reached GREEN. This phase's brief
explicitly required obtaining real-world evidence from outside this
development environment for these specific claims, and none was
obtainable by an AI agent working alone in a sandboxed environment --
stated directly rather than worked around. See this phase's closing
report for concrete next steps requiring human action.

### Fixed
- A false-independence bug in the quorum test's first (in-process)
  design -- shared module-level storage across "independent" instances.
- Non-reproducible package builds (missing `SOURCE_DATE_EPOCH`).
- Audit log actor identification collision risk (prefix -> hash).
- Framing correction in `docs/assurance-model.md`: hardware attestation
  relocates trust to the hardware vendor, it does not eliminate a trust
  assumption -- prior phases' docs described it as removing one.

## [0.3.0] -- Phase 3

### Added
- Role-based authorization (`PROVER`, `POLICY_AUTHORITY`, `ADMINISTRATOR`,
  `AUDITOR`), mapped to real trust boundaries, tested to genuinely
  restrict access (`tests/unit/test_authorization.py`, 12 tests).
- Key revocation, distinct from rotation: `VALID_AT_ISSUANCE` (signature
  fact, never changes) vs. `CURRENTLY_TRUSTED` (revocation-aware, changes
  when a key is revoked). A revoked key can never sign anything new
  (`RevokedKeyError`).
- A genuine second-language standalone verifier
  (`tools/standalone-verifier/verify_receipt.js`, Node's native Ed25519,
  zero npm dependencies), cross-checked against both Python
  implementations including Unicode/emoji edge cases. Honest common-mode-
  risk analysis of what this cross-checking does and doesn't prove
  (`docs/protocol/independent-verification.md`).
- `EvidenceEmitter`/`EmittedExecution` formal interface, with
  `AsyncQueueEvidenceEmitter` as the real reference implementation
  (relocated from example-only code, now shared infrastructure).
- A real Triton integration: `OTelSpanEvidenceAdapter`, tested against
  genuine `opentelemetry-sdk` spans (not hand-rolled stand-ins) --
  still unconfirmed against a live Triton instance, and says so.
- Eight named adversarial attacks against commit-reveal recomputation
  (`tests/adversarial/recomputation/`), four directly tested. Found and
  fixed a real design flaw in the process: `recompute_fn` used to receive
  only a bare digest, which cannot represent real recomputation.
- Fresh NVAT research finding a real schema discrepancy (`evidences` vs.
  `evidence_list` between local CLI and NRAS remote API) and a richer
  verified-claims schema this project doesn't consume yet
  (`docs/hardware/nvat-integration.md`).
- Hardware test harness that skips cleanly without a GPU and is designed
  to become executable the moment real hardware is available
  (`tests/hardware/nvidia/`).
- Security review: 2 real findings (world-readable private key files;
  missing digest-format validation), both fixed and regression-tested.
- Trust model, real-hardware CI design, Appia re-verification with
  required status categories, staged real-recomputation roadmap,
  cross-source consistency model for hidden computation.

### Fixed
- `recompute_fn` signature couldn't represent real recomputation (see
  Added, above) -- found via adversarial testing, not code review.
- Private key files were world-readable under the default umask.
- No digest-format validation in `ContentAddressedStore` (defense in
  depth -- no exploitable path found, fixed anyway).
- Two Phase 3 API endpoints existed but weren't documented in
  `docs/api-design.md` -- caught by the documentation consistency gate.

### Explicitly not included
Real NVIDIA hardware attestation (still no GPU), real recomputation of
actual inference, network evidence (deliberately), a live Triton/vLLM
instance to test against, key expiration, per-resource authorization,
real-hardware CI execution. See `docs/protocol-roadmap.md`.

## [0.2.0] -- Phase 2

### Added
- Real API-key authentication on mutating/sensitive endpoints
  (`frontier_verify/api/auth.py`).
- `KeyProvider` interface with a real `LocalFileKeyProvider` (rotation,
  key-id-based lookup so old receipts survive rotation) and honest
  `NotImplementedError` stubs for HSM/KMS/cloud KMS.
- Content-addressed evidence/attestation storage with integrity checking
  on read, replacing the pure in-memory dict.
- Evidence-id collision detection (409, not silent overwrite).
- `NvidiaAttestationProvider.parse_nvat_evidence()`: real parsing of
  NVAT's documented evidence JSON shape, tested against a clearly-labeled
  synthetic fixture.
- Standalone, dependency-minimal receipt verifier
  (`tools/standalone-verifier/`), cross-checked against the reference
  implementation.
- Commit-reveal recomputation sampling
  (`frontier_verify/recomputation/`), adversarially demonstrated to be
  unpredictable by a prover, with an honest accounting of what it does
  and doesn't solve.
- Generic Python integration wrapper with async, latency-isolated
  evidence submission (`examples/integration/generic_python_service/`).
- Conformance test suite (`tests/conformance/`, 25 tests).
- Research/documentation: NVIDIA attestation (re-researched, superseding
  Phase 1's now-stale findings), RATS/NIST/ISO/Appia ecosystem mapping,
  trust boundaries table, adversarial results for all 15 named attacks,
  vLLM/Triton integration research, compute-accounting and
  hidden-computation research notes, network-evidence protocol
  definition (deliberately without code), real performance measurements.

### Changed
- `GET /v1/policies/{id}` and `GET /v1/verifications/{id}` now require
  auth (were open in Phase 1).
- `/v1/receipts/verify` now looks up the verifier's public key by the
  receipt's own `verifier_key_id` when none is supplied, instead of
  defaulting to "whatever's current" -- required for rotation to be safe.

### Fixed
- A digest-consistency bug where `ContentAddressedStore`'s storage key
  diverged from `Evidence.digest()`'s own computation (different
  `exclude_none` handling), which broke evidence retrieval -- caught by
  running the test suite, not by inspection.
- A real deadlock in the generic integration wrapper's
  `wait_until_idle()`: it called `queue.Queue.join()`, which blocks
  forever without matching `task_done()` calls that were never made --
  caught by an actual test hang, not a code review.

### Explicitly not included
Real NVIDIA hardware attestation (still no GPU), real recomputation of
actual inference, network evidence (deliberately, see
`docs/network-evidence-protocol.md`), Kubernetes, a live vLLM/Triton
integration, key revocation, per-key authorization. See
`docs/protocol-roadmap.md`.

## [0.1.0] -- Phase 0 + Phase 1

### Added
- Phase 0 documentation set: architecture, threat model, assurance model,
  evidence model, receipt specification, API design, AI-2040 coverage
  matrix, adoption strategy, protocol roadmap, two ADRs, hardware provider
  guide.
- Phase 1 core verification fabric: canonical encoding, evidence schema,
  `AttestationProvider` interface with a mock implementation and an
  honest NVIDIA stub, policy model and evaluator, Ed25519-signed receipts,
  FastAPI verifier service, Python SDK (`VerifierClient`), `fv` CLI.
- 25 automated tests across unit, security, adversarial, and integration
  suites, all passing.
- JSON Schema exports for Evidence, Receipt, and Policy.
- End-to-end local demo script.

### Explicitly not included
See `docs/protocol-roadmap.md` -- real NVIDIA attestation, recomputation,
network evidence, Kubernetes deployment, inference-engine integrations,
conformance suite, second independent verifier implementation. None of
these have placeholder code implying otherwise, beyond the two interface
points documented in ADR-0001 and the 501-returning recomputation
endpoints.

### Known issues
- No authentication on the API (see `SECURITY.md`).
- No persistent storage -- in-memory only (see `architecture.md`).
- No `docker compose` demo -- not buildable/testable in the environment
  this was developed in, so not shipped rather than shipped unverified.
