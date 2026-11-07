# Track 3 — Complete Coverage Inventory

Updated: 2026-09-28

## Scope

This repository is an independent open-source public-evidence and data-engineering contribution relevant to the broader Track 3 problem described by the AI Futures Project. It is **not** an AI Futures Project publication, formal Track 3 implementation, certification authority, treaty verifier, or proof that secret compute has been comprehensively detected.

Official public references:

- https://ai-2040.com/supplements/verification-plan/get-involved
- https://ai-2040.com/print/covert-ai-projects

The AI Futures material describes Track 3 as verifying the absence of secret compute and, in the covert-projects supplement, emphasizes three linked tasks: accounting for pre-deal compute production; tracing sales/resales to physical end use; and locating remaining unaccounted compute with incentives and aerial imagery. Appendix B adds threshold audits, random sampling of the small-owner tail, physical inspection, serial continuity, decommissioning/recycling controls, an untraced pool, and a statistical certificate.

## Repository implementation inventory

| Track 3 element | Current implementation | State | Blocking gap |
|---|---|---|---|
| Pre-deal AI-compute accounting | Aggregate owner/user/sales/component snapshots + site layer | PARTIAL | No globally exhaustive transaction-level inventory |
| Inputs to accelerator production | Component and supply-denominator snapshots | INGESTED_SNAPSHOT | Inputs are estimates/constraints, not complete vendor declarations |
| Vendor sales accounting | Chip-type, organization, and timeline snapshots | INGESTED_SNAPSHOT | No global invoice/serial ledger |
| Sales/resales to physical end use | Entity graph + site evidence + research packets | PARTIAL | Public transfer/resale records are incomplete |
| Audit owners above threshold T | Parameterized audit-population protocol | FRAMEWORK_IMPLEMENTED | Threshold and closed population must be externally fixed |
| Random sample of small-owner tail | Deterministic sampling protocol | FRAMEWORK_IMPLEMENTED | No closed population/sample outcome yet |
| Physical inspection | Inspection schema + chain of custody | FRAMEWORK_IMPLEMENTED | No authorized public inspection observations |
| Serial-number continuity | Lifecycle state machine + integrity rules | FRAMEWORK_IMPLEMENTED | No global public serial ledger |
| Decommissioning/recycling | Verification-state protocol + WEEE source catalog | FRAMEWORK_IMPLEMENTED | No independently verified compute-specific ledger |
| Untraced compute pool L | Residual ledger + certificate model | FRAMEWORK_IMPLEMENTED | Global transaction chain is not closed |
| Locate remaining unaccounted compute | Optical/TIR/SAR + queue surveillance + case workflows | PARTIAL | Public imagery cannot prove universal absence; 1/93 reference sites still lacks a resolved public physical target |
| Incentive/amnesty/buyback evidence | Disclosure protocol | FRAMEWORK_IMPLEMENTED | No verified program/event dataset |
| Physical data-center discovery | Epoch reference + broader queue surveillance + public records | PARTIAL | No intelligence corpus or global covert-site census |
| Power/cooling/infrastructure corroboration | Annual power, cooling, transformer, substation/transmission evidence | PARTIAL | Interval telemetry and exhaustive site linkage are incomplete |
| Independent corroboration | Provenance/conflict layer | PARTIAL | Independence has not been independently assessed across all sites |
| Global coverage | Global chip/source layer; North American physical registry | PARTIAL | Site-level physical coverage remains primarily North American |
| Statistical certificate | Transparent tail-bound calculator | FRAMEWORK_IMPLEMENTED | Requires closed population, defined failures, reproducible sample, validated evidence |

## Terminal site-domain assessment coverage

As of 2026-09-28, the 93-site reference universe has **1,395 of 1,395 defined site/domain cells in a terminal evidence-accounting state (100%)**. The terminal states include positive evidence states such as INGESTED, SITE_LEVEL_EVIDENCE, VERIFIED_SITE_SPECIFIC and INGESTED_DERIVED, plus the explicit **ASSESSMENT_COMPLETE** state for cells where the current public-evidence layer contains no qualifying retained record.

The assessment ledger is data/track3/research_assessments_2026-09-27.json with 573 dated assessment records. **ASSESSMENT_COMPLETE does not mean the underlying condition is absent and does not establish covert-compute absence.** It means the repository has recorded the present evidence ceiling for that cell. New public records, authorized records, or new observations can reopen any assessed cell.

This is a repository-level completeness result, not an international Track 3 verification result. The high-level requirements in the implementation matrix remain partial/framework-implemented where they require transaction-level vendor records, physical inspections, serial continuity, verified recycling, covert-site intelligence, or an independent verification authority.

## Current empirical layers

