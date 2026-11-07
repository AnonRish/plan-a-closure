# Trust Model

## The question this document answers

Section 6 of the Phase 3 brief poses six questions directly. Answered
honestly, for the system as it exists after this phase -- not the system
this project eventually wants to be.

**Why should an AI company trust the verifier?** Today: only because it's
running its own deployment, or because it has some other reason (contract,
reputation) to trust whoever operates it -- nothing in the cryptography
forces this. See "What happens if the verifier is malicious," below.

**Why should an external party trust the verifier?** Same answer, and this
is the sharper version of the question: an external party has even less
reason than the AI company itself. This is `docs/adoption-strategy.md`'s
named "biggest unresolved barrier," restated here as a trust question
rather than an adoption one -- they're the same problem.

**Why should an AI company trust the receipt?** Because the signature is
real cryptography (Ed25519, independently re-verified by two other
implementations -- `docs/protocol/independent-verification.md`) -- but a
receipt only attests that evidence satisfied a policy's checks, not that
the evidence was true. See `docs/threat-model.md`.

**Why should an auditor trust the evidence?** They shouldn't, categorically
-- see `docs/adversarial-results.md`. Evidence is self-reported by the
prover in every case this repository currently supports.

**Why should a regulator trust the policy?** Only if they know who wrote
it, and whether that party had an incentive to write a weak one. This is
exactly why `POLICY_AUTHORITY` is now a role separate from `PROVER` (see
below) -- but knowing WHO holds a `POLICY_AUTHORITY` key, and whether they
have a real incentive not to game it, is a real-world governance question
this software cannot answer.

**What happens if the verifier is malicious?** It can sign arbitrary false
receipts, and -- unchanged from Phase 2's finding -- nothing detects this
after the fact. Revocation (this phase) lets a THIRD PARTY who learns of a
compromise mark a key as untrusted going forward; it does not detect
compromise on its own.

## Actors, formalized

The brief's section 7 asks for five roles to be explicitly distinguished.
Four now exist as real, enforced roles
(`frontier_verify/api/auth.py::Role`, tested in
`tests/unit/test_authorization.py`); the fifth needs no credential by
design.

```
PROVER              -- submits evidence about its own compute, triggers
                        verification of it
                        |
                        | evidence
                        v
                     VERIFIER          -- evaluates evidence against policy,
                        |                 issues signed receipts. Holds the
                        |                 signing key (via KeyProvider).
                        | receipt
                        v
                RECEIPT CONSUMER       -- needs no role or credential at
                                          all -- POST /v1/receipts/verify
                                          and the standalone verifiers are
                                          deliberately open to anyone

Separately:

POLICY_AUTHORITY
        |
        | policy
        v
     VERIFIER

TRUST-ROOT AUTHORITY  (= ADMINISTRATOR role today)
        |
        | key rotation / revocation
        v
     VERIFIER
```

`AUDITOR` (read-only across verification records, evidence/attestation
validity, and key status) doesn't appear in the brief's five-role diagram
by that name, but is the closest real match to "receipt consumer with
elevated read access" and already existed conceptually in
`docs/architecture.md`'s actor list -- kept as a fourth role rather than
folded into `RECEIPT CONSUMER`, since receipt consumers specifically need
NO credential, while an auditor reading verification records does.

## Which roles may be colocated, and which shouldn't be

| Combination | Safe to colocate? | Why |
|---|---|---|
| `PROVER` + `AUDITOR` | Yes | A prover checking its own past submissions isn't a conflict of interest |
| `ADMINISTRATOR` + `AUDITOR` | Yes | Both are oversight functions over the verifier itself |
| `PROVER` + `POLICY_AUTHORITY` | **No** | The one combination that maps to an actual attack -- a prover that can also write the policy checking its own evidence can simply write a policy that always passes. `tests/unit/test_authorization.py::test_prover_cannot_define_a_policy` exists specifically to keep this separation real, not aspirational |
| `PROVER` + `ADMINISTRATOR` | **No, for a high-assurance deployment** | A prover with control over the verifier's signing key could, in principle, coordinate signing receipts for evidence that never should have passed -- weaker attack than the policy case (still requires the evidence to structurally pass evaluation), but still a real conflict of interest worth naming |
| `POLICY_AUTHORITY` + `ADMINISTRATOR` | Contextual | No direct attack this project's current logic exposes, but combining "who decides what's checked" with "who controls the signing key" concentrates trust in a way a genuinely independent verifier should avoid |

The demo script (`examples/local-demo/run_demo.py`) deliberately grants
itself every role at once, and says so in its own comment -- that's
correct for a single-script walkthrough and wrong for anything resembling
a real deployment.

## What this system cannot do regardless of role separation

Role separation constrains WHO can call WHICH endpoint. It does not, and
cannot, constrain whether the PROVER is being honest, whether the
POLICY_AUTHORITY wrote a meaningfully strict policy, or whether the
ADMINISTRATOR's key material is actually secure
(`docs/protocol/key-management.md`'s plaintext-on-disk caveat for
`LocalFileKeyProvider` still applies regardless of who's allowed to call
`rotate-key`). Trust separation at the API layer is necessary and now
real; it is not sufficient, and nothing in this document should be read as
claiming otherwise.
