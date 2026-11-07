# Frontier AI Data-Center Queue & Connection Registry Universe

Updated: 2026-09-26

## Objective

The target is to trace every Epoch AI frontier/AI data-center site to the most
specific public electricity connection record that can be established.

This is a **source-universe** document. It does not treat a jurisdiction-level
queue as proof that a particular campus is a particular queue row.

The research hierarchy is:

1. **Site-specific public queue record** — queue ID/case ID, named project,
   location/POI and capacity align with the Epoch site.
2. **Site-specific public connection/service record** — a utility service
   agreement, regulator approval, customer planning record, or equivalent
   directly ties the site to the power system.
3. **Site-specific regulatory filing record** — state PUC/PSC, FERC, or
   equivalent filing identifies the load, utility, site, or connection terms.
4. **Queue-jurisdiction record** — the responsible RTO/ISO/utility queue is
   identified for the site's location, but no site-specific public queue row
   has yet been verified.
5. **External connection-system record** — for Epoch sites outside the
   North American registry geography, the national/transmission/distribution
   connection system is identified, but a site-level public queue record is
   not yet verified.
6. **No public record located** — only after the applicable source universe has
   been searched and documented.

A site must not be marked "queue verified" merely because it lies inside the
territory of an RTO, ISO, utility, or state queue.

## National / cross-cutting sources

### Primary / authoritative

- FERC eLibrary — federal regulatory filing corpus:
  https://www.ferc.gov/ferc-online/elibrary
- FERC Large Load Interconnection docket RM26-4:
  https://ferc.gov/rm26-4
- PJM Service Requests:
  https://www.pjm.com/planning/service-requests
- ERCOT Large Load Integration:
  https://www.ercot.com/services/rq/large-load-integration
- SPP High Impact Large Load:
  https://www.spp.org/largeload/
- SPP Generator Interconnection Active Studies:
  https://opsportal.spp.org/Studies/GIActive
- MISO Generator Interconnection Queue:
  https://www.misoenergy.org/api/giqueue/getprojects
- MISO GI Queue:
  https://www.misoenergy.org/planning/generator-interconnection/GI_Queue/
- NYISO Interconnection Queue:
  https://www.nyiso.com/documents/20142/1407078/NYISO-Interconnection-Queue.xlsx
- NYISO Interconnections:
  https://www.nyiso.com/interconnections
- CAISO interconnection / GRIP materials:
  https://www.caiso.com/
- ISO New England IRTT external reports:
  https://irtt.iso-ne.com/reports/external
- IESO Application Status:
  https://ieso.ca/Sector-Participants/Connection-Process/Application-Status
- AESO Connection Project Reporting:
  https://www.aeso.ca/grid/transmission-projects/connection-project-reporting/
- BPA Interconnection:
  https://www.bpa.gov/energy-and-services/transmission/interconnection

### U.S. national secondary datasets / discovery surfaces

- GridTracker — daily U.S. queue snapshots, data-center permit records, and
  regulatory filings; its public site says it covers every U.S. interconnection
  queue and has captured queue snapshots daily since April 2024:
  https://www.gridtracker.io/
- GridTracker MCP / primary-source research surface:
  https://www.gridtracker.io/mcp
- Interconnection.fyi — U.S. interconnection queues plus a data-center
  facility tracker:
  https://www.interconnection.fyi/
- Watt Street — state-level current interconnection queue views built from
  the queues of transmission providers operating in each state:
  https://www.wattstreet.net/
- Lawrence Berkeley National Laboratory, Queued Up 2026 Edition — historical
  project-level queue dataset covering 7 ISOs/RTOs and 50 non-ISO utilities.
  **Important:** LBNL explicitly says this dataset covers generator
  interconnection, not load interconnection, so it is a supporting historical
  source rather than a direct large-load queue:
  https://emp.lbl.gov/queues
- GridVision AI — secondary explorer of the LBNL Queued Up dataset:
  https://gridvisionai.com/interconnection-queue/explorer

### U.S. facility / permit / evidence registries

- DataCenter.fyi — facility, permit and grid-operator records:
  https://www.datacenter.fyi/
- DEPLOY — sourced data-center facility records:
  https://registry.deploy.report/datacenters
- SueDataCenters / Compute Atlas-derived public facility records:
  https://suedatacenters.org/data-centers
- DataCentersExposed:
  https://datacentersexposed.com/facilities
- Epoch AI — independent frontier AI data-center reference set:
  https://epoch.ai/data/ai-data-centers

These are evidence/discovery registries, not substitutes for a utility's
official queue or regulatory filing.

## State / utility queue families required by the current 77 U.S. Epoch sites

### ERCOT / Texas

Relevant source families:
- ERCOT Large Load Integration / Batch Zero
- ERCOT queue / GIS reports
- ERCOT large-load studies
- Public Utility Commission of Texas interchange / docket corpus
- County permits, tax abatements and local service records
- GridTracker's daily queue and PUCT corpus

