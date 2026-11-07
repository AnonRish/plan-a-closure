# Threat Model

## Purpose

The source specification poses thirteen adversarial questions (section 7,
labeled A-M) and says to use them to drive design. This document answers
each one **for the system as it exists today**, not for the system this
project eventually wants to be. Where the honest answer is "nothing stops
this yet," it says so. A threat model that only lists mitigated risks is
marketing, not a threat model.

## Actors and trust

| Actor | Trust level | Why |
|---|---|---|
| Prover | Untrusted | Controls its own machine, its own evidence, and (in Phase 1) has no independent check on anything it reports |
| Verifier process | Trusted, but a single point of failure | Holds the only signing key in this Phase 1 deployment; nothing checks *it* |
| MockAttestationProvider | Explicitly untrustworthy by design | Exists to unblock testing, not to provide assurance -- see its docstring |
| Receipt holder / auditor | Untrusted by the system, trusts only the signature | This is the actor the whole receipt design serves |
| In-memory store | Untrusted, not a root of trust | Section 53 of the source spec explicitly warns against this; Phase 1 violates that warning for expediency and says so |

## The adversarial questions, answered honestly

**A. If a frontier AI company intentionally attempted to evade
verification while controlling its datacenter, what could it fake?**
Everything. `ModelIdentity`, `RuntimeIdentity`, and (via
`MockAttestationProvider`, which exists specifically to fabricate evidence)
`HardwareEvidence` are all either self-reported or synthetic in Phase 1. A
dishonest prover can submit any digests it wants for a model it never ran,
on hardware it doesn't have, and nothing in this codebase independently
constrains those claims. This is precisely why `Policy.allow_mock_hardware`
defaults to `False`, and why no Phase 1 deployment should be described as
providing assurance above L1 (self-reported provenance, tamper-evident
receipt) -- not hardware-verified assurance. See `assurance-model.md`.

**B. What evidence remains trustworthy if the prover is dishonest?**
In Phase 1: none of the evidence *content* -- only the fact that a
*receipt*, once issued, has not been altered since the verifier signed it.
The Ed25519 signature protects receipt integrity in transit and storage; it
says nothing about whether the underlying evidence was truthful when it was
submitted. `tests/security/test_receipt_tamper.py` proves the former. There
is no test that could prove the latter, because Phase 1 has no mechanism
for it.

**C. What happens if the verifier is compromised?**
The verifier's private key can sign arbitrary false receipts, and nothing
downstream would know. Phase 1 has one verifier keypair, generated in
memory at process start (`frontier_verify/api/main.py`), with no rotation,
no revocation list, and no recovery procedure. A compromised verifier
process is a total compromise of everything it has ever signed or ever
will sign. This is tracked as NOT IMPLEMENTED in the coverage matrix, not
glossed over.

**D. What prevents replay attacks?**
Partial mitigation only: `Policy.max_evidence_age_seconds` rejects evidence
whose self-reported `created_at` is too old
(`frontier_verify/policies/evaluator.py`, tested in
`tests/unit/test_policy_evaluator.py`). This is weak on two counts: the
timestamp is self-reported (see I, below), and there is no nonce or
challenge-response, so a captured valid submission could in principle be
resubmitted within the freshness window. Real anti-replay needs
attestation-level nonces bound to the hardware evidence itself, which
requires Phase 2's real attestation provider to exist first.

**E. What prevents partial or selective reporting?**
Nothing. A prover can simply not submit evidence for a workload it doesn't
want observed, and Phase 1 has no way to detect that absence. Detecting
*silence* rather than *lies* is a fundamentally different problem --
it requires the network-evidence / passive-observation workstream (an
independent, prover-uninvolved source of truth about what happened), which
is NOT IMPLEMENTED beyond an interface stub. See ADR-0001 for why that
stub is deliberately unambitious.

**F. What prevents generating evidence from a clean environment rather
than the production environment?**
Nothing, and this is arguably the sharpest gap in Phase 1. Nothing stops a
prover from running `MockAttestationProvider` -- or a real attestation
provider pointed at a decoy machine -- and submitting the result as if it
described production traffic. This is exactly why hardware evidence must
eventually come from a real attestation provider with a hardware root of
trust that binds evidence to a specific physical device the prover does not
fully control, rather than from software self-report. It's also why Phase 1
refuses to call anything above L1 "verified."

**G. What prevents hidden/covert computation?**
Nothing yet. Requires the network evidence and side-channel/covert-channel
research tracks (source spec sections 25, 48), both NOT IMPLEMENTED beyond
the data-model stub in this repo.

**H. What prevents manipulation of network evidence?**
Not applicable in Phase 1 -- no network evidence exists yet for anyone to
manipulate.

**I. What prevents manipulation of timestamps, telemetry, or logs?**
`Evidence.created_at` is self-reported by the prover and completely
unverified by anything in Phase 1; the freshness check in the policy
evaluator (see D) can be trivially defeated by a prover that simply lies
about its own clock when constructing the `Evidence` object. A real
deployment needs either a trusted time source the prover cannot control, or
timestamps cryptographically bound to the attestation hardware itself
(e.g. a TPM-backed clock or an attestation nonce tied to verifier-issued
challenges).

**J. What happens if the hardware root of trust is compromised?**
Out of scope for an honest answer in Phase 1, because no real hardware
root of trust exists yet in this codebase to be compromised. This question
becomes answerable -- and needs a real answer -- the moment Phase 2 lands a
working `NvidiaAttestationProvider`.

**K. What happens if multiple trust roots fail together?**
Phase 1 has exactly one trust root: the verifier's Ed25519 key. There is no
composition, because there is nothing to compose yet. A single point of
failure by construction, not by oversight -- but worth stating plainly
rather than leaving implicit.

**L. What is the smallest trusted computing base?**
Currently: the verifier process holding the signing key, *and* every
prover that self-reports evidence -- which, stated plainly, means the
current TCB includes the exact party this system exists to check on. That
is not a viable end state; it is an honest description of a Phase 1
starting point that Phase 2 (real attestation) and Phase 7 (network
evidence collected without prover cooperation) both exist to shrink.

**M. Which properties can eventually be checked mathematically instead of
trusted?**
Already true today: receipt integrity. Given a receipt and a public key,
`verify_receipt()` is a deterministic, mechanically checkable function --
no trust required, only correct implementation of Ed25519 (delegated to
`pyca/cryptography`, not hand-rolled). Not yet true, and not close: evidence
*truthfulness*. That needs either a hardware root of trust (which is
*trusted*, not mathematically proven -- an important distinction the source
spec itself insists on in section 3) or genuine cryptographic proof of
computation, which remains open research for models at frontier scale. A
recent ICML 2026 paper, *Fingerprinting All AI Cluster I/O Without Mutually
Trusted Processors*, frames this exact gap as structurally analogous to
nuclear and biological arms-control verification, where the thing being
verified is inherently more dual-use than the physical materials those
regimes were built around -- worth reading before assuming a purely
cryptographic answer is close.

## What Phase 1 is honestly good for

Given all of the above: Phase 1 is a correctly-engineered, tested
mechanism for **tamper-evident record-keeping of self-reported claims**. It
is not, and does not claim to be, a mechanism for verifying that a prover
told the truth. Anyone citing this repository as evidence that a lab's
compute claims were "verified" in the AI-2040 sense, based only on Phase 1,
would be misusing it -- and the receipt itself says so, via
`Receipt.limitations`, on every single receipt it issues.
