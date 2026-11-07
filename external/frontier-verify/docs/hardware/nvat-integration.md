# NVAT Integration: Current State (researched August 2026, Phase 3)

Supersedes `docs/hardware/nvidia-attestation.md` (Phase 2's version) --
kept, not deleted, since section 2 of this phase's brief wants the
research trail visible, not overwritten. Every finding below was
re-verified this phase, not assumed from Phase 2's notes, per this
document's own recurring warning about staleness.

## What changed since Phase 2's research (two months earlier, in-story)

Mostly confirmation, not surprises -- with one genuinely important
correction, below. NVAT's release history is now visible in full: 1.0.0-alpha1
(Dec 2025) -> 1.0.0 (Jan 2026) -> 1.1.0, 1.1.1 (Feb 2026) -> **1.2.0
(March 2026, still latest)**. Recent point releases addressed security
vulnerabilities and bumped the minimum Python requirement for the
(deprecated) Python SDK to 3.9+ -- routine maintenance, not architectural
change. The Python SDK's own documentation now states outright: "Note:
The Python Attestation SDK is deprecated. For the latest features and
support, try the new CPP Attestation SDK" -- confirmed directly from
NVIDIA's docs, not inferred.

## Important correction: there are at least TWO evidence JSON shapes, not one

Phase 2's `frontier_verify/attestations/fixtures/nvidia_evidence_synthetic.json`
and `parse_nvat_evidence()` are built against the **local CLI's**
`nvattest collect-evidence` output, which uses an `evidences` (plural)
array. Fresh research this phase found the **NRAS remote API's** v3
release notes explicitly documenting a field rename: <cite index="25-1">the v3 API's changes from v2 include renaming the evidences field to evidence_list, and using a more lightweight base-64-encoded SPDM evidence format.</cite>
That means Phase 2's parser was built against ONE of at least two live
formats, and would silently fail (or need a different parser branch) for
the other. This is exactly the kind of gap fresh research is supposed to
catch -- and did.

## The richer, more useful discovery: verified CLAIMS, not just raw evidence

Phase 2's fixture only captured raw, unverified evidence
(`{"evidences": [{"evidence": "<base64>", ...}]}`) -- the input to
verification, not its output. This phase found NVIDIA's documented
**claims** schema (the output of `nvat_attest_device()`, after real
verification succeeds), which is materially richer and directly maps onto
every gap `docs/attestation-conformance.md` listed as `NOT_IMPLEMENTED`:

```json
{
  "dbgstat": "disabled",
  "hwmodel": "GH100 A01 GSP BROM",
  "measres": "success",
  "secboot": true,
  "x-nvidia-gpu-arch-check": true,
  "x-nvidia-gpu-attestation-report-cert-chain": {
    "x-nvidia-cert-expiration-date": "9999-12-31T23:59:59Z",
    "x-nvidia-cert-ocsp-status": "good",
    "x-nvidia-cert-revocation-reason": null,
    "x-nvidia-cert-status": "valid"
  },
  "x-nvidia-gpu-attestation-report-cert-chain-fwid-match": true,
  "x-nvidia-gpu-attestation-report-nonce-match": true,
  "x-nvidia-gpu-attestation-report-signature-verified": true,
  "x-nvidia-gpu-claims-version": "3.0"
}
```

This single JSON document, if genuinely produced by real hardware and
NVIDIA's own verification, directly answers several rows
`docs/attestation-conformance.md` scores as `NOT_IMPLEMENTED` for this
project's own parser: certificate chain validation
(`...cert-chain-fwid-match`, `...cert-chain.x-nvidia-cert-status`), replay
protection (`...nonce-match`), signature validation
(`...signature-verified`), and secure boot state (`secboot`) all arrive
as pre-computed booleans NVIDIA's own verifier already checked. **The gap
this project has is not that these checks don't exist anywhere -- NVIDIA
already performs them. The gap is that `parse_nvat_evidence()` doesn't
consume this claims output at all** -- it only parses the raw evidence
shape, before verification, and reports structural fields only. A real
Phase 4 implementation should target the CLAIMS output, not just raw
evidence collection, and should read these booleans directly rather than
re-implementing certificate validation from scratch.

## Relying-party policy: Rego, a real precedent worth learning from

Confirmed with an exact command this phase: <cite index="15-1">nvattest attest supports a --relying-party-policy flag pointing at a Rego file that defines a package policy and a boolean nv_match rule; if nv_match evaluates to false, attestation fails with error code NVAT_RP_POLICY_MISMATCH.</cite> This is a real, shipped precedent for exactly the relationship between "attestation evidence" and "the party consuming it defines its own acceptance policy" that this project's own `Policy`/`evaluate()` implements independently. Worth studying Rego's policy shape when this project's own policy language eventually needs more expressiveness than the current flat `allow_mock_hardware` / `max_evidence_age_seconds` fields support -- not adopted this phase, noted as a real precedent.

## Composed, multi-vendor attestation: a real existing example

<cite index="19-1">Intel and NVIDIA have collaborated to add NVIDIA GPU TEE remote attestation to Intel Trust Authority, making it possible to attest a confidential-VM TEE and NVIDIA confidential-computing GPUs together in one composite attestation workflow, where Intel Trust Authority forwards GPU evidence to NRAS and returns the result embedded in its own response.</cite> This is a genuine, shipped example of "composition of multiple trust roots" -- AI-2040 workstream #25 in `docs/ai2040-coverage-matrix.md`, still scored `NOT_IMPLEMENTED` in this project. Not something to copy directly (Frontier Verify has no CPU-TEE component to compose with), but real evidence that the composition pattern this project's coverage matrix marks as open research is already operational elsewhere, which changes "unsolved research problem" to "unsolved in THIS project, solved-in-practice by at least one other vendor pairing."

## Infrastructure that exists and this project doesn't use yet

NVIDIA's attestation suite has three named components: <cite index="20-1">NRAS (Remote Attestation Service), the RIM (Reference Integrity Manifest) Service, and the NDIS OCSP Responder.</cite> RIM provides reference measurements to compare against; OCSP provides certificate revocation checking. Both map directly onto gaps `docs/protocol/key-management.md` and `docs/attestation-conformance.md` name for THIS project's own key trust roots (revocation, reference values) -- NVIDIA has already built the equivalent infrastructure for GPU attestation specifically. A real Phase 4 implementation gets revocation-awareness essentially for free by consuming NRAS's OCSP-checked results, rather than needing to build a parallel revocation mechanism for hardware trust roots the way this project had to build one for its own verifier keys (`frontier_verify/keys/`, this phase).

## Updated prerequisites (confirmed, not changed from Phase 2)

Hopper-or-later GPU, Confidential Computing enabled, Ubuntu 22.04/24.04
CVM, NVML installed, and -- new detail this phase -- <cite index="10-1">building the C++ SDK from source requires cmake, git, pkg-config, clang, libcurl, libssl, libxml2/libxmlsec1 development headers, and a Rust toolchain via rustup.</cite> None of this exists in the sandbox this repository was built in.

## What this means for `frontier_verify/attestations/nvidia_provider.py`

Two concrete, scoped next steps, now that the gap is specific rather than
general:

1. Determine which evidence shape (`evidences` local-CLI vs. `evidence_list`
   NRAS-remote) a real deployment will actually consume, and parse that
   one deliberately -- not both defensively, which would be guessing at
   two specs instead of implementing one correctly.
2. Extend parsing to consume the CLAIMS output (post-verification
   booleans), not just raw evidence -- this is the difference between
   "structurally valid JSON" (what Phase 2/3's parser checks) and
   "NVIDIA's own hardware root of trust says this is genuine" (what the
   claims schema's `signature-verified`/`nonce-match`/`cert-chain-fwid-match`
   fields would let this project honestly claim, once actually consumed).
