# Independent External Review

**STATUS: NOT OBTAINED.** No human who did not write this system has
reviewed it. This document does not contain a review — it contains
everything a real one needs, and, separately and clearly labeled,
adversarial self-critique that is explicitly **not** a substitute for one.

## Why this document does not simulate a reviewer

Section 8 of the Phase 4 brief asks for a "blind review" — someone given
the repository without the author's explanation, asked to reconstruct
what the system claims, what it proves, and where it breaks. I am the
author. I wrote every line across four phases with full memory of doing
so, in the same session lineage each time. There is no way for me to
"forget" that context and produce output that is genuinely blind, and
labeling self-critique as if it came from someone else would be
fabricating a person's opinion — a different and worse thing than simply
not having a review yet. `docs/protocol/independent-verification.md`
already establishes exactly this limitation for the standalone verifiers;
it applies with even more force here, where the thing being "reviewed" is
the entire system's own reasoning about itself.

This is not a minor process gap. Independent review specifically matters
for AI-assisted code for reasons with real evidence behind them, not just
in principle: <cite index="46-3">research on Chrome extensions found developers using AI coding assistants were more likely to introduce security vulnerabilities while being more confident their code was secure.</cite> In real open-source projects, AI-authored contributions have needed heavy correction — <cite index="46-4">one Servo browser engine experiment required 113 revisions across a single contribution, and the Cockpit project found that roughly half of its AI-generated code reviews were pure noise.</cite> This project's own three-phase pattern of finding real bugs specifically when *actually running* code (a digest mismatch, a queue deadlock, a dropped executable bit, a false-independence bug in the quorum test itself) is a smaller-scale version of the same phenomenon: things that look right on inspection and are wrong in practice. Self-review by the same process that wrote the code is real, and has caught real things — but it structurally cannot catch a shared blind spot, by definition.

## Review readiness package

For whoever ends up doing this. Section 7's own challenge questions,
restated as a direct checklist rather than left as prose:

1. **How could a sophisticated dishonest prover defeat this system?**
   Start at `docs/threat-model.md` and `docs/adversarial-results.md` — if
   you find an attack not listed in either, that alone is a finding worth
   reporting regardless of anything else.
2. Reconstruct, from the repository alone, before reading this section:
   what the system **claims**, what it **actually proves**, what it
   **assumes**, and where it can be **defeated**. Then compare your
   answer against `docs/threat-model.md`'s own "What Phase 1 is honestly
   good for" section and `docs/assurance-model.md`. **Any mismatch
   between your independent read and what the docs claim is a
   documentation or design defect**, full stop, regardless of which side
   turns out to be "right."
3. Specifically stress: `docs/receipt-specification.md` (canonicalization
   and signatures), `docs/protocol/key-management.md` (key lifecycle),
   `docs/protocol/auth-model.md` (authorization), `docs/research/recomputation.md`
   and `docs/adversarial-results.md` (recomputation), `docs/network-evidence-protocol.md`
   (evidence completeness and hidden computation), `docs/assurance-model.md`
   (whether the L0-L5 claims are actually earned by what the code does).
4. Public conformance tests (`tests/conformance/`) are runnable directly
   — `pytest tests/conformance/ -v` — and are a legitimate starting point
   for probing the implementation without needing to read every line
   first.

## Adversarial self-critique (NOT independent review — read the section above again before trusting this list)

Three findings from re-examining this system adversarially this phase,
none previously documented across three prior phases:

1. **No audit trail for administrative actions.** `POST
   /v1/verifier/rotate-key` and `POST /v1/verifier/revoke-key` require
   the `ADMINISTRATOR` role, but multiple keys can hold that role
   simultaneously (`FV_API_KEYS` supports any number of
   `key:ADMINISTRATOR` entries), and **nothing records which specific
   credential performed which action, when.** `revocation_reason()`
   stores the human-supplied reason text, not an actor identity or
   precise timestamp beyond filesystem mtimes. If two administrators
   exist and one revokes a key maliciously, there is currently no way to
   determine which one did it. Found by directly grepping the codebase
   for logging — there is none — not by reasoning about the design in
   the abstract.
2. **Hardware attestation, if it existed, would not eliminate a trust
   problem — it would relocate it to a larger, less accountable party.**
   Every document in this repository frames real hardware attestation as
   the fix for evidence being self-reported. That's true as far as it
   goes, but it trades "trust the prover" for "trust NVIDIA's root of
   trust, NVIDIA's certificate infrastructure, and NVIDIA's own
   incentives not to issue a false attestation under any circumstance,
   including legal compulsion in whatever jurisdiction NVIDIA operates
   under." Nothing in this project's design gives an auditor any way to
   independently confirm NVIDIA itself is behaving honestly at the root.
   This is a known, general property of hardware-root-of-trust designs,
   not specific to NVIDIA — but this repository's own documentation has
   consistently described attestation as removing a trust assumption
   rather than substituting a different, harder-to-verify one, and that
   framing should be corrected.
3. **Supply-chain risk to the project itself has never been discussed.**
   Every threat model in this repository analyzes the PROVER as the
   adversary. None discuss a malicious CONTRIBUTOR to Frontier Verify's
   own source — a plausible-looking pull request that weakens
   `frontier_verify/policies/evaluator.py`'s checking in a subtle way, for
   instance. `docs/adversarial-results.md`'s attack #15 ("compromised
   management plane") gestures at infrastructure compromise but not
   specifically at the open-source contribution path as its own attack
   surface, which is a real gap given this project explicitly aspires to
   external contribution (`CONTRIBUTING.md`).

## How to actually get a real reviewer

Concrete options, not just an aspiration:

- **AI safety / governance research communities** where a project on
  compute verification is directly on-topic: LessWrong, the EA Forum, and
  <cite index="27-2">aisafety.com maintains a directory of AI safety communities and organizations</cite> worth checking for currently active groups. <cite index="27-1">Programs like SERI MATS pair mentees with mentors on AI safety research including technical governance work</cite> — a project like this is a plausible fit for that kind of pairing, even outside a formal program, as a concrete ask to someone in that community.
- **A GPU access provider's own technical community** — if pursuing real
  hardware validation (`docs/hardware/nvidia-real-test.md`) through a
  specific cloud provider, their forums/Discord often have people willing
  to sanity-check an attestation integration specifically, as a narrower,
  easier ask than "review the whole project."
- **This project's own eventual `CONTRIBUTING.md` process** — once (if)
  this repository has a public remote, opening it for external PRs and
  issues is itself a form of ongoing informal review, weaker than a
  dedicated read-through but real and cumulative.
