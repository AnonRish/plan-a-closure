# ADR-0001: Attestation Provider Abstraction, and Deferring the Literal Network-Tap Mechanism

## Status
Accepted (Phase 1)

## Context

The source specification asks for two things that this ADR treats
differently, per the authorization in its section 2 to modify or defer
AI-2040 mechanisms as long as the divergence is documented:

1. Real NVIDIA GPU/NVSwitch attestation integration (sections 12, 66).
2. A network-tap-based mechanism for independent recomputation, described
   in AI-2040's own inference-only proposal as passive network taps
   redirecting copies of traffic to trusted servers (sections 24-25).

## Decision 1: Attestation -- interface now, real integration later, target TBD

**AI-2040 objective:** hardware/platform attestation backing evidence, so
`HardwareEvidence.mock` can genuinely be `False`.

**Original mechanism:** integrate NVIDIA's current attestation SDK
directly.

**Identified limitation:** current-state research (web search performed
during this build, not assumed from training data) found the target itself
is unstable right now. Specifically:

- NVIDIA's standalone "Local GPU Verifier" is explicitly deprecated as a
  stand-alone tool in favor of the Attestation SDK.
- The Python Attestation SDK (`nv-attestation-sdk` on PyPI) is *itself*
  being superseded: NVIDIA's `attestation-sdk` repository describes NVAT
  (the `nvattest` CLI, C++/C API) as the successor of the Python-based
  guest tools in nvTrust, and states the project is in Alpha with the ABI
  and CLI subject to change before stabilization.
- A concrete deprecation date exists: `nv-attestation-sdk`,
  `nv-local-gpu-verifier`, and `nv-ppcie-verifier` v1.x carry a
  `DeprecationWarning` with end of support on **2026-09-15** -- about a
  month after this ADR was written.
- Both paths require a Hopper-or-later GPU with Confidential Computing
  support and either NVML (GPU evidence) or `libnvidia-nscq` (NVSwitch
  evidence) at the C level. This build environment has none of that
  (confirmed via `nvidia-smi`, `nvcc --version`, and `/dev/nvidia*` checks,
  not assumed).

**Alternative adopted for Phase 1:** fix the `AttestationProvider`
interface (`frontier_verify/attestations/base.py`) now -- one method, one
return type, vendor complexity hidden inside implementations -- and ship
exactly two implementations: `MockAttestationProvider` (fabricates
evidence, labeled `mock=True` everywhere including in its own docstring)
and `NvidiaAttestationProvider` (raises `NotImplementedError` rather than
either faking output or committing to an SDK that's mid-deprecation).

**Why this is stronger than committing to the Python SDK today:** writing
a real integration against `nv-attestation-sdk` right now would mean
shipping something that expires by contract in about a month, on a
specification the vendor itself calls a "guest tool" being superseded.
Building the *interface* first means Phase 2 is a matter of implementing
one class against whichever SDK has stabilized by then, without touching
anything that depends on `AttestationProvider` (the evidence schema, the
policy evaluator, the API, the CLI, the SDK) -- all of which are already
built, tested, and shipped in Phase 1 against the interface, not the
vendor.

**Preserved assurance properties:** none yet -- Phase 1 grants no assurance
above L1 regardless of this decision. What's preserved is *optionality*:
Phase 2 isn't locked into a specific SDK's shape.

**New assumptions:** that a working NVIDIA GPU attestation path will exist
in some form by the time Phase 2 starts, and that re-running this same
current-state-research step then (not relying on this ADR's findings,
which will be stale) is mandatory -- restated explicitly in
`nvidia_provider.py`'s own docstring so it isn't only here.

**Lost assurance properties:** none -- Phase 1 never claimed L2 to begin
with.

**Maturity:** `NvidiaAttestationProvider` is `NOT_IMPLEMENTED`. The
interface it implements is `EXPERIMENTAL`.

**Remaining risks:** the SDK landscape could shift again before Phase 2
starts; the interface itself could turn out to be wrong in some way that
only becomes apparent once real evidence needs to flow through it (e.g. if
NVAT's evidence shape doesn't map cleanly onto a single `HardwareEvidence`
object). That's a real risk this ADR can't resolve in advance -- it can
only make the eventual fix cheap by keeping the blast radius to one file.

## Decision 2: Physical network taps -- define the data model, defer the mechanism entirely

**AI-2040 objective:** independent, prover-uninvolved evidence of network
traffic, as a foundation for random partial recomputation and for detecting
selective/hidden reporting (source spec sections 25, 45; threat model
questions E and G).

**Original mechanism:** physical network taps, installed with documented
chain-of-custody and tamper evidence, copying traffic to trusted servers.

**Identified limitation:** this is a hardware and datacenter-operations
problem, not a software problem. Nothing written in this sandbox -- or
arguably in any pure software repository -- can honestly claim to validate
physical tap integrity, tamper evidence, or installation procedure. The
source spec itself says this directly in section 25: "Do not fake physical
optical taps... Do not claim software packet capture proves physical
properties that require actual hardware." Building a software simulation of
a network tap and calling it progress on this workstream would be exactly
the kind of fabrication section 4 prohibits, dressed up as an
"abstraction."

**Alternative adopted for Phase 1:** nothing. No `NetworkEvidence` class,
no capture interface stub, no simulated packet representation. The
workstream is recorded as `NOT_IMPLEMENTED` in the coverage matrix with no
code gesturing otherwise.

**Why this is more honest than a stub:** a stub interface for something
whose entire value proposition is "this happened somewhere software cannot
see" risks implying more progress than a documentation entry does. Compare
to Decision 1: the `AttestationProvider` interface stub is legitimate
because attestation *evidence*, once produced by real hardware, is
something software can meaningfully validate -- the interface is doing
real work fixing that validation's shape. A network-tap interface stub
would fix the shape of something this repository has no way to test even
partially, which is a different and weaker kind of "progress."

**Preserved assurance properties:** none claimed, none to preserve.

**New assumptions:** that this workstream requires a real datacenter
deployment and physical security cooperation from a prover before any
software work on it is meaningful -- i.e., it is not purely an engineering
problem this project can solve in isolation, unlike Decision 1.

**Lost assurance properties:** none.

**Maturity:** `NOT_IMPLEMENTED`.

**Remaining risks:** deferring this entirely means Phase 1 has no answer to
threat-model questions E, G, and H (selective reporting, hidden
computation, network evidence manipulation) beyond "not addressed yet."
That's an accurate risk statement, not a mitigated one -- see
`threat-model.md`.
