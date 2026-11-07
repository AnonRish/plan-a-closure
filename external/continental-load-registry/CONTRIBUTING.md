# Contributing Track 3 Evidence

This repository is an evidence registry, not a place to store unsupported conclusions. A good contribution makes a claim more auditable than it was before.

## Submission rule

Every new evidence item should answer:

1. **What entity or site is this about?**
2. **What exactly was observed or published?**
3. **When was it observed/published and when was it captured?**
4. **Who published it and what is the official source?**
5. **What was the raw value?**
6. **What normalized value did the registry derive, if any?**
7. **What evidence domain does it belong to?**
8. **What is the claim scope?**
9. **How independently was it corroborated?**
10. **What remains unknown?**

## Evidence object

Use the Track 3 schema in:

`data/track3_evidence_schema.json`

At minimum, provide:

- `evidence_id`
- `target_type`
- `target_id`
- `target_name`
- `domain`
- `evidence_type`
- `claim_scope`
- `status`
- `source_kind`
- `source_name`
- `source_url`
- `observed_on`
- `captured_on`
- `confidence`
- `basis`

Add raw/normalized values and units whenever a numerical observation exists.

## Source hierarchy

Prefer, in order where practical:

1. Primary government, regulator, utility, ISO/RTO, court, company filing, permit, contract, or inspection record.
2. Direct publisher dataset with reproducible retrieval.
3. Independent secondary source that identifies its underlying evidence.
4. Commercial research source, clearly attributed as such.

Do not silently convert secondary evidence into primary evidence.

## Dates and snapshots

Record both the date the observation applies to and the date the source was captured. When a downloaded source is preserved, record its SHA-256 hash in the applicable manifest.

A source update can supersede an older observation. Do not overwrite historical evidence merely to make the current dashboard cleaner.

## Missingness

Use explicit states such as `UNKNOWN`, `PENDING_RESEARCH`, `SOURCE_AVAILABLE_NOT_INGESTED`, and `NOT_INGESTED`.

A missing public record is not evidence that a site, chip stockpile, connection, shipment, owner, or load does not exist.

## Measurement separation

Keep these distinct:

- queue/interconnection capacity;
- utility service capacity;
- transmission capacity;
- generation capacity;
- contracted demand;
- Epoch IT power;
- projected IT power;
- chip TDP;
- measured site load.

Never add unlike quantities simply because they are all expressed in MW.

## Entity resolution

Record the basis for a site/entity match. Preserve unresolved and ambiguous cases. Do not publish unsupported accusations or speculative motive claims.

## Physical evidence

For cooling, transformer, remote-sensing, or telemetry contributions, include enough metadata for another researcher to understand what was measured:

- sensor/equipment or measurement method;
- scene, record, or document identifier;
- latitude/longitude when legally publishable;
- baseline and observed values where applicable;
- units;
- measurement interval;
- quality flag;
- source URL;
- observation date.

## AI 2040 Plan A alignment

For Track 3 contributions, use the mapping in:

`data/track3/ai2040_plan_a_mapping.json`

Especially valuable contributions are those that connect compute accounting across multiple stages:

`production -> sale -> transfer/resale -> owner -> physical location -> inspection`

and evidence for unresolved compute:

`unrecorded sale -> candidate -> physical observation -> inspection/accounting resolution`

## Pull requests

Use the repository PR template at .github/PULL_REQUEST_TEMPLATE.md. Keep PRs focused. Include the source links and explain exactly which fields changed and why. For regenerated artifacts, include the generating command and source capture date.

A contribution that changes an evidence state should identify the underlying evidence record that caused the transition.

## Issues

Use an issue for a missing source, schema problem, reproducibility problem, or specific research lead. Include the site/entity name, source URL, relevant dates, and the proposed evidence domain.

## Quality gate

Before opening a PR, run the relevant self-tests and validation commands documented in the README. A failing generated-artifact check should be fixed rather than worked around.

The goal is a registry that another researcher can challenge, reproduce, correct, and extend.
