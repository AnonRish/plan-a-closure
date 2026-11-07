# Track 3 Research Workflows

This is the operational research layer for effective unresolved publisher fields and open Track 3 domain cells in the 93-site canonical universe.

## Priority order: close before widening

The registry now treats a small number of end-to-end ambiguous cases as the primary validation unit. Broad coverage remains useful, but new coverage should not outrun the ability to close representative cases.

The pilot population is the Genuinely Ambiguous / Unclassified Large Load tier. Epoch sites are retained as an independent reference/cross-check rather than as the primary pilot universe.

## Candidate admission gate

Do not begin a load-discovery case merely because a record is large, unnamed, or missing a developer. First retain source evidence that the project type is Load, New load facility, Increase load, or an equivalent load-side category. Generation, Surplus, Transmission, Replacement, and Upgrade records remain outside the strict discovery candidate set unless their specific load component is separately established.

The 141-row Genuinely Ambiguous / Unclassified Large Load universe is therefore a **broad research pool**, not a count of 141 confirmed discoveries.

## Closed-case workflow

1. Select one candidate from the declared ambiguous-case population using the published selection rule.
2. Capture the most specific public queue/load record and preserve the source URL, identifier, project name and capacity.
3. Resolve the applicant/developer to an entity or record the mismatch explicitly.
4. Establish a defensible physical target and coordinate precision.
5. Collect project-specific public evidence and state exactly what each source proves.
6. Run the declared physical-observation workflow when the location gate closes. Retain acquisition identifiers, processing outputs and quality limitations.
7. Search the electrical/transformer evidence universe for a site-specific event. A missing public transformer record is a search outcome, not proof that no transformer exists.
8. Adjudicate the case into one terminal disposition: CONFIRMED_DATA_CENTER, CONFIRMED_OTHER_LARGE_LOAD, CONFIRMED_MANUFACTURING_OR_INDUSTRIAL, INCONCLUSIVE_AFTER_SEARCH, or RULED_OUT_DUPLICATE_WITHDRAWN_OR_DATA_ERROR.
9. Record every unresolved boundary and close the case only when each declared gate has a terminal state.

The current machine-readable pilot is data/track3/ambiguous_case_studies.json, with physical artifacts in data/track3/ambiguous_case_physical_observations.json and the selection rule in data/track3/ambiguous_case_selection.json.

## One-task workflow

1. Select one task ID from the Research Operations Console or the CSV queue.
2. Run the generated site-specific search links and named source sequence.
3. Capture the exact document, filing, permit, scene, or record; its URL; locator; dates; site linkage; and supported value/observation.
4. Reject company-wide, regional, nearby, generic, inferred, or otherwise non-site-specific claims.
5. For material claims, obtain independent corroboration and record what agrees or disagrees.
6. Classify the result explicitly: FOUND, PUBLIC_LEAD_REVIEW_REQUIRED, NO_PUBLIC_RECORD, SOURCE_UNAVAILABLE, DUPLICATE_OF_EXISTING_SOURCE, or CONFLICT_NEEDS_REVIEW.
7. Submit using the research submission schema. Canonical builders remain the state gate.

## Queue accounting

The generated queue has exactly one task per effective unresolved publisher field and exactly one task per open Track 3 domain cell. The build script asserts these counts against the canonical sweep before writing outputs.

## Sources

The playbooks prioritize official project/developer records, utility and regulator records, municipal/county records, environmental and permitting records, company disclosures, Epoch site-level records, and reputable independent reporting. Remote-sensing tasks use the public Copernicus and USGS source families already cataloged in the registry.

## Important evidence rules

- A public lead is not canonical evidence until source review and ingestion.
- Missing publication is not a publication date.
- Queue MW, utility service capacity, contracted demand, generation capacity, chip TDP, and measured load are different measurements.
- A source mirror or syndicated copy is not independent corroboration.
- A no-public-record outcome is a documented research result, not evidence that the infrastructure or relationship does not exist.
- A physical observation is evidence about the observed scene and processing metric, not automatic evidence of AI compute or operational status.

## Rebuild

Run:

python build_track3_research_backlog.py

The daily GitHub Actions workflow rebuilds the queue whenever the canonical sweep or workflow definitions change.