Example site-specific evidence already found:
- Goodnight: ERCOT queue records plus PUCT Docket 58881/59220.
- Helios: ERCOT Large Load Interconnection Study completion and additional
  approved capacity reported by Galaxy.

### MISO states

Indiana, Iowa, Louisiana, Michigan, Minnesota, Mississippi, North Dakota and
Wisconsin sites should be searched across:
- MISO GI queue and large-load materials
- State utility commission dockets
- Utility large-load tariffs/service agreements
- GridTracker daily MISO queue history
- Local utility planning/connection records
- Local permits and economic-development filings

Examples:
- MISO publicly published a new-load announcement table identifying Google
  Cedar Rapids (600 MW), Microsoft Mount Pleasant (1,480 MW), Microsoft Project
  Osmium (150 MW), Microsoft Ginger East (444 MW), and a 616 MW Cedar Rapids
  shell request. These are high-value load-evidence leads and should be
  cross-reconciled with the Epoch campuses rather than treated as automatic
  identity matches.

### PJM states

Ohio, Pennsylvania, New Jersey and Virginia:
- PJM Service Requests / planning records
- AEP Ohio / Ohio Power and other distribution utility records
- Pennsylvania utility/regulatory filings
- New Jersey utility/regulatory filings
- Dominion / Virginia SCC and other Virginia utility filings
- FERC eLibrary where the transmission-level transaction is federally filed
- GridTracker daily queue history and regulatory filings

### SPP states

Nebraska, Oklahoma and Missouri:
- SPP GI Active Studies
- SPP High Impact Large Load process
- OPPD / LES / Nebraska public utility and local-government records
- OG&E / Oklahoma utility records
- Evergy / Ameren / other Missouri utility records
- State regulatory filings
- GridTracker and Interconnection.fyi

### Tennessee / TVA

- TVA interconnection/large-customer materials
- TVA transmission planning
- Tennessee Valley Authority service arrangements
- Tennessee state and local regulatory records
- GridTracker / Watt Street
- Memphis Light, Gas and Water where relevant to Memphis sites
- County permits and tax records

Watt Street's current Tennessee page states that its queue aggregation covers
the queues of every transmission provider operating in Tennessee and identifies
TVA as the dominant queue operator there.

### Georgia / SERC

- Georgia Power large-load contracts and associated Georgia PSC Docket 44280
- Georgia PSC filing search
- Southern Company / Georgia Power transmission and load-planning materials
- SERC regional transmission records
- GridTracker / Watt Street / Interconnection.fyi
- Local development and permit records

The Georgia PSC currently has recurring 2026 large-load contract filings under
Docket 44280, including July and September 2026 filings. Georgia Power publicly
states that new large-energy users such as data centers are placed under
long-term service arrangements and that the utility files those contracts with
the PSC.

### Alabama / SERC

- Alabama PSC docket and tariff records
- Alabama Power large-load/service agreements
- Southern Company transmission records
- SERC queue sources
- GridTracker / Watt Street
- Local permits and economic-development records

### North Carolina / SERC

- Duke Energy Carolinas / Duke Energy Progress
- North Carolina Utilities Commission filings
- SERC / utility transmission records
- Watt Street / Interconnection.fyi / GridTracker
- Local permits and county records

### South Carolina / SERC

- Duke Energy / Dominion / Santee Cooper as applicable
- South Carolina Public Service Commission
- SERC transmission records
- Watt Street / Interconnection.fyi / GridTracker
- Local permits

### WECC western states

Arizona:
- Arizona Public Service
- Salt River Project
- Arizona Corporation Commission
- WECC transmission/interconnection records
- Watt Street / Interconnection.fyi / DataCenter.fyi

Idaho:
- Idaho Power
- PacifiCorp
- Avista
- Idaho PUC
- BPA / WECC where transmission-level
- Watt Street / Interconnection.fyi

Nevada:
- NV Energy
- Public Utilities Commission of Nevada
- WECC
- Watt Street / Interconnection.fyi

Utah:
- Rocky Mountain Power
- Utah Public Service Commission
- PacifiCorp
- WECC
- Watt Street / Interconnection.fyi

New Mexico:
- PNM
- New Mexico PRC
- WECC
- Watt Street / Interconnection.fyi

Wyoming:
- PacifiCorp / Rocky Mountain Power and other serving utilities
- Wyoming PSC
- WECC
- Watt Street / Interconnection.fyi

Oregon:
- Bonneville Power Administration
- Portland General Electric
- PacifiCorp
- Oregon PUC
- WECC
- Watt Street / Interconnection.fyi
- Local transmission-owner planning and connection records

## Other U.S. municipal / cooperative systems

Some Epoch campuses sit behind municipal or cooperative utilities rather than
an ISO/RTO queue. Those sites require utility-specific research rather than
forcing them into the nearest ISO.

