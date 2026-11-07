# Ecosystem Interoperability

Researched August 2026. Goal per the brief: determine what Frontier Verify
should implement, what it should map to, and what it should merely
interoperate with -- not adopt standards blindly, and not position this
project as a replacement for standards bodies.

## IETF RATS (RFC 9334) -- implement against, don't reinvent

RFC 9334 (Remote ATtestation ProcedureS Architecture, informational,
January 2023) defines the roles this entire project already, independently
arrived at: **Attester**, **Verifier**, **Relying Party**, plus
**Evidence**, **Endorsements**, **Reference Values**, and appraisal
policy producing an **Attestation Result**. It defines two interaction
models -- the Passport Model (Attester gets a reusable result from the
Verifier, presents it to Relying Parties) and the Background-Check Model
(Relying Party forwards Evidence to the Verifier itself).

This is the single most important interoperability finding in this phase.
The mapping is direct, not approximate:

| RATS role/concept | Frontier Verify equivalent |
|---|---|
| Attester | Prover |
| Verifier | Verifier (same name) |
| Relying Party | Auditor |
| Evidence | `Evidence` |
| Attestation Result | The pass/fail + `assurance_level` from `PolicyResult` |
| Appraisal Policy | `Policy` / `evaluate()` |
| (no direct equivalent) | `Receipt` -- RATS doesn't specify a portable, independently-verifiable output artifact the way this project's signed receipt is; that's a genuine Frontier-Verify-specific contribution on top of the RATS architecture, not a gap in following it |

NVIDIA's own NVAT documentation uses this exact terminology (see
`docs/hardware/nvidia-attestation.md`) -- which means adopting RATS
vocabulary isn't just theoretically clean, it's what the actual hardware
vendor this project targets already speaks. **Decision**: Frontier Verify
should describe its architecture in RATS terms going forward (this
document, `docs/architecture.md`'s next revision) rather than inventing
parallel vocabulary that means the same thing. It should NOT attempt to
literally implement CoRIM/EAT wire formats yet -- that's real additional
work with no current consumer, tracked as a research question, not
undertaken speculatively (section 28, "don't overbuild").

## NIST AI RMF and ISO/IEC 42001 -- different layer, not overlapping

Both real, both current as of August 2026: NIST AI RMF 1.0 (January 2023)
remains the only finalized version, with a revision underway but not
published; ISO/IEC 42001:2023 is the first certifiable AI management
system standard, structured around Plan-Do-Check-Act. Both are
**organizational governance and risk-management frameworks** -- how a
company structures accountability, documentation, and risk processes
around its AI systems. Neither specifies a technical evidence or
attestation format for AI **compute verification**, which is this
project's actual niche.

**Decision**: Frontier Verify is not a competitor or an alternative to
either. It's a plausible technical evidence source that COULD feed into
the "Measure" function of NIST AI RMF or the operational-monitoring
controls of an ISO 42001 AI management system, the same way a SOC 2
report or a penetration test feeds into a broader compliance program
without being one itself. Do not describe this project as "AI RMF-aligned"
or "ISO 42001-compliant" -- it operates one layer below where either
standard specifies anything concrete enough to comply with.

## Appia Foundation -- track, don't build against yet

Confirmed real in Phase 1's research and unchanged since: launched June
2026 under the Linux Foundation, backed by Google, Microsoft, OpenAI, Arm,
Mastercard, Siemens and others, aiming to build open modular
specifications and a third-party conformity-checking "trust layer" across
the AI value chain. As of this research, Appia has not published a
specific technical specification for AI compute/inference verification
concrete enough to implement against -- it is an organizational effort in
its early stages, not yet a wire protocol.

**Decision**: design Frontier Verify's evidence and receipt schemas to
remain plain, portable JSON Schema with no Frontier-Verify-specific
extensions baked into their core structure (already true -- see
`schemas/`), so that IF Appia or a similar body later defines a relevant
specification, mapping to it is a schema-translation exercise, not a
rewrite. Do not wait for Appia to define something before continuing this
project's own work; do not claim alignment with Appia specifically, since
there's nothing published yet to be aligned with.

## Confidential computing ecosystem

NVIDIA's Confidential Computing (the mechanism NVAT attests) is part of a
broader industry effort (Confidential Computing Consortium and similar
groups defining TEE-based attestation across CPU and accelerator vendors).
This project's `AttestationProvider` abstraction (vendor-neutral by
design, per `docs/architecture.md` and `docs/adr/0001...`) is already
structured to add a TEE-based provider alongside NVIDIA's GPU-specific one
without changing the core protocol -- no new decision needed here beyond
confirming the existing abstraction is compatible, which it is.

## What Frontier Verify should NOT do

- Define a competing attestation architecture when RATS already exists
  and NVIDIA's own tooling already speaks it.
- Claim compliance with NIST AI RMF or ISO 42001, which are the wrong
  layer for what this project does.
- Wait indefinitely for Appia before doing anything, or claim alignment
  with something not yet published.
- Invent new terminology where RATS terminology already says the same
  thing.
