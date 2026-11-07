# Continental Large-Load Interconnection & Telemetry Registry

**Version 2.3** -- adds per-facility research records, an official source catalog,
and automated regeneration of those records during refresh.

Open-source ETL pipeline and public dashboard tracking large (>=100 MW)
bulk-power interconnection requests across nine RTOs/ISOs -- PJM, ERCOT,
SPP, MISO, CAISO, NYISO, and ISO-NE in the U.S., and Canada's IESO and
AESO -- with an entity-resolution and power-to-compute estimation pass
aimed at surfacing large requests that lack a confirmed public operator.

### Honest state of Track 3

As of 2026-09-28, the repository has a 93-site Epoch AI reference universe, site-level evidence coverage for all 93 sites, 631 retained derived remote-sensing observations across 92 sites, and two defensible site-specific queue IDs. For the sole unresolved physical target, September 11, 2026 Reuters reporting provides an attributed area-level lead near Al Dhafra Air Base, but no canonical parcel or facility coordinate; the site therefore remains unresolved for site-specific physical processing. The grid-connection state is 88 sites with site-level evidence, 3 with documented researched-no-public-record outcomes, and 2 with verified site-specific queue IDs. Those are evidence-layer results, not 93 facility-wide verifications: the current facility-wide state remains INCONCLUSIVE unless the defined end-to-end Track 3 gates are met, and no absence claim is inferred from a missing public record. The domestic grid registry is an independent public-evidence accounting/observability layer that can contribute evidence to the broader undeclared-compute problem; it is not itself a formal AI 2040 Phase 1 or Track 3 implementation and is not a bilateral U.S.–China verification system.

### Ambiguous-load closure pilot

The highest-value empirical layer is now a small closure pilot drawn from the registry's **141-record broad ambiguity research pool** rather than the already-public 93-site Epoch reference universe. The 141 records are not treated as 141 confirmed large-load discoveries; strict case admission requires source-level load classification. Four cases are carried through queue identification, entity resolution, defensible location, public-record search, physical observation, transformer/electrical review, and bounded adjudication: **Micron Fab 3 (606 MW) → confirmed manufacturing/industrial project identity with an unresolved queue-applicant mismatch; Pontoon Bridge Road Data Center (250 MW) → confirmed proposed data-center identity; Project IQ197 (1,380 MW) → inconclusive after search, with no defensible physical coordinate; Wild Rose Power Hub (1,300 MW) → proposed data-centre project identity resolved to an official planning point and independently processed multi-modal observations.** The pilot contains **18 derived multi-sensor physical observations across three locatable cases**. Closure does not mean facility-wide certification or detection completeness; the IQ197 result deliberately demonstrates a stopping rule rather than forcing a label.

See [`closed-cases.html`](closed-cases.html), [`CLOSED_CASE_PROTOCOL.md`](CLOSED_CASE_PROTOCOL.md), [`CLASSIFICATION_AUDIT_2026-09-27.md`](CLASSIFICATION_AUDIT_2026-09-27.md), [`STRICT_DISCOVERY_RESEARCH.md`](STRICT_DISCOVERY_RESEARCH.md), [`data/track3/strict_discovery_candidates.json`](data/track3/strict_discovery_candidates.json), and [`data/track3/ambiguous_case_studies.json`](data/track3/ambiguous_case_studies.json).

The broad 141-record ambiguous pool is now separated from a five-record strict admitted-load research queue. The strict queue requires explicit source-level load classification before a candidate can enter the discovery workflow; missing developer information alone does not qualify as discovery evidence. See `STRICT_DISCOVERY_RESEARCH.md` for the case-by-case source ladder and next gates.

### Phase 1 vs. Track 3

| Layer | What this repository currently provides | What it does not claim |
|---|---|---|
| **Independent public infrastructure accounting layer** | Nine North American market/connection sources, large-load records, entity resolution, Epoch cross-reference, site-level utility/service evidence, and public physical observations. The work is potentially useful to broader compute-accounting and undeclared-compute research. | A formal AI 2040 Phase 1 implementation, complete accounting of all AI-relevant compute, or complete accounting of electricity consumption. |
| **Track 3-adjacent research contribution** | A public-data evidence layer, research queue, physical-observation pipeline, source-universe catalog, and machine-readable mapping to the broader Track 3 accounting problem. | A formal AI 2040 Track 3 implementation, bilateral verification regime, treaty inspection capability, or proof that covert facilities have been found. |

### Observation-layer comparison

The repository's queue-vs-satellite comparison explains the complementary signal classes. Interconnection and service records can expose electrical intent or planning before a campus is visibly built; satellite/permit evidence can show physical realization that a queue record may miss. A covert project that expands existing service, uses behind-the-meter/private generation, or otherwise avoids a new publicly visible interconnection can evade the grid signal, which is why queue evidence is not treated as a complete covert-compute detector.

The comparison also documents the relationship to Cankaya's public power/cooling/hardware-signature research and to Epoch's satellite/permit-based data-center methodology without claiming that this registry reproduces or solves either method in full.

# What's in this repository

- `ingest_grid_queues.py` -- extracts, normalizes, and filters the nine
  source registers into one schema (`queue_id`, `rto_region`, `state`,
  `county`, `poi_substation`, `capacity_mw`, `projected_date`,
  `developer_entity`, plus `status` / `project_name` / `raw_fuel_technology`
  with `--include-raw-fields`). Run `python ingest_grid_queues.py --help`
  for the full flag list, or `--selftest` to run the current 43-check suite
  against synthetic fixtures without hitting any network.