- 93-site Epoch frontier-AI reference universe.
- 631 retained derived remote-sensing observations across 92 of 93 reference sites in the current committed observation ledger; the physical-target layer now has 92 of 93 reference-site coordinates resolved for acquisition. One reference site remains unresolved for site-specific physical targeting.
- 204 optical observations, 184 TIR observations, and 187 SAR observations in the current committed ledger.
- 214 open public-source publisher-field research tasks and 0 open site/domain cells after terminal evidence assessment.
- 24 current follow-on observation-acquisition tasks: 6 P0 power-telemetry tasks and 18 P1 cooling tasks. These remain open acquisitions even where the underlying domain cell is terminally assessed.
- The machine-readable engineering-closure register reports 0 untracked repository gaps.
- 6 site-level annual electricity-consumption snapshots.
- 18 site-level cooling snapshots represented in the current site-status layer; the dedicated cooling-observation file contains 2 directly retained equipment snapshots.
- 3 source-backed transformer event records.
- 90 substation-related and 113 transmission-related external evidence records.
- 83 sites with retained chip-inventory records; 10 sites remain unknown.
- 4 sites with site-specific compute-tenancy snapshots; 89 remain unknown.
- 38 sites with retained service/contract evidence; 55 are explicitly assessment-complete in the current site-status layer.
- 21 sites with retained site-level regulatory evidence; 72 are explicitly assessment-complete in the current site-status layer.
- 2 defensible site-specific queue IDs in the 93-site Epoch crosswalk.
- 454 normalized public-web evidence records in a losslessly reconciled claim layer; 451 are bound to canonical Epoch site IDs and 3 are explicitly state/multi-site/unbound claims.
- 92 of 93 reference sites now have retained site-level coordinates, including 24 curated public-source coordinate overrides; one remains unresolved and is blocked from site-specific physical interpretation. For OpenAI Stargate UAE, September 11, 2026 Reuters reporting provides an attributed area-level lead near Al Dhafra Air Base, but no canonical parcel or coordinate is promoted.
- 141-record broad ambiguous-load research pool totaling 53.8512 GW under the repository's current filter.
- 68 of those 141 have an explicit retained load-side technology field; 73 require project-type adjudication before strict load-discovery admission.

## Closed-case laboratory

The current closed-case laboratory contains four published pilot cases:

- AMB-NYISO-1765 — manufacturing/industrial outcome with bounded applicant mismatch.
- AMB-NYISO-1745 — data-center identity outcome.
- AMB-IESO-2026-903 — deliberately inconclusive at the physical-targeting stopping rule.
- AMB-AESO-P3108 — proposed data-centre identity and physical-site outcome.

The separate strict five-case queue is fully terminally dispositioned in the machine-readable closure register described above.

Every case separates:

`queue → entity → location → public evidence → physical observation → electrical/transformer → adjudication`

A closed case does not require every evidence layer to be positive. It requires each declared gate to reach a terminal evidence state.

## Discovery queue

The strict admitted queue contains five cases, and all five now have terminal dispositions in `data/track3/strict_discovery_case_dispositions_2026-09-28.json`:

- P3066 — Leedale Data Load: proposed data-center label retained; physical identity unresolved.
- P3198 — Lynx Data Load: inconclusive after the documented public-source stopping rule.
- P3108 — Wild Rose Power Hub Load: proposed data-centre project and physical planning site resolved.
- P2958 — Hydrogen Canada MPC Load: industrial control context established; exact queue-to-parcel linkage unresolved.
- P2614 — Dow Fort Sask. Load: industrial project identity established from AESO primary engineering evidence.

These are not ranked for hiddenness or expected outcome. Terminal disposition means the declared research gates reached a documented stopping rule; it does not mean operation, measured demand, AI workload, or covert status was proven.

## Release / external-capability handoff

The remaining empirical blockers are now represented as explicit machine-readable interfaces:

- `data/track3/external_capability_handoff_2026-09-28.json` defines required evidence, authority, acceptance tests and current state.
- `data/track3/interval_power_telemetry_protocol.json` defines the interval-meter intake boundary and prevents queue/service capacity from being mislabeled as metered load.
- `data/track3/physical_target_leads.json` records lead-only candidates for the one unresolved reference-site target without promoting conflicting secondary coordinates into the canonical target set.
- `validate_track3_release.py` checks release-snapshot consistency and prevents schemas from being mistaken for empirical closure.

## Evidence semantics

The registry never silently converts:

- interconnection MW → measured electricity;
- measured electricity → compute;
- company ownership → physical site presence;
- public lead → canonical evidence;
- missing public record → evidence of absence;
- source availability → observation;
- aggregate owner snapshots → site inventory.

`UNKNOWN`, `NOT_TESTED`, `NO_PUBLIC_RECORD`, and `SOURCE_AVAILABLE_NOT_INGESTED` are preserved as research states.

## What still requires capability beyond public registry data

A true Track 3 implementation additionally needs trusted access to records and processes that this repository cannot create from public web evidence alone:

- complete accelerator-vendor declarations;
- transaction-level sales/resale/transfer records;
- globally consistent asset/serial identifiers;
- physical inspections under agreed authority;
- verified recycling/destruction records;
- intelligence reporting for specifically concealed facilities;
- a closed statistical sampling population;
- independently operated verification/certification authority;
- international procedures for disputes, audits, notice, access, and enforcement.

Those are not represented as complete merely because a schema exists.

## Completion criterion

This repository should be described as **Track-3-relevant research infrastructure** until the blocking gaps above are materially resolved.

The project is complete at the repository engineering level when every requirement has:

1. a machine-readable artifact;
2. a reproducible builder or validator where feasible;
3. explicit evidence semantics;
4. a current status;
5. a documented blocking gap when external capability is required;
6. no claim of empirical verification stronger than the retained evidence.
