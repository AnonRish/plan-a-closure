# Appia Foundation Mapping

Re-verified this phase, not assumed from Phase 2's research. One material
update: <cite index="28-1">the Appia Foundation's own roadmap through 2026 named the release of its full white paper and detailed specifications for August 2026</cite> -- which is now. This document was written before confirming whether that release has actually landed; treat everything below as accurate as of the search that produced it, and re-check before relying on it further.

## What's newly confirmed this phase

- Hosted specifically under the Linux Foundation's **Joint Development
  Foundation (JDF)**, not "the Linux Foundation" generically.
- Membership has grown since Phase 2's check: <cite index="26-1">Arm, Armilla AI, Ericsson, Google, Mastercard, Microsoft, Mitsubishi Electric, Naaia, Nemko, Omron, OpenAI, Schneider Electric, and Siemens.</cite>
- Two-layer architecture: <cite index="27-1">a Requirements and Guidance layer setting out what needs to be demonstrated, and an Assessment Enablement layer defining testing criteria, assessment materials, evaluation guidance, and a shared typology for identifying which part of an AI system is being examined -- necessary because an AI application may combine a foundation model from one provider, adaptations from another, integration work from a vendor, and deployment settings the customer controls.</cite>
- Explicitly builds on **existing** standards rather than replacing them: <cite index="27-1">Appia builds on standards from ISO/IEC and CEN/CENELEC.</cite> One source is blunt about this distinction: <cite index="44-1">Appia stressed that what it is offering are not standards -- which are set by recognized international bodies such as ISO/IEC -- but a means of assessing what those standards mean and how organizations can use them, though some of its criteria may become standards themselves over time.</cite>
- A named architectural feature directly relevant to this project: <cite index="29-1">the Appia specification architecture is designed for functional modularity and evidence pass-through.</cite> "Evidence pass-through" -- reusing conformity evidence across the value chain rather than re-assessing from scratch at every link -- is close to this project's own "evidence" and "receipt" design goals, applied one layer up (organizational conformity, not compute verification specifically).

## Mapping, per this document's required categories

| Frontier Verify concept | Appia status | Why |
|---|---|---|
| `Evidence` / `Receipt` as portable, signed artifacts | **MAPPABLE** | "Evidence pass-through" is architecturally compatible with a signed receipt being handed between value-chain parties -- but no Appia specification exists yet concrete enough to confirm actual compatibility, only architectural resemblance |
| `Policy` / `evaluate()` | **MAPPABLE** | Analogous role to Appia's Assessment Enablement layer's "testing criteria" -- both define what evidence must show to count as conforming -- but Appia's criteria will be written by Appia's working groups, not derivable from this project's schema |
| The `AttestationProvider` component typology (NVIDIA/AMD/TEE) | **MAPPABLE** | Appia's own "component typology" concept -- identifying which part of a composite AI system is being examined -- maps conceptually onto this project's own vendor-neutral provider abstraction, independently arrived at |
| Compute/inference verification specifically | **NOT_YET_MAPPED** | No Appia specification concrete enough to target exists yet, confirmed by this phase's research -- the white paper due this same month may change this, and should be checked again, not assumed unchanged |
| Formal conformance/certification against Appia | **NOT SUPPORTED** | Cannot be claimed honestly -- there is nothing published yet to conform to |

## What this project should do, concretely

Nothing beyond what Phase 2 already did: keep `schemas/evidence.schema.json`
and `schemas/receipt.schema.json` as plain, dependency-free JSON Schema
with no Frontier-Verify-specific lock-in, so that IF Appia's imminent
specifications turn out to define something this project's evidence model
could feed into, mapping is a translation exercise rather than a rewrite.
**Do not claim Appia alignment or compatibility in any marketing sense** --
sections 21's own instruction not to invent compatibility is being
followed literally here: everything above is scored `MAPPABLE` at most,
never `SUPPORTED`, because nothing concrete enough to support exists yet
as of this research pass.

## Immediate next step

Check `https://appiafoundation.org` again specifically for the August
2026 white paper and detailed specifications -- if published, this
document's `NOT_YET_MAPPED` row may need to change, and that should be a
deliberate re-research pass, not an assumption carried forward from this
phase.
