# Data Layers — Continental Large-Load / Track 3 Registry

Updated: 2026-09-28

## Accounting rule

The registry deliberately separates **unique row-level queue records**, **project-level records**, **site-level evidence assertions**, **research targets**, and **aggregate/historical evidence**. These populations are not summed unless the accounting file explicitly identifies an additive relationship.

The current additive large-load expansion is:

- Core row-level registry: **1,540 records / 358.7181 GW**
- Additional known MISO records: **83 / 35.9 GW**
- Expanded known scope: **1,623 records / 394.6181 GW**

Everything below is a separate evidence or research layer unless explicitly stated otherwise.

## Public machine-readable layers

| File | Records | Granularity | Map layer | Additive to core? |
|---|---:|---|---|---|
| `data/registry_raw.csv` | 751 retained raw rows | Source-field extract | Indirect | No |
| `data/large_load_scope.json` | — | Accounting | — | — |
| `data/market_universe_manifest.json` | 11 market/source families | Coverage manifest | — | — |
| `data/project_level_extractions.json` | **271** | Individual project / permit / service / queue evidence | Yes | No |
| `data/project_level_map.json` | **271** | Individual mapped project records | Yes | No |
| `data/epoch_connection_research_targets.json` | **93** | One target per canonical Epoch site | Yes | No |
| `data/epoch_site_evidence_records.json` | **102** | Discrete site-level evidence assertions across 93 sites | Via target popups | No |
| `data/supplemental_large_load_evidence.json` | **61** | Utility / regulator / planning / process evidence units | Yes when mappable | Only the designated 83 MISO layer is additive |
| `data/supplemental_aggregate_map.json` | **66** | Aggregate / historical geographic footprints | Yes | No |
| `data/caiso_cluster_history.json` | **435** historical projects in C8-and-prior through C14 series | Historical generator queue population | Yes, footprints | No |
| `data/pjm_large_load_submission_history.json` | **28** | Public LAS document/evidence entries | Document layer | No |
| `data/public_data_catalog.json` | **61** datasets | Dataset catalog | — | — |

## Epoch connection-research layer

Every one of the **93 canonical Epoch AI sites** has a connection target.

Current target states:

- **2** site-specific queue IDs verified
- **2** public service / contract matches
- **1** public customer-planning record
- **72** U.S. sites with jurisdiction mapped but no verified site-specific queue ID
- **16** international connection-system targets

The target records preserve coordinates from the canonical Epoch map and carry a precision field. A jurisdiction-only or county/city point is not evidence of queue membership.

The legacy site-evidence inventory contains **102 discrete assertions across 93 sites**. The canonical Track 3 evidence ledger is separate and currently contains **1,253 evidence records**. Evidence types include utility relationships, facility records, public contracts, capacity observations and other site-specific source material.

## Project-level layer

The **271** project records currently include:

- BPA large-load request records in the current committed snapshot; the layer is backed by a refresh path to BPA's official InterconnectionQueueOutput.xlsx and preserves the secondary reproduction only as provenance/corroboration
- 33 Virginia DEQ issued air-permit records
- 28 AESO Data Load records
- 12 NYISO Load Project crosswalk records
- 9 additional NYISO 2024 Gold Book Table IV-7 records
- 6 IESO load / increase-load application records
- 8 AEP named customer/project records
- 2 EEI-listed projects
- 2 ISO-NE forecast project records
- 28 historical ComEd data-center forecast rows
- 7 Dominion data-center service projects
- 3 named utility/service/contract/distribution projects
- 1 Idaho Power named data-center project

The project CSV preserves the first source-specific capacity claim in a flat column while the JSON preserves the full `capacity_claims` array with source dates, units and qualifiers.

## Map semantics

The main dashboard map has separate controls for:

- Core row-level queue records
- Project evidence
- BPA large-load request layer (current row/mapping counts are read from `data/bpa_large_load_registry.json`)
- Aggregate / historical footprints
- Epoch AI site observations
- Connection research targets

Project markers are individual records. Aggregate circles are explicitly regional footprints. Historical circles use a separate visual treatment. Connection targets use rings; a target is not the same thing as a verified queue match.

The map currently carries:

