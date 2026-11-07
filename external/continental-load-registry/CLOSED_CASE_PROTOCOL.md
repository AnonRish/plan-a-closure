# Track 3 Closed-Case Protocol

Updated: 2026-09-27

## Purpose

The registry's highest-leverage validation unit is no longer another batch of partially researched sites. It is a closed case: one unresolved large-load candidate taken through the full public-evidence workflow until every gate reaches a terminal state.

A closed case is a methodological demonstration, not a claim that every facility can be identified or that a facility is operating.

## Pilot rule

The pilot focuses on the registry's Genuinely Ambiguous / Unclassified Large Load tier rather than the 93-site Epoch reference set.

Epoch remains valuable as an independent public reference and cross-check. It is not the primary discovery universe for the pilot because those facilities are already publicly identified.

## Candidate admission gate

Before a case enters the closure workflow, independently establish that the underlying queue/application object is a **load-side request**. A missing developer name or an unclassified technology field is not sufficient. Generation, surplus, transmission, replacement, and upgrade records are not load-discovery cases unless a separate retained source establishes the specific load component under investigation.

This gate exists because an earlier broad ambiguity pool contained records whose missing site-identity fields were mistaken for evidence of unresolved large-load status. For example, current public MISO-derived records classify some such records as Generation or Surplus. Those records belong in a separate source-completeness worklist, not in the strict discovery set.

## Closure gates

1. Queue record — identify the most specific public load/interconnection record; retain the source URL, record identifier, project name and capacity; do not manufacture a site-specific match from jurisdiction alone.
2. Entity resolution — resolve the applicant/developer to a stable entity or document the unresolved mismatch; distinguish legal ownership, project sponsorship, developer identity and end use.
3. Location — obtain a defensible site locator; record coordinate precision; never substitute a county, city or utility-territory centroid for a site coordinate.
4. Public evidence — collect project-specific primary/independent records; record exactly what each source proves; a public lead is not canonical evidence until reviewed.
5. Physical observation — attempt the declared remote-sensing workflow; retain acquisition identifiers and processing outputs; a failed or degraded scene is a terminal observation state, not a reason to invent a result; physical imagery is not, by itself, proof of AI compute.
6. Electrical / transformer check — search for site-specific transformer procurement, delivery, installation, service or energization evidence; record no-public-record outcomes explicitly; infrastructure context is not the same as a project-specific transformer event.
7. Adjudication — choose exactly one terminal disposition: CONFIRMED_DATA_CENTER, CONFIRMED_OTHER_LARGE_LOAD, CONFIRMED_MANUFACTURING_OR_INDUSTRIAL, INCONCLUSIVE_AFTER_SEARCH, or RULED_OUT_DUPLICATE_WITHDRAWN_OR_DATA_ERROR.
8. Stopping rule — every gate has a terminal state; remaining uncertainty is written down as unresolved items; closure never means that every evidence layer produced a positive observation.

## Evidence semantics

The project must preserve the distinction between requested/interconnection capacity, utility service capacity, contracted demand, measured electricity use, physical observations, and compute estimates. None may be silently substituted for another.

Likewise: NO_PUBLIC_RECORD is a research result, not proof of absence; UNKNOWN is not FAIL; an unrun test is NOT_TESTED; degraded remote sensing remains degraded; and an entity mismatch stays visible until resolved.

## What makes a pilot case useful

A strong pilot contains at least one case that resolves to a data center, one that resolves to another industrial or large-load use, and one that remains genuinely inconclusive after a documented stopping rule. This prevents the demonstration from becoming a collection of only successful identifications.

## Current pilot

The repository currently retains four cases:

- AMB-NYISO-1745 — Pontoon Bridge Road Data Center — data-center identity outcome.
- AMB-NYISO-1765 — Micron Fab 3 — manufacturing/industrial outcome with a bounded applicant mismatch.
- AMB-IESO-2026-903 — Project IQ197 — deliberately inconclusive after the physical-targeting gate failed.

The machine-readable records are in data/track3/ambiguous_case_studies.json and data/track3/ambiguous_case_physical_observations.json.

## Evaluation standard

The pilot is successful when an independent reader can reproduce the reasoning from the retained evidence bundle and can see exactly where the method closed a claim, found contradictory or ambiguous evidence, failed to acquire an observation, or stopped without forcing an answer.

Coverage expansion comes after repeated closure, not before it.