- `compute_anomaly_detector.py` -- entity resolution against a small known
  hyperscaler/colocation-developer list, a PJM-specific heuristic for
  undisclosed developers, and a low/reference/high power-to-compute (FLOPs)
  range estimate. Also has `--selftest`. Unchanged in the MISO/CAISO/NYISO/
  ISO-NE/AESO update: its "Developer Not Disclosed" check already keys on the
  `NOT PUBLISHED...` prefix the new adapters use.
- `embed_registry_data.py` -- refreshes the data embedded in `index.html`
  from the two scripts' CSVs. Only the RTOs present in the CSVs are
  replaced, so one source can be refreshed without re-running the other
  eight, and re-running it is idempotent. `--dry-run` prints the
  before/after row and GW counts without writing.
- `build_facility_records.py` -- turns each published facility into a
  research-record artifact with the full union of normalized fields, retained
  ingest-level source fields when available, source/capture metadata, official
  links, and a source -> raw extract -> normalization -> enrichment ->
  publication provenance trail. `--check` verifies that every published
  facility has exactly one research record.
- `data/source_manifest.json` -- machine-readable official source catalog,
  including publisher, source URL, capture date/precision, scope, and source
  snapshot hashes where a source snapshot was retained by the build.
- `data/facility_records/` -- one JSON record set per RTO plus `index.json`.
  The public dashboard loads the relevant RTO file when a facility's Details
  view is opened.
- `index.html` -- the public dashboard. Single-file, Tailwind (CDN) +
  vanilla JS, no build step. The registry table's data is embedded
  directly in the file (by `embed_registry_data.py`), not fetched at
  page-load. Prose that quotes a count or a GW figure is filled in from
  that data at load time, so a re-embed cannot leave a stale number behind.
- `track3.html` -- the public Track 3 Evidence Observatory.
- `closed-cases.html` -- focused closure-pilot interface for three genuinely ambiguous large-load cases, with per-case evidence, physical observation summaries, scene IDs, adjudications, and explicit unresolved items. It loads the canonical Track 3 site-status, evidence, observation, power/cooling, source-stack, queue/source-universe, Module 1 gate, and external-source status artifacts, with site search, grid-state filtering, per-site evidence inspection, domain coverage accounting, source links, and explicit missingness semantics.
- `ai-data-center-explorer.html` -- Epoch-style interactive data-center explorer backed by the retained Epoch AI site, timeline, chip-quantity, chiller, and cooling-tower snapshots, with historical date controls and owner-logo mapping.
- `epoch-queue-vs-satellite.html` -- public comparison of the complementary observation channels: electrical/interconnection intent versus physical/satellite/permit evidence, including the disagreement set and explicit blind spots.
- `plan-a.html` -- public AI 2040 Plan A Track 3 research bridge. It maps the repository's current evidence and research tasks to the public AI 2040 Track 3 / Covert AI Projects discussion, provides direct AI 2040 reference links, and explains what is implemented, partial, or still design-only.
- `api.html` + `api/` -- the public machine-readable API surface, including the OpenAPI document and versioned JSON endpoints.
- `research.html` -- Research Operations Console for the 93-site Track 3 acquisition/research queue.
- `CLOSED_CASE_PROTOCOL.md` + `data/track3/ambiguous_case_studies.json` + `data/track3/strict_discovery_candidates.json` -- closure protocol and machine-readable case ledger for the ambiguous-load pilot.
- `bulk-download.html` + `data/bulk_download_manifest.json` -- downloadable dataset index and bulk-repository manifest.
- `PLAN_A.md` -- the repository-level Plan A contribution notes and scope boundary. This is an independent research contribution, not an AI Futures Project publication or certification.
- `CONTRIBUTING.md` -- evidence-submission protocol for adding reproducible Track 3 records.
- `CITATION.cff` -- machine-readable repository citation metadata.
- `PHYSICAL_SOURCES.md` + `data/track3/physical_source_manifest.json` -- provenance and retention rules for satellite/remote-sensing and building-footprint acquisition, with a read-only validator in `validate_physical_provenance.py`.
- `TRACK3_ONE_PAGE_SUMMARY.md` -- standalone technical summary for reviewers and outreach, separate from the interactive dashboard.
- `TRACK3_REVIEW_CHECKLIST_2026-09-27.md` -- current reviewer checklist with closed items and remaining gaps.

**Repository layout note:** The Track 3/Epoch/Plan A material is on the `main` branch alongside the registry core; the current audit found no separate `gh-pages` branch carrying a divergent Track 3 implementation.

## AI 2040 Plan A / Track 3 reference surface

