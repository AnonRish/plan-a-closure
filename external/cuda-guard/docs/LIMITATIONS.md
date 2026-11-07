# Limitations Report

Consolidated from every module's own docstrings and the capability
matrix's `known_limitations` field -- collected here once so nothing is
buried in "future work."

## Structural limitations (true even with every layer combined)

1. **L1 self-audit is not independent.** The governed party controls
   whether any hook in `cuda_guard.self_audit` is even loaded. A fully
   dishonest governed party can defeat all of L1 -- this is why L2-L5 exist,
   and why a `SUPPORTED_WITH_LIMITATIONS` verdict resting only on L1 is
   correctly labeled `WEAK` by `VerdictEngine`.

2. **The tamper-evident ledger has no external anchor.** It detects
   modification, deletion, insertion, and reordering of *retained* history
   (all four demonstrated in `tests/test_ledger.py`). It does not detect
   wholesale replacement of the entire ledger with a fabricated,
   internally-self-consistent alternative -- proven true by
   `test_known_limitation_wholesale_replacement_not_detected_by_design`,
   not merely asserted. Closing this needs periodic external publication of
   the latest `record_hash`, out of scope for a single-process prototype.

3. **`torch.autograd.grad()` is a real, currently-unhooked gap** in
   `InferenceOnlyGovernor`. Found by the bypass-test suite, not
   pre-announced in the design. Listed in the capability matrix as a known
   limitation, not silently left out of documentation.

4. **NVIDIA attestation proves firmware/hardware integrity only.** It has
   never, in this implementation, been allowed to establish workload
   intent, training vs. inference, physical location, or policy
   authorization -- see `cuda_guard.hardware.run_attestation`'s docstring
   and the `does_not_establish` field on every `EvidenceRecord` it produces.

5. **The device registry is a `LOCAL_DEMO_REGISTRY`.** It is a Python dict
   in this process's memory, editable by anything that can import
   `cuda_guard`. It is explicitly not a trust boundary. A real deployment
   needs a remotely-signed registry this prototype does not implement.

6. **FLOP accounting is a lower bound through two hooked call sites**
   (`F.linear`, `torch.matmul`). Any GEMM issued through `torch.mm`,
   `torch.bmm`, `torch.addmm`, a custom kernel, or a different framework is
   invisible to `ObservedFlopLedger`. (Spec Sec. 10 lists `torch.mm`,
   `torch.bmm`, `torch.addmm` as things to support -- only `F.linear` and
   `torch.matmul` were carried over from the prototype and re-verified in
   this pass; the other three are a documented, not-yet-implemented gap,
   not silently claimed as covered.)

7. **PCAP ingestion is replayed evidence, never live.** `LiveInterfaceSource`
   and `ExternalTapFeedSource` are real, clean interfaces that are
   `REAL_BUT_HARDWARE_DEPENDENT` and were not exercised in this environment
   (no `CAP_NET_RAW`, no physical tap). Nothing fakes their output.

8. **Recomputation is demonstrated on a toy model only.** `RecomputationVerifier`
   is marked `PROTOTYPE_RESEARCH` in the capability matrix specifically
   because a `torch.allclose` comparison on an `nn.Linear` stack is not
   evidence about how this would perform at frontier-model scale, with real
   numerical-precision drift across hardware, or under adversarial sample
   selection.

9. **Memory wipe proves application-buffer overwrite only.**
   `ApplicationMemoryWiper` never touches physical VRAM and never claims
   to. `HardwareBackedErasureAdapter` is `NOT_IMPLEMENTED` because no public
   API for hardware-backed erasure proof was confirmed to exist.

10. **Power correlation is a coarse plausibility envelope**, not a
    FLOPs-from-watts calculation. `correlate_power_with_compute`'s own
    output includes a `scope_note` saying so on every call.

11. **The verdict engine is only as strong as what's fed into it.**
    `VerdictEngine.assess()` reads real ledger state, but if a caller never
    calls `run_attestation`, never checks the registry, and never records
    external evidence, the resulting verdict correctly reports those layers
    `layers_missing` -- it cannot conjure evidence that was never collected.

## What was deferred entirely in this implementation pass

- `torch.mm`, `torch.bmm`, `torch.addmm` FLOP hooks (only `F.linear`/`torch.matmul` ported)
- Live network interface capture and external tap feed integration (interfaces exist, unexercised)
- A real, remotely-signed device registry (only `LOCAL_DEMO_REGISTRY` exists)
- Physical PDU/BMC integration (ingestion API exists; no physical adapter)
- GMMU read-only weight-page enforcement (no confirmed public API to build against)
- PTX/SASS optimizer-kernel fingerprinting (documented as adversarially weak by design; not built this pass)
- A red-team suite covering every item in spec Sec. 31's four categories exhaustively --
  covered: self-audit bypasses (7 scenarios), driver-interceptor bypasses (2 scenarios),
  ledger tamper/replay (7 scenarios), model-identity mutation (7 scenarios), verdict-engine
  evidence-conflict propagation (1 scenario). Not covered this pass: PCAP-specific adversarial
  tests (packet injection, flow splitting), live registry mismatch scenarios.