Known examples in the current Epoch set:
- Canton Municipal Utilities — Amazon Madison Mega Site
- Entergy Mississippi — Amazon Ridgeland
- MidAmerican Energy — Google Council Bluffs (East)
- Interstate Power and Light / Alliant — Google Cedar Rapids and QTS Cedar Rapids
- Northern Indiana Public Service — Anthropic-Amazon New Carlisle
- Duke Energy Indiana — Meta Jeffersonville
- I&M — Google Fort Wayne
- American Electric Power / South Central Power — Ohio Google sites
- Coleman County Electric Cooperative — Stargate Abilene
- Wisconsin Electric Power Company — Fairwater Wisconsin

These utility connections are supported by secondary public-record facility
registries in the current research layer; the next step is to replace each
secondary utility identification with the utility's own service agreement,
commission filing, connection study, tariff filing, or other primary record
where publicly available.

## International connection-system universe

Epoch's 16 non-U.S./Canada sites are not part of the nine-market North American
queue totals. They need their own national/transmission/distribution connection
research.

### United Kingdom

- NESO Connections 360 — connection-site search and contracted project view:
  https://www.neso.energy/industry-information/connections/connections-360
- NESO Connections registers:
  https://www.neso.energy/industry-information/connections/reports-and-registers
- TEC Register:
  https://www.neso.energy/data-portal/transmission-entry-capacity-tec-register
- Existing Agreement (EA) Register / Connections Reform:
  https://www.neso.energy/industry-information/connections-reform

### Finland

- Fingrid connection enquiry / main-grid connection process
- Fingrid open-data portal
- Fingrid's published material shows that more than half of recent high-volume
  electricity-consumption connection enquiries were related to data centers.

### Sweden

- Svenska kraftnät connection queue / connection process
- Svenska kraftnät public reporting states that it is actively reducing its
  large-scale connection queue.

### Norway

- Statnett connection process / connection queue
- Local distribution network operator records

### Australia

- AEMO NEM registration and exemption list
- AEMO connection applications / connection process
- AEMO connection scorecards
- Relevant Network Service Provider connection records

AEMO publicly publishes registration lists containing generators and scheduled
loads, and its Q1 2026 energy report separately quantified submitted data-center
load connection applications.

### Malaysia

- Tenaga Nasional Berhad (TNB) grid/service records
- TNB connection agreements and planning materials
- DayOne/TNB Electricity Supply Agreements

DayOne publicly announced an ESA with TNB for its Nusajaya campus, and a 2026
TNB collaboration concerning new large-scale data-center power infrastructure.

### Portugal

- REN transmission connection process
- E-REDES distribution connection process
- Start Campus public grid-power documentation
- Portuguese regulatory/municipal permitting

Start Campus states that SIN01 has secured grid power and that the Sines campus
is designed for a 1.2 GW build-out.

### Iceland

- Landsnet connection process / transmission records
- Local distribution connection records
- Icelandic regulatory filings

### China

- State Grid
- Provincial State Grid subsidiaries
- Provincial development and energy authorities
- Local utility/interconnection records
- Environmental, land, permit and government procurement records

### Indonesia

- PLN connection process
- Local/provincial PLN records
- Indonesian energy/regulatory filings

### United Arab Emirates

- Emirates Water and Electricity Company (EWEC)
- Local transmission/distribution utility records
- Abu Dhabi energy/regulatory records

The current public facility evidence identifies EWEC as the grid operator for
Epoch's Stargate UAE record.

## Current completion status

As of 2026-09-26, the repository contains:

- 93/93 Epoch sites imported.
- 93/93 Epoch sites assigned a geographic queue/connection jurisdiction.
- 77/77 U.S. sites assigned to a state/grid/utility jurisdiction.
- 16/16 international sites assigned to an external connection-system
  jurisdiction.
- 2 Epoch records have a site-specific queue ID verified in the current
  crosswalk (the two Lake Mariner records → NYISO Q1670).
- 3 Epoch records additionally have a public service/planning evidence record
  without a queue ID.
- 72 U.S. records remain **queue-jurisdiction mapped but site-specific queue ID
  not yet verified**.

That last category is the active research queue. It is intentionally not
counted as a site-level queue match.

## Important measurement rule

Never equate:
- Epoch current IT power,
- Epoch projected IT power,
- utility service capacity,
- interconnection requested capacity,
- transmission capacity,
- queue MW,
- generation capacity at a co-located site,
- or contracted demand

as interchangeable numbers.

They answer different questions and must remain separate fields.

## Why a perfect 93-for-93 queue-ID claim may be impossible

Some large loads are served by distribution utilities or municipal/cooperative
systems; some are already operating and therefore no longer appear as active
queue requests; some queue/application details are confidential; and some
projects appear publicly only through contracts, commission filings, permits, or
customer-planning documents.

The research objective is therefore not to manufacture a queue ID for every
site. It is to drive every site through the complete public-source universe
until the most specific public connection record is found, with the remaining
gap explicitly documented.