For researchers using this repository specifically in the context of AI 2040 Plan A Track 3, start with the public [Plan A / Track 3 research bridge](https://anonrish.github.io/continental-load-registry/plan-a.html), then use the [Track 3 Evidence Observatory](https://anonrish.github.io/continental-load-registry/track3.html) for the underlying site/evidence layer.

The repository separates three things that should not be conflated:

- AI 2040's public proposal and terminology, which should be cited directly from AI 2040.
- Repository-derived observations and generated artifacts, which should be cited by artifact path and commit/version.
- Upstream datasets and source records, which should be cited alongside the repository when they support a factual claim.

Machine-readable Plan A mapping is in `data/track3/ai2040_plan_a_mapping.json`; Recommendation / Appendix B traceability is in `data/track3/ai2040_plan_a_traceability.json`; the audit-chain schema is in `data/track3/plan_a_audit_schema.json`; and the complete commit-level CI audit is in `data/ci/commit_audit.json` with a human-readable companion at `CI_AUDIT_2026-09-26.md`.

The repository is an independent research contribution. It is not an AI Futures Project publication, does not speak for AI 2040, and does not certify a verification regime. The interconnection core is North America only and should be interpreted as an independent public-evidence accounting/observability layer, not as a formal AI 2040 Phase 1 implementation or bilateral U.S.–China verification system. Public-source coverage can raise the cost of hiding and map the ambiguous middle, but it cannot establish that every covert facility has been found.

The public research-surface CI is defined in `.github/workflows/validate_public_surface.yml` and separately validates the Plan A / Track 3 pages and machine-readable documentation contracts.


- `.github/workflows/monthly_registry_update.yml` -- refreshes the registry
  from the live feeds daily at 06:00 UTC, or on demand, and commits the result
  to `main`. The filename is retained for compatibility; the workflow is daily.
- `data/archive/registry_snapshot_2026-09-24.csv` -- preserved 1,802-record
  publication snapshot from September 24, 2026. It is intentionally separate
  from the current registry so superseded queue rows remain auditable without
  being counted as current active facilities.
- `guard_registry_refresh.py` -- (2.1) the per-RTO sanity gate that workflow
  runs between the pipeline and `embed_registry_data.py`. Has `--selftest`.
- `investigate_ambiguous_loads.py` -- (2.1) builds
  `ambiguous_facilities_dossier.md`, a worklist of search leads for the
  ambiguous large loads, and applies human-verified identities from
  `ground_truth_overrides.json`. Has `--selftest`. See "Investigating the
  ambiguous tier".
- `ground_truth_overrides.json` (empty template),
  `ground_truth_overrides_example.json` (a complete, fictional entry) and
  `ambiguous_facilities_dossier.md` (generated from this build's data with
  `--input data/computational_load_estimates_new5.csv`).
- `data/` -- the retained ingest outputs, source manifest, per-RTO research
  records, historical snapshot, and `SOURCES.md`. The publisher's original
  source files are not bundled; where a source snapshot was preserved for the
  build, its SHA-256 is recorded.
- `requirements.txt` (pandas, requests, pydantic, rapidfuzz, openpyxl, urllib3; the self-tests need them), `LICENSE` (Apache 2.0).

## Related repository: AI 2040 Verification

[`AnonRish/ai-2040-verification`](https://github.com/AnonRish/ai-2040-verification) is a complementary repository testing concrete inference-side and operational verification mechanisms from the AI 2040 Plan A discussion. This registry works at a different evidence layer: public grid/interconnection records, physical-site evidence, Epoch AI cross-references, and accounting/research workflows. The two repositories should not be read as a single verified system; they are separate experimental implementations that can be evaluated together as complementary evidence layers.

## Contributing by role

A Track 3 contribution does not require building the whole system. The repository currently has concrete entry points for:

- **Grid / power systems:** add another connection region, reconcile utility/service records, or extend the MISO/BPA supplemental layers.
- **Remote sensing / geospatial:** improve scene selection, thermal/SAR/optical processing, coordinate quality, footprint linkage, or physical-change validation.
- **Data engineering / provenance:** strengthen manifests, hashes, schemas, reconciliation checks, generated-artifact validation, and reproducible refreshes.
- **Research / policy:** close one research task using the evidence ladder, evaluate the Phase 1 vs. Track 3 boundary, or compare independent evidence sources without collapsing uncertainty.
- **Verification / security:** audit claim gates, design adversarial tests, or connect this public evidence layer to independently testable verification mechanisms.

Start with research.html, CONTRIBUTING.md, and the open issues labeled good first issue.

## Epoch AI secondary evidence layer

The repository also imports the current Epoch AI AI Data Centers dataset as a
separate research layer. Epoch's public dataset was updated September 24,
2026 and currently covers 93 major AI data-center sites. Epoch describes the
dataset as independent research using satellite imagery, permits, public
documents, company disclosures and regulatory filings. Its public
documentation defines core site fields including current H100-equivalents,
current IT power, owner/user confidence, country, address and selected
sources, with separate timeline and chip-quantity records. See:
https://epoch.ai/data/ai-data-centers
and https://epoch.ai/data/data-centers-documentation/records.

The repository keeps the source-specific values separate:

- data/external/epoch_ai/data_centers.csv -- raw Epoch data-center table.
- data/external/epoch_ai/data_center_timelines.csv -- raw dated timeline records.
- data/external/epoch_ai/data_centers_chip_quantities.csv -- raw chip-quantity records.
- data/external/epoch_ai/registry.json -- 93 normalized Epoch site records, latest available timeline snapshot, latest chip quantities by type, all raw data-center row values, source metadata and crosswalk.
- data/external/epoch_ai/crosswalk.csv -- one row for every Epoch site, showing conservative matches to current queue records.
- data/external/epoch_ai/queue_crosswalk.csv -- one row for every Epoch site with its geographic grid/queue jurisdiction and any site-specific queue/service evidence found.
- data/external/epoch_ai/queue_crosswalk.json -- the same 93-site geographic queue/connection crosswalk in machine-readable JSON.
- data/external/epoch_ai/manifest.json -- capture metadata, row counts and SHA-256 hashes.
- data/external/epoch_ai/match_overrides.json -- human-reviewed queue crosswalk overrides; currently records the Lake Mariner campus/phase relationship to NYISO Q1670.
- build_epoch_grid_crosswalk.py -- rebuilds the 93-site geographic queue/connection crosswalk and embeds it into registry.json.

A complete source-universe catalog is maintained in `QUEUE_REGISTRY_UNIVERSE.md`
and as `data/external/epoch_ai/queue_source_universe.json`. The catalog currently
contains **26 direct queue/connection registries, 14 cross-cutting public
sources, and 4 supporting public-record source families**.

The project also produces:
- `data/external/epoch_ai/queue_crosswalk.csv` -- geographic queue/connection jurisdiction for every Epoch site.
- `data/external/epoch_ai/queue_gap_analysis.csv` -- the 93-site research worklist for closing remaining site-specific queue/connection gaps.
- `data/external/epoch_ai/queue_gap_analysis.json` -- machine-readable version of the same worklist.
`data/track3/` -- canonical Track 3 site-status, evidence-record, research-queue, observation-queue, and summary artifacts.
`data/track3/power_observations.json` -- site-level annual electricity-consumption observations with source provenance; these are not interval meter telemetry.
`data/track3/cooling_observations.json` -- selected site-level cooling-equipment observations with source provenance.
- `build_epoch_grid_crosswalk.py` -- rebuilds the complete jurisdiction layer.
- `build_epoch_queue_gap_analysis.py` -- rebuilds the 93-site gap analysis.
The crosswalk is intentionally conservative. **All 93 Epoch sites now have a
grid/queue or connection-system jurisdiction.** That is different from a
site-specific queue ID. For the 77 U.S. sites, the jurisdiction points to the
applicable RTO/ISO or utility/transmission-provider queue family. For the 16
international sites, the record identifies the relevant national or utility
connection system while keeping them outside the North American queue totals.

A "site-specific queue ID not yet verified" result means the repository has not
established that the Epoch campus is a particular row in the public queue.
Operational sites can also have a service agreement, customer planning record,
or completed connection rather than a current queue entry. Queue MW and Epoch
IT-power MW are different measurements and must not be summed as though they
were the same metric.

.github/workflows/sync_epoch_ai_data_centers.yml refreshes the three Epoch CSV
datasets daily at 07:30 UTC, on demand, and whenever index.html or the
crosswalk tooling changes. It refuses to publish a malformed/non-93 center
dataset and validates all inline dashboard JavaScript before committing.
Epoch states that its data are free to use, distribute and reproduce with
attribution under CC BY 4.0.

### Track 3 research operations

The Research Operations Console (`research.html`) turns the current 93-site missing-information sweep into a one-task queue: **214 effective unresolved publisher fields + 0 open Track 3 domain cells; all 1,395 defined site/domain cells are in terminal evidence-accounting states. A separate follow-on acquisition queue contains 24 observation tasks (18 cooling and 6 power telemetry).**. Each task includes site-specific search links, a source ladder, evidence-capture requirements, acceptance/rejection rules, and a canonical submission schema.

The queue is generated by `build_track3_research_backlog.py` and refreshed by `.github/workflows/track3_research_backlog.yml`. The generator asserts that task counts match the canonical sweep before publishing outputs.

## Track 3 physical verification layers

Build revision: 2026-09-27 dedicated Track 3 physical rebuild trigger.

The physical-verification layer is now an active acquisition surface rather than a checklist only. Every change to the physical acquisition script, Epoch registry, or this section triggers the public acquisition workflow so the repository can publish the resulting scene-level measurement artifact and provenance instead of only declaring source availability. The repository retains compact Sentinel-2 optical, Landsat Collection 2 surface-temperature, and Sentinel-1 GRD derived observations with scene provenance when the public source scene is available. Full source rasters remain external.

Current building-footprint geometry is acquired from the Overture Maps building dataset and retained as per-site GeoJSON. Overture documents that building geometry represents a two-dimensional building footprint or roofprint, and its Python client supports bounding-box downloads; this repository uses the underlying public GeoParquet through DuckDB for batch acquisition.

Transformer supply-chain evidence is preserved separately in:
- `data/track3/transformer_supply_chain_events.json` and `.csv` -- source-backed procurement, delivery, planning/specification, or installation events only.
- `data/track3/transformer_event_targets.csv` -- 93-site research queue with required event fields and source families.
- `data/track3/TRANSFORMER_SUPPLY_CHAIN.md` -- provenance and missingness rules.

These layers do not treat missing imagery, missing transformer records, building geometry, or queue absence as evidence that AI compute is absent.


## Current data coverage -- read this before citing a number from the site

The published dashboard currently contains **1,540 row-level facilities / requests and 358.7181 GW** across nine organized markets. A separate scope layer also records **83 additional MISO requests totaling 35.9 GW** whose public source omits required location fields; these are held outside the row-level table rather than assigned guessed geography. The resulting **expanded known scope is 1,623 requests / records and 394.6181 GW**. The archived September 24 snapshot contains 1,802 rows and 420.2054 GW, but is retained separately and is not additive to current totals. The live GitHub Pages site is the publication surface; the exact row-level total is calculated from the embedded
`REGISTRY_DATA` array at page load.

| Source | Rows | GW | Origin | Read this before citing it |
|---|---:|---:|---|---|
| PJM | 37 | 7.6 | live queue export, 2026-09-26 | current accepted refresh |
| ERCOT | 714 | 154.8 | live GIS Report, 2026-09-26 | registry uses the GIS/interconnection product; not a complete per-project large-load register |
| SPP | 139 | 30.5 | GI active-request listing, Sept 2026 | applicant name is not published in the retained build |
| IESO | 30 | 10.0 | application status listing, Sept 2026 | exact capture time was not retained |
| MISO | 404 | 81.5 | GI Queue JSON, 2026-09-19 | 83 live >=100 MW requests (35.9 GW) lacked a published state and were excluded |
| CAISO | 63 | 23.1 | Cluster 15 request workbook, 2026-09-19 | **Cluster 15 only -- not CAISO's whole queue** |
| NYISO | 105 | 25.3 | interconnection queue workbook, 2026-09-19 | includes the Load Projects sheet |
| ISO-NE | 19 | 4.9 | IRTT public queue, 2026-09-19 | study stage is not published in the retained table |
| AESO | 47 | 24.2 | September 2026 Connection Project List | includes Data Load / Industrial Load rows |

### Data-universe completion

The project-level dataset now includes **60 BPA large-load request records** with public request identifiers, filed MW, POI text and status where the public cross-check exposes them. These are secondary reproductions of BPA public load-queue rows and remain non-additive.

The repository now includes a machine-readable **market universe manifest** at `data/market_universe_manifest.json` with a CSV companion. It explicitly separates what each operator publishes from what remains a disclosure limit. The dedicated `BPA_LARGE_LOAD.md` source note records the official workbook refresh contract, current fingerprint and geometry/missingness rules.

The project-level layer has grown to **271 records**, with **271 mapped project records**. The only intentionally unlocated project-level record is the **Woostor LLC Alabama Power contract**, because the public contract evidence reviewed does not identify a site. A separate `data/supplemental_aggregate_map.json` adds **66 geographic evidence footprints**; those footprints are shaded on the map and explicitly labeled as non-facility evidence.

The 271 project records have one canonical `evidence_type` each. Current counts are:

- `secondary_large_load_request_record`: 60
- `environmental_permit_record`: 33
- `nyiso_gold_book_large_load_record`: 31
- `aeso_data_load_project_record`: 28
- `utility_data_center_forecast_project_record`: 28
- `caiso_large_load_interconnection_project`: 14
- `nyiso_load_project_site_record`: 12
- `utility_data_center_service_project`: 9
- `named_utility_load_project`: 8
- `ieso_load_application_record`: 6
- `utility_named_data_center_service_project`: 5
- `utility_service_project_secondary_capacity`: 3
- `utility_large_load_contract_record`: 3
- `secondary_data_center_interconnection_project`: 3
- `named_large_load_project_from_industry_list`: 2
- `iso_ne_forecast_large_load_project`: 2
- `named_utility_contract_project`: 1
- `named_utility_service_project`: 1
- `named_distribution_connection_project`: 1
- `utility_named_data_center_project`: 1
- `utility_data_center_service_area_record`: 1
- `utility_named_large_load_transmission_project`: 1

Those counts are generated from the canonical JSON and sum to exactly 271. They are evidence-source classifications, not facility categories. The canonical JSON record and its cited sources remain authoritative for every individual record.

The interactive map overlays **271 mapped project-level records** and separately represents the unlocated Woostor contract through a labeled Alabama regional evidence footprint. `data/map_layer_manifest.json` is the machine-readable inventory of every map overlay and its geometry/accounting treatment.

PJM large-load history is cataloged in `data/pjm_large_load_submission_history.json` with **28 public 2025–2026 LAS material entries**, preserving the utility submission/document trail without treating documents as facility rows.

CAISO historical coverage is now represented in `data/caiso_cluster_history.json` and CSV. The series contains 49 Cluster 8-and-prior projects, 27 Cluster 9, 21 Cluster 10, 30 Cluster 11, 44 Cluster 12, 60 Cluster 13 and 204 Cluster 14 projects — 435 projects and 121.204 GW in that historical series. A separately published Cluster 15 energy-only subset is recorded at 48 projects / 14.421 GW. These generator-queue figures are a distinct history layer and are not added to the large-load total.

The remaining hard limits are explicit rather than hidden: MISO's 83 additional >=100 MW requests remain unlocated in the accessible public response; ERCOT's Batch Zero process has public forms and eligibility/verification notices but not a public completed-response table; PJM's public service-request pages expose generation/merchant-transmission/long-term-firm service structures but do not establish a per-load-request dataset; SPP's HILL framework is public but its customer-level load list is not; ISO-NE publishes a small forecast table but not project-specific study stages. These are tracked as source/disclosure states, not silently converted into fake rows.



The repository also preserves public utility, regulator, planning, connection and permit evidence that cannot safely be collapsed into the core nine-market row-level total without double-counting or inventing missing fields. See `data/supplemental_large_load_evidence.json`.

Current examples include:
- MISO: 83 additional live >=100 MW requests (35.9 GW) lacking published location fields.
- Dominion Energy Virginia: approximately 70 GW of large-load DP Requests advancing through its connection queue at the end of 2025.
- ComEd: 16 GW of highly probable large-load interconnection requests in its 2026 planning material.
- Salt River Project: 80 projects above 10 MW totaling 15.308 GW, including 52 data-center projects totaling 14.140 GW.
- BC Hydro: 15 AI/data-centre applications representing close to 800 MW.
- Portland General Electric: five executed data-centre customer contracts totaling 430 MW.
- Entergy Louisiana/Hut 8: River Bend initial 330 MW utility capacity for 245 MW critical IT load, with potential scaling to 1 GW utility capacity.
- ISO New England: a 200 MW data-center project listed in the CELT 2026 large-load forecast.
- Virginia DEQ: a data-center air-permit identity inventory alongside reports of 72 operating data centers in Loudoun County and nine more in planning.
- Ontario: the IESO application-status universe and OEB Centralized Capacity Information Map are preserved as broader connection/grid-context layers.

Additional utility layers now include APS's reported 19 GW uncommitted extra-large-customer queue, AEP's 69 GW of contracted load growth through 2030, AEP Ohio's approximately 12 GW of new contracted load through 2030, the planned 10 GW Piketon data-center campus, Ameren Missouri's up-to-2 GW demand-planning envelope, and PacifiCorp's ongoing tens-to-hundreds-of-MW large-customer request stream. These remain supplemental and are not added to the core total without project-level deduplication.

The supplemental evidence file now contains **61 source/evidence units**, while the dedicated Track 3 evidence graph contains **368 retained evidence records**. These layers are not automatically additive.

These measures are **not summed** into a single "total capacity" because they have different units, vintages, geographic scopes, stage definitions and overlap relationships. The only direct additive expansion to the current row-level registry is the separately identified 83-record / 35.9 GW MISO population used in the expanded-known scope metric.

### Epoch connection research targets

Every one of the **93 canonical Epoch AI sites** now has a connection-research target record in `data/epoch_connection_research_targets.json` with grid jurisdiction, site-specific queue state, current site IT-power context, evidence count, source trail, coordinates and next research action. The companion `data/epoch_connection_research_targets.csv` is a flat export. The target layer is intentionally separate from verified queue membership: a dashed map target can mean only that the relevant queue/utility system is known.

The canonical Track 3 evidence inventory is preserved in `data/track3/evidence_records.json`; the current build contains **1,221 retained evidence records across the 93-site universe**. A separate public research dossier at `data/track3/public_site_dossier.json` joins Epoch fields, grid crosswalks, public connection evidence, and publisher-field completeness. These assertions can identify utilities, public contracts, facility records or other site-specific evidence without establishing a formal queue ID. They are not additive capacity records.

On the map, the **Connection targets** toggle overlays all 93 research targets on the same site geometry as the Epoch layer. Target popups show the current grid jurisdiction, research state, queue ID/name where verified, site-specific capacity when known, evidence-item count, source links, and the next action. Geometry precision is carried through from the canonical Epoch map record.

### Project-level extraction

The repository has a dedicated project-level evidence layer at `data/project_level_extractions.json` with a CSV export at `data/project_level_extractions.csv`. It currently contains **271 individually identifiable records** extracted from public source material:

- **60 BPA large-load request records** remain in the separately curated project-level extraction, including publicly reproduced request IDs, filed MW, point-of-interconnection text and status where exposed. The broader dedicated BPA official-workbook source exposed **457 raw L-series rows**; the dedicated normalized Track 3 large-load layer retains **128 requests at >=100 MW** and is not counted inside the 271-record project extraction.
- **33 Virginia DEQ issued-air permit records**, with permit number, named site/project, county and issuance date.
- **28 AESO Data Load projects**, with project IDs, project names, planning-area/town identities and public DTS/contract-capacity values.
- **12 NYISO Load Project records**, with queue ID, project/developer, MW, county and POI/site information where publicly exposed.
- **6 IESO load/increase-load application records**, including applicant, project name, zone, MW and target date.
- **8 AEP named customer/project records**, **2 EEI-listed projects**, **2 ISO-NE forecast project records**, and **3 named utility/service/contract/distribution records** (Project Camellia, River Bend AI campus, and Vaughan MTS #6), plus **28 historical ComEd data-center forecast rows**, **7 Dominion data-center service projects**, **9 additional NYISO Gold Book rows**, and **1 Idaho Power named data-center project**.

The project layer is deliberately **not additive** to the 1,540-row core queue table or the 1,623-record expanded-known scope. Multiple dated capacity claims inside one project are retained separately. No MW is inferred when a utility does not publish the load.

The interactive map now overlays **271 mapped project-level records** and separately represents the one unlocated Woostor contract as a labeled aggregate footprint. Map geometry is explicitly display geography (public site-area, town, county, state/province or country centroid), not an invented street address. A separate `data/supplemental_aggregate_map.json` layer adds **66 aggregate utility/regulatory and historical-queue footprints**, displayed as shaded areas and labeled as non-facility evidence.

The Epoch AI map layer contains **93 frontier-site observations** and is backed by the canonical `data/external/epoch_ai/site_level_connection_evidence.json` crosswalk. The current Track 3 site-status layer reports **88 SITE_LEVEL_EVIDENCE, 3 RESEARCHED_NO_PUBLIC_RECORD, and 0 PENDING_RESEARCH** for grid connection; two sites have verified site-specific queue IDs. The map popups expose the evidence status and available source links.

The remaining hard limits are explicit rather than hidden. MISO's 83 additional >=100 MW requests remain outside the row-level table because the captured public response lacks the state/location fields needed to make defensible site rows. ERCOT's Batch Zero process is public, but completed RIOO responses are not exposed as a public per-project table. PJM's public Load Analysis Subcommittee materials provide a dated utility-submission history, but they do not establish a public per-load-request database. SPP's HILL process is public without a customer-level public load list. ISO-NE's forecast material names large-load projects but does not publish a complete project-specific study-stage history.

### PJM large-load submission history

`data/pjm_large_load_submission_history.json` and its CSV companion preserve **28 public 2025–2026 PJM Load Analysis Subcommittee material entries**, including the named utility large-load/data-center submission trail from the September 2025 and September 2026 meetings. These are document/evidence records, not unique facilities or additive MW rows.

### CAISO historical queue coverage

`data/caiso_cluster_history.json` and its CSV companion preserve a historical generator-interconnection series covering Cluster 8-and-prior through Cluster 14: **435 projects / 121.204 GW** in the historical series. A separately published Cluster 15 energy-only subset is recorded at **48 projects / 14.421 GW**. The current full CAISO Public Queue Report is linked from the dashboard as the source for future complete row-level refreshes; historical series values are kept separate and non-additive.

### Additional utility-linked projects

The project layer also includes six newly extracted utility-linked records outside the organized-market core: Google/Xcel's Pine Island, Minnesota data center; Google's West Memphis, Arkansas data center; AWS's Clinton, Mississippi data center; QTS Bessemer / Project Marvel; Cloverleaf Infrastructure's Project Red Clay; and the Sovereign Gazelle/Somerville large-load project. Source-specific capacity claims are retained only where the cited public record provides them; associated generation additions are not relabeled as data-center load.

### Supplemental public large-load evidence

The supplemental evidence file now contains **61 source/evidence units**. The website provides a searchable browser for all of them. These include MISO's unlocated requests, utility pipelines, regulatory aggregates, planning forecasts, connection/process sources, permit inventories, ERCOT Batch Zero source material and non-RTO utility evidence. The measures are not summed because their populations, dates, units and overlap relationships differ.

## Regulatory filings section

`index.html`'s "Regulatory filings" section links to two PDFs by filename:

- `FERC_Docket_RM26-4-000_Comments_Computational_Load_Telemetry.pdf`
- `BIS_Rulemaking_Petition_5USC553e_Computational_Load_CEII_Protocol.pdf`

The links are live (`available: true` in the `FILINGS` array near the
bottom of `index.html`), and both PDF files are now present in the repository
root with those exact filenames.
Place both files, with those exact names, in the same directory as
`index.html` (the repository root) before deploying, or the two Download
buttons will 404. The daily workflow fails if either link stops being marked
`available: true` in `index.html`, and raises a warning if either PDF is not in
the repository root.

## Automated daily refresh

`.github/workflows/monthly_registry_update.yml` (file name kept for compatibility)
runs at 06:00 UTC every day and on demand (Actions tab, *Daily Registry Update*,
Run workflow; tick `dry_run` to execute everything without committing). It checks
out the repo, sets up Python 3.12 with a pip cache, installs
`requirements.txt`, runs the self-tests of `ingest_grid_queues.py`,
`compute_anomaly_detector.py`, `investigate_ambiguous_loads.py` and
`guard_registry_refresh.py`, fetches every live feed, estimates compute load,
gates each RTO, embeds the accepted RTOs into `index.html`, and checks the two
regulatory PDF links. Then, only on `main` and only if `index.html` or the two
CSVs in `data/` changed, it commits and pushes as
`Automated Daily Registry Sync: [YYYY-MM-DD]`. Logs and the fresh outputs are
attached to every run for 30 days.

**Live validation status.** A production live-feed run completed successfully on
September 26, 2026. All four offline self-test stages passed, the live ingest
completed, the per-RTO refresh gate completed, and the registry update was
committed. For future changes, a manual run with `dry_run` ticked remains the
safe way to inspect the refresh gate before allowing publication. Some RTO
sites may also refuse requests from GitHub-hosted runners; that shows up as an
unavailable feed, not as a failure.

Each RTO ends a run in one of three states:

| Outcome | When | Effect |
|---|---|---|
| accepted | fresh row count and capacity are within 50%-200% of what `index.html` holds, or the RTO is new | its rows are replaced |
| unavailable | the run produced no rows for it (blocked, moved or failed feed) | previous rows kept; a warning is raised |
| rejected | outside that range, unknown RTO label, duplicate queue IDs, unreadable capacity, or the raw and enriched CSVs disagree | previous rows kept; an error is raised; the other RTOs are still committed and the run then ends red |

The two CSVs the workflow commits (`data/registry_raw.csv`,
`data/computational_load_estimates.csv`) hold only the RTOs accepted in the
latest run; `index.html` is the cumulative registry. Automated runs do not
record a SHA-256 of each raw capture the way `data/SOURCES.md` does for the
v2.0 build; the run log and the git history are the record. The thresholds are
the `--min-ratio` / `--max-ratio` arguments of the `guard_registry_refresh.py`
call.

Requirements: GitHub Actions enabled for the repository, no secrets, and a
`main` branch that accepts pushes from `github-actions[bot]` (a rule that
requires pull requests will make the final push fail).

## Investigating the ambiguous tier

`investigate_ambiguous_loads.py` turns the "genuinely ambiguous" large loads
into a worklist, `ambiguous_facilities_dossier.md`:

```bash
python investigate_ambiguous_loads.py                    # all nine sources, from index.html
python investigate_ambiguous_loads.py --input data/computational_load_estimates_new5.csv
                                                         # adds POI, status, technology and dates for those RTOs
python investigate_ambiguous_loads.py --rto PJM,ERCOT,SPP,IESO   # the original four sources
python investigate_ambiguous_loads.py --top 25 --engine bing --json leads.json
python investigate_ambiguous_loads.py --selftest
```

It reads the registry embedded in `index.html` (all nine RTOs) and lets an
enriched CSV replace the rows of the RTOs it contains, so a partial CSV never
drops an RTO. It keeps records with `capacity_mw >= 100`, tier `Genuinely
Ambiguous / Unclassified Large Load` and entity category `Developer Not Matched
To Known List` or `Developer Not Disclosed`, largest first. In this build that
is **141 facilities (53.9 GW)**: NYISO 38, MISO 36, AESO 30, IESO 25, SPP 12.
The "38" quoted for the first four sources is the four-source tier count; under
this filter those sources give 37, because IESO `2026-866` (Project ONT1, 450
MW) has a developer that resolved to a known colocation developer and is
excluded. PJM and ERCOT contribute none.

For each facility the dossier has up to seven search leads -- municipal council
minutes and zoning approvals, environmental and utility-regulator registries,
substation and interconnection filings -- worded for that jurisdiction (an
Ontario rezoning is a "zoning by-law amendment", an Alberta one a
"redesignation"). The script makes no network requests and verifies nothing: a
lead is a search, not a finding.

**Recording a verified identity.** When a person confirms a facility from a
public record, add an entry to `ground_truth_overrides.json` (format:
`ground_truth_overrides.example.json`) with `rto`, `queue_id`, a
`verified_label`, `confirmed_by`, `confirmed_on` and at least one `evidence`
citation. The allowed labels are Confirmed Data Center Campus; Confirmed
Industrial Park / Manufacturing; Confirmed Utility / Distribution Load Growth;
Confirmed Cryptocurrency Mining; Confirmed Other Large Load; Ruled Out
(Duplicate / Withdrawn / Data Error). Re-run and the facility gets a VERIFIED
block with the label and citations. An entry with no evidence, an unknown
label or a mistyped key stops the run (exit code 2) and lists every problem; an
entry that matches nothing in the registry is listed in the dossier's audit
section. Overrides change only the dossier -- not the CSVs, the tier
classification or the dashboard.

## Running the pipeline

```bash
pip install -r requirements.txt
python ingest_grid_queues.py --selftest
python compute_anomaly_detector.py --selftest
python ingest_grid_queues.py --pjm-file <path> --ercot-file <path> \
    --miso-file miso_gi_queue.json --caiso-file <cluster xlsx> \
    --nyiso-file <queue xlsx> --isone-file irtt.html --aeso-file <project list xlsx> \
    --include-raw-fields --output registry_raw.csv
python compute_anomaly_detector.py --input registry_raw.csv --output computational_load_estimates.csv
python embed_registry_data.py --raw registry_raw.csv --enriched computational_load_estimates.csv
```

Sources without a `--*-file` flag are fetched live. For a partial refresh,
run the two scripts on just the files you have and `embed_registry_data.py`
replaces only those RTOs in `index.html`.

To produce the dossier after a refresh: `python investigate_ambiguous_loads.py`.

## Deploying the dashboard

`index.html` is fully static and self-contained -- no server, no build,
no API keys. Open it directly in a browser, or serve the repository root
with any static host. See the GitHub Pages instructions provided alongside
this archive.

## License

Apache License 2.0 -- see `LICENSE`.

## Contact

grid.telemetry.initiative@gmail.com


**Map coverage:** `data/project_level_map.json` contains 271 mapped project records out of 271 project-level records; all records now have display geometry, with service-area/jurisdiction points explicitly labeled where a site address is not public. `data/supplemental_aggregate_map.json` contains 66 aggregate/historical records and currently has numeric display coordinates for all 63. Coordinate precision is retained per record; a centroid/display point is never presented as a street address.


Map-layer accounting is published in `data/map_layer_manifest.json` and `data/map_layer_manifest.csv`.


Live Track 3 rebuild revision: 2026-09-27T02:03Z.


<!-- Physical rebuild trigger: 2026-09-27 -->

## Global AI data-center coverage

The repository now preserves **100% of the current Epoch AI AI-data-centers explorer: 93 of 93 records**, accessed 2026-09-27. This is a complete mirror of the current Epoch explorer, not a claim that every AI data center on Earth is publicly known. Epoch's September 2026 research update reported 44% estimated global AI-compute coverage at the time its explorer contained 86 sites, with lower estimated coverage for China.

A separate discovery ledger in `data/global_ai_datacenter_coverage_2026-09-27.json` tracks external candidate facilities/programs from AI Data Center Index, Data Center Index and Compute Atlas. Candidates remain outside the canonical 93-site layer until entity resolution, source verification, capacity-scope checks and overlap testing are complete.


## Broader global compute database

The public site now includes [Global Compute Universe](https://anonrish.github.io/continental-load-registry/global-compute-universe.html), a federated discovery surface that is intentionally broader than the 93-site Epoch frontier-AI layer. It joins three separately labeled source universes:

- **Epoch AI:** 93 current frontier-AI explorer records.
- **Compute Atlas:** 2,228 U.S. compute records in its September 2026 dataset, including data centers, crypto-mining sites, and dedicated generation records.
- **Data Center Index:** 901 global tracked rows, including 702 counted campuses and additional non-campus rows.

These source populations are **not added together as a single census number**. The interface performs conservative name-plus-place linkage, preserves source provenance, and marks the source/type of every record. Compute Atlas and Data Center Index are reused under their stated CC BY 4.0 terms with attribution; the full source manifest is `data/global_compute_universe_sources_2026-09-27.json`.

The broader database also has a scheduled GitHub Actions refresh workflow at `.github/workflows/sync_global_compute_universe.yml`, which stores reproducible source snapshots when the publishers' public endpoints change.


## Company-by-company global facility layer

The public [Company Data-Center Registry](https://anonrish.github.io/continental-load-registry/company-registry.html) adds a company/entity layer on top of the facility database. It uses the current AI Data Center Index operator universe (225 operators) as the live discovery backbone and loads company-specific facility slices from the publisher's structured operator endpoints. It keeps operator, owner, developer, tenant, hardware partner and power-provider roles distinct. Company-region or availability-zone counts are not treated as physical-building counts.

The registry also preserves the 93-site Epoch frontier-AI universe and the broader Compute Atlas / Data Center Index discovery layers separately. Different populations are intentionally non-additive.
