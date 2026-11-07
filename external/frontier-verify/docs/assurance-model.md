# Assurance Model

## Levels

These are internal Frontier Verify levels. They are not mapped to any
external standard (e.g. an Appia Foundation assessment tier) yet -- doing
that mapping honestly requires an external framework stable enough to map
to, and requires someone other than this project's own author to check the
mapping. See `adoption-strategy.md`.

| Level | Name | What it requires | Phase 1 status |
|---|---|---|---|
| L0 | No verification | Nothing checked, or checks failed | Reachable today (a failed policy evaluation) |
| L1 | Provenance verification | Self-reported evidence, internally consistent, fresh, tamper-evident receipt | **The ceiling of what Phase 1 can honestly issue** |
| L2 | Hardware/platform attestation | Evidence backed by a real hardware root of trust (e.g. NVIDIA Confidential Computing attestation) | Not reachable -- `NvidiaAttestationProvider` raises `NotImplementedError` |
| L3 | Combined hardware + software + execution evidence | L2 plus runtime/container measurement tied to the same attestation | Not reachable |
| L4 | Independent sampled recomputation | L3 plus a separate party re-running sampled chunks of the actual workload and comparing results | Not reachable -- recomputation endpoints return 501 |
| L5 | Hardened multi-layer verification | Composition of multiple independent trust roots, side-channel monitoring, physical security | Not reachable |

## Why L1 is the honest ceiling right now

`frontier_verify/policies/evaluator.py` performs exactly two checks:
whether hardware evidence is marked `mock` (and whether the policy allows
that), and whether the evidence is fresh enough. Passing both of those
checks means the evidence is *internally consistent and recently
submitted* -- it does not mean any of its content is *true*. L1 is defined
to match that reality exactly: provenance record-keeping with a
tamper-evident receipt, nothing more.

The evaluator's code makes this explicit rather than implicit: even when
`hardware_evidence.mock` is `False`, the assurance level returned is still
`L1`, because Phase 1 does not validate a real hardware signature chain
regardless of that flag. Read the comment next to that branch in
`evaluator.py` before assuming a `mock=False` evidence bundle means
anything stronger -- as of Phase 1, it currently can't, because there is no
working non-mock provider to produce one.

## What would need to be true for L2

A framing correction, added this phase after adversarial self-critique
(`docs/reviews/external-review.md`, finding #2): every document in this
project up to this point described real hardware attestation as
*removing* the self-report trust problem. That overstates it. Attestation
would **relocate** trust from the prover to the hardware vendor's root of
trust, its certificate infrastructure, and its incentives not to issue a
false attestation under any circumstance, including legal compulsion.
That's a real improvement -- a large, mostly-disinterested hardware vendor
is a smaller, more scrutable trust surface than an arbitrary self-
interested prover -- but it is not the elimination of a trust assumption,
and this document should not describe it that way going forward.

1. A working `AttestationProvider` implementation (not the current
   `NvidiaAttestationProvider` stub) that produces evidence backed by an
   actual hardware attestation report -- see `hardware-provider-guide.md`
   and ADR-0001 for the current state of NVIDIA's tooling.
2. `frontier_verify/policies/evaluator.py` actually validating that report
   (signature chain against NVIDIA's or another vendor's root of trust),
   not just checking a boolean flag on a pydantic model.
3. A test that proves the evaluator rejects a *forged* hardware evidence
   report, not just a `mock=True` one -- the current adversarial tests only
   cover the latter because the former requires real cryptographic material
   from a real vendor that this repository does not have access to.

None of that exists yet. Anyone building on this repository who needs L2
or above should treat every current receipt as capped at L1 regardless of
what any individual field claims, until the evaluator's own logic changes.
