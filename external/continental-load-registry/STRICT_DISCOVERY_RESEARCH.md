# Strict Discovery Research Queue

Updated: 2026-09-28

## Purpose

This is the operational queue for the next ambiguous-load closure cases. It sits downstream of the broad 141-record ambiguity pool and upstream of final adjudication.

A candidate is admitted only when a retained public source identifies the underlying request as a load-side project. Developer non-disclosure, large MW, or proximity to a known data-center cluster are not sufficient.

## Standard case sequence

1. Reproduce the source-level load classification.
2. Resolve project, applicant, developer, owner, and end-use identities without collapsing distinct roles.
3. Establish a defensible physical parcel or site coordinate.
4. Search permits, land records, utility/regulator filings, planning records, and independent corroboration.
5. Run physical observations only after the location gate closes.
6. Search transformer, service, substation, and construction evidence.
7. Adjudicate or stop at an explicit boundary.

## P3066 — Leedale Data Load

Queue: AESO P3066 · 1,864 MW · Load · Clearwater County · POI 38-Caroline.

Current public sources identify P3066 as a load project. A separate public facility record describes it as a proposed data center, while the retained queue surface does not expose a developer/owner or defensible facility coordinate. The immediate research target is physical targeting and entity resolution.

Sources:
- https://www.interconnection.fyi/project/aeso-p3066
- https://www.datacenter.fyi/public-record/p3066-leedale-data-load-764c0be1
- https://gridlens.ca/substation/378S

Do not infer: Clearwater County or Caroline planning context is not the facility coordinate; a secondary data-center label is not developer/operator proof; 1,864 MW is not measured electricity use or IT power.

## P3198 — Lynx Data Load

Queue: AESO P3198 · 1,800 MW · Load · Strathcona County / Fort Saskatchewan planning context · POI 33-Fort Saskatchewan.

Current public sources identify P3198 as a load project, but the developer is not exposed in the retained public queue surface. GridLens provides useful planning/substation context; it does not by itself establish the project parcel.

Sources:
- https://www.interconnection.fyi/project/aeso-p3198
- https://gridlens.ca/substation/439S
- https://gridlens.ca/substation/233S

Do not infer: a planning-area association is not a parcel match; a similarly named GLDC project is not automatically P3198; 1,800 MW is not measured demand.

## P3108 — Wild Rose Power Hub Load

Queue: AESO P3108 · 1,300 MW · Load · Calgary planning area.

The retained AESO source labels P3108 as Data Load while the developer is not published in the source row and the project title does not itself identify a data-center operator. This is the primary generic-name ambiguity target.

Sources:
- https://www.aeso.ca/assets/Uploads/project-reporting/September-2026-Project-List.xlsx
- Public queue mirror / project record retained by the registry
- Municipal planning, land/property, permitting, utility and regulator records are the next source families

Do not infer: the Calgary planning area is not a facility coordinate; Data Load does not establish operator, users, hardware, or measured consumption; 1,300 MW is not measured electricity use or IT power.

## P2958 — Hydrogen Canada MPC Load (control)

Queue: AESO P2958 · 320 MW · Industrial Load · Fort Saskatchewan.

This is an explicit industrial-load control. It is included to test whether the workflow can resolve a non-data-center large load without forcing a compute interpretation.

Search sequence: AESO source → corporate/project records → municipal planning/land/permitting → utility/regulator evidence → physical target → transformer/service evidence.

Do not infer: industrial-load status does not establish compute relevance; missing developer information is not evidence of concealment.

## P2614 — Dow Fort Sask. Load (control)

Queue: AESO P2614 · 231 MW · Industrial Load · Fort Saskatchewan.

This is a second explicit industrial-load control for entity and physical resolution.

Search sequence: AESO source → Dow/project records → municipal planning/land/permitting → utility/regulator evidence → physical target → transformer/service evidence.

Do not infer: project identity from the company name alone; queue MW is not operating consumption.

## Current five-case closure result

The strict five-case queue is now terminally dispositioned in
`data/track3/strict_discovery_case_dispositions_2026-09-28.json`.

- **P3066 Leedale Data Load — closed at the public-evidence boundary:** public sources classify the project as a proposed data center/data load, but no defensible project parcel or developer/operator identity was established.
- **P3198 Lynx Data Load — closed as inconclusive:** the queue and Fort Saskatchewan planning context are established, but no project-specific parcel or developer/operator identity was established.
- **P3108 Wild Rose Power Hub — closed with public project + physical-site identity:** Rocky View County and Alberta Major Projects identify the proposed data-centre project and site; the 1,300 MW figure remains a connection request rather than measured demand.
- **P2958 Hydrogen Canada MPC Load — closed as an industrial control context:** public sources identify a Hydrogen Canada blue-hydrogen/ammonia project near Fort Saskatchewan and the queue is classified as Industrial Load, but the exact P2958-to-parcel linkage remains unresolved.
- **P2614 Dow Fort Sask. Load — closed as an industrial project:** AESO's engineering assessment directly identifies Dow Chemical Canada ULC, a 231 MW requested load, and an Industrial project type.

The closure result is **not** a claim that any of these sites are operational, that their queue MW equals electricity consumption, or that covert compute has been ruled out.

## Closure output

Every completed case should emit:

case_id → source set → raw observations → normalized fields → physical artifacts → electrical evidence search → adjudication → unresolved boundaries

A case may legitimately end as inconclusive. The stopping rule is part of the result.
