# Verifier Trust: Research Notes

The question this document exists to take seriously: an external party
still has no cryptographic reason to trust a Frontier Verify deployment it
doesn't operate itself. Section 9 of the Phase 4 brief lists eleven
candidate mitigations and explicitly warns against claiming any single one
solves this. Each evaluated honestly, several backed by real work done
this phase rather than left as a bare list.

| Mitigation | What it would actually buy | Real status in this project |
|---|---|---|
| Reproducible builds | An external party can confirm the verifier binary they're trusting matches the published source -- removes "trust the build pipeline," not "trust the operator" | **Demonstrated this phase**, empirically -- `docs/research/reproducible-builds.md`. Real, bit-identical, measured. Does not touch operator trust at all |
| Independently reproduced binaries | A third party rebuilding and hash-matching is stronger evidence than the same party rebuilding twice | Enabled by the above, not yet exercised by an actual third party -- no third party exists yet in this project's history |
| Remote attestation of the verifier itself | Proof the verifier is running unmodified code on hardware with its own root of trust -- would answer "is this verifier honest" the same way GPU attestation answers "is this GPU honest" | **Not implemented, not prototyped.** A real, structurally sound idea -- the verifier process itself becoming a Prover to some OTHER verification layer -- but this project has exactly the same hardware-access blocker for this as for GPU attestation, and building it would face the identical bootstrapping question one level up: who attests to THAT attester? |
| Confidential computing (for the verifier) | Verifier logic runs inside a TEE the operator can't inspect or tamper with even with full infrastructure access | Same blocker as above -- and a real open question independent of hardware access: does this project's threat model even want the OPERATOR unable to inspect their own verifier? An operator debugging a real incident needs exactly the access a TEE would deny them |
| Transparent logs (append-only, publicly auditable) | Detects a verifier that issues DIFFERENT receipts to different parties for the same input (equivocation) -- the receipt-signing analog of Certificate Transparency | **Not implemented.** Genuinely promising, low-hardware-cost direction -- unlike hardware attestation, a Merkle-tree-based transparency log is pure software and could plausibly be prototyped without external resources. Flagged as the most promising NEXT concrete step, not attempted this phase given time went to the items below |
| Append-only evidence | Prevents an operator from quietly deleting or rewriting evidence after the fact | **Partially present already**, not by this name: `ContentAddressedStore` (Phase 2) makes stored evidence tamper-EVIDENT (corruption is detected on read), but nothing prevents an operator with filesystem access from deleting an entry outright -- detection of tampering is not the same as prevention of deletion |
| Multiple independent verifiers / quorum | Distributes trust across operators who (ideally) don't collude -- a relying party trusting the MAJORITY rather than any one operator | **Built and tested this phase** -- `frontier_verify/quorum/`, real subprocess-isolated instances, agreement AND disagreement detection both demonstrated. See "What quorum actually buys," below, for the honest limit |
| Verifier diversity | Multiple INDEPENDENTLY-DESIGNED (not just independently-operated) verifier implementations, so a design flaw doesn't affect all of them | Genuinely started, not completed: `docs/protocol/independent-verification.md`'s cross-language receipt verifier is diversity for the NARROW receipt-checking function; the quorum experiment's three instances are diversity of OPERATION, not of DESIGN (all three run identical source) -- these are two different, both partial, answers |
| Deterministic policy evaluation | A given (evidence, policy) pair always produces the same decision, regardless of which verifier evaluates it -- necessary for quorum agreement to mean anything | **Already true, and now tested as a load-bearing property, not just assumed**: `test_quorum_agrees_on_honest_evidence` directly confirms three independent instances reach identical decisions on identical input |
| Public verification keys | Anyone can check a receipt's signature without asking the verifier -- the core design goal of receipts since Phase 1 | **Already fully real** -- `GET /v1/verifier/public-key/{key_id}`, the standalone verifiers, `docs/receipt-specification.md` |
| Public conformance tests | An external party can confirm ANY verifier implementation (not just this one) meets the protocol's requirements | `tests/conformance/` exists and is real, but it tests THIS repository's own implementation against itself -- nothing publishes these as an independently-runnable conformance SUITE a different implementation could run against itself. A real gap, not attempted this phase |

## What quorum actually buys, stated precisely

The quorum experiment (`frontier_verify/quorum/`,
`tests/integration/test_quorum.py`) tested exactly the question section
10 poses: does having multiple verifiers materially improve assurance if
they share the same design? The honest answer, backed by what was
actually built:

**Yes, for operator-level failures.** Three independently-keyed,
independently-operated verifier instances (real, memory-isolated OS
processes) genuinely catch a scenario where ONE operator is
misconfigured, compromised, or dishonest, WITHOUT a relying party needing
to know in advance which one -- `test_quorum_detects_disagreement_from_a_misconfigured_member`
demonstrates this directly, not hypothetically.

**No, for design-level failures.** All three instances run byte-identical
source code. A bug or a deliberate flaw in
`frontier_verify/policies/evaluator.py` -- the shared evaluation logic
every instance imports -- would produce IDENTICAL wrong answers on all
three, and quorum agreement would look exactly like quorum agreement on a
correct answer. This is not a hypothetical concern raised for
completeness; it's the literal bug class the quorum test suite's own
docstring names, because a real bug of exactly this shape (shared module
caching creating FALSE independence) was found and fixed while building
this experiment -- see `tests/integration/test_quorum.py`'s own module
docstring for that history.

**The honest overall statement**: a quorum of instances of the SAME
implementation raises the cost of a single dishonest OPERATOR to needing
to compromise multiple operators. It does nothing whatsoever against a
flaw in the shared DESIGN every instance runs. Both of these are real,
different, and this project has now empirically distinguished them rather
than asserted the distinction in prose alone.

## Most promising next step, in priority order

1. **A transparency log.** Pure software, no hardware blocker, directly
   answers a real attack (verifier equivocation) this project has not
   addressed at all. The single highest-value NEW mechanism not yet
   attempted.
2. **A genuinely independently-DESIGNED second full verifier** (not just
   a second receipt-checker) -- would need a different person, likely in
   a different language, ideally without reading this project's source
   first. Requires the same "needs a human who isn't the author" resource
   this entire phase keeps running into.
3. **Public, runnable conformance tests** a third-party implementation
   could execute against itself -- lower effort than #2, meaningful
   partial progress toward the same goal.