- **271 / 271** project records plotted
- **93 / 93** Epoch connection targets plotted
- **66** aggregate/historical footprints
- **93** Epoch AI site observations

The dedicated BPA project layer is a normalized request/project snapshot whose current record and mapped counts are recorded in `data/bpa_large_load_registry.json`. A GitHub Actions refresh pulls BPA's official load workbook and replaces the snapshot when a new source population is published; unsupported geometry remains null. The current MISO public response has **83 additional >=100 MW requests totaling 35.9 GW** without sufficient public location fields for a defensible site point. Those records are intentionally **not pinned** to an invented location.

## Market completion state

### BPA
BPA's public interconnection page links the underlying **InterconnectionQueueOutput.xlsx** workbook, while a September 2026 secondary reproduction reports its own source totals for context. The repository does not assume those secondary totals remain current: the automated BPA refresh parses the official workbook when reachable and records the actual row population, capture date, SHA-256 and mapped/unmapped counts. Existing display geometry is preserved by request ID; unsupported new geometry remains null.

### CAISO
Historical Cluster 8-and-prior through Cluster 14 is preserved as **435 projects / 121.204 GW**, with a separately published Cluster 15 energy-only subset of 48 / 14.421 GW. Full row-by-row ingestion of every historical workbook remains incomplete.

### MISO
The row-level registry has 404 records plus the separately accounted 83 additional >=100 MW requests. The 83 remain unresolved at the public site-location layer.

### PJM
The registry includes the core queue population plus historical/current large-load submission and service-request evidence. PJM's dedicated Large Load Registry is not yet a complete public per-project load table.

### ERCOT
The registry preserves Batch Zero process evidence and the published aggregate large-load pipeline. Completed RIOO verification responses are not a complete public project table.

### SPP
The generator queue is public and the HILL/HILLGA large-load process is public. A complete customer-level HILL project list is not currently exposed in the public source.

### NYISO
21 project-level load records are now represented: 12 current/public Load Project crosswalk records plus 9 older NYISO Gold Book records. This is a conservative subset and not a claim that every current load request has been site matched.

### ISO-NE
Two forecast-level large-load records are preserved. Public study/service-stage detail is not fully enumerated.

### AESO
All 28 retained Data Load rows are individually represented with project IDs, project names, planning areas and capacity values. Commercial customer/proponent identity remains unknown when omitted by the public row.

### IESO / Ontario
Six current load/increase-load records are represented from the 2,074-application universe. OEB CCIM is kept as distribution-capacity context rather than converted into customer rows.

### Utility / regulator / non-core queue sources
The project-level layer also preserves public records from BPA, Virginia DEQ, ComEd, AEP, Georgia Power, Dominion, Entergy, Alectra, Idaho Power and other utilities/regulators.

## Provenance rules

1. Preserve raw publisher values and source dates.
2. Never convert MVA to MW merely to make units line up.
3. Never treat generation capacity as load capacity.
4. Never treat a county/state queue as proof of a site-specific queue record.
5. Never replace a missing value with an estimate and label it as publisher data.
6. Keep overlapping populations non-additive unless a record is explicitly designated as the additive 83-request MISO expansion.
7. Use `UNKNOWN`, null or explicit disclosure-limit states instead of silently dropping difficult records.

## Global AI data-center coverage

The repository mirrors **93/93 current Epoch AI explorer records** and maintains an external discovery queue at `data/global_ai_datacenter_coverage_2026-09-27.json`. External discovery universes are not additive to the canonical site or large-load totals. Promotion requires entity resolution, public-source verification, explicit capacity scope, date/status verification, and overlap checks.

## Where to start

- Full data catalog: `data/public_data_catalog.json`
- Market coverage manifest: `data/market_universe_manifest.json`
- Scope accounting: `data/large_load_scope.json`
- Full project ledger: `data/project_level_extractions.json`
- Project map: `data/project_level_map.json`
- 93-site connection targets: `data/epoch_connection_research_targets.json`
- 68 site-evidence assertions: `data/epoch_site_evidence_records.json`
- Supplemental evidence: `data/supplemental_large_load_evidence.json`
- CAISO historical series: `data/caiso_cluster_history.json`

This file describes repository artifacts. Upstream utility, regulator, RTO/ISO, or Epoch facts should still be cited to their original publisher/source.
