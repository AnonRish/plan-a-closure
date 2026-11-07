# Network Evidence Protocol

MATURITY: NOT_IMPLEMENTED (deliberately -- see below). This document
defines the abstraction the brief asks for (section 19) in writing, without
shipping code that would imply more capability than exists. This updates,
rather than reverses, ADR-0001's Phase 1 decision to defer this workstream
entirely -- see "What changed since ADR-0001" below.

## What software capture can prove, and what it cannot

**Can prove**, if implemented: that a specific process, at a specific
point in the pipeline, observed specific bytes at a specific time, and
that a chain of custody for those bytes from observation to storage is
intact (via hashing, similar to how `ContentAddressedStore` protects
evidence bytes today).

**Cannot prove, no matter how well the software is written**: that the
capture point was not itself bypassed (traffic routed around it), that the
capture process is running on hardware the prover doesn't fully control,
or that the "passive tap" the evidence claims to come from is a real
physical device rather than a software loopback the prover configured to
feed the verifier whatever it likes. Software cannot attest to its own
physical deployment context -- this is the same class of limitation
`docs/threat-model.md` question F describes for a "clean environment"
attestation problem, applied to network capture instead of GPU evidence.

## The abstraction (schema-level only, not implemented)

If/when real capture infrastructure exists, evidence flowing through this
system's pipeline would need:

- **Capture source identity**: which physical or logical tap produced
  this evidence -- itself needs to be tied to something the prover doesn't
  control, or this field is just another self-report.
- **Capture identity**: a stable identifier for the capture instance/session.
- **Capture timestamp**: same self-report caveats as
  `Evidence.created_at` today (`docs/threat-model.md`, Q.I) unless bound
  to a trusted time source.
- **Packet/chunk identity**: how captured traffic maps onto the
  `WorkloadChunk` concept in `docs/research/recomputation.md`, so captured
  evidence and recomputation could eventually cross-reference each other.
- **Evidence chain / integrity**: hash-chaining captured segments, the
  same integrity principle `ContentAddressedStore` already applies to
  evidence storage.
- **Loss accounting**: what fraction of expected traffic the capture
  point actually observed -- a capture mechanism that silently drops
  packets without reporting the drop rate is worse than one that reports
  gaps honestly.
- **Replay protection**: preventing a prover from feeding the same
  captured segment through multiple times to inflate apparent volume.
- **Source attestation**: tying the capture appliance itself to a hardware
  root of trust -- structurally the same problem as GPU attestation
  (`docs/hardware/nvidia-attestation.md`), applied to network hardware
  instead, and equally unsolved here.
- **Verifier trust**: who is allowed to configure or read from a capture
  point -- ties into `docs/protocol/auth-model.md`'s authorization gap.

None of the above is implemented as a Python class, a pydantic model, or a
JSON Schema in this repository. That is a deliberate choice, not missing
scope.

## What requires physical infrastructure, explicitly

- **Physical passive taps**: optical or electrical taps that copy traffic
  without being routable-around by the prover's own network configuration.
  Requires physical installation, physical chain-of-custody documentation,
  and inspection procedures -- none of which a software repository can
  provide, verify, or simulate meaningfully.
- **Trusted capture appliances**: dedicated hardware with its own root of
  trust, analogous to a GPU's attestation hardware but for network
  capture.
- **NIC-level mechanisms**: SR-IOV port mirroring, hardware timestamping --
  real, existing technology, but requires specific NIC hardware and driver
  support this project has not inventoried.
- **Switch-level evidence**: mirrored ports, sFlow/NetFlow-style
  telemetry from network hardware the prover doesn't single-handedly
  control (e.g., a datacenter operator distinct from the AI company being
  verified) -- the most promising DIRECTION for eventually getting a
  signal genuinely outside the prover's control, per
  `docs/research/hidden-computation.md`'s "layered evidence model"
  discussion, but requires a datacenter operator's cooperation this
  project cannot obtain by writing code.

## What changed since ADR-0001

ADR-0001 (Phase 1) declined to build even an interface stub for network
evidence, reasoning that a stub for "something happened where software
cannot see" risks implying progress a documentation-only entry doesn't.
This document doesn't reverse that reasoning -- it still declines to ship
a `NetworkEvidence` Python class or JSON Schema, for the same reason. What
changed is scope of the WRITING, not the CODE: this phase's brief asked
explicitly for the abstraction to be defined and for the physical-vs-
software boundary to be stated explicitly (section 19), which this
document now does in more detail than ADR-0001's short paragraph did. The
underlying engineering judgment -- don't build a stub with zero real
capability behind it -- is unchanged.
