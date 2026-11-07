# Threat Model

Per spec Sec. 30: this document does not assume the governed party is
honest, does not assume NVIDIA is the only trusted party, and does not
assume the verifier itself is automatically trustworthy.

## Adversary capabilities considered, and what each can/cannot defeat

| Adversary can... | Defeats | Does NOT defeat |
|---|---|---|
| Modify software before running it (never load `cuda_guard` at all) | All of L1 self-audit | L2 (attestation is independent of whether L1 ran), L4/L5 if externally fed |
| Bypass hooks after loading (restore both `torch.Tensor.backward` AND `torch.autograd.backward`) | L1 backward interception -- demonstrated real bypass, see `tests/test_self_audit_bypass.py::test_full_monkeypatch_restoration_bypasses` | L1's redundant partial-restoration catch (a naive partial bypass IS caught) |
| Call `torch.autograd.grad()` instead of `.backward()` | L1's current backward hook (real, unpatched gap) | Nothing else -- this is a genuine current gap, listed in the capability matrix, not hidden |
| Replace model weights after a hash check | `ModelIdentity`'s one-time hash | `ModelContinuity`'s before/during/after checkpoints, IF a checkpoint happens to bracket the replacement -- undetected between checkpoints otherwise |
| Run an uninstrumented subprocess | All in-process L1 hooks (demonstrated: `tests/test_self_audit_bypass.py::test_subprocess_escape_not_detected`) | L2 attestation of the underlying hardware (attestation is process-independent) |
| Use a custom CUDA kernel or alternate framework (numpy, etc.) | All torch-specific L1 hooks | L2 attestation; the LD_PRELOAD interceptor if the custom kernel still calls `cudaMalloc`/`cuLaunchKernel` through the dynamic linker |
| Statically link CUDA calls (no dynamic symbol resolution) | The LD_PRELOAD interceptor -- demonstrated real bypass, `DriverInterceptor.bypass_test_static_link()` | Nothing else in L1; would still be caught by L2 attestation of firmware state |
| Modify local ledger records after the fact | Nothing -- detected by `verify_chain()`, demonstrated for modification/deletion/insertion/reordering | -- |
| Rebuild the entire ledger from scratch with a self-consistent fake chain | `verify_chain()` alone -- this IS a real, undefeated attack without an external anchor (see `tests/test_ledger.py::test_known_limitation_wholesale_replacement_not_detected_by_design`) | L2/L3/L4/L5, which don't depend on the ledger's own internal consistency |
| Replay previously-valid evidence | Nonce-tracked replay detection (`TamperEvidentLedger.check_and_register_nonce`) | -- |
| Spoof timestamps on ledger records | Detected -- timestamp is part of the hashed content, altering it breaks `record_hash` | -- |
| Tamper with `DeviceRegistry` inputs | Nothing -- it's a `LOCAL_DEMO_REGISTRY`, explicitly not a trust boundary in this prototype | A real, remotely-signed registry (not implemented here) would close this |
| Bypass network observation entirely (route traffic outside any tapped path) | All of L1's software NCCL auditor and file-based PCAP ingestion | An IOVT-class physical tap positioned to observe that path regardless of software cooperation -- if one exists (L5) |
| Tamper with physical infrastructure (PDU, BMC) | Nothing in this software layer -- physical security is out of scope for a software prototype | Whatever physical/operational controls the infrastructure owner has in place |
| Attack the verifier itself (this codebase, or whoever runs it) | Nothing here defends against a compromised verifier -- if the party running `cuda_guard` and interpreting its verdicts is itself dishonest or compromised, no software control in this repository prevents that | An independent auditor re-running the same evidence and ledger verification against their own copy |

## The organizing principle

Every "does not defeat" column entry is doing real work: it names the layer
whose trust root is *different* from the layer that was bypassed. That is
the whole reason the five-layer architecture exists -- no single layer's
compromise cascades into every other layer's compromise, because they don't
share a trust root. See `docs/LIMITATIONS.md` for what remains true even
when every layer is combined.
