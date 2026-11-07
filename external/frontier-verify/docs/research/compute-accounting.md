# Compute Accounting: Research Notes

MATURITY: NOT_IMPLEMENTED. No code in this repository measures or
verifies GPU-hours, utilization, or cluster scale. This document scopes
the problem rather than solving it, per the brief's instruction to
"implement only what can genuinely be supported."

## What can actually be independently observed, and by whom

| Signal | Independently observable by a THIRD PARTY? | Notes |
|---|---|---|
| GPU-hours claimed by the prover | No | Self-reported unless tied to attestation with a trusted clock |
| GPU-hours from cloud billing records | Partially | Requires the cloud provider's cooperation and honesty -- moves the trust problem, doesn't remove it |
| Accelerator utilization (`nvidia-smi`-style metrics) | No, if collected by the prover's own agent | Same self-report problem as evidence in general -- see `docs/threat-model.md` |
| Utilization via a real hardware attestation channel with signed telemetry | Possibly, once Phase 2 hardware attestation exists | Depends entirely on whether NVIDIA's (or another vendor's) attestation covers utilization counters, not just device identity -- unconfirmed, needs its own research pass against `docs/hardware/nvidia-attestation.md`'s findings |
| Cluster scale (node/GPU count) | Partially, via network evidence (NOT_IMPLEMENTED) or physical inspection | Neither exists in this project |
| Inference volume (request counts) | No | Same self-report problem; a prover can simply not report requests, same as attack #8 in `docs/adversarial-results.md` |

## Attacks this workstream would need to address

- **Under-reporting**: claim less compute than actually used, to appear
  compliant with a cap or evade a usage-based obligation.
- **Over-reporting**: claim MORE compute than actually used -- less
  obviously an attack, but relevant if compute claims feed into anything
  with an incentive to inflate them (e.g., demonstrating scale to
  investors or regulators).
- **Workload substitution**: report accounting for a cheap workload while
  actually running an expensive/sensitive one, or vice versa.
- **Idle GPU padding**: report utilization from idle-but-powered hardware
  to inflate apparent compute usage.
- **Hidden jobs**: run accounting-invisible workloads alongside reported
  ones -- structurally the same problem as `docs/adversarial-results.md`
  attack #12 (hidden computation), applied specifically to accounting
  rather than model/runtime identity.
- **Shared infrastructure**: attributing compute correctly when multiple
  tenants or workloads share the same physical hardware -- a real
  measurement problem even for an HONEST prover, not just an adversarial
  one.
- **Measurement manipulation**: tampering with the counters or telemetry
  source itself, upstream of anything Frontier Verify would ever see.

## Why nothing is implemented yet

Every plausible accounting signal either (a) requires real hardware
attestation with utilization telemetry included, which is unconfirmed to
even exist in NVIDIA's current tooling and hasn't been researched
specifically (see the open question in the table above), or (b) requires
network evidence / physical observation, both NOT_IMPLEMENTED for the
reasons in `docs/network-evidence-protocol.md`, or (c) requires trusting
exactly the party (the prover, or a cloud provider on the prover's behalf)
this whole project exists to avoid trusting unconditionally. Building a
compute-accounting module today would mean building it entirely on
self-reported numbers with a thin schema wrapper -- decorative, not
functional, exactly what the brief prohibits.

## Next research step

Determine whether NVIDIA's attestation evidence (or NVSwitch telemetry)
includes anything utilization-related that's covered by the hardware root
of trust, as opposed to being a separate, unattested metrics stream. This
is answerable by reading NVAT's evidence schema more closely than
`docs/hardware/nvidia-attestation.md` did this phase, and should happen
before any accounting code is written, not after.
