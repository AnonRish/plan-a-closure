# AI 2040 Plan A — Track 3 Research Contribution

## Purpose

This repository is an independent open-source research and data-engineering contribution intended to make public evidence relevant to AI 2040 Plan A Track 3 easier to find, audit, reproduce, and extend.

AI 2040 describes Track 3 as "Verifying the absence of secret compute." Its Plan A covert-projects supplement focuses on accounting for pre-deal AI-relevant compute, tracing sales and resales to physical end use, and locating remaining unaccounted compute with external evidence such as aerial imagery and incentive programs.

The verification-plan material also separately identifies global compute accounting/tracking as a Phase 1 priority. That recommendation is principally about how much AI-relevant compute exists globally and who owns it; it does not itself establish a site-location or electricity-telemetry requirement.

This repository is not an AI Futures Project publication, does not speak for AI 2040, and does not certify compliance with any treaty or verification regime.

## Primary AI 2040 references

- Track 3: https://ai-2040.com/supplements/verification-plan/get-involved
- Plan A — Covert AI Projects: https://ai-2040.com/print/covert-ai-projects
- Plan A scenario: https://ai-2040.com/print/scenario?book=1&plan=A

## What this repository contributes today

### Public infrastructure evidence

The repository maintains a nine-market North American large-load registry and a separate Epoch AI frontier-data-center evidence layer. It preserves site identity, construction history, grid/connection evidence, service/contract evidence, power observations, cooling observations, remote-sensing records, transformer-event research, and research backlogs.

The central rule is that queue/interconnection capacity, utility service capacity, Epoch IT power, projected IT power, contracted demand, chip TDP, and measured site load are different quantities. The pipeline does not silently substitute one for another.

### Ambiguous-load closure pilot

The highest-leverage validation unit is now a small set of cases from the registry's Genuinely Ambiguous / Unclassified Large Load tier.

The current pilot contains four cases, deliberately selected for methodological coverage rather than representativeness:

- AMB-NYISO-1745 — data-center identity outcome;
- AMB-NYISO-1765 — manufacturing/industrial outcome with a bounded applicant mismatch;
- AMB-IESO-2026-903 — deliberately inconclusive after the physical-targeting gate failed.
- AMB-AESO-P3108 — proposed data-centre identity and physical-site outcome with processed multi-modal observations.

Each case is taken through the same closure gates: queue record, entity resolution, location, public evidence, physical observation, electrical/transformer search, adjudication, and a documented stopping rule.

This is a demonstration that the workflow can produce a reproducible disposition without forcing ambiguous evidence into a positive label. The pilot does not establish complete discovery of covert compute.

### Epoch cross-check

Epoch AI's frontier-data-center dataset is retained as an independent public reference and cross-check. It is not treated as the discovery universe for the ambiguous-case pilot because those facilities are already publicly identified by Epoch.

The repository therefore separates:

known public AI sites -> independent cross-check

from:

ambiguous large load -> external discovery -> entity resolution -> physical/electrical evidence -> disposition

## Direct mapping to the AI 2040 Plan A Track 3 work

The machine-readable mapping is:

data/track3/ai2040_plan_a_mapping.json

It distinguishes:

- INGESTED_SNAPSHOT — a source snapshot is actually preserved.
- PARTIAL — part of the requirement is represented, but the complete verification chain is not.
- DESIGN_ONLY — the data model or research pathway is documented, but no completed public result is claimed.

The project should be described as adjacent to and potentially useful for Track 3 verification work, not as an implementation formally designated by AI 2040.

The repository's most direct operational contribution is public-evidence accounting and site-level observability around large computational loads. The broader Track 3 problem also requires capabilities outside this registry, including complete semiconductor production accounting, transaction-level sales and resales, recursive ownership tracing, physical inspection, serial-number continuity, verified decommissioning/recycling, randomized sampling of smaller owners, and a measured untraced pool.

## What a useful contribution looks like

A contribution should add one or more specific evidence objects, not just a narrative claim. The preferred unit is:

entity/site/batch -> source -> raw observation -> normalized value -> provenance -> review state

For a new record, preserve the original publisher value exactly when possible, then store the normalized value separately. Include the observed date, capture date, official source URL, and enough context for another researcher to reproduce the finding.

Do not turn:

- a state-level queue jurisdiction into a site-specific queue ID;
- an annual electricity total into interval telemetry;
- an estimated chip quantity into a physical inspection;
- a company identity inference into a verified ownership relationship;
- a missing public record into a conclusion that the underlying asset does not exist.

## Research priority

The project now prioritizes closure before coverage expansion.

For ambiguous-load research, the immediate target is:

unresolved -> external discovery -> candidate site -> entity resolution -> physical/electrical evidence -> adjudication

A case is considered closed only when every declared gate has a terminal state. Closure can therefore end in a confirmed data-center finding, a confirmed non-data-center finding, or an honest inconclusive result.

The wider compute-accounting bridge remains:

production -> sale -> transfer/resale -> current owner -> physical location -> inspection

The registry is one evidence layer in that larger chain, not the chain itself.

## Citation

For a compact machine-readable citation, use CITATION.cff.

When describing the work, a neutral formulation is:

> AnonRish, Continental Large-Load Interconnection & Telemetry Registry: AI 2040 Plan A Track 3 research contribution, 2026, https://github.com/AnonRish/continental-load-registry

Please cite the specific upstream publisher or dataset alongside this repository when a claim depends on it.
