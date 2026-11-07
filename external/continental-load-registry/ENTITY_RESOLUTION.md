# Track 3 Entity Resolution Layer

Generated from the current repository queue, Epoch site registry, project-level evidence, site-evidence records, and published building-footprint index.

## Current state

- 2039 canonicalized entity records.
- 735 distinct developer strings in 1558 core queue rows.
- 997 distinct core project-name strings.
- 1728 relationship edges.
- 31 explicit SEC Exhibit 21 parent/subsidiary edges.
- 51 sites mapped to 88505 building polygons.

Confidence is evidence strength, not a probability. Name normalization is a reconciliation key, not proof of legal identity. LLC/LP status is not evidence that an entity is a shell company.

GLEIF publishes Level 2 data connecting legal entities to direct and ultimate accounting parents; OpenCorporates exposes company relationship statements with provenance; SEC EDGAR Exhibit 21 is an issuer-reported subsidiary source. citeturn387553search9turn387553search0turn390760search1

## Outputs

- `data/track3/entity_resolution.json`
- `data/track3/entity_resolution_entities.csv`
- `data/track3/entity_resolution_relationships.csv`
- `data/track3/entity_resolution_research_queue.csv`
