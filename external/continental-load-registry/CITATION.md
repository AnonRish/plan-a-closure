# Citation Guide

## Repository citation

AnonRish. *Continental Large-Load Interconnection & Telemetry Registry: AI 2040 Plan A Track 3 research contribution*. 2026. https://github.com/AnonRish/continental-load-registry

## Suggested BibTeX

    @software{anonrish_continental_load_registry_2026,
      author  = {AnonRish},
      title   = {Continental Large-Load Interconnection \& Telemetry Registry: AI 2040 Plan A Track 3 research contribution},
      year    = {2026},
      url     = {https://github.com/AnonRish/continental-load-registry}
    }

## Artifact-specific citation

When citing a particular result, prefer the narrowest artifact:

- Main registry: index.html
- Track 3 evidence surface: track3.html
- Plan A research bridge: plan-a.html
- AI 2040 mapping: data/track3/ai2040_plan_a_mapping.json
- Recommendation / Appendix B traceability: data/track3/ai2040_plan_a_traceability.json
- Plan A audit-chain schema: data/track3/plan_a_audit_schema.json
- External source manifest: data/track3/external_source_snapshots.json
- Complete commit audit: data/ci/commit_audit.json

## Upstream sources

This repository is an independent implementation. When a claim depends on an upstream publisher, cite that source alongside this repository. In particular, AI 2040 Plan A / Track 3 claims should cite the relevant AI 2040 page directly.

## Reproducibility

Use the repository commit SHA, artifact path, and source capture date when a reproducible citation is important. Do not treat a moving main branch as an immutable research snapshot.

## Persistent archival

A future release should be tagged and archived with a service such as Zenodo so a versioned DOI can be cited alongside the GitHub repository. No DOI is claimed by this repository unless and until one is actually issued.


## Large-load / Track 3 artifact citations

For the expanded large-load universe, cite the narrowest artifact used:
- `data/large_load_scope.json` — core versus expanded-known accounting.
- `data/market_universe_manifest.json` — market-by-market coverage and public-disclosure limits.
- `data/project_level_extractions.json` — individually identifiable utility, permit, connection and queue-related project records.
- `data/project_level_map.json` — mapped project geometry.
- `data/epoch_connection_research_targets.json` — all 93 Epoch-site connection research targets.
- `data/epoch_site_evidence_records.json` — discrete site-level evidence assertions.
- `data/supplemental_large_load_evidence.json` — non-additive utility/regulator/planning evidence units.
- `data/supplemental_aggregate_map.json` — mapped aggregate and historical footprints.
- `data/caiso_cluster_history.json` — historical CAISO cluster-population series.

These artifacts do not make an upstream utility or regulator's unpublished information public. Cite the upstream publisher for facts derived from that source.
