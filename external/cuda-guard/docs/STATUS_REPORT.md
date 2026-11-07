# Implementation Status Report

Covers Phases 0-19 (spec Sec. 4) plus Phases 32-34 (capability matrix,
diagnostics, CLI). 41 tests, all real (no design-intent assertions), all
passing as of this build. Every claim below is backed by a specific test in
`tests/` or a specific real-execution result reported in this
conversation -- cross-reference `capabilities.json` / `CAPABILITY_MATRIX.md`
for the machine-readable form of this same information.

## REAL AND WORKING

- Typed evidence model (`cuda_guard.evidence`) -- `EvidenceStatus`/`EpistemicClass` correctly
  non-interchangeable (tested: UNAVAILABLE≠FAILED≠SIMULATED semantics)
- Tamper-evident hash-chained ledger -- 7 real tamper/replay scenarios, all detected
- Backward/optimizer-step interception -- 7 real bypass scenarios, mixed results honestly reported
  (some detected via genuine defense-in-depth, some genuine bypasses, one genuine gap found)
- NCCL size-threshold auditor (software heuristic, self-documented limitation)
- Observed FLOP ledger (`F.linear`, `torch.matmul` -- verified against hand-computed FLOPs)
- LD_PRELOAD CUDA driver interceptor -- real subprocess+harness proof, 2 real bypass tests
  (no-preload, static-link) both correctly demonstrate the interceptor's real limits
- Device discovery via NVML with emulated fallback
- Real NVIDIA attestation adapter (`nv-attestation-sdk` integration) -- gating logic verified
  fast/non-hanging; claim scoping (never workload/location/authorization) enforced in code
- Attestation+authorization composition logic -- 4 branches tested, no layer silently erases another
- Model identity (SHA-256) -- full 7-case test matrix from spec Sec. 12
- Model-state continuity checkpointing
- PCAP network evidence -- real binary-format parser, validated against an independent tool
  (system `file` command confirms our synthetic PCAP is a genuinely valid capture file)
- Deterministic-mode reproducibility check -- verified both the positive case (identical hashes)
  and that injected nondeterminism would be caught (mismatch detection is real, not decorative)
- Sampled recomputation verifier (toy-model scale) -- verified detects a deliberately corrupted
  captured output, not just a rubber-stamp pass
- Application memory wipe -- verified non-zero buffer → wipe → independently re-read all-zero
- Power-FLOP plausibility correlation logic
- Governance verdict engine -- 5 scenarios tested including tamper-ledger → EVIDENCE_CONFLICT
  propagation and failed-attestation → HARDWARE_ATTESTATION_FAILED (never silently absorbed)
- Capability registry -- self-verifies against real import introspection (0 discrepancies found)
- Environment diagnostics (`verify system` equivalent) -- real environment queried, not templated
- CLI -- 6 subcommands, all real-executed against this environment

## REAL BUT HARDWARE-DEPENDENT

- GPU Confidential Computing / H-TEE, Blackwell TEE-I/O, SPDM, eRoT, OOB BMC telemetry --
  all confirmed real NVIDIA infrastructure (Rev. 2 web-verification pass); none exercised here,
  none faked
- Real NVIDIA attestation's actual challenge-response path -- the *adapter* is real and tested
  (gating, timeout safety, claim-parsing structure verified against NVIDIA's documented example
  token), but the live challenge-response itself requires Hopper+ CC-enabled silicon this
  sandbox does not have
- Live network interface capture (`LiveInterfaceSource`) -- requires CAP_NET_RAW/root
- External tap feed / IOVT-class observation (`ExternalTapFeedSource`) -- requires physical
  tap hardware, a separate workstream by design
- Physical PDU / power evidence ingestion -- the ingestion API is real and tested with a manual
  fixture; no physical PDU is connected in this environment

## PROTOTYPE/RESEARCH

- Sampled recomputation verifier, at anything beyond toy-model scale -- the mechanism is real
  and tested, but has not been demonstrated on realistic model sizes, numerical-precision drift
  across hardware, or adversarial sample selection
- PTX/SASS optimizer-kernel fingerprinting -- not implemented this pass; documented as
  adversarially weak by construction even if built (evasion-cost-raising heuristic only)

## SIMULATED ONLY

- Device authorization registry (`DeviceRegistry`) -- explicitly a `LOCAL_DEMO_REGISTRY`,
  labeled as such in every evidence record it produces, never presented as a real signed registry
- Device discovery, when no NVML/driver is present -- falls back to an explicitly-labeled
  emulated `DeviceIdentity` record (`is_emulated=True`, `EvidenceStatus.SIMULATED`)

## NOT IMPLEMENTED

- `torch.mm`, `torch.bmm`, `torch.addmm` FLOP hooks (spec Sec. 10 lists these; only
  `F.linear`/`torch.matmul` were carried over and re-verified this pass)
- A real, remotely-signed device registry (only the local demo version exists)
- Hardware-backed VRAM erasure proof (`HardwareBackedErasureAdapter` is a clean interface only)
- Physical PDU/BMC hardware integration (software ingestion point exists; no adapter)
- Red-team coverage for PCAP-specific adversarial scenarios (packet injection, flow splitting,
  timestamp alteration on a captured file) and live registry-mismatch scenarios

## NOT TECHNICALLY PROVABLE BY THIS LAYER

- GMMU read-only weight-page enforcement -- no public CUDA driver API for arbitrary
  device-allocation write protection was confirmed to exist; this is a research question about
  whether the mechanism can exist at all with current public APIs, not an implementation gap
- "This chip is in an authorized physical location" from attestation alone -- structurally
  impossible; attestation proves firmware integrity, full stop (Trust Architecture doc, Sec. 1)
- "This traffic is R&D vs. deployment" from network pattern alone -- structurally impossible;
  size/pattern carries no semantic tag (same document, same section)
- Wholesale ledger replacement detection without an external anchor -- a hash chain cannot, by
  itself, prove it wasn't rebuilt from scratch; provably true, not just claimed (see
  `tests/test_ledger.py::test_known_limitation_wholesale_replacement_not_detected_by_design`)

## What would change this report

Running this exact codebase on real Hopper/Blackwell hardware would move the "REAL BUT
HARDWARE-DEPENDENT" attestation items into "REAL AND WORKING" without any code changes -- the
gating logic already correctly detects and routes to the real path (`cc_capable_gpu_suspected`).
Connecting a real PDU or IOVT-class tap and calling `record_external_evidence()` would populate
L4/L5 in `GovernanceVerdict` for the first time, also without code changes -- the interface was
built for exactly this. Nothing in this report describes a gap that requires redesigning the
architecture to close; every hardware-dependent item is a matter of connecting real hardware to
an interface that already exists and is already tested against its own contract.
