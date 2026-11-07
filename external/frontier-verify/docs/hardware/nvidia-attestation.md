# NVIDIA Attestation: Current State (researched August 2026)

This document exists because section 2 of the Phase 2 brief requires
fresh, dated research recorded separately from code, so staleness is
checkable later. **Re-run this research before building against it** --
the note in `frontier_verify/attestations/nvidia_provider.py` explicitly
flags that this exact document superseded Phase 1's version two months
earlier, and will itself go stale the same way.

## Authoritative sources consulted

- NVIDIA's `NVIDIA/nvtrust` GitHub repository (GPU/NVSwitch attestation
  tooling, historical Python guest tools).
- NVIDIA's `NVIDIA/attestation-sdk` GitHub repository (NVAT / `nvattest`,
  the current C++ SDK and CLI).
- Release notes and version history for both repositories.

## The migration, concretely

| Component | Status | Notes |
|---|---|---|
| Local GPU Verifier (standalone Python tool) | Deprecated as standalone | NVIDIA's own guidance: use the Attestation SDK instead of running it stand-alone |
| Python Attestation SDK (`nv-attestation-sdk` on PyPI) | Deprecated, firm end date | `DeprecationWarning` added; **end of support 2026-09-15** |
| `nv-local-gpu-verifier`, `nv-ppcie-verifier` v1.x | Deprecated alongside the SDK above | Same end-of-support date |
| NVAT / `nvattest` (C++ CLI + C API, `NVIDIA/attestation-sdk` repo) | **Current recommended path** | Versioned releases since Dec 2025 (1.0.0-alpha1); reached **1.2.0 in March 2026** |
| `nv-ppcie-verifier` v2.x | Current | Migrated to use `nvattest` internally rather than the Python path |

**Direct implication for this project**: a Phase-1-era decision to wait on
NVAT's stability was reasonable in July/August 2026 terms but is no longer
the most defensible read of the evidence -- NVAT has real versioned
releases now, not an unstable alpha. A new implementation effort should
target NVAT specifically, not the Python SDK, which will stop receiving
support before this document is even a month old.

## Evidence flow

NVIDIA's own architecture documentation for NVAT explicitly follows IETF
RATS (RFC 9334) terminology -- **Attester**, **Verifier**, **Relying
Party** -- and describes the flow as: collect evidence from an Attester
(the GPU host), submit it to a Verifier to obtain an attestation result,
then apply appraisal policy to that result. This maps directly onto
Frontier Verify's own Prover / Verifier / Auditor roles and its Policy /
`evaluate()` design -- see `docs/ecosystem-interoperability.md`.

Two attestation paths exist:

- **Local**: the `nvattest` CLI collects and verifies evidence on the same
  machine, without a network round trip to NVIDIA.
- **Remote**: evidence is submitted to NVIDIA's Remote Attestation Service
  (NRAS), which returns a signed attestation result. This requires an NGC
  (NVIDIA GPU Cloud) account and service key.

NVAT also supports policy evaluation using Open Policy Agent's Rego
language for relying-party-side appraisal -- a real, independent
precedent for "the party consuming attestation results defines its own
acceptance policy," which is exactly the relationship between Frontier
Verify's `Evidence` and `Policy`/`evaluate()`.

## Evidence format

`nvattest collect-evidence` produces JSON shaped like:

```json
{
  "evidences": [
    {
      "version": "1.0",
      "arch": "HOPPER",
      "nonce": "<hex>",
      "vbios_version": "96.00.00.00.01",
      "driver_version": "575.03",
      "evidence": "<base64>",
      "certificate": "<PEM>"
    }
  ],
  "result_code": 0,
  "result_message": "Ok"
}
```

A synthetic (fabricated values, real shape) fixture matching this exactly
is bundled at
`frontier_verify/attestations/fixtures/nvidia_evidence_synthetic.json`,
with a prominent in-file warning about what it is and is not. `nvattest
attest --gpu-evidence <file>` supports verifying a pre-collected evidence
file offline, separate from live collection -- useful for testing a
verifier's evidence-handling logic without needing hardware attached at
verification time, though evidence still has to come from real hardware
at collection time, which this environment cannot do.

## Prerequisites for a real implementation

- A Hopper-generation or later NVIDIA GPU (confirmed: the fixture's `arch`
  field would read `HOPPER` or a later architecture name).
- NVIDIA Confidential Computing mode enabled on that GPU.
- Current NVIDIA driver (the fixture shows `575.03` as an example; check
  NVAT's current support matrix, not this number, before deploying).
- NVAT installed (`nvattest` CLI + supporting libraries).
- For remote/NRAS attestation: an NGC account and service key.
- For NVSwitch attestation specifically: `libnvidia-nscq` and
  multi-GPU/NVSwitch topology, relevant mainly to Blackwell-class
  multi-GPU systems.

None of the above exists in the sandbox this repository was built in
(confirmed via `nvidia-smi`, `nvcc --version`, and `/dev/nvidia*` checks
in both Phase 1 and Phase 2, not assumed).

## Trust assumptions

Attestation proves the GPU's own hardware root of trust vouches for the
reported architecture, VBIOS, driver, and Confidential Computing state --
it does NOT prove anything about what workload subsequently ran on that
GPU, which is a separate claim (`ModelIdentity`/`RuntimeIdentity` in this
project's schema, still self-reported). See `docs/threat-model.md`,
question F, for why hardware attestation alone doesn't close that gap.

## Failure modes worth designing for

- Driver/VBIOS version drift between attestation time and inference time
  (attest once, then the environment changes).
- NRAS unavailability -- local-only attestation is weaker (no third-party
  confirmation) but must remain usable, or the whole system becomes
  unusable whenever NVIDIA's service has an outage.
- Nonce reuse/replay if a verifier doesn't generate a fresh nonce per
  attestation request -- NVAT's evidence format includes a `nonce` field
  specifically to prevent this; a Frontier Verify integration must
  generate and check this nonce itself, not just pass the field through.

## Implementation status in this repository

`frontier_verify/attestations/nvidia_provider.py`:
`get_platform_evidence()` -- NOT_IMPLEMENTED, raises deliberately.
`parse_nvat_evidence()` -- EXPERIMENTAL, real and tested against the
synthetic fixture (`tests/conformance/test_nvidia_evidence_parsing.py`),
parses the real field shape into `HardwareEvidence`, does **not** validate
certificates or call NRAS.
