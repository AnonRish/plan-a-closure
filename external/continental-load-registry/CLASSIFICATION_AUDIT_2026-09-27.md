# Large-load candidate classification audit

Updated: 2026-09-27

## Why this audit exists

The 141-row Genuinely Ambiguous / Unclassified Large Load set is a broad research pool, not 141 confirmed large-load discovery targets. Before a case is promoted into the closed-case pilot, its source record must independently establish that the underlying project is a load request rather than generation, surplus, transmission, replacement, upgrade, or another project type.

## Concrete false-positive found

MISO J1490 appears in the broad registry ambiguity universe as a 1,000 MW unnamed project in Randolph County, Missouri. The current public MISO-derived project record identifies J1490 as a Generation project associated with the McCredie–Montgomery 345 kV Line Tap. It therefore fails the strict load-admission gate and must not be treated as a large-load discovery candidate merely because it entered an earlier unclassified pool.

The same issue is visible for other MISO records that were carried in the unresolved-location worklist: the worklist reason is about missing site-identity fields and does not establish project type. Some records are classified by current public data as Surplus rather than Load.

## Corrected admission rule

A strict discovery candidate must satisfy all of the following before physical or end-use research is treated as a load-discovery case:

1. A retained source explicitly identifies the project as **Load**, **new load facility**, **increase load**, or an equivalent load-specific type.
2. The request is not a generation, surplus, transmission, replacement, upgrade, storage, or hybrid project unless the source explicitly identifies the load component being investigated.
3. The candidate is not merely an RTO/ISO/utility-jurisdiction match; the project record itself must be the starting object.
4. Any developer/entity ambiguity remains explicit rather than being inferred from project naming.
5. A physical target must be established independently before satellite-derived observations are interpreted as site evidence.

## Current strict pilot candidates

The current set contains five strict admitted-load cases: three primary ambiguity targets plus two explicit industrial controls.

- **AESO P3066 — Leedale Data Load, 1,864 MW.** Public queue-derived evidence identifies a load request while the developer is not published. The physical parcel is not retained. This is a primary identity/location closure target.
- **AESO P3198 — Lynx Data Load, 1,800 MW.** Public queue-derived evidence identifies a load request while the developer is not published. The physical parcel is not retained. This is a primary identity/location closure target.
- **AESO P3108 — Wild Rose Power Hub Load, 1,300 MW.** The retained AESO source labels the project `Data Load`, the developer is not published, and the title does not itself name a data-center operator. This is the primary generic-name ambiguity target.
- **AESO P2958 — Hydrogen Canada MPC Load, 320 MW.** The retained AESO source labels this `Industrial Load` and the developer is not published. It is a non-data-center control to test correct reclassification rather than compute over-interpretation.
- **AESO P2614 — Dow Fort Sask. Load, 231 MW.** The retained AESO source labels this `Industrial Load` and the developer is not published. It is a second non-data-center control for entity and physical resolution.

These five are not presented as a representative sample or as a ranking of hiddenness. The primary targets test discovery/identity resolution; the controls test whether the workflow can correctly terminate on non-data-center large loads.
## Rule for the website

The UI should call the 141 records a **broad ambiguous research pool**. The strict candidate page should use **admitted load candidates**. A broad-pool row never becomes a discovery finding merely because it lacks an identified developer.

## Sources used for this audit

- MISO/queue-derived project classification surfaces in the registry's retained data.
- NYSRC large-load queue reports.
- Interconnection.fyi project records.
- GridLens AESO connection project reporting.

Where a secondary source is used, it remains secondary evidence and should not overwrite the underlying queue-origin field.
