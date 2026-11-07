# Public source coverage audit

Audit date: 2026-09-26

This is a coverage audit, not a claim that the public web can ever be proven exhaustively searched. It records official public source families that materially expand what can be known about the facilities in the registry.

## ERCOT

Current registry source:
- GIS Report: https://www.ercot.com/mp/data-products/data-product-details?id=pg7-200-er
- Resource / data products: https://www.ercot.com/gridinfo/resource

Additional public large-load source family identified:
- Large Load Integration: https://www.ercot.com/services/rq/large-load-integration
- Batch Zero / PGRR145 / verification materials, including RFI guides, attestations, exhibit lists and process documentation, are published from that page.
- ERCOT Market Notice M-A090926-01 (September 9, 2026) documents issuance of Batch Zero verification RFIs to a majority of Interconnecting Large Load Entities conditionally included in Batch Zero.

Coverage implication:
The current ERCOT registry layer is not a complete large-load application register. The dedicated Large Load Integration / Batch Zero material should be treated as a separate source layer and, where a public project identifier can be matched, linked to the corresponding facility research record.

## PJM

Current registry source:
- Service Requests / Interconnection Queue Status: https://www.pjm.com/planning/service-requests

Additional public source families identified:
- PJM Planning / RTEP: https://www.pjm.com/planning
- Public project-level study reports, including System Impact Study and related reports, are linked from PJM planning materials.
- PJM Load Forecast Development Process and 2026 Long-Term Load Forecast materials: https://www.pjm.com/planning/resource-adequacy-planning-load-forecast
- PJM publishes data-center / load-forecast analytical materials in its planning work.

Coverage implication:
Queue status alone does not capture all public PJM evidence. Project study reports and load-forecast materials can add transmission constraints, modeled MW, facilities, timing, and other context.

## SPP

Current registry source:
- GI Active Requests: https://opsportal.spp.org/Studies/GIActive

Additional public source families identified:
- Generator Interconnection Study Listing: https://opsportal.spp.org/Studies/GenList
- The public active listing exposes fields including nearest town/county, state, transmission owner, proposed and commercial dates, capacity, service type, requested injection/deliverability, generation/fuel type, substation/line, status, associated studies, facility report and executed GIA columns.
- Public study listings contain downloadable interconnection study reports, including ERAS-related facility studies and other 100 MW+ studies.

Coverage implication:
The registry can retain substantially more study-level provenance than a single queue row, especially links/identifiers for associated studies and facility reports.

## CAISO

Current registry source:
- Cluster 15 request workbook: https://www.caiso.com/documents/cluster-15-interconnection-requests.xlsx

Additional public source families identified:
- Generator Interconnection: https://www.caiso.com/generation-interconnection
- Interconnection facility information / queue reports: https://www.caiso.com/generation-interconnection/interconnection-facility-information
- Cluster 15 queue report and associated documents.
- Point-of-interconnection heatmap / POI information published with the Cluster 15 materials.

Coverage implication:
The current registry correctly labels CAISO as Cluster 15 only, but facility/study detail beyond the workbook should be linked separately. Earlier clusters and serial projects are outside the current CAISO table.

## MISO

Current registry source:
- Generator Interconnection Queue API: https://www.misoenergy.org/api/giqueue/getprojects
- GI Queue program page: https://www.misoenergy.org/planning/generator-interconnection/GI_Queue/

Additional public source family identified:
- Generator Interconnection Queue Improvements / ERAS materials: https://www.misoenergy.org/generator-interconnection/
- MISO publishes public queue-reform and ERAS materials, including study and process information that is not equivalent to the basic queue JSON.

Coverage implication:
The current MISO API remains a core source, but the newest requests can omit location/technology. Those missing fields must stay missing unless an independent public source supplies them.

## ISO New England

Current registry source:
- IRTT external public queue: https://irtt.iso-ne.com/reports/external

Additional public source family identified:
- Interconnection Request Studies: https://www.iso-ne.com/participate/support/customer-learning/interconnection-request-studies
- Public reports can contain study-stage, transmission, facility and system-impact information beyond the queue row.

Coverage implication:
The public IRTT table does not expose every underlying study document in a single row. A facility research layer should preserve the study/report relationships where public.

## NYISO

Current registry source:
- Interconnection workbook: https://www.nyiso.com/documents/20142/1407078/NYISO-Interconnection-Queue.xlsx
- Interconnections: https://www.nyiso.com/interconnections

Additional public source families identified:
- NYISO's Load Projects portion of the queue is materially different from generation-only queues.
- NYISO publishes system load forecast material that provides contextual, not facility-specific, evidence.

Coverage implication:
The existing use of the Load Projects sheet is important and should be preserved. Queue rows should be distinguished from broader NYISO load-forecast evidence.

## IESO

Current registry source:
- Application Status: https://ieso.ca/Sector-Participants/Connection-Process/Application-Status

Additional public source family identified:
- The public application-status list covers connection proposals including load, generation, transmission and ancillary services.
- IESO states that some final System Impact Assessment reports and addenda that are no longer posted publicly can be requested by project ID.

Coverage implication:
The public status page is useful but not equivalent to a complete document archive. The registry should record when a report is public, requestable, or not posted.

## AESO

Current registry source:
- Connection Project List: https://www.aeso.ca/assets/Uploads/project-reporting/September-2026-Project-List.xlsx
- Connection project reporting: https://www.aeso.ca/grid/transmission-projects/connection-project-reporting/

Additional public source families identified:
- Large Load Projects: https://www.aeso.ca/grid/large-load-projects/
- AESO publishes a large-load/data-centre project map and connection-project reporting material.
- Individual project pages and transmission connection solution documents may expose additional project-specific information.
- AESO publishes GIS/KML/project-reporting material alongside the monthly list.

Coverage implication:
The September 2026 connection list is only one layer. Large-load pages, maps and project-level pages should be cross-linked where a project can be matched.

## Non-ISO/RTO public-record layer

The nine organized-market feeds do not cover the whole public evidence universe. Facility research can also require jurisdiction-specific records such as:

- municipal zoning by-law amendments, site-plan approvals, development permits and council minutes;
- environmental assessment, air/water/noise and conservation-agency records;
- provincial/state utility-regulator or public-service-commission filings;
- transmission/distribution utility planning and rate-case documents;
- land-development, planning and property records;
- corporate registries and public procurement records;
- public company SEC/SEDAR+ disclosures when a relevant developer is publicly reporting;
- local electricity-service requests, transformer/substation upgrades and transmission-owner planning documents.

These sources must be treated as independent evidence. A search lead or name match is not itself a verification.

## What the current registry can honestly claim

The current project is best described as:

"An open-source registry of large (>=100 MW) public interconnection/connection requests across nine selected organized markets, with normalized records, retained source fields where available, capture metadata, provenance and a research layer for unresolved facilities."

It should not be described as a complete census of every public large-load project or every public document concerning those projects.
