# Track 3 automated pipeline

## What is automated now

The repository has source-specific ingestion adapters for the public source families currently supported by executable sync code:

- PJM Cycle Service Requests
- MISO public queue
- CAISO public queue
- NYISO public queue
- SPP active public queue
- Epoch AI data-center and global compute snapshots
- ERCOT GIS public source capture
- ISO-NE IRTT public-page capture
- IESO Application Status public-page capture
- AESO Connection Project List XLSX capture
- physical-verification/building acquisition workflows where the source pipeline is executable

These adapters run sequentially in `.github/workflows/track3_automated_pipeline.yml` so one source cannot silently overwrite another source's generated files.

## Source coverage contract

Every source in the source catalog is assigned an explicit mode:

- **AUTOMATED_ADAPTER** — a repository parser/sync workflow exists and is executed by the pipeline.
- **HEALTHCHECK_ONLY** — the source URL is monitored for availability/change, but the repository does not have a safe parser for automatic ingestion yet.
- **SNAPSHOT_OR_HEALTHCHECK_ONLY** — the source is represented by a retained point-in-time snapshot and monitored, but has no current executable refresh adapter.
- **CATALOG_ONLY** — source is documented but has no public URL suitable for automated retrieval.

A raw-capture adapter may be marked ingested at the source-byte level without implying that its rows have been normalized or joined to a facility. A source is never labeled fully site-verified just because its URL is reachable.

## Scheduled operation

Source-specific workflows keep their own schedules; the unified control plane runs daily after those refresh windows. It also supports manual `workflow_dispatch` and push-triggered regression checks.

## Source-change detection

`track3_automation.py` fingerprints cataloged URLs using HTTP status plus ETag, Last-Modified, content length, and a bounded response sample hash. It compares the current fingerprint to the previous successful monitor result.

This is change detection, not a claim that a changed source is substantively different in every field.

## Queue-release diffing

The pipeline stores a dated current-registry snapshot and compares it with the previous retained snapshot. It reports:

- added queue records;
- removed queue records;
- changed records;
- current/previous cardinality;
- content fingerprint.

The diff is generated from the current `REGISTRY_DATA` and is separate from the historical archive.

## Duplicate detection

The quality scan checks:

- duplicate queue/request IDs;
- exact duplicate rows;
- repeated project + developer + MW signatures.

A duplicate flag is a data-quality finding. It is not a facility identity judgment.

## Geographic matching

The quality scan reports state/county coverage for queue records and checks the Epoch/crosswalk geographic join coverage. Stable IDs and curated crosswalks are preferred over geocoding guesses.

## Evidence and entity pipelines

After source adapters run, the unified workflow rebuilds:

```
build_track3_evidence.py
build_entity_resolution.py
build_facility_provenance.py
build_time_series_verification.py
build_track3_verification.py
```

Then it runs the canonical Track 3 validator and the read-only claim-level verifier.

## Automated data-quality report

The pipeline publishes:

- `data/automation/source_health.json`
- `data/automation/adapter_run_report.json`
- `data/automation/queue_release_diff.json`
- `data/automation/duplicate_report.json`
- `data/automation/geographic_match_report.json`
- `data/automation/evidence_quality_report.json`
- `data/automation/data_quality_report.json`
- `data/automation/pipeline_report.json`

These are machine-readable and are uploaded as a workflow artifact.

## Failed-source alerts

A source or adapter failure does not get converted to zero records.

The workflow opens or updates a GitHub issue titled:

`[Track 3 automated source alert] pipeline failures detected`

The issue contains the failing adapter/source and the pipeline run reference. Source or adapter failures remain explicitly recorded and issue-alerted; the publication gate blocks only integrity failures such as duplicate IDs or malformed evidence.

## Current limitation

Not every cataloged source currently has a safe executable parser. In particular, several public sources are currently snapshot/healthcheck-only because their public material does not expose a stable machine-readable feed, or the repository has not yet implemented and validated a parser.

Those gaps are explicitly surfaced in the automation matrix rather than being hidden behind a green status.

## Reproduce

```
python track3_automation.py
python run_track3_source_adapters.py
python build_track3_evidence.py
python build_entity_resolution.py
python build_facility_provenance.py
python build_time_series_verification.py
python build_track3_verification.py
python validate_track3_ledger.py
python verify_track3.py
```
