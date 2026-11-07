# Track 3 Evidence Layer

This layer turns the continental registry from a queue table into an auditable evidence graph for whether material AI compute can be accounted for through public physical, electrical, hardware, and independent evidence.

### Scope and limits

The current registry is a **North America public-evidence layer**, not an international U.S.–China verification system. It maps most directly to the Phase 1 task of establishing how much publicly evidenced compute/load exists and who is associated with it. Extending that work to bilateral U.S.–China visibility would require additional country-specific public sources, legal/access pathways, and independent verification mechanisms beyond this registry.

The observatory should also not be described as a detector of secret facilities. Its observations are built from public signals: queue and connection records, utility/service records, permits, regulatory documents, operator disclosures, imagery and other publicly accessible evidence. A genuinely covert project would have an incentive to avoid those signals. The defensible claim is that the registry can **raise the cost of hiding and map the ambiguous middle**, while keeping uncertainty explicit.

# Evidence states

**PENDING_RESEARCH**, **SOURCE_AVAILABLE_NOT_INGESTED**, and **NOT_INGESTED** never mean that a facility or compute stockpile is absent.

| State | Meaning |
|---|---|
| VERIFIED_SITE_SPECIFIC | A defensible site-specific queue/connection record is attached. |
| SITE_LEVEL_EVIDENCE | A site-specific utility, service, planning, regulatory, or facility record exists, but no queue ID is asserted. |
| JURISDICTION_ONLY | The applicable grid/connection family is known, but the physical site is not tied to a site-specific public record. |
| PENDING_RESEARCH | The site-specific search has not yet produced a retained connection/service record. |
| SOURCE_AVAILABLE_NOT_INGESTED | A relevant public external dataset exists and is cataloged, but has not yet been joined to the evidence graph. |
| NOT_INGESTED | The evidence stream is specified by the verification design but numeric observations are not yet ingested. |
| INGESTED_DERIVED | Numeric/derived observations have been computed from a public source scene and retained with provenance; this is not a positive finding about AI compute by itself. |
| INGESTED_POLYGONIZED | Current building-footprint polygons have been ingested with source provenance; geometry alone does not establish AI tenancy. |
| INGESTED_PARTIAL | Source-backed records are ingested for part of the site universe; uncovered sites remain explicit gaps. |
| RESEARCH_QUEUE | A structured, site-specific acquisition/research target exists, but the requested evidence has not yet been retained for that site. |
| UNKNOWN | The evidence needed to classify the field is not currently available. |

## Current site evidence

As of 2026-09-28, the preserved 93-site Epoch universe has site-level research coverage for all 93 sites. The canonical site-status layer distinguishes 2 verified site-specific queue IDs, 88 sites with site-level grid/connection evidence without a verified queue ID, and 3 sites where a documented site-specific public-record search produced no retained public queue/service identifier. The 3 no-public-record outcomes are not evidence that grid service is absent.

The canonical grid-connection status is now 2 `VERIFIED_SITE_SPECIFIC`, 88 `SITE_LEVEL_EVIDENCE`, 3 `RESEARCHED_NO_PUBLIC_RECORD`, and 0 `PENDING_RESEARCH`. The zero-pending state means every site's current site-specific search has a documented outcome. `RESEARCHED_NO_PUBLIC_RECORD` means the public search did not produce a retained queue/service identifier; it does not mean the site lacks an electrical connection.

A separate power-observation layer now contains six company-reported 2023 annual electricity-consumption snapshots for Meta facilities (Eagle Mountain, Los Lunas, New Albany/Meta Prometheus, Sarpy, Gallatin, and Huntsville). These are aggregate annual figures, not interval utility telemetry, so the P0 interval-demand acquisition tasks remain open. Eighteen site-level cooling snapshots are represented in the current site-status layer; two directly retained equipment snapshots are published for Google Arcola and Google Kansas City East. These are supporting infrastructure evidence, not direct thermal telemetry.

The site-status model also tracks service/energy-contract evidence separately from grid-queue evidence, plus a distinct compute-tenancy domain. This prevents contracts and leases from being silently presented as queue IDs.

The physical-verification acquisition pipeline now runs Sentinel-2 optical, Landsat Collection 2 surface-temperature, and Sentinel-1 GRD searches against public STAC catalogs. Successful scene windows produce compact derived measurements with scene provenance; full rasters remain external. A separate current building-footprint pipeline ingests Overture Maps building polygons, while dated construction chronology remains separate.

The time-series verification layer is now published at `data/track3/time_series_verification.json` with a CSV event ledger. The current source snapshot yields **545 Epoch timeline rows**, of which **449 are observed/reported** through 2026-09-27 and **96 are future/predicted**; all 93 Epoch sites have at least one observed timeline point. It separately retains six site-specific annual electricity-consumption snapshots, eight CAISO historical-series records, and 28 dated PJM LAS material records. Event-to-event IT/total-power changes are derived only where both source rows provide numeric values. A universal interval-load, transient, or training/checkpointing signal is not claimed without interval telemetry.

