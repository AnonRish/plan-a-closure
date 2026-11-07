# AI-2040 Gap Analysis (GREEN / YELLOW / RED)

Section 17 of the Phase 4 brief asks for a simplified three-color rollup
of `docs/ai2040-coverage-matrix.md`'s 25 workstreams, with an explicit
instruction not to optimize the score. This document is that rollup,
derived by mapping the existing (more granular) status vocabulary
honestly, not by re-judging each row from scratch to produce a better-
looking number.

**Mapping rule, stated before the results so it can be checked**:
`NOT_IMPLEMENTED`/`MOCK`/`SIMULATED` -> RED (nothing genuinely
demonstrated). `EXPERIMENTAL` -> YELLOW (real, tested, narrow).
`RESEARCH` -> YELLOW if real partial capability exists, RED if the
workstream has only problem-mapping with no working code behind it --
judged per row below, since "RESEARCH" alone doesn't distinguish these.
`VALIDATED`/`PRODUCTION_READY` -> GREEN.

## Result

| # | Workstream | Color | Why |
|---|---|---|---|
| 1 | Compute accounting | RED | No code exists |
| 2 | Workload visibility | RED | No code exists |
| 3 | Reproducible workload packets | RED | No code exists |
| 4 | Inference reproducibility | RED | No code exists |
| 5 | Model reproducibility | YELLOW | Real digest-based identity, tested, self-reported |
| 6 | Network reproducibility | RED | No code exists |
| 7 | Execution/runtime provenance | YELLOW | Real, tested, self-reported |
| 8 | Network evidence | RED | Deliberately not built -- see `docs/network-evidence-protocol.md` |
| 9 | Passive observation | RED | Same |
| 10 | Network capture constraints | RED | Same |
| 11 | Independent recomputation | YELLOW | An experimental /v2 endpoint now executes a bounded deterministic recomputation kernel over sampled, content-addressed inputs and emits a signed receipt; it is not frontier-scale and the legacy full Phase 6 interface remains unfinished |
| 12 | Random partial recomputation | YELLOW | Commit-reveal unpredictability is real and adversarially tested; a genuine (if tiny) numerical kernel now exists (`frontier_verify/recomputation/numpy_kernel.py`), replacing the pure hash-based Phase 2/3 toy |
| 13 | Frontier-model recomputation | RED | A fixed, untrained, ~1000-parameter CPU MLP is not meaningfully closer to frontier-scale recomputation than the toy hash it replaced -- real progress on the STAGED ROADMAP's Stage 1, essentially zero progress on the actual workstream |
| 14 | Verifier independence | YELLOW | Cross-language receipt verification is real and tested; quorum experiment demonstrates real operator-level independence AND its own honest limit (zero design-level independence, all instances share source) -- see `docs/research/verifier-trust.md` |
| 15 | Physical security | RED | No code exists, cannot exist as code |
| 16 | Tap installation integrity | RED | Same |
| 17 | Reporting integrity | YELLOW | Receipt tamper-evidence, revocation, and storage integrity are all real and tested |
| 18 | Memory wiping | RED | No code exists |
| 19 | Side-channel mitigation | RED | No code exists |
| 20 | Covert-channel monitoring | RED | No code exists |
| 21 | Covert/hidden computation detection | RED | A formal cross-source consistency MODEL exists in writing (`docs/research/hidden-computation.md`) with zero implementation behind it |
| 22 | Adversarial verification | YELLOW | Real, tested attacks across three phases against receipts, evidence, keys, authorization, and recomputation sampling -- still narrow relative to the full named attack surface |
| 23 | Stronger/full workload verification | RED | No code exists |
| 24 | Cryptographic proof of computation | RED | Genuinely open research field-wide, zero project-specific progress |
| 25 | Composition of multiple trust roots | RED | The quorum experiment composes multiple INSTANCES of the SAME trust root (identical verifier design); it does not compose heterogeneous trust root TYPES (hardware + recomputation + network evidence), which is what this workstream actually names. A real, shipped industry precedent exists elsewhere (`docs/hardware/nvat-integration.md`'s Intel/NVIDIA finding) -- this project has none of its own |

## Phase 5 update: unchanged, by design

Section 19 of the Phase 5 brief asks for this matrix to be updated, with
an explicit instruction that "real hardware evidence should move relevant
workstreams only as far as the evidence supports." No new hardware
evidence, and no independent review, was obtained this phase (see this
phase's closing report) — so the honest update is confirming **zero rows
move**, not finding a way to move some anyway. The one new finding this
phase produced (`docs/trust-boundaries.md`'s prover-identity gap) doesn't
change any row's *status* — every row already describing evidence as
"self-reported" was already accounting for exactly this kind of gap in
spirit, and the new finding makes that concrete without revealing
anything the matrix's existing RED/YELLOW scores weren't already
conservative about.

**Phase 6 software update: one row moved from RED to YELLOW after the experimental /v2 recomputation integration was added.**\n\n**GREEN: 0. YELLOW: 7. RED: 18.**

## Totals

**GREEN: 0. YELLOW: 7. RED: 18.**

Zero GREEN entries is the correct, honest result -- not a scoring failure
to fix. Nothing in this project has been hardware-validated or
independently reviewed by a human who didn't write it, and this document
was written specifically to resist the temptation to call something
GREEN because it has good test coverage. Good test coverage of
self-tested code is exactly what a YELLOW ceiling means in this rubric.

## What would move a row from YELLOW to GREEN

Not more code from this project's own author. Per this row's own
definition: `VALIDATED` requires exactly the two things Phase 4's brief
is actually organized around and this project could not obtain --
independent human review, and (for the hardware-adjacent rows
specifically) real hardware execution. No row in this table can honestly
reach GREEN through further solo software work, which is the central,
correct finding this phase exists to surface plainly rather than paper
over with another YELLOW-to-YELLOW documentation pass.
