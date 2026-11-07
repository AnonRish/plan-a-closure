# Hidden Computation: Research Notes

MATURITY: NOT_IMPLEMENTED. The central question, per the brief: "If the
prover controls the datacenter, how can an independent verifier detect
computation that the evidence pipeline does not report?" This document
maps the space; nothing here claims to solve it.

## Candidate signal sources, and why none of them are sufficient alone

| Source | What it could show | Why it's not sufficient alone |
|---|---|---|
| Network observation | Traffic volume/pattern inconsistent with declared workload | Requires physical/network infrastructure this project deliberately does not fake -- see `docs/network-evidence-protocol.md` |
| Accelerator telemetry (utilization, memory occupancy) | GPU busy when no declared workload should be running | Telemetry collected by the prover's own agent is just more self-reported evidence -- see `docs/threat-model.md`, Q.A. Only useful if it comes through a channel the prover cannot control, which circles back to needing real hardware attestation with telemetry coverage (open question, see `docs/research/compute-accounting.md`) |
| Power/thermal signals | Correlate power draw with claimed idle/active state | Legitimately accessible only with physical instrumentation or a trusted hardware channel; also a genuinely hard signal-processing problem (workload-dependent power signatures, noise) that this project has not attempted |
| Scheduling evidence (job scheduler logs) | Cross-check declared jobs against what was actually scheduled | The scheduler is inside the prover's infrastructure -- same self-report problem, one layer up |
| Job accounting systems | Same as above | Same limitation |
| Independent recomputation | Confirms SAMPLED declared chunks were computed as claimed | Says nothing about UNDECLARED computation -- recomputation only checks things that were reported in the first place (see `docs/research/recomputation.md`) |
| Randomized challenges to the prover ("prove you were NOT running X at time T") | Forces a response that's costly to fake | An unexplored, genuinely different mechanism from sampling-based recomputation -- proving a negative is a different cryptographic problem (closer to proof-of-idle or capacity-commitment schemes in other domains) than proving a positive claim was computed correctly. Not designed or implemented here |
| Cross-source consistency (agreement between two or more independently-collected signals) | Raises the cost of successfully hiding computation, since the prover has to fake multiple consistent stories | The most promising DIRECTION found in this research pass, precisely because it doesn't rely on any single trusted channel -- but "promising direction" is not an implementation, and this project has not built even a first cross-source consistency check |

## The honest layered picture

Every candidate signal above is EITHER (a) collected by the prover's own
infrastructure, and therefore no more trustworthy than any other
self-reported evidence, or (b) requires physical/network infrastructure
this project does not have and will not fake, or (c) both. There is no
signal source available to this project today that is BOTH independently
collected AND currently implementable in software alone. This is not a
gap in effort -- it's the actual shape of the problem, and stating it
plainly is more useful than a NetworkEvidence class that implies otherwise.

## Layered evidence model (design direction, not implementation)

The most defensible direction found in this research pass: no single
signal source needs to be individually unforgeable if enough
INDEPENDENTLY-SOURCED signals must be consistent with each other for a
prover's story to hold together. A prover controlling its own scheduler
logs, its own telemetry agent, AND needing those to also stay consistent
with something it does NOT control (real hardware attestation, eventually
real network evidence) raises the cost of hiding computation even before
any single one of those sources is individually trustworthy. This is a
direction for future work, not a mechanism implemented in this
repository -- there is no code here implementing cross-source consistency
checking, and building a schema for it now, with nothing behind it, would
be exactly the kind of scaffolding with no real capability this project's
own discipline (see `docs/adr/0001...`, the network-tap deferral
reasoning) argues against.

## What would need to exist before this workstream could move to EXPERIMENTAL

1. Real hardware attestation (Phase 2+) covering more than device identity
   -- ideally utilization/activity telemetry with the same hardware-root-
   of-trust backing, per the open question in
   `docs/research/compute-accounting.md`.
2. At least one signal source genuinely outside the prover's control --
   network evidence is the most obvious candidate, and remains
   NOT_IMPLEMENTED by deliberate choice (`docs/network-evidence-protocol.md`).
3. A defined cross-source consistency check with a stated, testable
   claim about what inconsistency would actually mean -- not yet designed.

## A formal cross-source consistency model (Phase 3 -- design, not implementation)

Phase 3's brief asks specifically: "if one evidence source is dishonest,
can discrepancies be detected using independent sources?" A model precise
enough to eventually test, still entirely undeveloped in code:

**Sources, and what controls each** (extending the table above with an
explicit control axis):

| Source | Controlled by |
|---|---|
| Scheduler logs | Prover (its own infrastructure) |
| Telemetry agent | Prover |
| Hardware attestation (once real) | Hardware vendor's root of trust -- NOT the prover, once Phase 2+ lands |
| Network evidence (if ever built) | Whoever operates the physical tap -- ideally not the prover |
| Recomputation results | Verifier, over evidence the prover already submitted |

**The consistency claim, stated precisely enough to be falsifiable
later**: for a given time window and a given physical device, the
following should be mutually derivable from each other within a stated
tolerance -- (a) declared workload duration from scheduler logs, (b) GPU-
active time from telemetry, (c) hardware attestation's device-busy state
if the attestation channel ever reports it (unconfirmed --
`docs/research/compute-accounting.md`'s open question), (d) network
traffic volume if network evidence ever exists. **A discrepancy between
any two sources that are controlled by DIFFERENT parties is a genuine
finding.** A discrepancy between two sources BOTH controlled by the
prover (e.g., its own scheduler logs vs. its own telemetry agent
disagreeing with each other) is much weaker evidence -- a dishonest prover
controlling both can make them agree with each other while both lie
equally, which is exactly why this model requires at least one source
outside prover control to be meaningful at all, restating this document's
central finding in formal terms rather than prose.

**What this model does NOT claim**: that building it would DETECT hidden
computation with any stated confidence level -- no false-positive/false-
negative rates are estimated here, because doing so honestly would
require real data from real deployments this project doesn't have.
Restating the finding above once more for emphasis: two prover-controlled
sources agreeing is not a finding. This model is a specification of what
"consistency" would need to mean, not a working detector.