The transformer layer now retains source-backed events rather than a zero-record placeholder. Three source-backed transformer events are currently retained, including the Meta Hyperion planned MISO transformer specification and an Entergy-reported transformer transport event; the third record remains source-backed without being treated as installation/energization proof. The layer also publishes a 93-site transformer research target queue. Planned specifications are not installation/energization evidence, and missing transformer events are not evidence of absence.

## Facility-level provenance

The facility-level provenance ledger is published at `data/track3/facility_provenance.json` with a row-oriented export at `data/track3/facility_provenance_records.csv` and schema at `data/track3_facility_provenance_schema.json`.

For each of the 93 Epoch facilities, the ledger exposes:

- retained raw Epoch publisher fields and the corresponding normalized values;
- the source URL and repository raw-source locator;
- capture/access dates separately from dataset update dates;
- the exact retained source field/value where the repository actually contains it;
- the transformation applied by the provenance builder;
- evidence type and the published confidence label;
- conservative primary/secondary/unclassified evidence-origin metadata;
- metadata-derived corroboration across distinct source URLs/names;
- structured conflict checks without treating different sources as automatically contradictory;
- latest available verification date;
- automated audit trail, with no human reviewer invented;
- Git commit/content-hash information for reproducible historical snapshots.

A missing publication date or source excerpt remains explicitly missing. The ledger does not substitute a dataset update date for a publication date, and it does not claim that a source is independent merely because it is hosted at a different URL.

The rebuild is automated by `.github/workflows/track3_facility_provenance.yml`. Each build can create a new manifest under `data/track3/provenance_snapshots/`, keyed to the build commit.

## Evidence domains

Each Epoch site receives machine-readable status for site identity, construction history, chip inventory, grid/connection, service/energy contracts, compute tenancy, actual power telemetry, remote sensing, cooling, transformer supply chain, chip ownership, chip users, and chip shipments.

## Build

```
python build_track3_evidence.py
```

The builder joins both the primary site-level evidence file and the public evidence embedded in the queue crosswalk. Crosswalk evidence is retained as a separate provenance layer and is never promoted to a queue ID without a defensible match.

Outputs:

- `data/track3/site_status.json`
- `data/track3/evidence_records.json`
- `data/track3/research_queue.json`
- `data/track3/summary.json`

The Epoch sync workflow rebuilds and validates these artifacts after refresh.

## Measurement separation

Epoch IT power, projected IT power, utility service capacity, queue/interconnection capacity, transmission capacity, generation capacity, contracted demand, chip TDP, and actual measured site load are different measurements and must remain separate.

## Observation acquisition queue

`data/track3/observation_queue.json` is a generated, state-dependent acquisition worklist for the 93 Epoch sites. Its task count changes automatically when supporting source snapshots become available. The current build retains separate tasks for interval power telemetry, remote sensing, cooling equipment, and HV-transformer supply; chip ownership, chip users, and chip shipments are promoted to snapshot-backed evidence when all required public source files are present.

Each task carries its current state, priority, required fields, site-specific next action, and—where available—the primary grid source URL/type/date plus the existing public source families to search. `data/track3/observation_queue.csv` is the flattened review version, and the JSON includes generated counts by domain and priority so CI can verify that the summary and task list agree.

Completing a task requires attaching the resulting observation or record with source provenance. A task's `NOT_INGESTED`, `SOURCE_AVAILABLE_NOT_INGESTED`, `UNKNOWN`, or `PENDING_RESEARCH` state is not evidence that the underlying facility condition is absent.


## Research operations backlog

The dated missing-information sweep is converted into a one-task research queue at `data/track3/research_work_queue.json` and `data/track3/research_work_queue.csv`. The Research Operations Console is published at `research.html` and is driven by the queue. The backlog generator asserts that every effective unresolved publisher field and every open Track 3 domain cell becomes exactly one research task before outputs are written.

- Effective unresolved publisher fields: 214
- Open Track 3 domain cells: 0
- Total open public-source research tasks: 214
- Separate follow-on observation-acquisition tasks: 24 (6 interval-power telemetry, 18 cooling)
- Canonical sites represented: 93

The machine-readable engineering-closure register at `data/track3/engineering_closure_2026-09-28.json` verifies that these remaining tasks are explicitly accounted for; it does not convert them into completed evidence.

The operational playbooks are in `data/track3/research_workflows.json` and `RESEARCH_WORKFLOWS.md`. They specify source ladders, site-specific search query templates, evidence-capture fields, acceptance/rejection rules, result dispositions, and the canonical handoff schema. A public lead or NO_PUBLIC_RECORD outcome is never silently converted into a positive canonical fact.
