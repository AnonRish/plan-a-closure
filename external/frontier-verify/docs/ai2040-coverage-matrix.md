# AI-2040 Coverage Matrix

Status legend (identical vocabulary to `Maturity` in
`frontier_verify/evidence/models.py`, so code and docs can't drift apart
without someone noticing): `NOT_IMPLEMENTED`, `MOCK`, `SIMULATED`,
`EXPERIMENTAL`, `RESEARCH`, `VALIDATED`, `PRODUCTION_READY`.

Nothing below is marked `VALIDATED` or `PRODUCTION_READY`. Phase 1 hasn't
earned either label yet, and section 4 of the source spec is explicit that
passing tests isn't sufficient grounds to claim one.

| # | Workstream | Status | Evidence / notes |
|---|---|---|---|
| 1 | Compute accounting | NOT_IMPLEMENTED | No FLOP/utilization accounting exists in this repo |
| 2 | Workload visibility | NOT_IMPLEMENTED | `workload_ref` is a bare optional string field with nothing reading it |
| 3 | Reproducible workload packets | NOT_IMPLEMENTED | |
| 4 | Inference reproducibility | NOT_IMPLEMENTED | |
| 5 | Model reproducibility | EXPERIMENTAL | `ModelIdentity` + deterministic digesting is real and tested (`tests/unit/test_evidence.py`), but every digest is self-reported, not independently derived from the actual weights |
| 6 | Network reproducibility | NOT_IMPLEMENTED | |
| 7 | Execution/runtime provenance | EXPERIMENTAL | `RuntimeIdentity` exists and digests deterministically; same self-report caveat as #5 |
| 8 | Network evidence | NOT_IMPLEMENTED | No abstraction exists yet, not even a stub -- deliberately deferred, see ADR-0001 |
| 9 | Passive observation | NOT_IMPLEMENTED | |
| 10 | Network capture constraints | NOT_IMPLEMENTED | |
| 11 | Independent recomputation | EXPERIMENTAL | `/v1/recomputation/v2` now provides an experimental end-to-end challenge/submission/check path with a real deterministic software kernel and signed receipt; the legacy `/v1/recomputation` interface and full frontier-scale recomputation remain unfinished. Phase 3 fixed a real design flaw found via adversarial review: `recompute_fn` used to receive only a bare digest, which cannot represent real recomputation (a hash can't be inverted back into data to run inference on) -- now retrieves real content via `ContentAddressedStore`. Four of the eight named attacks in Phase 3's adversarial pass are directly tested (`tests/adversarial/recomputation/`); the other four require real ML inference, a real serving-layer binding, or restate an already-tracked risk category -- see `docs/adversarial-results.md` |
| 12 | Random partial recomputation | RESEARCH | Unchanged conclusion from Phase 2, now with a corrected implementation underneath it (see #11) and a documented residual attack: even correct commit-reveal sampling only changes predictability, not the economics of partial detection -- see `docs/research/recomputation.md`'s "What commit-reveal does not solve" |
| 13 | Frontier-model recomputation | RESEARCH | Unchanged -- AI-2040 itself and current literature (e.g. the ICML 2026 cluster-fingerprinting paper cited in `threat-model.md`) both treat this as open; no shortcut exists |
| 14 | Verifier independence | EXPERIMENTAL | Phase 3 adds a genuine second LANGUAGE implementation (`tools/standalone-verifier/verify_receipt.js`, Node's native Ed25519, zero shared dependencies with either Python implementation), cross-checked against both Python implementations including Unicode/emoji edge cases (`tests/conformance/test_cross_language_verifier_agrees.py`). `docs/protocol/independent-verification.md` is the honest common-mode-risk analysis the brief's own section 11 demanded -- it explicitly does NOT claim this upgrades the workstream past what same-author, same-session cross-checking can support, regardless of how many languages are involved |
| 15 | Physical security | NOT_IMPLEMENTED | Cannot be validated by writing software; see ADR-0001 |
| 16 | Tap installation integrity | NOT_IMPLEMENTED | Depends on #15 and on hardware that doesn't exist in this project |
| 17 | Reporting integrity | EXPERIMENTAL | Phase 3 adds key revocation with the VALID_AT_ISSUANCE vs CURRENTLY_TRUSTED distinction (`frontier_verify/keys/`, tested end-to-end including a full revoke-rotate-recover cycle through the live API and SDK), and role-based authorization so reporting integrity claims aren't trivially gameable by an unauthenticated caller (`frontier_verify/api/auth.py`). Truthfulness of the underlying report remains a separate, unsolved problem -- see #5, #7 |
| 18 | Memory wiping | NOT_IMPLEMENTED | |
| 19 | Side-channel mitigation | NOT_IMPLEMENTED | Research track only, per source spec section 48 |
| 20 | Covert-channel monitoring | NOT_IMPLEMENTED | |
| 21 | Covert/hidden computation detection | NOT_IMPLEMENTED | Depends on #8-#10 existing first. `docs/research/hidden-computation.md` maps candidate signal sources and why none are sufficient alone -- mapping the problem, not solving it |
| 22 | Adversarial verification | EXPERIMENTAL | Phase 3 directly attacked the Phase 2 commit-reveal recomputation system per the brief's own section 17 (`tests/adversarial/recomputation/`), which is how the digest-only `recompute_fn` design flaw (see #11) was actually found -- not by inspection, by trying to break it. Also adds role-restriction attack tests (`tests/unit/test_authorization.py`, 12 tests confirming each role genuinely CANNOT do what it shouldn't, not just that auth exists) and key-revocation attack coverage. Still narrow relative to the full attack surface named across three phases' briefs -- see `docs/adversarial-results.md`'s own disclaimer |
| 23 | Stronger/full workload verification | NOT_IMPLEMENTED | RESEARCH-adjacent; depends on #11-#13 |
| 24 | Cryptographic proof of computation | RESEARCH | Explicitly open per source spec section 51; efficient verifiable computation for frontier-scale inference is not a solved problem anywhere, not just in this repo |
| 25 | Composition of multiple trust roots | NOT_IMPLEMENTED | Still exactly one trust root in this project's own code (the verifier key) -- unchanged. New finding this phase, not new code: `docs/hardware/nvat-integration.md` documents a real, shipped example of composed multi-vendor attestation (Intel Trust Authority + NVIDIA NRAS) elsewhere in the industry, which changes this row's honest framing from "unsolved research problem" to "unsolved in this project specifically, operational precedent exists elsewhere" -- worth citing, not yet worth claiming as this project's own capability |

## Reading this table honestly

Six rows say `EXPERIMENTAL`. All six are real, tested code -- not
placeholders -- but every one of them is narrower than its name suggests
once you read the notes column. None of the AI-2040 workstreams whose
entire point is *catching a dishonest, resourced adversary* (compute
accounting, network evidence, recomputation, side channels, covert
computation) have any implementation yet. That's not a criticism to bury;
it's the actual state of the project after Phase 1, and it's the reason
`threat-model.md` exists as a separate document instead of a paragraph at
the bottom of the README.
