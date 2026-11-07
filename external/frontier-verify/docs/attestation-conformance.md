# Attestation Conformance

What a hardware attestation provider has to supply for Frontier Verify to
accept it -- so a second vendor could implement `AttestationProvider`
without reading NVIDIA-specific code. See
`frontier_verify/attestations/base.py` for the interface itself and
`docs/hardware-provider-guide.md` for the original Phase 1 onboarding
notes, which this document extends rather than replaces.

## Required, checked today

| Requirement | Where it's enforced | Status |
|---|---|---|
| `mock: bool` set honestly | `frontier_verify/policies/evaluator.py` rejects `mock=True` unless the policy explicitly allows it | VALIDATED (tested, `tests/unit/test_policy_evaluator.py`) |
| `maturity` from the fixed `Maturity` vocabulary | Pydantic schema validation rejects any other value | VALIDATED (tested, `tests/conformance/test_schema_compatibility.py`) |
| Structural schema validity | Pydantic `HardwareEvidence` model | VALIDATED |
| Freshness (`Evidence.created_at` within policy window) | `evaluate()` | EXPERIMENTAL -- weak, self-reported timestamp, see `docs/threat-model.md` Q.I |

## Required by the brief, NOT checked today

| Requirement | Status | Why |
|---|---|---|
| Nonce handling (freshness bound to the attestation itself, not a self-reported timestamp) | NOT_IMPLEMENTED | Needs a real attestation provider to generate/consume nonces against; NVAT's evidence format includes a `nonce` field (`docs/hardware/nvidia-attestation.md`) but nothing here issues or checks one yet |
| Signature validation (of the hardware's own attestation report) | NOT_IMPLEMENTED | `NvidiaAttestationProvider.parse_nvat_evidence()` parses the evidence JSON shape but does not validate the embedded certificate against any root of trust -- see its own docstring |
| Certificate chain validation | NOT_IMPLEMENTED | Same reason |
| Platform identity / GPU identity | PARTIAL | The parser extracts `arch`, `vbios_version`, `driver_version` into `claims`, but nothing CONFIRMS these are cryptographically bound to a specific physical device |
| Firmware measurements | NOT_IMPLEMENTED | Not present in the fixture/parser at all yet |
| Runtime measurements | NOT_IMPLEMENTED | Separate from hardware attestation; would live in `RuntimeIdentity`, still entirely self-reported |
| Revocation | NOT_IMPLEMENTED | See `docs/protocol/key-management.md` -- same gap applies to attestation trust roots, not just verifier signing keys |
| Expiration | NOT_IMPLEMENTED | |
| Replay protection | PARTIAL | Same freshness-window mechanism as evidence generally; no nonce-based protection specific to attestation |

## The honest summary

A conformant `AttestationProvider` implementation today only has to clear
a schema-validity and self-labeled-honesty bar (`mock`, `maturity`
correctly set) -- Frontier Verify's own checking does not yet reach into
signature or certificate validation for ANY vendor, NVIDIA included. This
is why `docs/assurance-model.md` caps everything at L1 regardless of
whether `mock` is `True` or `False`: the ceiling isn't about NVIDIA
specifically, it's that nothing in this repository validates a hardware
signature chain for anyone yet. A second hardware vendor implementing this
interface today would be held to exactly the same (currently low) bar
NVIDIA's stub is held to -- which is honest, but also means "conformant"
and "trustworthy" are not yet the same claim for attestation the way they
already are for receipts (`docs/receipt-specification.md`, where signature
validation is real and thoroughly tested).
