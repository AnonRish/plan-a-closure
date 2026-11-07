# Evidence Model

## Schema

Defined in `frontier_verify/evidence/models.py`, exported as JSON Schema in
`schemas/evidence.schema.json` (regenerate with the one-liner in that
file's header comment, or see `Makefile`'s `schemas` target).

```
Evidence
├── evidence_id: str
├── created_at: datetime          (self-reported by the prover -- see threat-model.md, question I)
├── model_identity: ModelIdentity
│   ├── model_digest: str         (required)
│   ├── weights_digest, tokenizer_digest, architecture_digest, config_digest: str | None
│   ├── quantization, name, version: str | None
├── runtime_identity: RuntimeIdentity
│   ├── serving_engine, engine_version, container_digest, hardware_summary: str | None
├── hardware_evidence: HardwareEvidence
│   ├── provider_name: str
│   ├── maturity: Maturity enum   (NOT_IMPLEMENTED | MOCK | SIMULATED | EXPERIMENTAL | RESEARCH | VALIDATED | PRODUCTION_READY)
│   ├── mock: bool                (read by the policy evaluator -- not decorative)
│   ├── claims: dict
│   ├── raw_evidence_digest: str | None
│   ├── collected_at: datetime
└── workload_ref: str | None
```

Every model in this schema exposes `.digest()`, which canonicalizes the
model (via `frontier_verify.core.canonical`) and SHA-256 hashes it. Two
evidence bundles with identical content produce identical digests
regardless of field order or which code path constructed them --
`tests/unit/test_evidence.py` and `tests/unit/test_canonical.py` pin this
behavior with fixed inputs, not just "equal to itself" tautologies.

## Deliberately narrow field set

The source specification's evidence model (sections 18-19) lists more
provenance fields than Phase 1 implements -- build metadata, software
version, deployment identity, dependency lists, and so on. Every field that
exists here is one that (a) has a clear, non-speculative meaning, and (b) is
actually read by something (the digest functions, or the policy evaluator).
Adding fields nothing reads yet would be exactly the kind of "decorative
placeholder" section 5 of the source spec warns against. Extend the schema
when a real consumer needs a real field, not preemptively.

## Canonicalization limits (read before depending on this for interop)

`frontier_verify/core/canonical.py` implements a JCS-*inspired* encoding
(sorted keys, no whitespace, UTF-8), not a certified RFC 8785
implementation. The known gap: JCS's number-formatting rules (derived from
ECMA-262) are stricter than Python's `json.dumps` about float
representation edge cases (very large exponents, negative zero). Every
field in the current schema is a string, bool, dict, or datetime (rendered
as an ISO string via `mode="json"`) -- no floats -- so the gap doesn't bite
today. It will the moment a numeric field (e.g. a FLOP count or a
confidence score) is added. See ADR-0002 for the decision context.

## What "self-reported" means concretely

Every field above except the receipt's own signature is supplied by the
prover with nothing in Phase 1 independently confirming it. This isn't
buried in prose -- it's why `HardwareEvidence.mock` exists as a field at
all, why the policy evaluator reads it, and why `assurance-model.md` caps
Phase 1 at L1. Read `threat-model.md` question A before treating any
`Evidence` object as more than a structured, tamper-evident claim.
