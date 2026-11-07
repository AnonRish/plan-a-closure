# Track 3 Ambiguous-Load Closure Pilot

Purpose: close a small, deliberately selected subset of the registry's genuinely ambiguous large-load tier end-to-end before expanding coverage.

## Pilot cases

The pilot starts from the repository's 141-facility Genuinely Ambiguous / Unclassified Large Load dossier (>=100 MW; developer not matched to the known entity list or not disclosed). Three cases are selected to test different outcomes rather than maximize coverage:

| Case | RTO / queue | MW | Closure role |
|---|---|---:|---|
| AMB-NYISO-1765 | NYISO 1765 — Micron Fab 3 | 606 | entity-resolution stress test; manufacturing outcome |
| AMB-NYISO-1745 | NYISO 1745 — Pontoon Bridge Road Data Center | 250 | data-center identity outcome |
| AMB-IESO-2026-903 | IESO 2026-903 — Project IQ197 | 1,380 | intentionally unresolved outcome; tests location/identity stopping rule |

CPXP Sarnia Hydrogen Facility (IESO 2025-854) is retained as a next control candidate but is not counted in this first closure set because the reviewed public record did not establish a defensible facility parcel for satellite targeting.

## Closure gates

A case is closed only when every gate has a terminal, source-backed state. A gate may conclude with FOUND, NO_PUBLIC_RECORD, INCONCLUSIVE, or PHYSICAL_TARGET_UNRESOLVED; closure does not mean a positive finding.

1. Queue record: exact ID, capacity, status, project name, applicant, POI/electrical geography, and primary source.
2. Entity resolution: legal/entity identity or documented mismatch without guessing.
3. Location: exact public address/coordinates when available; otherwise explicit coarse precision. Never use a county/zone centroid as a facility coordinate.
4. Public-record search: operator, municipal, environmental/regulatory, company, planning, and infrastructure records with URL, dates, and claim scope.
5. Satellite/physical pull: public STAC acquisition against the defensible coordinate, retaining scene IDs, dates, collection, processing version, and compact metrics. An unresolved coordinate is itself a terminal negative result for this gate, not a reason to fabricate a point.
6. Transformer/electrical check: project-specific transformer/substation procurement, delivery, installation, energization, and utility work. No record is recorded as NO_PUBLIC_EVENT_FOUND, not absence.
7. Adjudication: CONFIRMED_DATA_CENTER; CONFIRMED_OTHER_LARGE_LOAD; CONFIRMED_MANUFACTURING_OR_INDUSTRIAL; INCONCLUSIVE_AFTER_SEARCH; or RULED_OUT_DUPLICATE_WITHDRAWN_OR_DATA_ERROR.
8. Boundary statement: explicitly state what remains unknown and why a stronger claim is not justified.

## Stopping rule

Close after the primary sources are checked; the municipal/regulatory/company search ladder is run; the best physical coordinate is established or its absence recorded; satellite pull succeeds or records a documented failure; transformer searches have a terminal status; and conflicting identity evidence is recorded. Do not keep searching indefinitely to manufacture a desired answer.

## Interpretation rule

A closed case demonstrates that the workflow can move an ambiguous registry row to a documented disposition. It does not establish detection completeness, covert-compute detection, or facility-wide verification beyond the evidence actually observed.
