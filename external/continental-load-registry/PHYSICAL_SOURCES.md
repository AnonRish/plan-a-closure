# Track 3 physical-source provenance

This document is the human-readable companion to [`data/track3/physical_source_manifest.json`](./data/track3/physical_source_manifest.json). It applies the same provenance discipline as the grid-source layer, with one important distinction: the satellite pipelines intentionally do **not** commit full source rasters.

## Satellite imagery

| Source | Exact source / STAC entry point | Collection | Capture window | Raw bytes retained? | What is retained |
|---|---|---|---|---|---|
| Copernicus Sentinel-2 | https://dataspace.copernicus.eu/data-collections/copernicus-sentinel-missions/sentinel-2 | `sentinel-2-l2a` | 2021-01-01 through 2026-09-27 | No | Scene ID, STAC item URL, observation date, source collection, processing version, compact derived metrics |
| Copernicus Sentinel-1 | https://dataspace.copernicus.eu/data-collections/copernicus-sentinel-missions/sentinel-1 | `sentinel-1-grd` | 2021-01-01 through 2026-09-27 | No | Scene ID, STAC item URL, observation date, source collection, processing version, compact VV/VH-derived metrics |
| USGS/NASA Landsat Collection 2 | https://www.usgs.gov/landsat-missions/landsat-collection-2-level-2-science-products | `landsat-c2-l2` | 2021-01-01 through 2026-09-27 | No | Scene ID, STAC item URL, observation date, source collection, processing version, compact surface-temperature metrics |

Because the raw scenes are not retained, a raw-raster SHA-256 would be misleading. The canonical derived ledger at [`data/track3/remote_sensing_observations.json`](./data/track3/remote_sensing_observations.json) records the exact scene/item locator for each retained observation.

## Building footprints

| Source | Exact documentation / access URL | Release | Capture date | Coverage |
|---|---|---|---|---:|
| Overture Maps buildings | https://docs.overturemaps.org/guides/buildings/ | 2026-09-23.1 | 2026-09-27 | 93 site targets; 68 sites currently have retained polygon GeoJSON files |

The retained building layer is current geometry, not a construction time series. Footprint proximity/overlap does not establish AI tenancy or workload identity.

## Retained-artifact integrity

The machine-readable manifest records the Git blob SHA-1 identifier exposed by GitHub for the retained derivative/index files. These are deliberately labeled **SHA-1**, not SHA-256. The manifest leaves `sha256`/byte fields null where the audit environment did not independently materialize the full file bytes; it does not invent hashes.

Current retained artifact locators include:

- `data/track3/remote_sensing_observations.json` — 421 derived observation records.
- `data/track3/remote_sensing_observations.csv` — flattened form of the same ledger.
- `data/track3/building_footprints_index.json` — 93-site footprint acquisition/index manifest.
- `data/physical_verification_layer.json` — aggregate physical-verification state layer.

The companion validator is [`validate_physical_provenance.py`](./validate_physical_provenance.py). It is read-only and runs without network access; CI invokes it in [`.github/workflows/track3_validation.yml`](./.github/workflows/track3_validation.yml).

## Interpretation rule

A satellite observation, thermal anomaly, SAR metric, NDVI metric, building footprint, geocoded coordinate, or source-scene match is an observation layer. None of these fields alone proves AI compute, ownership, tenancy, power draw, or covert activity. Missing imagery or missing source bytes are not evidence of absence.
