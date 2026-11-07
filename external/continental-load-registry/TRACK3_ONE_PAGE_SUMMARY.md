# Track 3 — One-Page Technical Summary

## What this project is

The Continental Large-Load Interconnection & Telemetry Registry is an open-source public-evidence system for tracking large electricity-load/interconnection signals and connecting them to a broader AI-data-center evidence graph.

Its North American registry currently covers nine organized markets. A separate Epoch AI layer supplies a 93-site frontier-AI reference universe and provides a physically grounded comparison population rather than being silently merged into the queue totals.

## What has actually been built

The repository has a reproducible grid-ingestion pipeline with source hashes and filter funnels; conservative entity resolution; facility research records; a 93-site Epoch crosswalk; public site-level utility/service evidence; a structured Track 3 evidence ledger; terminal site/domain accounting; separate research and observation queues; and public API/bulk-download surfaces.

The physical layer is no longer just a design checklist. As of 2026-09-28 it retains 631 derived remote-sensing observations across 92 of the 93 Epoch sites, based on public Sentinel-2, Sentinel-1, and Landsat Collection 2 STAC scenes. The current physical-target layer has defensible site coordinates for 92 of 93 sites; one site remains unresolved and is not fabricated into a target. The unresolved site is OpenAI Stargate UAE: September 11, 2026 Reuters reporting adds an area-level lead near Al Dhafra Air Base, but it does not establish a canonical parcel or facility coordinate, so no site-specific observation is claimed there.

The physical observations are intentionally compact: scene/item IDs, dates, source URLs, processing version, and derived metrics are retained rather than full raster archives.

## What the evidence means

A queue/interconnection record is primarily an electrical/planning signal. Satellite imagery, thermal observations, SAR, permits, and building footprints are physical-realization signals. They answer different questions and can disagree.

The useful research problem is therefore the disagreement set:

queue + physical → public electrical and physical evidence both present
queue without physical → planning/intention signal without corresponding retained physical observation
physical without queue → physical realization without a matching public new-connection record
neither → no signal in these public layers

The last category is not proof of absence.

## Phase 1 versus Track 3

The nine-market registry is an independent public-evidence accounting/observability layer for large loads. It may contribute evidence to broader compute-accounting and undeclared-compute research, but it is not a formal AI 2040 Phase 1 implementation.

The broader Track 3 / international verification problem requires additional accounting of compute production, sales/resales, ownership transfers, physical inspection, and independent verification mechanisms. This repository contributes evidence and discovery infrastructure to that problem; it does not constitute a bilateral U.S.–China verification regime.

## Honest current state

There are currently 93 sites in the reference universe, but not 93 facility-wide verifications. Site-level evidence coverage is broader than site-specific queue matching, and the repository intentionally keeps those concepts separate. Facility-wide state remains INCONCLUSIVE unless the defined end-to-end evidence gates are satisfied.

## How another researcher can contribute

Grid / power systems: extend the geographic source universe, reconcile utility/service records, or address the 83 unlocated MISO requests.

Remote sensing / geospatial: process the remaining sites, improve scene selection, validate thermal/SAR/optical metrics, or strengthen building/change linkage.

Data engineering / provenance: improve hashing, manifests, schema validation, generated-artifact checks, and refresh reproducibility.

Research / policy: close one site-specific evidence task, test the Phase 1/Track 3 boundary, or compare independent sources without collapsing uncertainty.

Verification / security: audit claim gates, design adversarial tests, and connect public physical/accounting evidence to independently testable verification mechanisms.

Start from the Research Operations Console, the Track 3 completion gate, and the external-capability handoff. The software/data contract is complete where public evidence permits; the remaining empirical requirements require authorized or non-public capabilities.

## Current engineering closure

The repository now publishes a machine-readable external-capability handoff, an interval-power-telemetry intake protocol, and a physical-target-lead ledger for the one unresolved Epoch reference site. These artifacts turn the remaining gaps into explicit, testable handoff contracts instead of leaving them as prose-only TODOs.

## Important limits

This system uses public evidence. A genuinely covert project may avoid new publicly visible interconnection, service, permit, or other observable signals. Public-source absence therefore remains an explicit unknown, not an absence finding.

The work is independently authored and should not be represented as an AI Futures Project publication, certification, or endorsement.