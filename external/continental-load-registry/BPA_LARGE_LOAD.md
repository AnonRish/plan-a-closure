# BPA Large-Load Layer

## Current official snapshot

The repository now ingests the BPA **Line/Load Interconnection** workbook directly from the official BPA source family.

- Official source page: https://www.bpa.gov/energy-and-services/transmission/interconnection
- Official workbook: https://www.bpa.gov/-/media/Aep/transmission-media-documents/InterconnectionQueueOutput.xlsx
- Capture date: **2026-09-28**
- Raw L-series source population: **457 rows**
- Normalized large-load layer: **128 rows at >=100 MW**
- Non-terminal / live-by-published-status rows in the normalized layer: **81**
- Normalized rows with retained display geometry carried forward by request ID: **25**
- Normalized rows without retained display geometry: **103**
- Workbook SHA-256: `c98e1dad406d5615a28defffb7cbf5130b17abfe1818223fd2efeb647bbcd208`
- Downloaded workbook size: **228,486 bytes**

The official workbook contains older/smaller L-series records as well as the >=100 MW load requests. The dedicated Track 3 large-load layer is therefore threshold-filtered: rows below 100 MW are retained only in the raw source-population accounting, not in the normalized large-load record set.

The machine-readable current layer is a **128-row >=100 MW normalized subset** of that raw source population:

- `data/bpa_large_load_registry.json`
- `data/bpa_large_load_registry.csv`

The current thresholded layer is also indexed in:

- `data/market_universe_manifest.json`
- `data/map_layer_manifest.json`
- `data/public_data_catalog.json`
- `data/data_universe_checklist.json`

## What the rows mean

The BPA workbook is a **Line/Load interconnection request population**, not a facility registry and not a measured-demand dataset.

The normalized records preserve the request identifier, project name, requester where published, county/state, published status, point-of-interconnection text, requested/service MW field selected from the workbook, request date when recoverable, and row-level source provenance.

The requested MW value is retained **as filed**. It is not reinterpreted as:

- energized capacity;
- contracted demand;
- actual electricity consumption;
- measured IT load;
- GPU/chip load;
- or proof that a project is an AI or data-center facility.

The official workbook does not provide a reliable end-use classification that can be used to turn every load request into an AI/data-center row. The dedicated BPA layer therefore remains broader than the project's AI-specific project extraction.

## Geometry policy

The map layer never geocodes or invents a location from a project name, POI, county or other text.

For a refreshed workbook, geometry is carried forward only when the same BPA request ID already has a retained display point in the repository. New rows receive no coordinate unless independently supported by existing repository evidence.

Consequently, the official 2026-09-28 snapshot contains 25 mapped display points and 432 explicitly unmapped rows.

A mapped point is display geography, not a claim that the project occupies that exact point.

## Relationship to the core registry

This layer is **non-additive** to the nine-market core registry.

The 457 raw L-series BPA rows are not added to the 1,540-row core total or the 1,623-record expanded-known scope. The separate project-level extraction retains its own 60 curated BPA evidence records because that layer is an entity-resolution/public-project evidence dataset, not a complete transcription of the BPA Line/Load workbook.

Keeping these two layers separate prevents a single BPA request from being counted simultaneously as:

1. a core queue row,
2. a project-evidence record,
3. and a separate auxiliary source row

without explicit population accounting.

## Reproduction and refresh

The refresh implementation is `ingest_bpa_large_loads.py`.

The automated workflow is:

`.github/workflows/refresh_bpa_large_loads.yml`

It:

1. downloads the current official BPA workbook;
2. parses L-series load requests;
3. preserves prior geometry only by request-ID match;
4. fingerprints the downloaded workbook with SHA-256;
5. updates the BPA JSON/CSV layer and its manifests;
6. runs the canonical cross-artifact consistency validator;
7. commits only a changed normalized snapshot.

The binary workbook is **not committed** to the repository. Its SHA-256 and byte size are retained so the exact source used for a published refresh can be identified without storing the external binary in Git history.

## Secondary corroboration

The repository also retains these secondary BPA sources for cross-checking and historical context:

- https://substationscout.com/large-load-registry/
- https://www.wattstreet.net/load-ledger/

Secondary sources are not allowed to silently override the official workbook. They remain useful for corroborating identifiers, request interpretation and historical versions when the authoritative source changes.

## Track 3 relevance and limits

The BPA layer improves the observable public evidence surface for large-load connection demand, but it does **not** close Track 3 by itself.

It can establish that public load-request rows exist and provide source-backed request/status/POI information. It cannot establish:

- that every AI/data-center facility is represented in BPA's load queue;
- that every BPA request is an AI/data-center request;
- that a requested MW value became energized demand;
- that all observed compute is accounted for;
- or that secret/unreported compute is absent.

Those remain separate evidence gates in the Track 3 architecture.
