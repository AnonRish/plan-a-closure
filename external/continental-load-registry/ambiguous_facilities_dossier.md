# Ambiguous large-load facilities — investigative dossier

Generated 2026-09-27 by `investigate_ambiguous_loads.py`.

**Read this first.** This is a worklist of leads, not a set of findings. Nothing here was fetched or verified: each search URL points at a public search engine, and results still need a human to read them. The broad ambiguity filter is not a load-classification proof: a candidate must pass the strict source-level load-admission gate before it is treated as a load-discovery case. "Developer Not Disclosed" is usually a property of what the source register publishes (SPP, MISO, CAISO, ISO-NE and AESO publish no applicant), not evidence about the developer. A facility's label changes only when a researcher records a verified identity with evidence in `ground_truth_overrides.json`.

## Scope

Filter: `capacity_mw >= 100`, `load_type_tier == "Genuinely Ambiguous / Unclassified Large Load"`, `entity_category` in ("Developer Not Matched To Known List", "Developer Not Disclosed").

| Filter step | Rows |
|---|---:|
| Registry rows loaded | 1,540 |
| Not in the ambiguous tier | 1,398 |
| Capacity missing or unreadable | 0 |
| Below 100 MW | 0 |
| Developer resolved to a known entity (outside the two categories) | 1 |
| **Facilities in this dossier** | **141** (53.9 GW) |

Data sources:

- `index.html`: 1,540 rows, AESO, CAISO, ERCOT, IESO, ISO-NE, MISO, NYISO, PJM, SPP
- `data/computational_load_estimates.csv`: 733 rows, ERCOT, PJM — replaces 733 index.html rows for ERCOT, PJM

| RTO | Facilities | GW | Verified |
|---|---:|---:|---:|
| AESO | 30 | 20.4 | 0 |
| NYISO | 38 | 13.5 | 0 |
| IESO | 25 | 8.7 | 0 |
| MISO | 36 | 8.6 | 0 |
| SPP | 12 | 2.7 | 0 |

**Ground-truth overrides: 0 of 141.** This pool is not a set of confirmed discoveries; promote cases only after strict load-admission review. Record confirmed identities in `ground_truth_overrides.json` and re-run.

## Ranked summary

All facilities, by capacity.

| # | RTO | Queue ID | MW | Location | Project / developer | Status | Verified |
|--:|---|---|--:|---|---|---|---|
| 1 | NYISO | 1743 | 1,935 | NY · St. Lawrence | St. Lawrence Infrastructure 2 | Under Study | — |
| 2 | AESO | P3066 | 1,864 | AB · Caroline area | Leedale Data Load | Under Study | — |
| 3 | AESO | P3198 | 1,800 | AB · Fort Saskatchewan area | Lynx Data Load | Active | — |
| 4 | AESO | P2970 | 1,400 | AB · Calgary area | Beacon Langdon A.I. Hub 2 Load | Active | — |
| 5 | IESO | 2026-903 | 1,380 | ON · Essa zone | Project IQ197 | Under Study | — |
| 6 | AESO | P3108 | 1,300 | AB · Calgary area | Wild Rose Power Hub Load | Under Study | — |
| 7 | AESO | P3109 | 1,200 | AB · Brooks area | Newell Data Center MPC Load | Under Study | — |
| 8 | AESO | P2942 | 1,000 | AB · Wabamun area | Genesee Data Center 1 MPC Load | Under Study | — |
| 9 | IESO | 2026-885 | 1,000 | ON · West zone | N49 Digital | Under Study | — |
| 10 | MISO | J1490 | 1,000 | MO · Randolph | (no project name published) | IA in Progress | — |
| 11 | NYISO | 1738 | 1,000 | NY · Dutchess | 1 Gig Data Center East Fishkill, NY | Under Study | — |
| 12 | AESO | P2936 | 970 | AB · Fort Saskatchewan area | GLDC Load Phase 1.1 | Under Study | — |
| 13 | AESO | P3101 | 950 | AB · Didsbury area | Carstairs Technology Park MPC Load | Under Study | — |
| 14 | AESO | P3102 | 950 | AB · Strathmore/Blackie area | Goldfinch Technology Park MPC Load | Under Study | — |
| 15 | NYISO | 1742 | 860 | NY · St. Lawrence | St. Lawrence Infrastructure 1 | Under Study | — |
| 16 | AESO | P3151 | 830 | AB · Fort Saskatchewan area | GLDC Load Phase 1.2 | Under Study | — |
| 17 | AESO | P3116 | 800 | AB · Calgary area | Rocky View Data Center MPC Load | Under Study | — |
| 18 | AESO | P3137 | 800 | AB · Sheerness area | Sheerness Data MPC Load | Active | — |
| 19 | IESO | 2025-833 | 707 | ON · Toronto zone | Priority 1 & Priority 2 Transformer Stations Load Increase | Under Study | — |
| 20 | IESO | 2025-848 | 695 | ON · West zone | EPC/PUC TransCo TS - Phase 1A | Under Study | — |
| 21 | MISO | S1156 | 632 | TX | (no project name published) | Active | — |
| 22 | MISO | S1161 | 625 | AR | (no project name published) | Active | — |
| 23 | NYISO | 1765 | 606 | NY · Onondaga | Micron Fab 3 | Active | — |
| 24 | NYISO | 1627 | 576 | NY · Onondaga | Micron Fab 2 | Facilities Study | — |
| 25 | IESO | 2025-863 | 550 | ON · West zone | Essex Transmission - Phase 1B | Under Study | — |
| 26 | MISO | S1157 | 534 | TX | (no project name published) | Active | — |
| 27 | AESO | P2946 | 500 | AB · Wabamun area | Genesee Data Center 2 MPC Load | Under Study | — |
| 28 | MISO | J1488 | 500 | MO · Randolph | (no project name published) | IA in Progress | — |
| 29 | NYISO | 1741 | 500 | NY · Niagara | North East Data LLC Data Center | Under Study | — |
| 30 | SPP | GEN-2024-013 | 496 | OK · McClain | (no project name published) | Under Study | — |
| 31 | SPP | GEN-2024-GR1 | 492 | OK · Harrah | (no project name published) | IA in Progress | — |
| 32 | NYISO | 1536 | 480 | NY · Onondaga | White Pine Phase 1 | IA in Progress | — |
| 33 | NYISO | 1730 | 467 | NY · St Lawrence | Arsenal Data Site 1000 | Under Study | — |
| 34 | AESO | P3095 | 466 | AB · Wabamun area | Keephills Data Centre Phase 2 | Under Study | — |
| 35 | AESO | P3112 | 450 | AB · Calgary area | North Calgary Three Data Centre MPC Load | Active | — |
| 36 | IESO | 2026-899 | 447 | ON · West zone | Leamington Area Load Increase | Under Study | — |
| 37 | NYISO | 0979 | 435 | NY · St. Lawrence | North Country Data Center | IA in Progress | — |
| 38 | AESO | P3136 | 401 | AB · Wabamun area | Sundance Data MPC Load | Active | — |
| 39 | AESO | P2926 | 400 | AB · High River area | Beacon Foothills A.I. Hub Load | Under Study | — |
| 40 | AESO | P2927 | 400 | AB · Wabamun area | Beacon Harry Smith A.I. Hub Load | Under Study | — |
| 41 | AESO | P2928 | 400 | AB · Calgary area | Beacon Langdon A.I. Hub Load | Under Study | — |
| 42 | AESO | P2934 | 400 | AB · Fort Saskatchewan area | Beacon Heartland A.I. Hub Load | Under Study | — |
| 43 | AESO | P2935 | 400 | AB · Edmonton area | Beacon Saunders Lake A.I. Hub Load | Under Study | — |
| 44 | AESO | P3106 | 400 | AB · Lethbridge area | Alberta South A.I. Load | Active | — |
| 45 | AESO | P3107 | 400 | AB · Calgary area | Chestermere Enterprise A.I. Load | Active | — |
| 46 | AESO | P3175 | 400 | AB · Fort Saskatchewan area | Beacon Heartland Data Load | Active | — |
| 47 | IESO | 2026-881 | 400 | ON · Northeast zone | Algoma Data Center | Under Study | — |
| 48 | NYISO | 1740 | 400 | NY · Herkimer | Incremental Load Request for Remington Factory Redevelopment | Under Study | — |
| 49 | NYISO | 1762 | 400 | PA · Clearfield | Highwall Data Center | Under Study | — |
| 50 | SPP | GEN-2025-SR9 | 400 | OK · Fort Gibson | (no project name published) | Under Study | — |
| 51 | MISO | S1162 | 390 | AR | (no project name published) | Active | — |
| 52 | NYISO | 1763 | 350 | PA · Tioga | Patriot Forge | Under Study | — |
| 53 | AESO | P2958 | 320 | AB · Fort Saskatchewan area | Hydrogen Canada MPC Load | Under Study | — |
| 54 | AESO | P3110 | 300 | AB · Peace River area | Mihta Askiy Data Load | Active | — |
| 55 | AESO | P3156 | 300 | AB · Calgary area | High Plains East Industrial Park | Active | — |
| 56 | IESO | 2024-819 | 300 | ON · Southwest zone | Industrial Production Facility | Under Study | — |
| 57 | IESO | 2026-872 | 300 | ON · Toronto zone | Moldenhauer Energy 1 & 2 | Under Study | — |
| 58 | MISO | S1054 | 300 | MN · Cottonwood | (no project name published) | Active | — |
| 59 | NYISO | 0580 | 300 | NY · Genesee | WNY STAMP | IA in Progress | — |
| 60 | NYISO | 1484 | 300 | NY · Genesee | 580 STAMP load increase | IA in Progress | — |
| 61 | NYISO | 1726 | 300 | NY · Erie | Data & Technology Campus | Under Study | — |
| 62 | NYISO | 1731 | 300 | NY · St. Lawrence | New York State Artificial Intelligence Data Center | Under Study | — |
| 63 | NYISO | 1736 | 270 | NY · Onondaga | Ranalli SuperDC | Under Study | — |
| 64 | IESO | 2025-857 | 250 | ON · East zone | Napanee Data Park | Under Study | — |
| 65 | IESO | 2026-871 | 250 | ON · Toronto zone | Creekside Industrial Load | Under Study | — |
| 66 | NYISO | 1670 | 250 | NY · Niagara | Lake Mariner Data II | Under Study | — |
| 67 | NYISO | 1732 | 250 | NY · Niagara | Wulf Compute Data Center II | Under Study | — |
| 68 | NYISO | 1745 | 250 | NY · St Lawrence | Pontoon Bridge Road Data Center | Under Study | — |
| 69 | NYISO | 1752 | 250 | NY · Broome | Broome County Tech Park | Under Study | — |
| 70 | SPP | GEN-2025-SR10 | 238 | OK · Konawa | (no project name published) | Under Study | — |
| 71 | NYISO | 1728 | 233 | NY · St Lawrence | Arsenal Data Site 250 | Under Study | — |
| 72 | NYISO | 1729 | 233 | NY · St Lawrence | Arsenal Data Site 500 | Under Study | — |
| 73 | AESO | P2614 | 231 | AB · Fort Saskatchewan area | Dow Fort Sask. Load | IA in Progress | — |
| 74 | AESO | P3083 | 230 | AB · Wabamun area | Keephills Data Centre Phase 1.1 | Under Study | — |
| 75 | MISO | S1148 | 230 | MN · Rock | (no project name published) | Active | — |
| 76 | MISO | S1086 | 225 | MO · Stoddard | (no project name published) | Active | — |
| 77 | MISO | S1130 | 225 | MI | (no project name published) | Active | — |
| 78 | MISO | S1057 | 210 | IL · Cumberland and Coles | (no project name published) | Active | — |
| 79 | IESO | 2025-838 | 207.2 | ON · Toronto zone | Project Rebel | Under Study | — |
| 80 | IESO | 2025-836 | 200 | ON · Southwest zone | Mikinak Data Center | Under Study | — |
| 81 | IESO | 2025-846 | 200 | ON · Southwest zone | Beach TS & Gage TS Load Increase | Under Study | — |
| 82 | IESO | 2026-877 | 200 | ON · East zone | Millhaven Data Center | Under Study | — |
| 83 | IESO | 2026-894 | 200 | ON · Southwest zone | Mikinak Phase 2 Data Center | Under Study | — |
| 84 | IESO | 2026-913 | 200 | ON · West zone | St. Clair Technology Centre | Under Study | — |
| 85 | MISO | S1074 | 200 | AR · Phillips | (no project name published) | Active | — |
| 86 | MISO | S1091 | 200 | MO · Cape Girardeau | (no project name published) | Active | — |
| 87 | MISO | S1133 | 200 | LA · Sangamon | (no project name published) | Active | — |
| 88 | MISO | S1140 | 200 | MN · Clinton | (no project name published) | Active | — |
| 89 | MISO | S1144 | 200 | MI | (no project name published) | Active | — |
| 90 | MISO | S1155 | 200 | MO | (no project name published) | Active | — |
| 91 | MISO | S1164 | 200 | AR · Mississippi | (no project name published) | Active | — |
| 92 | NYISO | 1213 | 200 | NY · St. Lawrence | St Lawrence Data and Agricultural Center | IA in Progress | — |
| 93 | NYISO | 1717 | 200 | NY · Westchester | Proposed Datacenters at 450 Broadway, Buchanan, NY, 10511 | Under Study | — |
| 94 | NYISO | 1725 | 200 | NY · Yates | Greenidge 200 MW Data Center Project | Under Study | — |
| 95 | NYISO | 1751 | 200 | NY · St; Lawrence | Massena Development LLC Power Allocation | Under Study | — |
| 96 | SPP | GEN-2025-SR24 | 200 | NE · Blair | (no project name published) | Facilities Study | — |
| 97 | SPP | GEN-2025-SR26 | 200 | NE · Plattsmouth | (no project name published) | Facilities Study | — |
| 98 | IESO | 2024-809 | 198 | ON · Southwest zone | Project Chisel | Under Study | — |
| 99 | IESO | 2025-825 | 198 | ON · Southwest zone | Project Chisel 2 | Under Study | — |
| 100 | NYISO | 1747 | 192 | NY · Niagara | Globe Digital Holdings - 1 | Under Study | — |
| 101 | NYISO | 1748 | 192 | NY · Niagara Falls | GLOBE DH 2 | Under Study | — |
| 102 | NYISO | 1749 | 192 | NY · Niagara Falls | Globe DH 3 | Under Study | — |
| 103 | MISO | J2656 | 180 | IL · Macon | (no project name published) | Active | — |
| 104 | NYISO | 1754 | 180 | NY · Albany | Kenwood Tech Center | Under Study | — |
| 105 | NYISO | 1721 | 176.6 | NY · Suffolk | Brookhaven Logistics Center | Facilities Study | — |
| 106 | AESO | P3152 | 165 | AB · Wabamun area | Keephills Data Centre Phase 1.2 | Active | — |
| 107 | NYISO | 1733 | 162 | NY · Tompkins | Cayuga Data | Under Study | — |
| 108 | IESO | 2025-856 | 153 | ON · Toronto zone | Richmond Hill MTS #3 | Under Study | — |
| 109 | IESO | 2025-832 | 150 | ON · Southwest zone | Enova #11 TS: Waterloo MTS3 Expansion | Under Study | — |
| 110 | IESO | 2026-873 | 150 | ON · West zone | Bell AI - Sovereign Canadian Data Center | Under Study | — |
| 111 | MISO | S1052 | 150 | IL · Cumberland | (no project name published) | Active | — |
| 112 | MISO | S1068 | 150 | MI · Hillsdale | (no project name published) | Active | — |
| 113 | MISO | S1137 | 150 | LA | (no project name published) | Active | — |
| 114 | MISO | S1154 | 150 | MN | (no project name published) | Active | — |
| 115 | MISO | S1160 | 150 | SD | (no project name published) | Active | — |
| 116 | NYISO | 1760 | 150 | NY · Dutchess | iPark 84 Data Center Interconnection | Under Study | — |
| 117 | NYISO | 1761 | 150 | NY · Horseheads | NYISO Load Interconnection Process - Data Center Inquiry | Active | — |
| 118 | NYISO | 1681 | 140 | NY · Niagara | Niagara Digital Campus | Facilities Study | — |
| 119 | MISO | S1152 | 139 | MO | (no project name published) | Active | — |
| 120 | MISO | S1143 | 135 | IL | (no project name published) | Active | — |
| 121 | MISO | S1147 | 132 | MI | (no project name published) | Active | — |
| 122 | IESO | 2025-854 | 130 | ON · West zone | CPXP Sarnia Hydrogen Facility | Under Study | — |
| 123 | MISO | S1146 | 125 | MI · Muskegon | (no project name published) | Active | — |
| 124 | SPP | GEN-2025-SR13 | 125 | OK · Konawa | (no project name published) | Under Study | — |
| 125 | SPP | GEN-2025-SR15 | 125 | OK · Newcastle | (no project name published) | Under Study | — |
| 126 | IESO | 2025-865 | 120 | ON · Toronto zone | GTAA MTS | Under Study | — |
| 127 | MISO | S1047 | 120 | SD · Codington | (no project name published) | Active | — |
| 128 | NYISO | 1315 | 120 | NY · St. Lawrence | SDC St. Lawrence | Facilities Study | — |
| 129 | MISO | S1166 | 108.9 | MN | (no project name published) | Active | — |
| 130 | SPP | GEN-2024-003 | 102.2 | AR · Franklin | (no project name published) | Under Study | — |
| 131 | MISO | S1059 | 100.3 | MI · Tuscola | (no project name published) | Active | — |
| 132 | IESO | 2024-812 | 100 | ON · Toronto zone | IBM Markham CTS - Load Increase | IA in Progress | — |
| 133 | MISO | S1053 | 100 | MN · Chisago | (no project name published) | Active | — |
| 134 | MISO | S1075 | 100 | IN · Jasper and Starke | (no project name published) | Active | — |
| 135 | MISO | S1136 | 100 | MI | (no project name published) | Active | — |
| 136 | MISO | S1138 | 100 | MI | (no project name published) | Active | — |
| 137 | MISO | S1159 | 100 | WI | (no project name published) | Active | — |
| 138 | NYISO | 1735 | 100 | NY · Herkimer | Remington Factory Redevelopment | Under Study | — |
| 139 | SPP | GEN-2025-SR19 | 100 | OK · Chouteau | (no project name published) | IA in Progress | — |
| 140 | SPP | GEN-2025-SR22 | 100 | OK · Harrah | (no project name published) | IA in Progress | — |
| 141 | SPP | GEN-2025-SR23 | 100 | OK · Oklahoma City | (no project name published) | IA in Progress | — |

## Where the records live

Static entry points for the jurisdictions in this dossier. The per-facility queries use `site:` restrictions only where the domain is confidently known; treat every domain as a search hint.

| Operator | Entry point | `site:` used for its documents |
|---|---|---|
| SPP | <https://opsportal.spp.org/Studies/GIActive> | `spp.org` |
| MISO | <https://www.misoenergy.org/> | `misoenergy.org` |
| NYISO | <https://www.nyiso.com/> | `nyiso.com` |
| IESO | <https://www.ieso.ca/Sector-Participants/Connection-Process/Application-Status> | `ieso.ca` |
| AESO | <https://www.aeso.ca/> | `aeso.ca` |

| State / province | Environmental | Utility regulator / siting |
|---|---|---|
| AB (Alberta) | Alberta Environment and Protected Areas | Alberta Utilities Commission; AUC (<https://auc.ab.ca/>) |
| AR (Arkansas) | Arkansas Division of Environmental Quality; ADEQ | Arkansas Public Service Commission |
| IL (Illinois) | Illinois EPA; Illinois Environmental Protection Agency (<https://epa.illinois.gov/>) | Illinois Commerce Commission (<https://icc.illinois.gov/>) |
| IN (Indiana) | IDEM; Indiana Department of Environmental Management | Indiana Utility Regulatory Commission; IURC |
| LA (Louisiana) | Louisiana Department of Environmental Quality; LDEQ (<https://deq.louisiana.gov/>) | Louisiana Public Service Commission (<https://lpsc.louisiana.gov/>) |
| MI (Michigan) | EGLE; Michigan Department of Environment, Great Lakes, and Energy | Michigan Public Service Commission; MPSC |
| MN (Minnesota) | Minnesota Pollution Control Agency; MPCA | Minnesota Public Utilities Commission |
| MO (Missouri) | Missouri Department of Natural Resources (<https://dnr.mo.gov/>) | Missouri Public Service Commission (<https://psc.mo.gov/>) |
| NE (Nebraska) | Nebraska Department of Environment and Energy; NDEE (<https://dee.ne.gov/>) | Nebraska Power Review Board |
| NY (New York) | NYSDEC; New York State Department of Environmental Conservation (<https://dec.ny.gov/>) | New York Public Service Commission; NY DPS (<https://dps.ny.gov/>) |
| OK (Oklahoma) | Oklahoma Department of Environmental Quality; Oklahoma DEQ | Oklahoma Corporation Commission |
| ON (Ontario) | Environmental Registry of Ontario (<https://ero.ontario.ca/>) | Ontario Energy Board (<https://oeb.ca/>) |
| PA (Pennsylvania) | Pennsylvania Department of Environmental Protection; PA DEP (<https://dep.pa.gov/>) | Pennsylvania Public Utility Commission (<https://puc.pa.gov/>) |
| SD (South Dakota) | South Dakota Department of Agriculture and Natural Resources; DANR (<https://danr.sd.gov/>) | South Dakota Public Utilities Commission (<https://puc.sd.gov/>) |
| TX (Texas) | TCEQ; Texas Commission on Environmental Quality (<https://tceq.texas.gov/>) | Public Utility Commission of Texas; PUCT (<https://puc.texas.gov/>) |
| WI (Wisconsin) | Wisconsin Department of Natural Resources (<https://dnr.wisconsin.gov/>) | Public Service Commission of Wisconsin (<https://psc.wi.gov/>) |

Federal filings: FERC eLibrary <https://elibrary.ferc.gov/> (interconnection agreements and large-load or co-location proceedings).

## Facility dossiers

### 1. NYISO 1743 — St. Lawrence Infrastructure 2 · 1,935 MW · NY

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | St. Lawrence Infrastructure, LLC — Developer Not Matched To Known List |
| Point of interconnection | NYPA's 230kV Moses Massena 1 (MMS-1) and 230kV Moses Massena 2 (MMS-2) |
| Location field | county field "St. Lawrence", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("St. Lawrence Infrastructure 2" OR "St. Lawrence Infrastructure") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22St.+Lawrence+Infrastructure+2%22+OR+%22St.+Lawrence+Infrastructure%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("St. Lawrence Infrastructure 2" OR "St. Lawrence Infrastructure") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22St.+Lawrence+Infrastructure+2%22+OR+%22St.+Lawrence+Infrastructure%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("St. Lawrence Infrastructure 2" OR "St. Lawrence Infrastructure") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22St.+Lawrence+Infrastructure+2%22+OR+%22St.+Lawrence+Infrastructure%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("St. Lawrence Infrastructure 2" OR "St. Lawrence Infrastructure") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22St.+Lawrence+Infrastructure+2%22+OR+%22St.+Lawrence+Infrastructure%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"NYPA's 230kV Moses Massena 1 (MMS-1) and 230kV Moses Massena 2 (MMS-2)" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22NYPA%27s+230kV+Moses+Massena+1+%28MMS-1%29+and+230kV+Moses+Massena+2+%28MMS-2%29%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1743" OR Q1743 OR "Queue #1743" OR 1743 OR "St. Lawrence Infrastructure 2")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231743%22+OR+Q1743+OR+%22Queue+%231743%22+OR+1743+OR+%22St.+Lawrence+Infrastructure+2%22%29) |

### 2. AESO P3066 — Leedale Data Load · 1,864 MW · AB

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "Caroline" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "Leedale Data" Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22Leedale+Data%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "Leedale Data" Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22Leedale+Data%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "Leedale Data" Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22Leedale+Data%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "Leedale Data" Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22Leedale+Data%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P3066 OR "Leedale Data Load")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P3066+OR+%22Leedale+Data+Load%22%29) |

### 3. AESO P3198 — Lynx Data Load · 1,800 MW · AB

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "Fort Saskatchewan" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "Lynx Data" Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22Lynx+Data%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "Lynx Data" Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22Lynx+Data%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "Lynx Data" Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22Lynx+Data%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "Lynx Data" Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22Lynx+Data%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P3198 OR "Lynx Data Load")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P3198+OR+%22Lynx+Data+Load%22%29) |

### 4. AESO P2970 — Beacon Langdon A.I. Hub 2 Load · 1,400 MW · AB

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "Calgary" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "Beacon Langdon A.I. Hub 2" Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22Beacon+Langdon+A.I.+Hub+2%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "Beacon Langdon A.I. Hub 2" Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22Beacon+Langdon+A.I.+Hub+2%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "Beacon Langdon A.I. Hub 2" Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22Beacon+Langdon+A.I.+Hub+2%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "Beacon Langdon A.I. Hub 2" Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22Beacon+Langdon+A.I.+Hub+2%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P2970 OR "Beacon Langdon A.I. Hub 2 Load")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P2970+OR+%22Beacon+Langdon+A.I.+Hub+2+Load%22%29) |

### 5. IESO 2026-903 — Project IQ197 · 1,380 MW · ON

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | 197 McKay Barrie Corp — Developer Not Matched To Known List |
| Point of interconnection | not published by the source register |
| Location field | IESO electrical zone "Essa" (a grid region, not a municipality) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "planning committee" OR "committee of the whole") minutes ("Project IQ197" OR "197 McKay Barrie") Ontario`](https://www.google.com/search?q=%28council+OR+%22planning+committee%22+OR+%22committee+of+the+whole%22%29+minutes+%28%22Project+IQ197%22+OR+%22197+McKay+Barrie%22%29+Ontario) |
| Municipal · Zoning & development applications | [`("zoning by-law amendment" OR "official plan amendment" OR "site plan" OR "minister's zoning order") ("Project IQ197" OR "197 McKay Barrie") Ontario`](https://www.google.com/search?q=%28%22zoning+by-law+amendment%22+OR+%22official+plan+amendment%22+OR+%22site+plan%22+OR+%22minister%27s+zoning+order%22%29+%28%22Project+IQ197%22+OR+%22197+McKay+Barrie%22%29+Ontario) |
| Environmental / regulator · Environmental registry / permits | [`site:ero.ontario.ca ("Project IQ197" OR "197 McKay Barrie") Ontario`](https://www.google.com/search?q=site%3Aero.ontario.ca+%28%22Project+IQ197%22+OR+%22197+McKay+Barrie%22%29+Ontario) |
| Environmental / regulator · Utility-commission / siting filings | [`site:oeb.ca ("Project IQ197" OR "197 McKay Barrie") Ontario`](https://www.google.com/search?q=site%3Aoeb.ca+%28%22Project+IQ197%22+OR+%22197+McKay+Barrie%22%29+Ontario) |
| Substation · RTO / ISO documents | [`site:ieso.ca ("2026-903" OR "Project IQ197")`](https://www.google.com/search?q=site%3Aieso.ca+%28%222026-903%22+OR+%22Project+IQ197%22%29) |

### 6. AESO P3108 — Wild Rose Power Hub Load · 1,300 MW · AB

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "Calgary" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "Wild Rose Power Hub" Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22Wild+Rose+Power+Hub%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "Wild Rose Power Hub" Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22Wild+Rose+Power+Hub%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "Wild Rose Power Hub" Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22Wild+Rose+Power+Hub%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "Wild Rose Power Hub" Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22Wild+Rose+Power+Hub%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P3108 OR "Wild Rose Power Hub Load")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P3108+OR+%22Wild+Rose+Power+Hub+Load%22%29) |

### 7. AESO P3109 — Newell Data Center MPC Load · 1,200 MW · AB

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "Brooks" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "Newell Data Center" Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22Newell+Data+Center%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "Newell Data Center" Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22Newell+Data+Center%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "Newell Data Center" Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22Newell+Data+Center%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "Newell Data Center" Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22Newell+Data+Center%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P3109 OR "Newell Data Center MPC Load")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P3109+OR+%22Newell+Data+Center+MPC+Load%22%29) |

### 8. AESO P2942 — Genesee Data Center 1 MPC Load · 1,000 MW · AB

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "Wabamun" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "Genesee Data Center 1" Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22Genesee+Data+Center+1%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "Genesee Data Center 1" Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22Genesee+Data+Center+1%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "Genesee Data Center 1" Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22Genesee+Data+Center+1%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "Genesee Data Center 1" Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22Genesee+Data+Center+1%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P2942 OR "Genesee Data Center 1 MPC Load")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P2942+OR+%22Genesee+Data+Center+1+MPC+Load%22%29) |

### 9. IESO 2026-885 — N49 Digital · 1,000 MW · ON

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | N49 Digital Ltd. — Developer Not Matched To Known List |
| Point of interconnection | not published by the source register |
| Location field | IESO electrical zone "West" (a grid region, not a municipality) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "planning committee" OR "committee of the whole") minutes "N49 Digital" Ontario`](https://www.google.com/search?q=%28council+OR+%22planning+committee%22+OR+%22committee+of+the+whole%22%29+minutes+%22N49+Digital%22+Ontario) |
| Municipal · Zoning & development applications | [`("zoning by-law amendment" OR "official plan amendment" OR "site plan" OR "minister's zoning order") "N49 Digital" Ontario`](https://www.google.com/search?q=%28%22zoning+by-law+amendment%22+OR+%22official+plan+amendment%22+OR+%22site+plan%22+OR+%22minister%27s+zoning+order%22%29+%22N49+Digital%22+Ontario) |
| Environmental / regulator · Environmental registry / permits | [`site:ero.ontario.ca "N49 Digital" Ontario`](https://www.google.com/search?q=site%3Aero.ontario.ca+%22N49+Digital%22+Ontario) |
| Environmental / regulator · Utility-commission / siting filings | [`site:oeb.ca "N49 Digital" Ontario`](https://www.google.com/search?q=site%3Aoeb.ca+%22N49+Digital%22+Ontario) |
| Substation · RTO / ISO documents | [`site:ieso.ca ("2026-885" OR "N49 Digital")`](https://www.google.com/search?q=site%3Aieso.ca+%28%222026-885%22+OR+%22N49+Digital%22%29) |

### 10. MISO J1490 — (no project name published) · 1,000 MW · MO

| | |
|---|---|
| Status (as published) | IA in Progress |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | McCredie - Montgomery 345 kV Line Tap |
| Location field | county field "Randolph", Missouri |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "McCredie - Montgomery 345 kV Line Tap" "Randolph" County Missouri ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22McCredie+-+Montgomery+345+kV+Line+Tap%22+%22Randolph%22+County+Missouri+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "McCredie - Montgomery 345 kV Line Tap" "Randolph" County Missouri ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22McCredie+-+Montgomery+345+kV+Line+Tap%22+%22Randolph%22+County+Missouri+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`site:dnr.mo.gov "Randolph" County Missouri ("data center" OR "large load")`](https://www.google.com/search?q=site%3Adnr.mo.gov+%22Randolph%22+County+Missouri+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`site:psc.mo.gov "McCredie - Montgomery 345 kV Line Tap" "Randolph" County Missouri ("data center" OR "large load")`](https://www.google.com/search?q=site%3Apsc.mo.gov+%22McCredie+-+Montgomery+345+kV+Line+Tap%22+%22Randolph%22+County+Missouri+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"McCredie - Montgomery 345 kV Line Tap" (substation OR interconnection OR "facilities study" OR "system impact study") Missouri`](https://www.google.com/search?q=%22McCredie+-+Montgomery+345+kV+Line+Tap%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Missouri) |
| Substation · RTO / ISO documents | [`site:misoenergy.org J1490`](https://www.google.com/search?q=site%3Amisoenergy.org+J1490) |

### 11. NYISO 1738 — 1 Gig Data Center East Fishkill, NY · 1,000 MW · NY

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | Donovan Drive Holdings LLC — Developer Not Matched To Known List |
| Point of interconnection | East Fishkill to Wood Street 345 kV lines (38 and 39) |
| Location field | county field "Dutchess", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("1 Gig Data Center East Fishkill, NY" OR "Donovan Drive Holdings") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%221+Gig+Data+Center+East+Fishkill%2C+NY%22+OR+%22Donovan+Drive+Holdings%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("1 Gig Data Center East Fishkill, NY" OR "Donovan Drive Holdings") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%221+Gig+Data+Center+East+Fishkill%2C+NY%22+OR+%22Donovan+Drive+Holdings%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("1 Gig Data Center East Fishkill, NY" OR "Donovan Drive Holdings") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%221+Gig+Data+Center+East+Fishkill%2C+NY%22+OR+%22Donovan+Drive+Holdings%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("1 Gig Data Center East Fishkill, NY" OR "Donovan Drive Holdings") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%221+Gig+Data+Center+East+Fishkill%2C+NY%22+OR+%22Donovan+Drive+Holdings%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"East Fishkill to Wood Street 345 kV lines (38 and 39)" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22East+Fishkill+to+Wood+Street+345+kV+lines+%2838+and+39%29%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1738" OR Q1738 OR "Queue #1738" OR 1738 OR "1 Gig Data Center East Fishkill, NY")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231738%22+OR+Q1738+OR+%22Queue+%231738%22+OR+1738+OR+%221+Gig+Data+Center+East+Fishkill%2C+NY%22%29) |

### 12. AESO P2936 — GLDC Load Phase 1.1 · 970 MW · AB

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "Fort Saskatchewan" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "GLDC" Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22GLDC%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "GLDC" Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22GLDC%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "GLDC" Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22GLDC%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "GLDC" Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22GLDC%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P2936 OR "GLDC Load Phase 1.1")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P2936+OR+%22GLDC+Load+Phase+1.1%22%29) |

### 13. AESO P3101 — Carstairs Technology Park MPC Load · 950 MW · AB

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "Didsbury" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "Carstairs Technology Park" Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22Carstairs+Technology+Park%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "Carstairs Technology Park" Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22Carstairs+Technology+Park%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "Carstairs Technology Park" Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22Carstairs+Technology+Park%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "Carstairs Technology Park" Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22Carstairs+Technology+Park%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P3101 OR "Carstairs Technology Park MPC Load")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P3101+OR+%22Carstairs+Technology+Park+MPC+Load%22%29) |

### 14. AESO P3102 — Goldfinch Technology Park MPC Load · 950 MW · AB

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "Strathmore/Blackie" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "Goldfinch Technology Park" Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22Goldfinch+Technology+Park%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "Goldfinch Technology Park" Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22Goldfinch+Technology+Park%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "Goldfinch Technology Park" Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22Goldfinch+Technology+Park%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "Goldfinch Technology Park" Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22Goldfinch+Technology+Park%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P3102 OR "Goldfinch Technology Park MPC Load")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P3102+OR+%22Goldfinch+Technology+Park+MPC+Load%22%29) |

### 15. NYISO 1742 — St. Lawrence Infrastructure 1 · 860 MW · NY

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | St. Lawrence Infrastructure, LLC — Developer Not Matched To Known List |
| Point of interconnection | NYPA HA-2, 345kV Transmission Line |
| Location field | county field "St. Lawrence", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("St. Lawrence Infrastructure 1" OR "St. Lawrence Infrastructure") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22St.+Lawrence+Infrastructure+1%22+OR+%22St.+Lawrence+Infrastructure%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("St. Lawrence Infrastructure 1" OR "St. Lawrence Infrastructure") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22St.+Lawrence+Infrastructure+1%22+OR+%22St.+Lawrence+Infrastructure%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("St. Lawrence Infrastructure 1" OR "St. Lawrence Infrastructure") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22St.+Lawrence+Infrastructure+1%22+OR+%22St.+Lawrence+Infrastructure%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("St. Lawrence Infrastructure 1" OR "St. Lawrence Infrastructure") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22St.+Lawrence+Infrastructure+1%22+OR+%22St.+Lawrence+Infrastructure%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"NYPA HA-2, 345kV Transmission Line" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22NYPA+HA-2%2C+345kV+Transmission+Line%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1742" OR Q1742 OR "Queue #1742" OR 1742 OR "St. Lawrence Infrastructure 1")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231742%22+OR+Q1742+OR+%22Queue+%231742%22+OR+1742+OR+%22St.+Lawrence+Infrastructure+1%22%29) |

### 16. AESO P3151 — GLDC Load Phase 1.2 · 830 MW · AB

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "Fort Saskatchewan" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "GLDC" Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22GLDC%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "GLDC" Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22GLDC%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "GLDC" Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22GLDC%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "GLDC" Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22GLDC%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P3151 OR "GLDC Load Phase 1.2")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P3151+OR+%22GLDC+Load+Phase+1.2%22%29) |

### 17. AESO P3116 — Rocky View Data Center MPC Load · 800 MW · AB

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "Calgary" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "Rocky View Data Center" Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22Rocky+View+Data+Center%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "Rocky View Data Center" Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22Rocky+View+Data+Center%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "Rocky View Data Center" Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22Rocky+View+Data+Center%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "Rocky View Data Center" Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22Rocky+View+Data+Center%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P3116 OR "Rocky View Data Center MPC Load")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P3116+OR+%22Rocky+View+Data+Center+MPC+Load%22%29) |

### 18. AESO P3137 — Sheerness Data MPC Load · 800 MW · AB

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "Sheerness" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "Sheerness Data" Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22Sheerness+Data%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "Sheerness Data" Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22Sheerness+Data%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "Sheerness Data" Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22Sheerness+Data%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "Sheerness Data" Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22Sheerness+Data%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P3137 OR "Sheerness Data MPC Load")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P3137+OR+%22Sheerness+Data+MPC+Load%22%29) |

### 19. IESO 2025-833 — Priority 1 & Priority 2 Transformer Stations Load Increase · 707 MW · ON

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | ALECTRA UTILITIES CORPORATION — Developer Not Matched To Known List |
| Point of interconnection | not published by the source register |
| Location field | IESO electrical zone "Toronto" (a grid region, not a municipality) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "planning committee" OR "committee of the whole") minutes ("Priority 1 & Priority 2 Transformer Stations" OR "ALECTRA UTILITIES") Ontario`](https://www.google.com/search?q=%28council+OR+%22planning+committee%22+OR+%22committee+of+the+whole%22%29+minutes+%28%22Priority+1+%26+Priority+2+Transformer+Stations%22+OR+%22ALECTRA+UTILITIES%22%29+Ontario) |
| Municipal · Zoning & development applications | [`("zoning by-law amendment" OR "official plan amendment" OR "site plan" OR "minister's zoning order") ("Priority 1 & Priority 2 Transformer Stations" OR "ALECTRA UTILITIES") Ontario`](https://www.google.com/search?q=%28%22zoning+by-law+amendment%22+OR+%22official+plan+amendment%22+OR+%22site+plan%22+OR+%22minister%27s+zoning+order%22%29+%28%22Priority+1+%26+Priority+2+Transformer+Stations%22+OR+%22ALECTRA+UTILITIES%22%29+Ontario) |
| Environmental / regulator · Environmental registry / permits | [`site:ero.ontario.ca ("Priority 1 & Priority 2 Transformer Stations" OR "ALECTRA UTILITIES") Ontario`](https://www.google.com/search?q=site%3Aero.ontario.ca+%28%22Priority+1+%26+Priority+2+Transformer+Stations%22+OR+%22ALECTRA+UTILITIES%22%29+Ontario) |
| Environmental / regulator · Utility-commission / siting filings | [`site:oeb.ca ("Priority 1 & Priority 2 Transformer Stations" OR "ALECTRA UTILITIES") Ontario`](https://www.google.com/search?q=site%3Aoeb.ca+%28%22Priority+1+%26+Priority+2+Transformer+Stations%22+OR+%22ALECTRA+UTILITIES%22%29+Ontario) |
| Substation · RTO / ISO documents | [`site:ieso.ca ("2025-833" OR "Priority 1 & Priority 2 Transformer Stations Load Increase")`](https://www.google.com/search?q=site%3Aieso.ca+%28%222025-833%22+OR+%22Priority+1+%26+Priority+2+Transformer+Stations+Load+Increase%22%29) |

### 20. IESO 2025-848 — EPC/PUC TransCo TS - Phase 1A · 695 MW · ON

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | EPC/PUC Transmission — Developer Not Matched To Known List |
| Point of interconnection | not published by the source register |
| Location field | IESO electrical zone "West" (a grid region, not a municipality) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "planning committee" OR "committee of the whole") minutes ("EPC/PUC TransCo TS" OR "EPC/PUC Transmission") Ontario`](https://www.google.com/search?q=%28council+OR+%22planning+committee%22+OR+%22committee+of+the+whole%22%29+minutes+%28%22EPC%2FPUC+TransCo+TS%22+OR+%22EPC%2FPUC+Transmission%22%29+Ontario) |
| Municipal · Zoning & development applications | [`("zoning by-law amendment" OR "official plan amendment" OR "site plan" OR "minister's zoning order") ("EPC/PUC TransCo TS" OR "EPC/PUC Transmission") Ontario`](https://www.google.com/search?q=%28%22zoning+by-law+amendment%22+OR+%22official+plan+amendment%22+OR+%22site+plan%22+OR+%22minister%27s+zoning+order%22%29+%28%22EPC%2FPUC+TransCo+TS%22+OR+%22EPC%2FPUC+Transmission%22%29+Ontario) |
| Environmental / regulator · Environmental registry / permits | [`site:ero.ontario.ca ("EPC/PUC TransCo TS" OR "EPC/PUC Transmission") Ontario`](https://www.google.com/search?q=site%3Aero.ontario.ca+%28%22EPC%2FPUC+TransCo+TS%22+OR+%22EPC%2FPUC+Transmission%22%29+Ontario) |
| Environmental / regulator · Utility-commission / siting filings | [`site:oeb.ca ("EPC/PUC TransCo TS" OR "EPC/PUC Transmission") Ontario`](https://www.google.com/search?q=site%3Aoeb.ca+%28%22EPC%2FPUC+TransCo+TS%22+OR+%22EPC%2FPUC+Transmission%22%29+Ontario) |
| Substation · RTO / ISO documents | [`site:ieso.ca ("2025-848" OR "EPC/PUC TransCo TS - Phase 1A")`](https://www.google.com/search?q=site%3Aieso.ca+%28%222025-848%22+OR+%22EPC%2FPUC+TransCo+TS+-+Phase+1A%22%29) |

### 21. MISO S1156 — (no project name published) · 632 MW · TX

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | county not published, Texas |
| Transmission owner | ENTERGY TEXAS, INC. |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes Texas ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+Texas+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") Texas ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+Texas+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`site:tceq.texas.gov Texas ("data center" OR "large load")`](https://www.google.com/search?q=site%3Atceq.texas.gov+Texas+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`site:puc.texas.gov Texas ("data center" OR "large load")`](https://www.google.com/search?q=site%3Apuc.texas.gov+Texas+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1156`](https://www.google.com/search?q=site%3Amisoenergy.org+S1156) |
| Substation · Transmission-owner filings | [`"ENTERGY TEXAS, INC." ("large load" OR "data center" OR interconnection OR substation) Texas`](https://www.google.com/search?q=%22ENTERGY+TEXAS%2C+INC.%22+%28%22large+load%22+OR+%22data+center%22+OR+interconnection+OR+substation%29+Texas) |

### 22. MISO S1161 — (no project name published) · 625 MW · AR

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | county not published, Arkansas |
| Transmission owner | ENTERGY ARKANSAS, LLC |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes Arkansas ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+Arkansas+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") Arkansas ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+Arkansas+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`("Arkansas Division of Environmental Quality" OR ADEQ) ("air permit" OR "construction permit" OR "environmental assessment") Arkansas ("data center" OR "large load")`](https://www.google.com/search?q=%28%22Arkansas+Division+of+Environmental+Quality%22+OR+ADEQ%29+%28%22air+permit%22+OR+%22construction+permit%22+OR+%22environmental+assessment%22%29+Arkansas+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`"Arkansas Public Service Commission" ("certificate of public convenience" OR siting OR "large load") Arkansas ("data center" OR "large load")`](https://www.google.com/search?q=%22Arkansas+Public+Service+Commission%22+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+Arkansas+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1161`](https://www.google.com/search?q=site%3Amisoenergy.org+S1161) |
| Substation · Transmission-owner filings | [`"ENTERGY ARKANSAS, LLC" ("large load" OR "data center" OR interconnection OR substation) Arkansas`](https://www.google.com/search?q=%22ENTERGY+ARKANSAS%2C+LLC%22+%28%22large+load%22+OR+%22data+center%22+OR+interconnection+OR+substation%29+Arkansas) |

### 23. NYISO 1765 — Micron Fab 3 · 606 MW · NY

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | Eldo Varghese — Developer Not Matched To Known List |
| Point of interconnection | National Grid - Clay Substation |
| Location field | county field "Onondaga", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("Micron Fab 3" OR "Eldo Varghese") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22Micron+Fab+3%22+OR+%22Eldo+Varghese%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("Micron Fab 3" OR "Eldo Varghese") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22Micron+Fab+3%22+OR+%22Eldo+Varghese%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("Micron Fab 3" OR "Eldo Varghese") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22Micron+Fab+3%22+OR+%22Eldo+Varghese%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("Micron Fab 3" OR "Eldo Varghese") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22Micron+Fab+3%22+OR+%22Eldo+Varghese%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"National Grid - Clay Substation" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22National+Grid+-+Clay+Substation%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1765" OR Q1765 OR "Queue #1765" OR 1765 OR "Micron Fab 3")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231765%22+OR+Q1765+OR+%22Queue+%231765%22+OR+1765+OR+%22Micron+Fab+3%22%29) |

### 24. NYISO 1627 — Micron Fab 2 · 576 MW · NY

| | |
|---|---|
| Status (as published) | Facilities Study |
| Developer (as published) | Micron New York Semiconductor Manufacturing LLC — Developer Not Matched To Known List |
| Point of interconnection | National Grid Clay 345 kV Substation |
| Location field | county field "Onondaga", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("Micron Fab 2" OR "Micron New York Semiconductor Manufacturing") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22Micron+Fab+2%22+OR+%22Micron+New+York+Semiconductor+Manufacturing%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("Micron Fab 2" OR "Micron New York Semiconductor Manufacturing") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22Micron+Fab+2%22+OR+%22Micron+New+York+Semiconductor+Manufacturing%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("Micron Fab 2" OR "Micron New York Semiconductor Manufacturing") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22Micron+Fab+2%22+OR+%22Micron+New+York+Semiconductor+Manufacturing%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("Micron Fab 2" OR "Micron New York Semiconductor Manufacturing") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22Micron+Fab+2%22+OR+%22Micron+New+York+Semiconductor+Manufacturing%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"National Grid Clay 345 kV Substation" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22National+Grid+Clay+345+kV+Substation%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1627" OR Q1627 OR "Queue #1627" OR 1627 OR "Micron Fab 2")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231627%22+OR+Q1627+OR+%22Queue+%231627%22+OR+1627+OR+%22Micron+Fab+2%22%29) |

### 25. IESO 2025-863 — Essex Transmission - Phase 1B · 550 MW · ON

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | Essex Transmission LP — Developer Not Matched To Known List |
| Point of interconnection | not published by the source register |
| Location field | IESO electrical zone "West" (a grid region, not a municipality) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "planning committee" OR "committee of the whole") minutes "Essex Transmission" Ontario`](https://www.google.com/search?q=%28council+OR+%22planning+committee%22+OR+%22committee+of+the+whole%22%29+minutes+%22Essex+Transmission%22+Ontario) |
| Municipal · Zoning & development applications | [`("zoning by-law amendment" OR "official plan amendment" OR "site plan" OR "minister's zoning order") "Essex Transmission" Ontario`](https://www.google.com/search?q=%28%22zoning+by-law+amendment%22+OR+%22official+plan+amendment%22+OR+%22site+plan%22+OR+%22minister%27s+zoning+order%22%29+%22Essex+Transmission%22+Ontario) |
| Environmental / regulator · Environmental registry / permits | [`site:ero.ontario.ca "Essex Transmission" Ontario`](https://www.google.com/search?q=site%3Aero.ontario.ca+%22Essex+Transmission%22+Ontario) |
| Environmental / regulator · Utility-commission / siting filings | [`site:oeb.ca "Essex Transmission" Ontario`](https://www.google.com/search?q=site%3Aoeb.ca+%22Essex+Transmission%22+Ontario) |
| Substation · RTO / ISO documents | [`site:ieso.ca ("2025-863" OR "Essex Transmission - Phase 1B")`](https://www.google.com/search?q=site%3Aieso.ca+%28%222025-863%22+OR+%22Essex+Transmission+-+Phase+1B%22%29) |

### 26. MISO S1157 — (no project name published) · 534 MW · TX

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | county not published, Texas |
| Transmission owner | ENTERGY TEXAS, INC. |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes Texas ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+Texas+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") Texas ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+Texas+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`site:tceq.texas.gov Texas ("data center" OR "large load")`](https://www.google.com/search?q=site%3Atceq.texas.gov+Texas+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`site:puc.texas.gov Texas ("data center" OR "large load")`](https://www.google.com/search?q=site%3Apuc.texas.gov+Texas+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1157`](https://www.google.com/search?q=site%3Amisoenergy.org+S1157) |
| Substation · Transmission-owner filings | [`"ENTERGY TEXAS, INC." ("large load" OR "data center" OR interconnection OR substation) Texas`](https://www.google.com/search?q=%22ENTERGY+TEXAS%2C+INC.%22+%28%22large+load%22+OR+%22data+center%22+OR+interconnection+OR+substation%29+Texas) |

### 27. AESO P2946 — Genesee Data Center 2 MPC Load · 500 MW · AB

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "Wabamun" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "Genesee Data Center 2" Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22Genesee+Data+Center+2%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "Genesee Data Center 2" Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22Genesee+Data+Center+2%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "Genesee Data Center 2" Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22Genesee+Data+Center+2%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "Genesee Data Center 2" Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22Genesee+Data+Center+2%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P2946 OR "Genesee Data Center 2 MPC Load")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P2946+OR+%22Genesee+Data+Center+2+MPC+Load%22%29) |

### 28. MISO J1488 — (no project name published) · 500 MW · MO

| | |
|---|---|
| Status (as published) | IA in Progress |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | McCredie - Montgomery 345 kV Line Tap |
| Location field | county field "Randolph", Missouri |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "McCredie - Montgomery 345 kV Line Tap" "Randolph" County Missouri ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22McCredie+-+Montgomery+345+kV+Line+Tap%22+%22Randolph%22+County+Missouri+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "McCredie - Montgomery 345 kV Line Tap" "Randolph" County Missouri ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22McCredie+-+Montgomery+345+kV+Line+Tap%22+%22Randolph%22+County+Missouri+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`site:dnr.mo.gov "Randolph" County Missouri ("data center" OR "large load")`](https://www.google.com/search?q=site%3Adnr.mo.gov+%22Randolph%22+County+Missouri+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`site:psc.mo.gov "McCredie - Montgomery 345 kV Line Tap" "Randolph" County Missouri ("data center" OR "large load")`](https://www.google.com/search?q=site%3Apsc.mo.gov+%22McCredie+-+Montgomery+345+kV+Line+Tap%22+%22Randolph%22+County+Missouri+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"McCredie - Montgomery 345 kV Line Tap" (substation OR interconnection OR "facilities study" OR "system impact study") Missouri`](https://www.google.com/search?q=%22McCredie+-+Montgomery+345+kV+Line+Tap%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Missouri) |
| Substation · RTO / ISO documents | [`site:misoenergy.org J1488`](https://www.google.com/search?q=site%3Amisoenergy.org+J1488) |

### 29. NYISO 1741 — North East Data LLC Data Center · 500 MW · NY

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | North East Data LLC — Developer Not Matched To Known List |
| Point of interconnection | 230kV lines 77 and 78 |
| Location field | county field "Niagara", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("North East Data LLC Data Center" OR "North East Data") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22North+East+Data+LLC+Data+Center%22+OR+%22North+East+Data%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("North East Data LLC Data Center" OR "North East Data") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22North+East+Data+LLC+Data+Center%22+OR+%22North+East+Data%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("North East Data LLC Data Center" OR "North East Data") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22North+East+Data+LLC+Data+Center%22+OR+%22North+East+Data%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("North East Data LLC Data Center" OR "North East Data") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22North+East+Data+LLC+Data+Center%22+OR+%22North+East+Data%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"230kV lines 77 and 78" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22230kV+lines+77+and+78%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1741" OR Q1741 OR "Queue #1741" OR 1741 OR "North East Data LLC Data Center")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231741%22+OR+Q1741+OR+%22Queue+%231741%22+OR+1741+OR+%22North+East+Data+LLC+Data+Center%22%29) |

### 30. SPP GEN-2024-013 — (no project name published) · 496 MW · OK

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | Norman Hills 345 kV |
| Location field | county field "McClain", Oklahoma |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "Norman Hills 345 kV" "McClain" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22Norman+Hills+345+kV%22+%22McClain%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "Norman Hills 345 kV" "McClain" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22Norman+Hills+345+kV%22+%22McClain%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`("Oklahoma Department of Environmental Quality" OR "Oklahoma DEQ") ("air permit" OR "construction permit" OR "environmental assessment") "McClain" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%28%22Oklahoma+Department+of+Environmental+Quality%22+OR+%22Oklahoma+DEQ%22%29+%28%22air+permit%22+OR+%22construction+permit%22+OR+%22environmental+assessment%22%29+%22McClain%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`"Oklahoma Corporation Commission" ("certificate of public convenience" OR siting OR "large load") "Norman Hills 345 kV" "McClain" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%22Oklahoma+Corporation+Commission%22+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+%22Norman+Hills+345+kV%22+%22McClain%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"Norman Hills 345 kV" (substation OR interconnection OR "facilities study" OR "system impact study") Oklahoma`](https://www.google.com/search?q=%22Norman+Hills+345+kV%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Oklahoma) |
| Substation · RTO / ISO documents | [`site:spp.org "GEN-2024-013"`](https://www.google.com/search?q=site%3Aspp.org+%22GEN-2024-013%22) |

### 31. SPP GEN-2024-GR1 — (no project name published) · 492 MW · OK

| | |
|---|---|
| Status (as published) | IA in Progress |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | Horseshoe Lake 138kV |
| Location field | county field "Harrah", Oklahoma |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "Horseshoe Lake 138kV" "Harrah" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22Horseshoe+Lake+138kV%22+%22Harrah%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "Horseshoe Lake 138kV" "Harrah" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22Horseshoe+Lake+138kV%22+%22Harrah%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`("Oklahoma Department of Environmental Quality" OR "Oklahoma DEQ") ("air permit" OR "construction permit" OR "environmental assessment") "Harrah" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%28%22Oklahoma+Department+of+Environmental+Quality%22+OR+%22Oklahoma+DEQ%22%29+%28%22air+permit%22+OR+%22construction+permit%22+OR+%22environmental+assessment%22%29+%22Harrah%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`"Oklahoma Corporation Commission" ("certificate of public convenience" OR siting OR "large load") "Horseshoe Lake 138kV" "Harrah" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%22Oklahoma+Corporation+Commission%22+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+%22Horseshoe+Lake+138kV%22+%22Harrah%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"Horseshoe Lake 138kV" (substation OR interconnection OR "facilities study" OR "system impact study") Oklahoma`](https://www.google.com/search?q=%22Horseshoe+Lake+138kV%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Oklahoma) |
| Substation · RTO / ISO documents | [`site:spp.org "GEN-2024-GR1"`](https://www.google.com/search?q=site%3Aspp.org+%22GEN-2024-GR1%22) |

### 32. NYISO 1536 — White Pine Phase 1 · 480 MW · NY

| | |
|---|---|
| Status (as published) | IA in Progress |
| Developer (as published) | Micron New York Semiconductor Manufacturing LLC — Developer Not Matched To Known List |
| Point of interconnection | Clay 345 kV Substation |
| Location field | county field "Onondaga", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("White Pine" OR "Micron New York Semiconductor Manufacturing") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22White+Pine%22+OR+%22Micron+New+York+Semiconductor+Manufacturing%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("White Pine" OR "Micron New York Semiconductor Manufacturing") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22White+Pine%22+OR+%22Micron+New+York+Semiconductor+Manufacturing%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("White Pine" OR "Micron New York Semiconductor Manufacturing") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22White+Pine%22+OR+%22Micron+New+York+Semiconductor+Manufacturing%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("White Pine" OR "Micron New York Semiconductor Manufacturing") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22White+Pine%22+OR+%22Micron+New+York+Semiconductor+Manufacturing%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"Clay 345 kV Substation" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22Clay+345+kV+Substation%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1536" OR Q1536 OR "Queue #1536" OR 1536 OR "White Pine Phase 1")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231536%22+OR+Q1536+OR+%22Queue+%231536%22+OR+1536+OR+%22White+Pine+Phase+1%22%29) |

### 33. NYISO 1730 — Arsenal Data Site 1000 · 467 MW · NY

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | Arconic Corporation — Developer Not Matched To Known List |
| Point of interconnection | Haverstock to Adirondak 345kV line HA-1 |
| Location field | county field "St Lawrence", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("Arsenal Data Site 1000" OR "Arconic") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22Arsenal+Data+Site+1000%22+OR+%22Arconic%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("Arsenal Data Site 1000" OR "Arconic") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22Arsenal+Data+Site+1000%22+OR+%22Arconic%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("Arsenal Data Site 1000" OR "Arconic") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22Arsenal+Data+Site+1000%22+OR+%22Arconic%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("Arsenal Data Site 1000" OR "Arconic") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22Arsenal+Data+Site+1000%22+OR+%22Arconic%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"Haverstock to Adirondak 345kV line HA-1" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22Haverstock+to+Adirondak+345kV+line+HA-1%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1730" OR Q1730 OR "Queue #1730" OR 1730 OR "Arsenal Data Site 1000")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231730%22+OR+Q1730+OR+%22Queue+%231730%22+OR+1730+OR+%22Arsenal+Data+Site+1000%22%29) |

### 34. AESO P3095 — Keephills Data Centre Phase 2 · 466 MW · AB

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "Wabamun" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "Keephills Data Centre" Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22Keephills+Data+Centre%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "Keephills Data Centre" Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22Keephills+Data+Centre%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "Keephills Data Centre" Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22Keephills+Data+Centre%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "Keephills Data Centre" Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22Keephills+Data+Centre%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P3095 OR "Keephills Data Centre Phase 2")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P3095+OR+%22Keephills+Data+Centre+Phase+2%22%29) |

### 35. AESO P3112 — North Calgary Three Data Centre MPC Load · 450 MW · AB

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "Calgary" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "North Calgary Three Data Centre" Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22North+Calgary+Three+Data+Centre%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "North Calgary Three Data Centre" Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22North+Calgary+Three+Data+Centre%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "North Calgary Three Data Centre" Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22North+Calgary+Three+Data+Centre%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "North Calgary Three Data Centre" Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22North+Calgary+Three+Data+Centre%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P3112 OR "North Calgary Three Data Centre MPC Load")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P3112+OR+%22North+Calgary+Three+Data+Centre+MPC+Load%22%29) |

### 36. IESO 2026-899 — Leamington Area Load Increase · 447 MW · ON

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | HYDRO ONE NETWORKS INC. — Developer Not Matched To Known List |
| Point of interconnection | not published by the source register |
| Location field | IESO electrical zone "West" (a grid region, not a municipality) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "planning committee" OR "committee of the whole") minutes ("Leamington Area" OR "HYDRO ONE NETWORKS") Ontario`](https://www.google.com/search?q=%28council+OR+%22planning+committee%22+OR+%22committee+of+the+whole%22%29+minutes+%28%22Leamington+Area%22+OR+%22HYDRO+ONE+NETWORKS%22%29+Ontario) |
| Municipal · Zoning & development applications | [`("zoning by-law amendment" OR "official plan amendment" OR "site plan" OR "minister's zoning order") ("Leamington Area" OR "HYDRO ONE NETWORKS") Ontario`](https://www.google.com/search?q=%28%22zoning+by-law+amendment%22+OR+%22official+plan+amendment%22+OR+%22site+plan%22+OR+%22minister%27s+zoning+order%22%29+%28%22Leamington+Area%22+OR+%22HYDRO+ONE+NETWORKS%22%29+Ontario) |
| Environmental / regulator · Environmental registry / permits | [`site:ero.ontario.ca ("Leamington Area" OR "HYDRO ONE NETWORKS") Ontario`](https://www.google.com/search?q=site%3Aero.ontario.ca+%28%22Leamington+Area%22+OR+%22HYDRO+ONE+NETWORKS%22%29+Ontario) |
| Environmental / regulator · Utility-commission / siting filings | [`site:oeb.ca ("Leamington Area" OR "HYDRO ONE NETWORKS") Ontario`](https://www.google.com/search?q=site%3Aoeb.ca+%28%22Leamington+Area%22+OR+%22HYDRO+ONE+NETWORKS%22%29+Ontario) |
| Substation · RTO / ISO documents | [`site:ieso.ca ("2026-899" OR "Leamington Area Load Increase")`](https://www.google.com/search?q=site%3Aieso.ca+%28%222026-899%22+OR+%22Leamington+Area+Load+Increase%22%29) |

### 37. NYISO 0979 — North Country Data Center · 435 MW · NY

| | |
|---|---|
| Status (as published) | IA in Progress |
| Developer (as published) | North Country Data Center — Developer Not Matched To Known List |
| Point of interconnection | Reynolds 115kV |
| Location field | county field "St. Lawrence", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes "North Country Data Center" New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%22North+Country+Data+Center%22+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) "North Country Data Center" New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%22North+Country+Data+Center%22+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov "North Country Data Center" New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%22North+Country+Data+Center%22+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov "North Country Data Center" New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%22North+Country+Data+Center%22+New+York) |
| Substation · Substation / point of interconnection | [`"Reynolds 115kV" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22Reynolds+115kV%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#0979" OR Q0979 OR "Queue #0979" OR 0979 OR "North Country Data Center")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%230979%22+OR+Q0979+OR+%22Queue+%230979%22+OR+0979+OR+%22North+Country+Data+Center%22%29) |

### 38. AESO P3136 — Sundance Data MPC Load · 401 MW · AB

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "Wabamun" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "Sundance Data" Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22Sundance+Data%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "Sundance Data" Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22Sundance+Data%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "Sundance Data" Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22Sundance+Data%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "Sundance Data" Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22Sundance+Data%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P3136 OR "Sundance Data MPC Load")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P3136+OR+%22Sundance+Data+MPC+Load%22%29) |

### 39. AESO P2926 — Beacon Foothills A.I. Hub Load · 400 MW · AB

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "High River" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "Beacon Foothills A.I. Hub" Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22Beacon+Foothills+A.I.+Hub%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "Beacon Foothills A.I. Hub" Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22Beacon+Foothills+A.I.+Hub%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "Beacon Foothills A.I. Hub" Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22Beacon+Foothills+A.I.+Hub%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "Beacon Foothills A.I. Hub" Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22Beacon+Foothills+A.I.+Hub%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P2926 OR "Beacon Foothills A.I. Hub Load")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P2926+OR+%22Beacon+Foothills+A.I.+Hub+Load%22%29) |

### 40. AESO P2927 — Beacon Harry Smith A.I. Hub Load · 400 MW · AB

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "Wabamun" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "Beacon Harry Smith A.I. Hub" Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22Beacon+Harry+Smith+A.I.+Hub%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "Beacon Harry Smith A.I. Hub" Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22Beacon+Harry+Smith+A.I.+Hub%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "Beacon Harry Smith A.I. Hub" Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22Beacon+Harry+Smith+A.I.+Hub%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "Beacon Harry Smith A.I. Hub" Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22Beacon+Harry+Smith+A.I.+Hub%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P2927 OR "Beacon Harry Smith A.I. Hub Load")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P2927+OR+%22Beacon+Harry+Smith+A.I.+Hub+Load%22%29) |

### 41. AESO P2928 — Beacon Langdon A.I. Hub Load · 400 MW · AB

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "Calgary" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "Beacon Langdon A.I. Hub" Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22Beacon+Langdon+A.I.+Hub%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "Beacon Langdon A.I. Hub" Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22Beacon+Langdon+A.I.+Hub%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "Beacon Langdon A.I. Hub" Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22Beacon+Langdon+A.I.+Hub%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "Beacon Langdon A.I. Hub" Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22Beacon+Langdon+A.I.+Hub%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P2928 OR "Beacon Langdon A.I. Hub Load")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P2928+OR+%22Beacon+Langdon+A.I.+Hub+Load%22%29) |

### 42. AESO P2934 — Beacon Heartland A.I. Hub Load · 400 MW · AB

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "Fort Saskatchewan" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "Beacon Heartland A.I. Hub" Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22Beacon+Heartland+A.I.+Hub%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "Beacon Heartland A.I. Hub" Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22Beacon+Heartland+A.I.+Hub%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "Beacon Heartland A.I. Hub" Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22Beacon+Heartland+A.I.+Hub%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "Beacon Heartland A.I. Hub" Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22Beacon+Heartland+A.I.+Hub%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P2934 OR "Beacon Heartland A.I. Hub Load")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P2934+OR+%22Beacon+Heartland+A.I.+Hub+Load%22%29) |

### 43. AESO P2935 — Beacon Saunders Lake A.I. Hub Load · 400 MW · AB

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "Edmonton" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "Beacon Saunders Lake A.I. Hub" Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22Beacon+Saunders+Lake+A.I.+Hub%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "Beacon Saunders Lake A.I. Hub" Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22Beacon+Saunders+Lake+A.I.+Hub%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "Beacon Saunders Lake A.I. Hub" Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22Beacon+Saunders+Lake+A.I.+Hub%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "Beacon Saunders Lake A.I. Hub" Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22Beacon+Saunders+Lake+A.I.+Hub%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P2935 OR "Beacon Saunders Lake A.I. Hub Load")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P2935+OR+%22Beacon+Saunders+Lake+A.I.+Hub+Load%22%29) |

### 44. AESO P3106 — Alberta South A.I. Load · 400 MW · AB

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "Lethbridge" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "Alberta South A.I." Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22Alberta+South+A.I.%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "Alberta South A.I." Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22Alberta+South+A.I.%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "Alberta South A.I." Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22Alberta+South+A.I.%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "Alberta South A.I." Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22Alberta+South+A.I.%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P3106 OR "Alberta South A.I. Load")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P3106+OR+%22Alberta+South+A.I.+Load%22%29) |

### 45. AESO P3107 — Chestermere Enterprise A.I. Load · 400 MW · AB

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "Calgary" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "Chestermere Enterprise A.I." Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22Chestermere+Enterprise+A.I.%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "Chestermere Enterprise A.I." Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22Chestermere+Enterprise+A.I.%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "Chestermere Enterprise A.I." Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22Chestermere+Enterprise+A.I.%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "Chestermere Enterprise A.I." Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22Chestermere+Enterprise+A.I.%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P3107 OR "Chestermere Enterprise A.I. Load")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P3107+OR+%22Chestermere+Enterprise+A.I.+Load%22%29) |

### 46. AESO P3175 — Beacon Heartland Data Load · 400 MW · AB

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "Fort Saskatchewan" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "Beacon Heartland Data" Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22Beacon+Heartland+Data%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "Beacon Heartland Data" Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22Beacon+Heartland+Data%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "Beacon Heartland Data" Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22Beacon+Heartland+Data%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "Beacon Heartland Data" Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22Beacon+Heartland+Data%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P3175 OR "Beacon Heartland Data Load")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P3175+OR+%22Beacon+Heartland+Data+Load%22%29) |

### 47. IESO 2026-881 — Algoma Data Center · 400 MW · ON

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | RED JAR ALGOMA DATA CENTER CORP. — Developer Not Matched To Known List |
| Point of interconnection | not published by the source register |
| Location field | IESO electrical zone "Northeast" (a grid region, not a municipality) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "planning committee" OR "committee of the whole") minutes ("Algoma Data Center" OR "RED JAR ALGOMA DATA CENTER") Ontario`](https://www.google.com/search?q=%28council+OR+%22planning+committee%22+OR+%22committee+of+the+whole%22%29+minutes+%28%22Algoma+Data+Center%22+OR+%22RED+JAR+ALGOMA+DATA+CENTER%22%29+Ontario) |
| Municipal · Zoning & development applications | [`("zoning by-law amendment" OR "official plan amendment" OR "site plan" OR "minister's zoning order") ("Algoma Data Center" OR "RED JAR ALGOMA DATA CENTER") Ontario`](https://www.google.com/search?q=%28%22zoning+by-law+amendment%22+OR+%22official+plan+amendment%22+OR+%22site+plan%22+OR+%22minister%27s+zoning+order%22%29+%28%22Algoma+Data+Center%22+OR+%22RED+JAR+ALGOMA+DATA+CENTER%22%29+Ontario) |
| Environmental / regulator · Environmental registry / permits | [`site:ero.ontario.ca ("Algoma Data Center" OR "RED JAR ALGOMA DATA CENTER") Ontario`](https://www.google.com/search?q=site%3Aero.ontario.ca+%28%22Algoma+Data+Center%22+OR+%22RED+JAR+ALGOMA+DATA+CENTER%22%29+Ontario) |
| Environmental / regulator · Utility-commission / siting filings | [`site:oeb.ca ("Algoma Data Center" OR "RED JAR ALGOMA DATA CENTER") Ontario`](https://www.google.com/search?q=site%3Aoeb.ca+%28%22Algoma+Data+Center%22+OR+%22RED+JAR+ALGOMA+DATA+CENTER%22%29+Ontario) |
| Substation · RTO / ISO documents | [`site:ieso.ca ("2026-881" OR "Algoma Data Center")`](https://www.google.com/search?q=site%3Aieso.ca+%28%222026-881%22+OR+%22Algoma+Data+Center%22%29) |

### 48. NYISO 1740 — Incremental Load Request for Remington Factory Redevelopment · 400 MW · NY

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | Turin Management LLC — Developer Not Matched To Known List |
| Point of interconnection | Line 1: 345KV from EDIC to Fraser. Line 2: 345 KV from Marcy to Coopers Corners |
| Location field | county field "Herkimer", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("Incremental Load Request for Remington" OR "Turin Management") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22Incremental+Load+Request+for+Remington%22+OR+%22Turin+Management%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("Incremental Load Request for Remington" OR "Turin Management") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22Incremental+Load+Request+for+Remington%22+OR+%22Turin+Management%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("Incremental Load Request for Remington" OR "Turin Management") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22Incremental+Load+Request+for+Remington%22+OR+%22Turin+Management%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("Incremental Load Request for Remington" OR "Turin Management") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22Incremental+Load+Request+for+Remington%22+OR+%22Turin+Management%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"Line 1: 345KV from EDIC to Fraser. Line 2: 345 KV from Marcy to" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22Line+1%3A+345KV+from+EDIC+to+Fraser.+Line+2%3A+345+KV+from+Marcy+to%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1740" OR Q1740 OR "Queue #1740" OR 1740 OR "Incremental Load Request for Remington Factory Redevelopment")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231740%22+OR+Q1740+OR+%22Queue+%231740%22+OR+1740+OR+%22Incremental+Load+Request+for+Remington+Factory+Redevelopment%22%29) |

### 49. NYISO 1762 — Highwall Data Center · 400 MW · PA

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | Highwall Energy, LLC — Developer Not Matched To Known List |
| Point of interconnection | same POI of Q#1080 (Mineral Basin Solar), connects to NYSEG's L47 line |
| Location field | county field "Clearfield", Pennsylvania |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes ("Highwall Data Center" OR "Highwall Energy") Pennsylvania`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%28%22Highwall+Data+Center%22+OR+%22Highwall+Energy%22%29+Pennsylvania) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") ("Highwall Data Center" OR "Highwall Energy") Pennsylvania`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%28%22Highwall+Data+Center%22+OR+%22Highwall+Energy%22%29+Pennsylvania) |
| Environmental / regulator · Environmental registry / permits | [`site:dep.pa.gov ("Highwall Data Center" OR "Highwall Energy") Pennsylvania`](https://www.google.com/search?q=site%3Adep.pa.gov+%28%22Highwall+Data+Center%22+OR+%22Highwall+Energy%22%29+Pennsylvania) |
| Environmental / regulator · Utility-commission / siting filings | [`site:puc.pa.gov ("Highwall Data Center" OR "Highwall Energy") Pennsylvania`](https://www.google.com/search?q=site%3Apuc.pa.gov+%28%22Highwall+Data+Center%22+OR+%22Highwall+Energy%22%29+Pennsylvania) |
| Substation · Substation / point of interconnection | [`"same POI of Q#1080 (Mineral Basin Solar), connects to NYSEG's L47 line" (substation OR interconnection OR "facilities study" OR "system impact study") Pennsylvania`](https://www.google.com/search?q=%22same+POI+of+Q%231080+%28Mineral+Basin+Solar%29%2C+connects+to+NYSEG%27s+L47+line%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Pennsylvania) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1762" OR Q1762 OR "Queue #1762" OR 1762 OR "Highwall Data Center")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231762%22+OR+Q1762+OR+%22Queue+%231762%22+OR+1762+OR+%22Highwall+Data+Center%22%29) |

### 50. SPP GEN-2025-SR9 — (no project name published) · 400 MW · OK

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | Muskogee 345 KV Substation |
| Location field | county field "Fort Gibson", Oklahoma |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "Muskogee 345 KV Substation" "Fort Gibson" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22Muskogee+345+KV+Substation%22+%22Fort+Gibson%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "Muskogee 345 KV Substation" "Fort Gibson" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22Muskogee+345+KV+Substation%22+%22Fort+Gibson%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`("Oklahoma Department of Environmental Quality" OR "Oklahoma DEQ") ("air permit" OR "construction permit" OR "environmental assessment") "Fort Gibson" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%28%22Oklahoma+Department+of+Environmental+Quality%22+OR+%22Oklahoma+DEQ%22%29+%28%22air+permit%22+OR+%22construction+permit%22+OR+%22environmental+assessment%22%29+%22Fort+Gibson%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`"Oklahoma Corporation Commission" ("certificate of public convenience" OR siting OR "large load") "Muskogee 345 KV Substation" "Fort Gibson" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%22Oklahoma+Corporation+Commission%22+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+%22Muskogee+345+KV+Substation%22+%22Fort+Gibson%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"Muskogee 345 KV Substation" (substation OR interconnection OR "facilities study" OR "system impact study") Oklahoma`](https://www.google.com/search?q=%22Muskogee+345+KV+Substation%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Oklahoma) |
| Substation · RTO / ISO documents | [`site:spp.org "GEN-2025-SR9"`](https://www.google.com/search?q=site%3Aspp.org+%22GEN-2025-SR9%22) |

### 51. MISO S1162 — (no project name published) · 390 MW · AR

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | county not published, Arkansas |
| Transmission owner | ENTERGY ARKANSAS, LLC |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes Arkansas ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+Arkansas+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") Arkansas ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+Arkansas+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`("Arkansas Division of Environmental Quality" OR ADEQ) ("air permit" OR "construction permit" OR "environmental assessment") Arkansas ("data center" OR "large load")`](https://www.google.com/search?q=%28%22Arkansas+Division+of+Environmental+Quality%22+OR+ADEQ%29+%28%22air+permit%22+OR+%22construction+permit%22+OR+%22environmental+assessment%22%29+Arkansas+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`"Arkansas Public Service Commission" ("certificate of public convenience" OR siting OR "large load") Arkansas ("data center" OR "large load")`](https://www.google.com/search?q=%22Arkansas+Public+Service+Commission%22+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+Arkansas+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1162`](https://www.google.com/search?q=site%3Amisoenergy.org+S1162) |
| Substation · Transmission-owner filings | [`"ENTERGY ARKANSAS, LLC" ("large load" OR "data center" OR interconnection OR substation) Arkansas`](https://www.google.com/search?q=%22ENTERGY+ARKANSAS%2C+LLC%22+%28%22large+load%22+OR+%22data+center%22+OR+interconnection+OR+substation%29+Arkansas) |

### 52. NYISO 1763 — Patriot Forge · 350 MW · PA

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | Patriot Forge PA, LLC — Developer Not Matched To Known List |
| Point of interconnection | Tap on the NYSEG 345 kV Line 47 (Homer City -Mainesburg 345 kV) |
| Location field | county field "Tioga", Pennsylvania |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes ("Patriot Forge" OR "Patriot Forge PA") Pennsylvania`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%28%22Patriot+Forge%22+OR+%22Patriot+Forge+PA%22%29+Pennsylvania) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") ("Patriot Forge" OR "Patriot Forge PA") Pennsylvania`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%28%22Patriot+Forge%22+OR+%22Patriot+Forge+PA%22%29+Pennsylvania) |
| Environmental / regulator · Environmental registry / permits | [`site:dep.pa.gov ("Patriot Forge" OR "Patriot Forge PA") Pennsylvania`](https://www.google.com/search?q=site%3Adep.pa.gov+%28%22Patriot+Forge%22+OR+%22Patriot+Forge+PA%22%29+Pennsylvania) |
| Environmental / regulator · Utility-commission / siting filings | [`site:puc.pa.gov ("Patriot Forge" OR "Patriot Forge PA") Pennsylvania`](https://www.google.com/search?q=site%3Apuc.pa.gov+%28%22Patriot+Forge%22+OR+%22Patriot+Forge+PA%22%29+Pennsylvania) |
| Substation · Substation / point of interconnection | [`"Tap on the NYSEG 345 kV Line 47 (Homer City -Mainesburg 345 kV)" (substation OR interconnection OR "facilities study" OR "system impact study") Pennsylvania`](https://www.google.com/search?q=%22Tap+on+the+NYSEG+345+kV+Line+47+%28Homer+City+-Mainesburg+345+kV%29%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Pennsylvania) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1763" OR Q1763 OR "Queue #1763" OR 1763 OR "Patriot Forge")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231763%22+OR+Q1763+OR+%22Queue+%231763%22+OR+1763+OR+%22Patriot+Forge%22%29) |

### 53. AESO P2958 — Hydrogen Canada MPC Load · 320 MW · AB

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "Fort Saskatchewan" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "Hydrogen Canada" Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22Hydrogen+Canada%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "Hydrogen Canada" Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22Hydrogen+Canada%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "Hydrogen Canada" Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22Hydrogen+Canada%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "Hydrogen Canada" Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22Hydrogen+Canada%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P2958 OR "Hydrogen Canada MPC Load")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P2958+OR+%22Hydrogen+Canada+MPC+Load%22%29) |

### 54. AESO P3110 — Mihta Askiy Data Load · 300 MW · AB

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "Peace River" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "Mihta Askiy Data" Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22Mihta+Askiy+Data%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "Mihta Askiy Data" Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22Mihta+Askiy+Data%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "Mihta Askiy Data" Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22Mihta+Askiy+Data%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "Mihta Askiy Data" Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22Mihta+Askiy+Data%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P3110 OR "Mihta Askiy Data Load")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P3110+OR+%22Mihta+Askiy+Data+Load%22%29) |

### 55. AESO P3156 — High Plains East Industrial Park · 300 MW · AB

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "Calgary" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "High Plains East Industrial Park" Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22High+Plains+East+Industrial+Park%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "High Plains East Industrial Park" Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22High+Plains+East+Industrial+Park%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "High Plains East Industrial Park" Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22High+Plains+East+Industrial+Park%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "High Plains East Industrial Park" Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22High+Plains+East+Industrial+Park%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P3156 OR "High Plains East Industrial Park")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P3156+OR+%22High+Plains+East+Industrial+Park%22%29) |

### 56. IESO 2024-819 — Industrial Production Facility · 300 MW · ON

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | Vianode Canada Inc. — Developer Not Matched To Known List |
| Point of interconnection | not published by the source register |
| Location field | IESO electrical zone "Southwest" (a grid region, not a municipality) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "planning committee" OR "committee of the whole") minutes ("Industrial Production Facility" OR "Vianode Canada") Ontario`](https://www.google.com/search?q=%28council+OR+%22planning+committee%22+OR+%22committee+of+the+whole%22%29+minutes+%28%22Industrial+Production+Facility%22+OR+%22Vianode+Canada%22%29+Ontario) |
| Municipal · Zoning & development applications | [`("zoning by-law amendment" OR "official plan amendment" OR "site plan" OR "minister's zoning order") ("Industrial Production Facility" OR "Vianode Canada") Ontario`](https://www.google.com/search?q=%28%22zoning+by-law+amendment%22+OR+%22official+plan+amendment%22+OR+%22site+plan%22+OR+%22minister%27s+zoning+order%22%29+%28%22Industrial+Production+Facility%22+OR+%22Vianode+Canada%22%29+Ontario) |
| Environmental / regulator · Environmental registry / permits | [`site:ero.ontario.ca ("Industrial Production Facility" OR "Vianode Canada") Ontario`](https://www.google.com/search?q=site%3Aero.ontario.ca+%28%22Industrial+Production+Facility%22+OR+%22Vianode+Canada%22%29+Ontario) |
| Environmental / regulator · Utility-commission / siting filings | [`site:oeb.ca ("Industrial Production Facility" OR "Vianode Canada") Ontario`](https://www.google.com/search?q=site%3Aoeb.ca+%28%22Industrial+Production+Facility%22+OR+%22Vianode+Canada%22%29+Ontario) |
| Substation · RTO / ISO documents | [`site:ieso.ca ("2024-819" OR "Industrial Production Facility")`](https://www.google.com/search?q=site%3Aieso.ca+%28%222024-819%22+OR+%22Industrial+Production+Facility%22%29) |

### 57. IESO 2026-872 — Moldenhauer Energy 1 & 2 · 300 MW · ON

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | 1001490547 Ontario Inc. (Moldenhauer) — Developer Not Matched To Known List |
| Point of interconnection | not published by the source register |
| Location field | IESO electrical zone "Toronto" (a grid region, not a municipality) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "planning committee" OR "committee of the whole") minutes ("Moldenhauer Energy 1 & 2" OR "1001490547 Ontario Inc. (Moldenhauer)") Ontario`](https://www.google.com/search?q=%28council+OR+%22planning+committee%22+OR+%22committee+of+the+whole%22%29+minutes+%28%22Moldenhauer+Energy+1+%26+2%22+OR+%221001490547+Ontario+Inc.+%28Moldenhauer%29%22%29+Ontario) |
| Municipal · Zoning & development applications | [`("zoning by-law amendment" OR "official plan amendment" OR "site plan" OR "minister's zoning order") ("Moldenhauer Energy 1 & 2" OR "1001490547 Ontario Inc. (Moldenhauer)") Ontario`](https://www.google.com/search?q=%28%22zoning+by-law+amendment%22+OR+%22official+plan+amendment%22+OR+%22site+plan%22+OR+%22minister%27s+zoning+order%22%29+%28%22Moldenhauer+Energy+1+%26+2%22+OR+%221001490547+Ontario+Inc.+%28Moldenhauer%29%22%29+Ontario) |
| Environmental / regulator · Environmental registry / permits | [`site:ero.ontario.ca ("Moldenhauer Energy 1 & 2" OR "1001490547 Ontario Inc. (Moldenhauer)") Ontario`](https://www.google.com/search?q=site%3Aero.ontario.ca+%28%22Moldenhauer+Energy+1+%26+2%22+OR+%221001490547+Ontario+Inc.+%28Moldenhauer%29%22%29+Ontario) |
| Environmental / regulator · Utility-commission / siting filings | [`site:oeb.ca ("Moldenhauer Energy 1 & 2" OR "1001490547 Ontario Inc. (Moldenhauer)") Ontario`](https://www.google.com/search?q=site%3Aoeb.ca+%28%22Moldenhauer+Energy+1+%26+2%22+OR+%221001490547+Ontario+Inc.+%28Moldenhauer%29%22%29+Ontario) |
| Substation · RTO / ISO documents | [`site:ieso.ca ("2026-872" OR "Moldenhauer Energy 1 & 2")`](https://www.google.com/search?q=site%3Aieso.ca+%28%222026-872%22+OR+%22Moldenhauer+Energy+1+%26+2%22%29) |

### 58. MISO S1054 — (no project name published) · 300 MW · MN

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | Lakefield Junction 345kV |
| Location field | county field "Cottonwood", Minnesota |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "Lakefield Junction 345kV" "Cottonwood" County Minnesota ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22Lakefield+Junction+345kV%22+%22Cottonwood%22+County+Minnesota+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "Lakefield Junction 345kV" "Cottonwood" County Minnesota ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22Lakefield+Junction+345kV%22+%22Cottonwood%22+County+Minnesota+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`("Minnesota Pollution Control Agency" OR MPCA) ("air permit" OR "construction permit" OR "environmental assessment") "Cottonwood" County Minnesota ("data center" OR "large load")`](https://www.google.com/search?q=%28%22Minnesota+Pollution+Control+Agency%22+OR+MPCA%29+%28%22air+permit%22+OR+%22construction+permit%22+OR+%22environmental+assessment%22%29+%22Cottonwood%22+County+Minnesota+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`"Minnesota Public Utilities Commission" ("certificate of public convenience" OR siting OR "large load") "Lakefield Junction 345kV" "Cottonwood" County Minnesota ("data center" OR "large load")`](https://www.google.com/search?q=%22Minnesota+Public+Utilities+Commission%22+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+%22Lakefield+Junction+345kV%22+%22Cottonwood%22+County+Minnesota+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"Lakefield Junction 345kV" (substation OR interconnection OR "facilities study" OR "system impact study") Minnesota`](https://www.google.com/search?q=%22Lakefield+Junction+345kV%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Minnesota) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1054`](https://www.google.com/search?q=site%3Amisoenergy.org+S1054) |

### 59. NYISO 0580 — WNY STAMP · 300 MW · NY

| | |
|---|---|
| Status (as published) | IA in Progress |
| Developer (as published) | Genesee County Economic Devel. — Developer Not Matched To Known List |
| Point of interconnection | Kintigh/Niagara - New Rochester 345kV |
| Location field | county field "Genesee", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("WNY STAMP" OR "Genesee County Economic Devel.") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22WNY+STAMP%22+OR+%22Genesee+County+Economic+Devel.%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("WNY STAMP" OR "Genesee County Economic Devel.") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22WNY+STAMP%22+OR+%22Genesee+County+Economic+Devel.%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("WNY STAMP" OR "Genesee County Economic Devel.") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22WNY+STAMP%22+OR+%22Genesee+County+Economic+Devel.%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("WNY STAMP" OR "Genesee County Economic Devel.") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22WNY+STAMP%22+OR+%22Genesee+County+Economic+Devel.%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"Kintigh/Niagara - New Rochester 345kV" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22Kintigh%2FNiagara+-+New+Rochester+345kV%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#0580" OR Q0580 OR "Queue #0580" OR 0580 OR "WNY STAMP")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%230580%22+OR+Q0580+OR+%22Queue+%230580%22+OR+0580+OR+%22WNY+STAMP%22%29) |

### 60. NYISO 1484 — 580 STAMP load increase · 300 MW · NY

| | |
|---|---|
| Status (as published) | IA in Progress |
| Developer (as published) | GCEDC — Developer Not Matched To Known List |
| Point of interconnection | 115 kv STAMP substation |
| Location field | county field "Genesee", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("580 STAMP" OR "GCEDC") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22580+STAMP%22+OR+%22GCEDC%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("580 STAMP" OR "GCEDC") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22580+STAMP%22+OR+%22GCEDC%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("580 STAMP" OR "GCEDC") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22580+STAMP%22+OR+%22GCEDC%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("580 STAMP" OR "GCEDC") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22580+STAMP%22+OR+%22GCEDC%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"115 kv STAMP substation" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22115+kv+STAMP+substation%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1484" OR Q1484 OR "Queue #1484" OR 1484 OR "580 STAMP load increase")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231484%22+OR+Q1484+OR+%22Queue+%231484%22+OR+1484+OR+%22580+STAMP+load+increase%22%29) |

### 61. NYISO 1726 — Data & Technology Campus · 300 MW · NY

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | Riverview Innovation & Technology Campus, Inc. — Developer Not Matched To Known List |
| Point of interconnection | Huntley - Packard 230kV line 78 |
| Location field | county field "Erie", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("Data & Technology Campus" OR "Riverview Innovation & Technology Campus") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22Data+%26+Technology+Campus%22+OR+%22Riverview+Innovation+%26+Technology+Campus%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("Data & Technology Campus" OR "Riverview Innovation & Technology Campus") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22Data+%26+Technology+Campus%22+OR+%22Riverview+Innovation+%26+Technology+Campus%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("Data & Technology Campus" OR "Riverview Innovation & Technology Campus") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22Data+%26+Technology+Campus%22+OR+%22Riverview+Innovation+%26+Technology+Campus%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("Data & Technology Campus" OR "Riverview Innovation & Technology Campus") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22Data+%26+Technology+Campus%22+OR+%22Riverview+Innovation+%26+Technology+Campus%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"Huntley - Packard 230kV line 78" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22Huntley+-+Packard+230kV+line+78%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1726" OR Q1726 OR "Queue #1726" OR 1726 OR "Data & Technology Campus")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231726%22+OR+Q1726+OR+%22Queue+%231726%22+OR+1726+OR+%22Data+%26+Technology+Campus%22%29) |

### 62. NYISO 1731 — New York State Artificial Intelligence Data Center · 300 MW · NY

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | ZeroC Data Centers, LLC — Developer Not Matched To Known List |
| Point of interconnection | Haverstock-Adirondack 345kV transmission line HA-2 |
| Location field | county field "St. Lawrence", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("New York State Artificial Intelligence Data" OR "ZeroC Data Centers") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22New+York+State+Artificial+Intelligence+Data%22+OR+%22ZeroC+Data+Centers%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("New York State Artificial Intelligence Data" OR "ZeroC Data Centers") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22New+York+State+Artificial+Intelligence+Data%22+OR+%22ZeroC+Data+Centers%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("New York State Artificial Intelligence Data" OR "ZeroC Data Centers") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22New+York+State+Artificial+Intelligence+Data%22+OR+%22ZeroC+Data+Centers%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("New York State Artificial Intelligence Data" OR "ZeroC Data Centers") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22New+York+State+Artificial+Intelligence+Data%22+OR+%22ZeroC+Data+Centers%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"Haverstock-Adirondack 345kV transmission line HA-2" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22Haverstock-Adirondack+345kV+transmission+line+HA-2%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1731" OR Q1731 OR "Queue #1731" OR 1731 OR "New York State Artificial Intelligence Data Center")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231731%22+OR+Q1731+OR+%22Queue+%231731%22+OR+1731+OR+%22New+York+State+Artificial+Intelligence+Data+Center%22%29) |

### 63. NYISO 1736 — Ranalli SuperDC · 270 MW · NY

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | Ranalli SuperDC LLC — Developer Not Matched To Known List |
| Point of interconnection | Clay to Pannell ckts PC-1 and PC-2 |
| Location field | county field "Onondaga", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes "Ranalli SuperDC" New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%22Ranalli+SuperDC%22+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) "Ranalli SuperDC" New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%22Ranalli+SuperDC%22+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov "Ranalli SuperDC" New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%22Ranalli+SuperDC%22+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov "Ranalli SuperDC" New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%22Ranalli+SuperDC%22+New+York) |
| Substation · Substation / point of interconnection | [`"Clay to Pannell ckts PC-1 and PC-2" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22Clay+to+Pannell+ckts+PC-1+and+PC-2%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1736" OR Q1736 OR "Queue #1736" OR 1736 OR "Ranalli SuperDC")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231736%22+OR+Q1736+OR+%22Queue+%231736%22+OR+1736+OR+%22Ranalli+SuperDC%22%29) |

### 64. IESO 2025-857 — Napanee Data Park · 250 MW · ON

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | Napanee Environmental Complex, Inc. — Developer Not Matched To Known List |
| Point of interconnection | not published by the source register |
| Location field | IESO electrical zone "East" (a grid region, not a municipality) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "planning committee" OR "committee of the whole") minutes ("Napanee Data Park" OR "Napanee Environmental Complex") Ontario`](https://www.google.com/search?q=%28council+OR+%22planning+committee%22+OR+%22committee+of+the+whole%22%29+minutes+%28%22Napanee+Data+Park%22+OR+%22Napanee+Environmental+Complex%22%29+Ontario) |
| Municipal · Zoning & development applications | [`("zoning by-law amendment" OR "official plan amendment" OR "site plan" OR "minister's zoning order") ("Napanee Data Park" OR "Napanee Environmental Complex") Ontario`](https://www.google.com/search?q=%28%22zoning+by-law+amendment%22+OR+%22official+plan+amendment%22+OR+%22site+plan%22+OR+%22minister%27s+zoning+order%22%29+%28%22Napanee+Data+Park%22+OR+%22Napanee+Environmental+Complex%22%29+Ontario) |
| Environmental / regulator · Environmental registry / permits | [`site:ero.ontario.ca ("Napanee Data Park" OR "Napanee Environmental Complex") Ontario`](https://www.google.com/search?q=site%3Aero.ontario.ca+%28%22Napanee+Data+Park%22+OR+%22Napanee+Environmental+Complex%22%29+Ontario) |
| Environmental / regulator · Utility-commission / siting filings | [`site:oeb.ca ("Napanee Data Park" OR "Napanee Environmental Complex") Ontario`](https://www.google.com/search?q=site%3Aoeb.ca+%28%22Napanee+Data+Park%22+OR+%22Napanee+Environmental+Complex%22%29+Ontario) |
| Substation · RTO / ISO documents | [`site:ieso.ca ("2025-857" OR "Napanee Data Park")`](https://www.google.com/search?q=site%3Aieso.ca+%28%222025-857%22+OR+%22Napanee+Data+Park%22%29) |

### 65. IESO 2026-871 — Creekside Industrial Load · 250 MW · ON

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | CREEKSIDE INDUSTRIAL LP — Developer Not Matched To Known List |
| Point of interconnection | not published by the source register |
| Location field | IESO electrical zone "Toronto" (a grid region, not a municipality) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "planning committee" OR "committee of the whole") minutes "Creekside Industrial" Ontario`](https://www.google.com/search?q=%28council+OR+%22planning+committee%22+OR+%22committee+of+the+whole%22%29+minutes+%22Creekside+Industrial%22+Ontario) |
| Municipal · Zoning & development applications | [`("zoning by-law amendment" OR "official plan amendment" OR "site plan" OR "minister's zoning order") "Creekside Industrial" Ontario`](https://www.google.com/search?q=%28%22zoning+by-law+amendment%22+OR+%22official+plan+amendment%22+OR+%22site+plan%22+OR+%22minister%27s+zoning+order%22%29+%22Creekside+Industrial%22+Ontario) |
| Environmental / regulator · Environmental registry / permits | [`site:ero.ontario.ca "Creekside Industrial" Ontario`](https://www.google.com/search?q=site%3Aero.ontario.ca+%22Creekside+Industrial%22+Ontario) |
| Environmental / regulator · Utility-commission / siting filings | [`site:oeb.ca "Creekside Industrial" Ontario`](https://www.google.com/search?q=site%3Aoeb.ca+%22Creekside+Industrial%22+Ontario) |
| Substation · RTO / ISO documents | [`site:ieso.ca ("2026-871" OR "Creekside Industrial Load")`](https://www.google.com/search?q=site%3Aieso.ca+%28%222026-871%22+OR+%22Creekside+Industrial+Load%22%29) |

### 66. NYISO 1670 — Lake Mariner Data II · 250 MW · NY

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | Lake Mariner Data LLC — Developer Not Matched To Known List |
| Point of interconnection | Kintigh 345kV Substation |
| Location field | county field "Niagara", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("Lake Mariner Data II" OR "Lake Mariner Data") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22Lake+Mariner+Data+II%22+OR+%22Lake+Mariner+Data%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("Lake Mariner Data II" OR "Lake Mariner Data") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22Lake+Mariner+Data+II%22+OR+%22Lake+Mariner+Data%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("Lake Mariner Data II" OR "Lake Mariner Data") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22Lake+Mariner+Data+II%22+OR+%22Lake+Mariner+Data%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("Lake Mariner Data II" OR "Lake Mariner Data") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22Lake+Mariner+Data+II%22+OR+%22Lake+Mariner+Data%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"Kintigh 345kV Substation" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22Kintigh+345kV+Substation%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1670" OR Q1670 OR "Queue #1670" OR 1670 OR "Lake Mariner Data II")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231670%22+OR+Q1670+OR+%22Queue+%231670%22+OR+1670+OR+%22Lake+Mariner+Data+II%22%29) |

### 67. NYISO 1732 — Wulf Compute Data Center II · 250 MW · NY

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | TeraWulf Brookings LLC — Developer Not Matched To Known List |
| Point of interconnection | Kintigh 345kV sub-station |
| Location field | county field "Niagara", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("Wulf Compute Data Center II" OR "TeraWulf Brookings") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22Wulf+Compute+Data+Center+II%22+OR+%22TeraWulf+Brookings%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("Wulf Compute Data Center II" OR "TeraWulf Brookings") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22Wulf+Compute+Data+Center+II%22+OR+%22TeraWulf+Brookings%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("Wulf Compute Data Center II" OR "TeraWulf Brookings") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22Wulf+Compute+Data+Center+II%22+OR+%22TeraWulf+Brookings%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("Wulf Compute Data Center II" OR "TeraWulf Brookings") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22Wulf+Compute+Data+Center+II%22+OR+%22TeraWulf+Brookings%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"Kintigh 345kV sub-station" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22Kintigh+345kV+sub-station%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1732" OR Q1732 OR "Queue #1732" OR 1732 OR "Wulf Compute Data Center II")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231732%22+OR+Q1732+OR+%22Queue+%231732%22+OR+1732+OR+%22Wulf+Compute+Data+Center+II%22%29) |

### 68. NYISO 1745 — Pontoon Bridge Road Data Center · 250 MW · NY

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | American Data Center Partners LLC — Developer Not Matched To Known List |
| Point of interconnection | Haverstock-Adirondack 345kV transmission lines |
| Location field | county field "St Lawrence", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("Pontoon Bridge Road Data Center" OR "American Data Center Partners") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22Pontoon+Bridge+Road+Data+Center%22+OR+%22American+Data+Center+Partners%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("Pontoon Bridge Road Data Center" OR "American Data Center Partners") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22Pontoon+Bridge+Road+Data+Center%22+OR+%22American+Data+Center+Partners%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("Pontoon Bridge Road Data Center" OR "American Data Center Partners") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22Pontoon+Bridge+Road+Data+Center%22+OR+%22American+Data+Center+Partners%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("Pontoon Bridge Road Data Center" OR "American Data Center Partners") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22Pontoon+Bridge+Road+Data+Center%22+OR+%22American+Data+Center+Partners%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"Haverstock-Adirondack 345kV transmission lines" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22Haverstock-Adirondack+345kV+transmission+lines%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1745" OR Q1745 OR "Queue #1745" OR 1745 OR "Pontoon Bridge Road Data Center")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231745%22+OR+Q1745+OR+%22Queue+%231745%22+OR+1745+OR+%22Pontoon+Bridge+Road+Data+Center%22%29) |

### 69. NYISO 1752 — Broome County Tech Park · 250 MW · NY

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | The Agency — Developer Not Matched To Known List |
| Point of interconnection | 345 kV POI via a loop on the existing Oakdale-Fraser Line 32. The interconnection substation will have a ring bus configuration. |
| Location field | county field "Broome", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("Broome County Tech Park" OR "The Agency") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22Broome+County+Tech+Park%22+OR+%22The+Agency%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("Broome County Tech Park" OR "The Agency") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22Broome+County+Tech+Park%22+OR+%22The+Agency%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("Broome County Tech Park" OR "The Agency") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22Broome+County+Tech+Park%22+OR+%22The+Agency%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("Broome County Tech Park" OR "The Agency") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22Broome+County+Tech+Park%22+OR+%22The+Agency%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"345 kV POI via a loop on the existing Oakdale-Fraser Line 32. The" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22345+kV+POI+via+a+loop+on+the+existing+Oakdale-Fraser+Line+32.+The%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1752" OR Q1752 OR "Queue #1752" OR 1752 OR "Broome County Tech Park")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231752%22+OR+Q1752+OR+%22Queue+%231752%22+OR+1752+OR+%22Broome+County+Tech+Park%22%29) |

### 70. SPP GEN-2025-SR10 — (no project name published) · 238 MW · OK

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | Seminole 345 KV Substation |
| Location field | county field "Konawa", Oklahoma |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "Seminole 345 KV Substation" "Konawa" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22Seminole+345+KV+Substation%22+%22Konawa%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "Seminole 345 KV Substation" "Konawa" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22Seminole+345+KV+Substation%22+%22Konawa%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`("Oklahoma Department of Environmental Quality" OR "Oklahoma DEQ") ("air permit" OR "construction permit" OR "environmental assessment") "Konawa" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%28%22Oklahoma+Department+of+Environmental+Quality%22+OR+%22Oklahoma+DEQ%22%29+%28%22air+permit%22+OR+%22construction+permit%22+OR+%22environmental+assessment%22%29+%22Konawa%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`"Oklahoma Corporation Commission" ("certificate of public convenience" OR siting OR "large load") "Seminole 345 KV Substation" "Konawa" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%22Oklahoma+Corporation+Commission%22+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+%22Seminole+345+KV+Substation%22+%22Konawa%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"Seminole 345 KV Substation" (substation OR interconnection OR "facilities study" OR "system impact study") Oklahoma`](https://www.google.com/search?q=%22Seminole+345+KV+Substation%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Oklahoma) |
| Substation · RTO / ISO documents | [`site:spp.org "GEN-2025-SR10"`](https://www.google.com/search?q=site%3Aspp.org+%22GEN-2025-SR10%22) |

### 71. NYISO 1728 — Arsenal Data Site 250 · 233 MW · NY

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | Arconic Corporation — Developer Not Matched To Known List |
| Point of interconnection | Haverstock to Adirondak 345kV line HA-1 |
| Location field | county field "St Lawrence", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("Arsenal Data Site 250" OR "Arconic") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22Arsenal+Data+Site+250%22+OR+%22Arconic%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("Arsenal Data Site 250" OR "Arconic") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22Arsenal+Data+Site+250%22+OR+%22Arconic%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("Arsenal Data Site 250" OR "Arconic") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22Arsenal+Data+Site+250%22+OR+%22Arconic%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("Arsenal Data Site 250" OR "Arconic") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22Arsenal+Data+Site+250%22+OR+%22Arconic%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"Haverstock to Adirondak 345kV line HA-1" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22Haverstock+to+Adirondak+345kV+line+HA-1%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1728" OR Q1728 OR "Queue #1728" OR 1728 OR "Arsenal Data Site 250")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231728%22+OR+Q1728+OR+%22Queue+%231728%22+OR+1728+OR+%22Arsenal+Data+Site+250%22%29) |

### 72. NYISO 1729 — Arsenal Data Site 500 · 233 MW · NY

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | Arconic Corporation — Developer Not Matched To Known List |
| Point of interconnection | Haverstock to Adirondak 345kV line HA-1 |
| Location field | county field "St Lawrence", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("Arsenal Data Site 500" OR "Arconic") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22Arsenal+Data+Site+500%22+OR+%22Arconic%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("Arsenal Data Site 500" OR "Arconic") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22Arsenal+Data+Site+500%22+OR+%22Arconic%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("Arsenal Data Site 500" OR "Arconic") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22Arsenal+Data+Site+500%22+OR+%22Arconic%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("Arsenal Data Site 500" OR "Arconic") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22Arsenal+Data+Site+500%22+OR+%22Arconic%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"Haverstock to Adirondak 345kV line HA-1" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22Haverstock+to+Adirondak+345kV+line+HA-1%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1729" OR Q1729 OR "Queue #1729" OR 1729 OR "Arsenal Data Site 500")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231729%22+OR+Q1729+OR+%22Queue+%231729%22+OR+1729+OR+%22Arsenal+Data+Site+500%22%29) |

### 73. AESO P2614 — Dow Fort Sask. Load · 231 MW · AB

| | |
|---|---|
| Status (as published) | IA in Progress |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "Fort Saskatchewan" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "Dow Fort Sask." Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22Dow+Fort+Sask.%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "Dow Fort Sask." Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22Dow+Fort+Sask.%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "Dow Fort Sask." Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22Dow+Fort+Sask.%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "Dow Fort Sask." Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22Dow+Fort+Sask.%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P2614 OR "Dow Fort Sask. Load")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P2614+OR+%22Dow+Fort+Sask.+Load%22%29) |

### 74. AESO P3083 — Keephills Data Centre Phase 1.1 · 230 MW · AB

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "Wabamun" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "Keephills Data Centre" Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22Keephills+Data+Centre%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "Keephills Data Centre" Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22Keephills+Data+Centre%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "Keephills Data Centre" Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22Keephills+Data+Centre%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "Keephills Data Centre" Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22Keephills+Data+Centre%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P3083 OR "Keephills Data Centre Phase 1.1")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P3083+OR+%22Keephills+Data+Centre+Phase+1.1%22%29) |

### 75. MISO S1148 — (no project name published) · 230 MW · MN

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | Magnolia |
| Location field | county field "Rock", Minnesota |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "Magnolia" "Rock" County Minnesota ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22Magnolia%22+%22Rock%22+County+Minnesota+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "Magnolia" "Rock" County Minnesota ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22Magnolia%22+%22Rock%22+County+Minnesota+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`("Minnesota Pollution Control Agency" OR MPCA) ("air permit" OR "construction permit" OR "environmental assessment") "Rock" County Minnesota ("data center" OR "large load")`](https://www.google.com/search?q=%28%22Minnesota+Pollution+Control+Agency%22+OR+MPCA%29+%28%22air+permit%22+OR+%22construction+permit%22+OR+%22environmental+assessment%22%29+%22Rock%22+County+Minnesota+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`"Minnesota Public Utilities Commission" ("certificate of public convenience" OR siting OR "large load") "Magnolia" "Rock" County Minnesota ("data center" OR "large load")`](https://www.google.com/search?q=%22Minnesota+Public+Utilities+Commission%22+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+%22Magnolia%22+%22Rock%22+County+Minnesota+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"Magnolia" (substation OR interconnection OR "facilities study" OR "system impact study") Minnesota`](https://www.google.com/search?q=%22Magnolia%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Minnesota) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1148`](https://www.google.com/search?q=site%3Amisoenergy.org+S1148) |

### 76. MISO S1086 — (no project name published) · 225 MW · MO

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | Stoddard - Morley 161kV |
| Location field | county field "Stoddard", Missouri |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "Stoddard - Morley 161kV" "Stoddard" County Missouri ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22Stoddard+-+Morley+161kV%22+%22Stoddard%22+County+Missouri+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "Stoddard - Morley 161kV" "Stoddard" County Missouri ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22Stoddard+-+Morley+161kV%22+%22Stoddard%22+County+Missouri+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`site:dnr.mo.gov "Stoddard" County Missouri ("data center" OR "large load")`](https://www.google.com/search?q=site%3Adnr.mo.gov+%22Stoddard%22+County+Missouri+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`site:psc.mo.gov "Stoddard - Morley 161kV" "Stoddard" County Missouri ("data center" OR "large load")`](https://www.google.com/search?q=site%3Apsc.mo.gov+%22Stoddard+-+Morley+161kV%22+%22Stoddard%22+County+Missouri+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"Stoddard - Morley 161kV" (substation OR interconnection OR "facilities study" OR "system impact study") Missouri`](https://www.google.com/search?q=%22Stoddard+-+Morley+161kV%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Missouri) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1086`](https://www.google.com/search?q=site%3Amisoenergy.org+S1086) |

### 77. MISO S1130 — (no project name published) · 225 MW · MI

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | county not published, Michigan |
| Transmission owner | METC |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`(EGLE OR "Michigan Department of Environment, Great Lakes, and Energy") ("air permit" OR "construction permit" OR "environmental assessment") Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28EGLE+OR+%22Michigan+Department+of+Environment%2C+Great+Lakes%2C+and+Energy%22%29+%28%22air+permit%22+OR+%22construction+permit%22+OR+%22environmental+assessment%22%29+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`("Michigan Public Service Commission" OR MPSC) ("certificate of public convenience" OR siting OR "large load") Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28%22Michigan+Public+Service+Commission%22+OR+MPSC%29+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1130`](https://www.google.com/search?q=site%3Amisoenergy.org+S1130) |
| Substation · Transmission-owner filings | [`"METC" ("large load" OR "data center" OR interconnection OR substation) Michigan`](https://www.google.com/search?q=%22METC%22+%28%22large+load%22+OR+%22data+center%22+OR+interconnection+OR+substation%29+Michigan) |

### 78. MISO S1057 — (no project name published) · 210 MW · IL

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | Neoga South |
| Location field | county field "Cumberland and Coles", Illinois |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "Neoga South" "Cumberland and Coles" County Illinois ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22Neoga+South%22+%22Cumberland+and+Coles%22+County+Illinois+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "Neoga South" "Cumberland and Coles" County Illinois ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22Neoga+South%22+%22Cumberland+and+Coles%22+County+Illinois+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`site:epa.illinois.gov "Cumberland and Coles" County Illinois ("data center" OR "large load")`](https://www.google.com/search?q=site%3Aepa.illinois.gov+%22Cumberland+and+Coles%22+County+Illinois+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`site:icc.illinois.gov "Neoga South" "Cumberland and Coles" County Illinois ("data center" OR "large load")`](https://www.google.com/search?q=site%3Aicc.illinois.gov+%22Neoga+South%22+%22Cumberland+and+Coles%22+County+Illinois+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"Neoga South" (substation OR interconnection OR "facilities study" OR "system impact study") Illinois`](https://www.google.com/search?q=%22Neoga+South%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Illinois) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1057`](https://www.google.com/search?q=site%3Amisoenergy.org+S1057) |

### 79. IESO 2025-838 — Project Rebel · 207.2 MW · ON

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | Bird Construction Group — Developer Not Matched To Known List |
| Point of interconnection | not published by the source register |
| Location field | IESO electrical zone "Toronto" (a grid region, not a municipality) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "planning committee" OR "committee of the whole") minutes ("Project Rebel" OR "Bird Construction Group") Ontario`](https://www.google.com/search?q=%28council+OR+%22planning+committee%22+OR+%22committee+of+the+whole%22%29+minutes+%28%22Project+Rebel%22+OR+%22Bird+Construction+Group%22%29+Ontario) |
| Municipal · Zoning & development applications | [`("zoning by-law amendment" OR "official plan amendment" OR "site plan" OR "minister's zoning order") ("Project Rebel" OR "Bird Construction Group") Ontario`](https://www.google.com/search?q=%28%22zoning+by-law+amendment%22+OR+%22official+plan+amendment%22+OR+%22site+plan%22+OR+%22minister%27s+zoning+order%22%29+%28%22Project+Rebel%22+OR+%22Bird+Construction+Group%22%29+Ontario) |
| Environmental / regulator · Environmental registry / permits | [`site:ero.ontario.ca ("Project Rebel" OR "Bird Construction Group") Ontario`](https://www.google.com/search?q=site%3Aero.ontario.ca+%28%22Project+Rebel%22+OR+%22Bird+Construction+Group%22%29+Ontario) |
| Environmental / regulator · Utility-commission / siting filings | [`site:oeb.ca ("Project Rebel" OR "Bird Construction Group") Ontario`](https://www.google.com/search?q=site%3Aoeb.ca+%28%22Project+Rebel%22+OR+%22Bird+Construction+Group%22%29+Ontario) |
| Substation · RTO / ISO documents | [`site:ieso.ca ("2025-838" OR "Project Rebel")`](https://www.google.com/search?q=site%3Aieso.ca+%28%222025-838%22+OR+%22Project+Rebel%22%29) |

### 80. IESO 2025-836 — Mikinak Data Center · 200 MW · ON

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | Mikinak MCFN-RJEP Data Centre — Developer Not Matched To Known List |
| Point of interconnection | not published by the source register |
| Location field | IESO electrical zone "Southwest" (a grid region, not a municipality) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "planning committee" OR "committee of the whole") minutes ("Mikinak Data Center" OR "Mikinak MCFN-RJEP Data Centre") Ontario`](https://www.google.com/search?q=%28council+OR+%22planning+committee%22+OR+%22committee+of+the+whole%22%29+minutes+%28%22Mikinak+Data+Center%22+OR+%22Mikinak+MCFN-RJEP+Data+Centre%22%29+Ontario) |
| Municipal · Zoning & development applications | [`("zoning by-law amendment" OR "official plan amendment" OR "site plan" OR "minister's zoning order") ("Mikinak Data Center" OR "Mikinak MCFN-RJEP Data Centre") Ontario`](https://www.google.com/search?q=%28%22zoning+by-law+amendment%22+OR+%22official+plan+amendment%22+OR+%22site+plan%22+OR+%22minister%27s+zoning+order%22%29+%28%22Mikinak+Data+Center%22+OR+%22Mikinak+MCFN-RJEP+Data+Centre%22%29+Ontario) |
| Environmental / regulator · Environmental registry / permits | [`site:ero.ontario.ca ("Mikinak Data Center" OR "Mikinak MCFN-RJEP Data Centre") Ontario`](https://www.google.com/search?q=site%3Aero.ontario.ca+%28%22Mikinak+Data+Center%22+OR+%22Mikinak+MCFN-RJEP+Data+Centre%22%29+Ontario) |
| Environmental / regulator · Utility-commission / siting filings | [`site:oeb.ca ("Mikinak Data Center" OR "Mikinak MCFN-RJEP Data Centre") Ontario`](https://www.google.com/search?q=site%3Aoeb.ca+%28%22Mikinak+Data+Center%22+OR+%22Mikinak+MCFN-RJEP+Data+Centre%22%29+Ontario) |
| Substation · RTO / ISO documents | [`site:ieso.ca ("2025-836" OR "Mikinak Data Center")`](https://www.google.com/search?q=site%3Aieso.ca+%28%222025-836%22+OR+%22Mikinak+Data+Center%22%29) |

### 81. IESO 2025-846 — Beach TS & Gage TS Load Increase · 200 MW · ON

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | ALECTRA UTILITIES CORPORATION — Developer Not Matched To Known List |
| Point of interconnection | not published by the source register |
| Location field | IESO electrical zone "Southwest" (a grid region, not a municipality) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "planning committee" OR "committee of the whole") minutes ("Beach TS & Gage TS" OR "ALECTRA UTILITIES") Ontario`](https://www.google.com/search?q=%28council+OR+%22planning+committee%22+OR+%22committee+of+the+whole%22%29+minutes+%28%22Beach+TS+%26+Gage+TS%22+OR+%22ALECTRA+UTILITIES%22%29+Ontario) |
| Municipal · Zoning & development applications | [`("zoning by-law amendment" OR "official plan amendment" OR "site plan" OR "minister's zoning order") ("Beach TS & Gage TS" OR "ALECTRA UTILITIES") Ontario`](https://www.google.com/search?q=%28%22zoning+by-law+amendment%22+OR+%22official+plan+amendment%22+OR+%22site+plan%22+OR+%22minister%27s+zoning+order%22%29+%28%22Beach+TS+%26+Gage+TS%22+OR+%22ALECTRA+UTILITIES%22%29+Ontario) |
| Environmental / regulator · Environmental registry / permits | [`site:ero.ontario.ca ("Beach TS & Gage TS" OR "ALECTRA UTILITIES") Ontario`](https://www.google.com/search?q=site%3Aero.ontario.ca+%28%22Beach+TS+%26+Gage+TS%22+OR+%22ALECTRA+UTILITIES%22%29+Ontario) |
| Environmental / regulator · Utility-commission / siting filings | [`site:oeb.ca ("Beach TS & Gage TS" OR "ALECTRA UTILITIES") Ontario`](https://www.google.com/search?q=site%3Aoeb.ca+%28%22Beach+TS+%26+Gage+TS%22+OR+%22ALECTRA+UTILITIES%22%29+Ontario) |
| Substation · RTO / ISO documents | [`site:ieso.ca ("2025-846" OR "Beach TS & Gage TS Load Increase")`](https://www.google.com/search?q=site%3Aieso.ca+%28%222025-846%22+OR+%22Beach+TS+%26+Gage+TS+Load+Increase%22%29) |

### 82. IESO 2026-877 — Millhaven Data Center · 200 MW · ON

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | RED JAR ENERGY PARTNERS INC. — Developer Not Matched To Known List |
| Point of interconnection | not published by the source register |
| Location field | IESO electrical zone "East" (a grid region, not a municipality) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "planning committee" OR "committee of the whole") minutes ("Millhaven Data Center" OR "RED JAR ENERGY PARTNERS") Ontario`](https://www.google.com/search?q=%28council+OR+%22planning+committee%22+OR+%22committee+of+the+whole%22%29+minutes+%28%22Millhaven+Data+Center%22+OR+%22RED+JAR+ENERGY+PARTNERS%22%29+Ontario) |
| Municipal · Zoning & development applications | [`("zoning by-law amendment" OR "official plan amendment" OR "site plan" OR "minister's zoning order") ("Millhaven Data Center" OR "RED JAR ENERGY PARTNERS") Ontario`](https://www.google.com/search?q=%28%22zoning+by-law+amendment%22+OR+%22official+plan+amendment%22+OR+%22site+plan%22+OR+%22minister%27s+zoning+order%22%29+%28%22Millhaven+Data+Center%22+OR+%22RED+JAR+ENERGY+PARTNERS%22%29+Ontario) |
| Environmental / regulator · Environmental registry / permits | [`site:ero.ontario.ca ("Millhaven Data Center" OR "RED JAR ENERGY PARTNERS") Ontario`](https://www.google.com/search?q=site%3Aero.ontario.ca+%28%22Millhaven+Data+Center%22+OR+%22RED+JAR+ENERGY+PARTNERS%22%29+Ontario) |
| Environmental / regulator · Utility-commission / siting filings | [`site:oeb.ca ("Millhaven Data Center" OR "RED JAR ENERGY PARTNERS") Ontario`](https://www.google.com/search?q=site%3Aoeb.ca+%28%22Millhaven+Data+Center%22+OR+%22RED+JAR+ENERGY+PARTNERS%22%29+Ontario) |
| Substation · RTO / ISO documents | [`site:ieso.ca ("2026-877" OR "Millhaven Data Center")`](https://www.google.com/search?q=site%3Aieso.ca+%28%222026-877%22+OR+%22Millhaven+Data+Center%22%29) |

### 83. IESO 2026-894 — Mikinak Phase 2 Data Center · 200 MW · ON

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | Red Jar Energy Partners Inc — Developer Not Matched To Known List |
| Point of interconnection | not published by the source register |
| Location field | IESO electrical zone "Southwest" (a grid region, not a municipality) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "planning committee" OR "committee of the whole") minutes ("Mikinak Phase 2 Data Center" OR "Red Jar Energy Partners") Ontario`](https://www.google.com/search?q=%28council+OR+%22planning+committee%22+OR+%22committee+of+the+whole%22%29+minutes+%28%22Mikinak+Phase+2+Data+Center%22+OR+%22Red+Jar+Energy+Partners%22%29+Ontario) |
| Municipal · Zoning & development applications | [`("zoning by-law amendment" OR "official plan amendment" OR "site plan" OR "minister's zoning order") ("Mikinak Phase 2 Data Center" OR "Red Jar Energy Partners") Ontario`](https://www.google.com/search?q=%28%22zoning+by-law+amendment%22+OR+%22official+plan+amendment%22+OR+%22site+plan%22+OR+%22minister%27s+zoning+order%22%29+%28%22Mikinak+Phase+2+Data+Center%22+OR+%22Red+Jar+Energy+Partners%22%29+Ontario) |
| Environmental / regulator · Environmental registry / permits | [`site:ero.ontario.ca ("Mikinak Phase 2 Data Center" OR "Red Jar Energy Partners") Ontario`](https://www.google.com/search?q=site%3Aero.ontario.ca+%28%22Mikinak+Phase+2+Data+Center%22+OR+%22Red+Jar+Energy+Partners%22%29+Ontario) |
| Environmental / regulator · Utility-commission / siting filings | [`site:oeb.ca ("Mikinak Phase 2 Data Center" OR "Red Jar Energy Partners") Ontario`](https://www.google.com/search?q=site%3Aoeb.ca+%28%22Mikinak+Phase+2+Data+Center%22+OR+%22Red+Jar+Energy+Partners%22%29+Ontario) |
| Substation · RTO / ISO documents | [`site:ieso.ca ("2026-894" OR "Mikinak Phase 2 Data Center")`](https://www.google.com/search?q=site%3Aieso.ca+%28%222026-894%22+OR+%22Mikinak+Phase+2+Data+Center%22%29) |

### 84. IESO 2026-913 — St. Clair Technology Centre · 200 MW · ON

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | TRUENORTH SUSTAINABLE INFRASTRUCTURE INC. — Developer Not Matched To Known List |
| Point of interconnection | not published by the source register |
| Location field | IESO electrical zone "West" (a grid region, not a municipality) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "planning committee" OR "committee of the whole") minutes ("St. Clair Technology Centre" OR "TRUENORTH SUSTAINABLE INFRASTRUCTURE") Ontario`](https://www.google.com/search?q=%28council+OR+%22planning+committee%22+OR+%22committee+of+the+whole%22%29+minutes+%28%22St.+Clair+Technology+Centre%22+OR+%22TRUENORTH+SUSTAINABLE+INFRASTRUCTURE%22%29+Ontario) |
| Municipal · Zoning & development applications | [`("zoning by-law amendment" OR "official plan amendment" OR "site plan" OR "minister's zoning order") ("St. Clair Technology Centre" OR "TRUENORTH SUSTAINABLE INFRASTRUCTURE") Ontario`](https://www.google.com/search?q=%28%22zoning+by-law+amendment%22+OR+%22official+plan+amendment%22+OR+%22site+plan%22+OR+%22minister%27s+zoning+order%22%29+%28%22St.+Clair+Technology+Centre%22+OR+%22TRUENORTH+SUSTAINABLE+INFRASTRUCTURE%22%29+Ontario) |
| Environmental / regulator · Environmental registry / permits | [`site:ero.ontario.ca ("St. Clair Technology Centre" OR "TRUENORTH SUSTAINABLE INFRASTRUCTURE") Ontario`](https://www.google.com/search?q=site%3Aero.ontario.ca+%28%22St.+Clair+Technology+Centre%22+OR+%22TRUENORTH+SUSTAINABLE+INFRASTRUCTURE%22%29+Ontario) |
| Environmental / regulator · Utility-commission / siting filings | [`site:oeb.ca ("St. Clair Technology Centre" OR "TRUENORTH SUSTAINABLE INFRASTRUCTURE") Ontario`](https://www.google.com/search?q=site%3Aoeb.ca+%28%22St.+Clair+Technology+Centre%22+OR+%22TRUENORTH+SUSTAINABLE+INFRASTRUCTURE%22%29+Ontario) |
| Substation · RTO / ISO documents | [`site:ieso.ca ("2026-913" OR "St. Clair Technology Centre")`](https://www.google.com/search?q=site%3Aieso.ca+%28%222026-913%22+OR+%22St.+Clair+Technology+Centre%22%29) |

### 85. MISO S1074 — (no project name published) · 200 MW · AR

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | Ritchie Plant 230 kV Substation |
| Location field | county field "Phillips", Arkansas |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "Ritchie Plant 230 kV Substation" "Phillips" County Arkansas ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22Ritchie+Plant+230+kV+Substation%22+%22Phillips%22+County+Arkansas+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "Ritchie Plant 230 kV Substation" "Phillips" County Arkansas ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22Ritchie+Plant+230+kV+Substation%22+%22Phillips%22+County+Arkansas+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`("Arkansas Division of Environmental Quality" OR ADEQ) ("air permit" OR "construction permit" OR "environmental assessment") "Phillips" County Arkansas ("data center" OR "large load")`](https://www.google.com/search?q=%28%22Arkansas+Division+of+Environmental+Quality%22+OR+ADEQ%29+%28%22air+permit%22+OR+%22construction+permit%22+OR+%22environmental+assessment%22%29+%22Phillips%22+County+Arkansas+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`"Arkansas Public Service Commission" ("certificate of public convenience" OR siting OR "large load") "Ritchie Plant 230 kV Substation" "Phillips" County Arkansas ("data center" OR "large load")`](https://www.google.com/search?q=%22Arkansas+Public+Service+Commission%22+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+%22Ritchie+Plant+230+kV+Substation%22+%22Phillips%22+County+Arkansas+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"Ritchie Plant 230 kV Substation" (substation OR interconnection OR "facilities study" OR "system impact study") Arkansas`](https://www.google.com/search?q=%22Ritchie+Plant+230+kV+Substation%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Arkansas) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1074`](https://www.google.com/search?q=site%3Amisoenergy.org+S1074) |

### 86. MISO S1091 — (no project name published) · 200 MW · MO

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | Adna 345 kV |
| Location field | county field "Cape Girardeau", Missouri |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "Adna 345 kV" "Cape Girardeau" County Missouri ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22Adna+345+kV%22+%22Cape+Girardeau%22+County+Missouri+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "Adna 345 kV" "Cape Girardeau" County Missouri ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22Adna+345+kV%22+%22Cape+Girardeau%22+County+Missouri+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`site:dnr.mo.gov "Cape Girardeau" County Missouri ("data center" OR "large load")`](https://www.google.com/search?q=site%3Adnr.mo.gov+%22Cape+Girardeau%22+County+Missouri+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`site:psc.mo.gov "Adna 345 kV" "Cape Girardeau" County Missouri ("data center" OR "large load")`](https://www.google.com/search?q=site%3Apsc.mo.gov+%22Adna+345+kV%22+%22Cape+Girardeau%22+County+Missouri+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"Adna 345 kV" (substation OR interconnection OR "facilities study" OR "system impact study") Missouri`](https://www.google.com/search?q=%22Adna+345+kV%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Missouri) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1091`](https://www.google.com/search?q=site%3Amisoenergy.org+S1091) |

### 87. MISO S1133 — (no project name published) · 200 MW · LA

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | 343515 Chatham Main - 346555 North Aurburn (Ameren) 138.0kV |
| Location field | county field "Sangamon", Louisiana |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "343515 Chatham Main - 346555 North Aurburn (Ameren) 138.0kV" "Sangamon" Parish Louisiana ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22343515+Chatham+Main+-+346555+North+Aurburn+%28Ameren%29+138.0kV%22+%22Sangamon%22+Parish+Louisiana+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "343515 Chatham Main - 346555 North Aurburn (Ameren) 138.0kV" "Sangamon" Parish Louisiana ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22343515+Chatham+Main+-+346555+North+Aurburn+%28Ameren%29+138.0kV%22+%22Sangamon%22+Parish+Louisiana+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`site:deq.louisiana.gov "Sangamon" Parish Louisiana ("data center" OR "large load")`](https://www.google.com/search?q=site%3Adeq.louisiana.gov+%22Sangamon%22+Parish+Louisiana+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`site:lpsc.louisiana.gov "343515 Chatham Main - 346555 North Aurburn (Ameren) 138.0kV" "Sangamon" Parish Louisiana ("data center" OR "large load")`](https://www.google.com/search?q=site%3Alpsc.louisiana.gov+%22343515+Chatham+Main+-+346555+North+Aurburn+%28Ameren%29+138.0kV%22+%22Sangamon%22+Parish+Louisiana+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"343515 Chatham Main - 346555 North Aurburn (Ameren) 138.0kV" (substation OR interconnection OR "facilities study" OR "system impact study") Louisiana`](https://www.google.com/search?q=%22343515+Chatham+Main+-+346555+North+Aurburn+%28Ameren%29+138.0kV%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Louisiana) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1133`](https://www.google.com/search?q=site%3Amisoenergy.org+S1133) |

### 88. MISO S1140 — (no project name published) · 200 MW · MN

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | Calamus East |
| Location field | county field "Clinton", Minnesota |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "Calamus East" "Clinton" County Minnesota ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22Calamus+East%22+%22Clinton%22+County+Minnesota+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "Calamus East" "Clinton" County Minnesota ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22Calamus+East%22+%22Clinton%22+County+Minnesota+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`("Minnesota Pollution Control Agency" OR MPCA) ("air permit" OR "construction permit" OR "environmental assessment") "Clinton" County Minnesota ("data center" OR "large load")`](https://www.google.com/search?q=%28%22Minnesota+Pollution+Control+Agency%22+OR+MPCA%29+%28%22air+permit%22+OR+%22construction+permit%22+OR+%22environmental+assessment%22%29+%22Clinton%22+County+Minnesota+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`"Minnesota Public Utilities Commission" ("certificate of public convenience" OR siting OR "large load") "Calamus East" "Clinton" County Minnesota ("data center" OR "large load")`](https://www.google.com/search?q=%22Minnesota+Public+Utilities+Commission%22+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+%22Calamus+East%22+%22Clinton%22+County+Minnesota+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"Calamus East" (substation OR interconnection OR "facilities study" OR "system impact study") Minnesota`](https://www.google.com/search?q=%22Calamus+East%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Minnesota) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1140`](https://www.google.com/search?q=site%3Amisoenergy.org+S1140) |

### 89. MISO S1144 — (no project name published) · 200 MW · MI

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | county not published, Michigan |
| Transmission owner | METC |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`(EGLE OR "Michigan Department of Environment, Great Lakes, and Energy") ("air permit" OR "construction permit" OR "environmental assessment") Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28EGLE+OR+%22Michigan+Department+of+Environment%2C+Great+Lakes%2C+and+Energy%22%29+%28%22air+permit%22+OR+%22construction+permit%22+OR+%22environmental+assessment%22%29+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`("Michigan Public Service Commission" OR MPSC) ("certificate of public convenience" OR siting OR "large load") Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28%22Michigan+Public+Service+Commission%22+OR+MPSC%29+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1144`](https://www.google.com/search?q=site%3Amisoenergy.org+S1144) |
| Substation · Transmission-owner filings | [`"METC" ("large load" OR "data center" OR interconnection OR substation) Michigan`](https://www.google.com/search?q=%22METC%22+%28%22large+load%22+OR+%22data+center%22+OR+interconnection+OR+substation%29+Michigan) |

### 90. MISO S1155 — (no project name published) · 200 MW · MO

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | county not published, Missouri |
| Transmission owner | AMEREN MISSOURI |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes Missouri ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+Missouri+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") Missouri ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+Missouri+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`site:dnr.mo.gov Missouri ("data center" OR "large load")`](https://www.google.com/search?q=site%3Adnr.mo.gov+Missouri+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`site:psc.mo.gov Missouri ("data center" OR "large load")`](https://www.google.com/search?q=site%3Apsc.mo.gov+Missouri+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1155`](https://www.google.com/search?q=site%3Amisoenergy.org+S1155) |
| Substation · Transmission-owner filings | [`"AMEREN MISSOURI" ("large load" OR "data center" OR interconnection OR substation) Missouri`](https://www.google.com/search?q=%22AMEREN+MISSOURI%22+%28%22large+load%22+OR+%22data+center%22+OR+interconnection+OR+substation%29+Missouri) |

### 91. MISO S1164 — (no project name published) · 200 MW · AR

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | Dell - Manila 161 kV |
| Location field | county field "Mississippi", Arkansas |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "Dell - Manila 161 kV" "Mississippi" County Arkansas ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22Dell+-+Manila+161+kV%22+%22Mississippi%22+County+Arkansas+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "Dell - Manila 161 kV" "Mississippi" County Arkansas ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22Dell+-+Manila+161+kV%22+%22Mississippi%22+County+Arkansas+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`("Arkansas Division of Environmental Quality" OR ADEQ) ("air permit" OR "construction permit" OR "environmental assessment") "Mississippi" County Arkansas ("data center" OR "large load")`](https://www.google.com/search?q=%28%22Arkansas+Division+of+Environmental+Quality%22+OR+ADEQ%29+%28%22air+permit%22+OR+%22construction+permit%22+OR+%22environmental+assessment%22%29+%22Mississippi%22+County+Arkansas+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`"Arkansas Public Service Commission" ("certificate of public convenience" OR siting OR "large load") "Dell - Manila 161 kV" "Mississippi" County Arkansas ("data center" OR "large load")`](https://www.google.com/search?q=%22Arkansas+Public+Service+Commission%22+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+%22Dell+-+Manila+161+kV%22+%22Mississippi%22+County+Arkansas+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"Dell - Manila 161 kV" (substation OR interconnection OR "facilities study" OR "system impact study") Arkansas`](https://www.google.com/search?q=%22Dell+-+Manila+161+kV%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Arkansas) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1164`](https://www.google.com/search?q=site%3Amisoenergy.org+S1164) |

### 92. NYISO 1213 — St Lawrence Data and Agricultural Center · 200 MW · NY

| | |
|---|---|
| Status (as published) | IA in Progress |
| Developer (as published) | ZeroC Data Centers, LLC — Developer Not Matched To Known List |
| Point of interconnection | Dennison 115kV substation |
| Location field | county field "St. Lawrence", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("St Lawrence Data and Agricultural Center" OR "ZeroC Data Centers") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22St+Lawrence+Data+and+Agricultural+Center%22+OR+%22ZeroC+Data+Centers%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("St Lawrence Data and Agricultural Center" OR "ZeroC Data Centers") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22St+Lawrence+Data+and+Agricultural+Center%22+OR+%22ZeroC+Data+Centers%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("St Lawrence Data and Agricultural Center" OR "ZeroC Data Centers") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22St+Lawrence+Data+and+Agricultural+Center%22+OR+%22ZeroC+Data+Centers%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("St Lawrence Data and Agricultural Center" OR "ZeroC Data Centers") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22St+Lawrence+Data+and+Agricultural+Center%22+OR+%22ZeroC+Data+Centers%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"Dennison 115kV substation" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22Dennison+115kV+substation%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1213" OR Q1213 OR "Queue #1213" OR 1213 OR "St Lawrence Data and Agricultural Center")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231213%22+OR+Q1213+OR+%22Queue+%231213%22+OR+1213+OR+%22St+Lawrence+Data+and+Agricultural+Center%22%29) |

### 93. NYISO 1717 — Proposed Datacenters at 450 Broadway, Buchanan, NY, 10511 · 200 MW · NY

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | Holtec Decommissioning International (HDI) — Developer Not Matched To Known List |
| Point of interconnection | Buchanan 138kV Substation |
| Location field | county field "Westchester", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("Proposed Datacenters at 450 Broadway" OR "Holtec Decommissioning International (HDI)") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22Proposed+Datacenters+at+450+Broadway%22+OR+%22Holtec+Decommissioning+International+%28HDI%29%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("Proposed Datacenters at 450 Broadway" OR "Holtec Decommissioning International (HDI)") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22Proposed+Datacenters+at+450+Broadway%22+OR+%22Holtec+Decommissioning+International+%28HDI%29%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("Proposed Datacenters at 450 Broadway" OR "Holtec Decommissioning International (HDI)") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22Proposed+Datacenters+at+450+Broadway%22+OR+%22Holtec+Decommissioning+International+%28HDI%29%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("Proposed Datacenters at 450 Broadway" OR "Holtec Decommissioning International (HDI)") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22Proposed+Datacenters+at+450+Broadway%22+OR+%22Holtec+Decommissioning+International+%28HDI%29%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"Buchanan 138kV Substation" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22Buchanan+138kV+Substation%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1717" OR Q1717 OR "Queue #1717" OR 1717 OR "Proposed Datacenters at 450 Broadway, Buchanan, NY, 10511")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231717%22+OR+Q1717+OR+%22Queue+%231717%22+OR+1717+OR+%22Proposed+Datacenters+at+450+Broadway%2C+Buchanan%2C+NY%2C+10511%22%29) |

### 94. NYISO 1725 — Greenidge 200 MW Data Center Project · 200 MW · NY

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | Greenidge Generation, LLC — Developer Not Matched To Known List |
| Point of interconnection | New York State Electric & Gas (NYSEG) - Greenidge 115 kV Substation |
| Location field | county field "Yates", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("Greenidge 200 MW Data Center Project" OR "Greenidge Generation") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22Greenidge+200+MW+Data+Center+Project%22+OR+%22Greenidge+Generation%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("Greenidge 200 MW Data Center Project" OR "Greenidge Generation") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22Greenidge+200+MW+Data+Center+Project%22+OR+%22Greenidge+Generation%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("Greenidge 200 MW Data Center Project" OR "Greenidge Generation") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22Greenidge+200+MW+Data+Center+Project%22+OR+%22Greenidge+Generation%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("Greenidge 200 MW Data Center Project" OR "Greenidge Generation") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22Greenidge+200+MW+Data+Center+Project%22+OR+%22Greenidge+Generation%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"New York State Electric & Gas (NYSEG) - Greenidge 115 kV Substation" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22New+York+State+Electric+%26+Gas+%28NYSEG%29+-+Greenidge+115+kV+Substation%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1725" OR Q1725 OR "Queue #1725" OR 1725 OR "Greenidge 200 MW Data Center Project")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231725%22+OR+Q1725+OR+%22Queue+%231725%22+OR+1725+OR+%22Greenidge+200+MW+Data+Center+Project%22%29) |

### 95. NYISO 1751 — Massena Development LLC Power Allocation · 200 MW · NY

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | North Country Data Center LLC — Developer Not Matched To Known List |
| Point of interconnection | NYPA - HW1 and HW2 (345kV) Lines - at Haverstock Substation |
| Location field | county field "St. Lawrence", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("Massena Development LLC Power Allocation" OR "North Country Data Center") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22Massena+Development+LLC+Power+Allocation%22+OR+%22North+Country+Data+Center%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("Massena Development LLC Power Allocation" OR "North Country Data Center") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22Massena+Development+LLC+Power+Allocation%22+OR+%22North+Country+Data+Center%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("Massena Development LLC Power Allocation" OR "North Country Data Center") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22Massena+Development+LLC+Power+Allocation%22+OR+%22North+Country+Data+Center%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("Massena Development LLC Power Allocation" OR "North Country Data Center") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22Massena+Development+LLC+Power+Allocation%22+OR+%22North+Country+Data+Center%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"NYPA - HW1 and HW2 (345kV) Lines - at Haverstock Substation" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22NYPA+-+HW1+and+HW2+%28345kV%29+Lines+-+at+Haverstock+Substation%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1751" OR Q1751 OR "Queue #1751" OR 1751 OR "Massena Development LLC Power Allocation")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231751%22+OR+Q1751+OR+%22Queue+%231751%22+OR+1751+OR+%22Massena+Development+LLC+Power+Allocation%22%29) |

### 96. SPP GEN-2025-SR24 — (no project name published) · 200 MW · NE

| | |
|---|---|
| Status (as published) | Facilities Study |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | Fort Calhoun 345kV Substation |
| Location field | county field "Blair", Nebraska |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "Fort Calhoun 345kV Substation" "Blair" County Nebraska ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22Fort+Calhoun+345kV+Substation%22+%22Blair%22+County+Nebraska+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "Fort Calhoun 345kV Substation" "Blair" County Nebraska ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22Fort+Calhoun+345kV+Substation%22+%22Blair%22+County+Nebraska+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`site:dee.ne.gov "Blair" County Nebraska ("data center" OR "large load")`](https://www.google.com/search?q=site%3Adee.ne.gov+%22Blair%22+County+Nebraska+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`"Nebraska Power Review Board" ("certificate of public convenience" OR siting OR "large load") "Fort Calhoun 345kV Substation" "Blair" County Nebraska ("data center" OR "large load")`](https://www.google.com/search?q=%22Nebraska+Power+Review+Board%22+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+%22Fort+Calhoun+345kV+Substation%22+%22Blair%22+County+Nebraska+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"Fort Calhoun 345kV Substation" (substation OR interconnection OR "facilities study" OR "system impact study") Nebraska`](https://www.google.com/search?q=%22Fort+Calhoun+345kV+Substation%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Nebraska) |
| Substation · RTO / ISO documents | [`site:spp.org "GEN-2025-SR24"`](https://www.google.com/search?q=site%3Aspp.org+%22GEN-2025-SR24%22) |

### 97. SPP GEN-2025-SR26 — (no project name published) · 200 MW · NE

| | |
|---|---|
| Status (as published) | Facilities Study |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | Cass County 345kV Substation |
| Location field | county field "Plattsmouth", Nebraska |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "Cass County 345kV Substation" "Plattsmouth" County Nebraska ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22Cass+County+345kV+Substation%22+%22Plattsmouth%22+County+Nebraska+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "Cass County 345kV Substation" "Plattsmouth" County Nebraska ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22Cass+County+345kV+Substation%22+%22Plattsmouth%22+County+Nebraska+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`site:dee.ne.gov "Plattsmouth" County Nebraska ("data center" OR "large load")`](https://www.google.com/search?q=site%3Adee.ne.gov+%22Plattsmouth%22+County+Nebraska+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`"Nebraska Power Review Board" ("certificate of public convenience" OR siting OR "large load") "Cass County 345kV Substation" "Plattsmouth" County Nebraska ("data center" OR "large load")`](https://www.google.com/search?q=%22Nebraska+Power+Review+Board%22+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+%22Cass+County+345kV+Substation%22+%22Plattsmouth%22+County+Nebraska+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"Cass County 345kV Substation" (substation OR interconnection OR "facilities study" OR "system impact study") Nebraska`](https://www.google.com/search?q=%22Cass+County+345kV+Substation%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Nebraska) |
| Substation · RTO / ISO documents | [`site:spp.org "GEN-2025-SR26"`](https://www.google.com/search?q=site%3Aspp.org+%22GEN-2025-SR26%22) |

### 98. IESO 2024-809 — Project Chisel · 198 MW · ON

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | Bird Construction Group Limited — Developer Not Matched To Known List |
| Point of interconnection | not published by the source register |
| Location field | IESO electrical zone "Southwest" (a grid region, not a municipality) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "planning committee" OR "committee of the whole") minutes ("Project Chisel" OR "Bird Construction Group") Ontario`](https://www.google.com/search?q=%28council+OR+%22planning+committee%22+OR+%22committee+of+the+whole%22%29+minutes+%28%22Project+Chisel%22+OR+%22Bird+Construction+Group%22%29+Ontario) |
| Municipal · Zoning & development applications | [`("zoning by-law amendment" OR "official plan amendment" OR "site plan" OR "minister's zoning order") ("Project Chisel" OR "Bird Construction Group") Ontario`](https://www.google.com/search?q=%28%22zoning+by-law+amendment%22+OR+%22official+plan+amendment%22+OR+%22site+plan%22+OR+%22minister%27s+zoning+order%22%29+%28%22Project+Chisel%22+OR+%22Bird+Construction+Group%22%29+Ontario) |
| Environmental / regulator · Environmental registry / permits | [`site:ero.ontario.ca ("Project Chisel" OR "Bird Construction Group") Ontario`](https://www.google.com/search?q=site%3Aero.ontario.ca+%28%22Project+Chisel%22+OR+%22Bird+Construction+Group%22%29+Ontario) |
| Environmental / regulator · Utility-commission / siting filings | [`site:oeb.ca ("Project Chisel" OR "Bird Construction Group") Ontario`](https://www.google.com/search?q=site%3Aoeb.ca+%28%22Project+Chisel%22+OR+%22Bird+Construction+Group%22%29+Ontario) |
| Substation · RTO / ISO documents | [`site:ieso.ca ("2024-809" OR "Project Chisel")`](https://www.google.com/search?q=site%3Aieso.ca+%28%222024-809%22+OR+%22Project+Chisel%22%29) |

### 99. IESO 2025-825 — Project Chisel 2 · 198 MW · ON

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | Bird Construction Group Ltd — Developer Not Matched To Known List |
| Point of interconnection | not published by the source register |
| Location field | IESO electrical zone "Southwest" (a grid region, not a municipality) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "planning committee" OR "committee of the whole") minutes ("Project Chisel 2" OR "Bird Construction Group") Ontario`](https://www.google.com/search?q=%28council+OR+%22planning+committee%22+OR+%22committee+of+the+whole%22%29+minutes+%28%22Project+Chisel+2%22+OR+%22Bird+Construction+Group%22%29+Ontario) |
| Municipal · Zoning & development applications | [`("zoning by-law amendment" OR "official plan amendment" OR "site plan" OR "minister's zoning order") ("Project Chisel 2" OR "Bird Construction Group") Ontario`](https://www.google.com/search?q=%28%22zoning+by-law+amendment%22+OR+%22official+plan+amendment%22+OR+%22site+plan%22+OR+%22minister%27s+zoning+order%22%29+%28%22Project+Chisel+2%22+OR+%22Bird+Construction+Group%22%29+Ontario) |
| Environmental / regulator · Environmental registry / permits | [`site:ero.ontario.ca ("Project Chisel 2" OR "Bird Construction Group") Ontario`](https://www.google.com/search?q=site%3Aero.ontario.ca+%28%22Project+Chisel+2%22+OR+%22Bird+Construction+Group%22%29+Ontario) |
| Environmental / regulator · Utility-commission / siting filings | [`site:oeb.ca ("Project Chisel 2" OR "Bird Construction Group") Ontario`](https://www.google.com/search?q=site%3Aoeb.ca+%28%22Project+Chisel+2%22+OR+%22Bird+Construction+Group%22%29+Ontario) |
| Substation · RTO / ISO documents | [`site:ieso.ca ("2025-825" OR "Project Chisel 2")`](https://www.google.com/search?q=site%3Aieso.ca+%28%222025-825%22+OR+%22Project+Chisel+2%22%29) |

### 100. NYISO 1747 — Globe Digital Holdings - 1 · 192 MW · NY

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | GLOBE DH LLC — Developer Not Matched To Known List |
| Point of interconnection | Beck Packard 76 230kV |
| Location field | county field "Niagara", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("Globe Digital Holdings - 1" OR "GLOBE DH") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22Globe+Digital+Holdings+-+1%22+OR+%22GLOBE+DH%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("Globe Digital Holdings - 1" OR "GLOBE DH") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22Globe+Digital+Holdings+-+1%22+OR+%22GLOBE+DH%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("Globe Digital Holdings - 1" OR "GLOBE DH") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22Globe+Digital+Holdings+-+1%22+OR+%22GLOBE+DH%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("Globe Digital Holdings - 1" OR "GLOBE DH") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22Globe+Digital+Holdings+-+1%22+OR+%22GLOBE+DH%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"Beck Packard 76 230kV" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22Beck+Packard+76+230kV%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1747" OR Q1747 OR "Queue #1747" OR 1747 OR "Globe Digital Holdings - 1")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231747%22+OR+Q1747+OR+%22Queue+%231747%22+OR+1747+OR+%22Globe+Digital+Holdings+-+1%22%29) |

### 101. NYISO 1748 — GLOBE DH 2 · 192 MW · NY

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | GLOBE DH LLC — Developer Not Matched To Known List |
| Point of interconnection | Beck Packard 76 230kV |
| Location field | county field "Niagara Falls", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("GLOBE DH 2" OR "GLOBE DH") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22GLOBE+DH+2%22+OR+%22GLOBE+DH%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("GLOBE DH 2" OR "GLOBE DH") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22GLOBE+DH+2%22+OR+%22GLOBE+DH%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("GLOBE DH 2" OR "GLOBE DH") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22GLOBE+DH+2%22+OR+%22GLOBE+DH%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("GLOBE DH 2" OR "GLOBE DH") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22GLOBE+DH+2%22+OR+%22GLOBE+DH%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"Beck Packard 76 230kV" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22Beck+Packard+76+230kV%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1748" OR Q1748 OR "Queue #1748" OR 1748 OR "GLOBE DH 2")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231748%22+OR+Q1748+OR+%22Queue+%231748%22+OR+1748+OR+%22GLOBE+DH+2%22%29) |

### 102. NYISO 1749 — Globe DH 3 · 192 MW · NY

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | GLOBE DH LLC — Developer Not Matched To Known List |
| Point of interconnection | Niagara Packard 77 230kV |
| Location field | county field "Niagara Falls", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("Globe DH 3" OR "GLOBE DH") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22Globe+DH+3%22+OR+%22GLOBE+DH%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("Globe DH 3" OR "GLOBE DH") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22Globe+DH+3%22+OR+%22GLOBE+DH%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("Globe DH 3" OR "GLOBE DH") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22Globe+DH+3%22+OR+%22GLOBE+DH%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("Globe DH 3" OR "GLOBE DH") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22Globe+DH+3%22+OR+%22GLOBE+DH%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"Niagara Packard 77 230kV" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22Niagara+Packard+77+230kV%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1749" OR Q1749 OR "Queue #1749" OR 1749 OR "Globe DH 3")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231749%22+OR+Q1749+OR+%22Queue+%231749%22+OR+1749+OR+%22Globe+DH+3%22%29) |

### 103. MISO J2656 — (no project name published) · 180 MW · IL

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | 4LATHAM-4N DEC E 138 kV |
| Location field | county field "Macon", Illinois |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "4LATHAM-4N DEC E 138 kV" "Macon" County Illinois ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%224LATHAM-4N+DEC+E+138+kV%22+%22Macon%22+County+Illinois+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "4LATHAM-4N DEC E 138 kV" "Macon" County Illinois ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%224LATHAM-4N+DEC+E+138+kV%22+%22Macon%22+County+Illinois+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`site:epa.illinois.gov "Macon" County Illinois ("data center" OR "large load")`](https://www.google.com/search?q=site%3Aepa.illinois.gov+%22Macon%22+County+Illinois+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`site:icc.illinois.gov "4LATHAM-4N DEC E 138 kV" "Macon" County Illinois ("data center" OR "large load")`](https://www.google.com/search?q=site%3Aicc.illinois.gov+%224LATHAM-4N+DEC+E+138+kV%22+%22Macon%22+County+Illinois+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"4LATHAM-4N DEC E 138 kV" (substation OR interconnection OR "facilities study" OR "system impact study") Illinois`](https://www.google.com/search?q=%224LATHAM-4N+DEC+E+138+kV%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Illinois) |
| Substation · RTO / ISO documents | [`site:misoenergy.org J2656`](https://www.google.com/search?q=site%3Amisoenergy.org+J2656) |

### 104. NYISO 1754 — Kenwood Tech Center · 180 MW · NY

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | EKG Group LLC — Developer Not Matched To Known List |
| Point of interconnection | Albany?Bethlehem 115 kV Line #18 |
| Location field | county field "Albany", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("Kenwood Tech Center" OR "EKG Group") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22Kenwood+Tech+Center%22+OR+%22EKG+Group%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("Kenwood Tech Center" OR "EKG Group") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22Kenwood+Tech+Center%22+OR+%22EKG+Group%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("Kenwood Tech Center" OR "EKG Group") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22Kenwood+Tech+Center%22+OR+%22EKG+Group%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("Kenwood Tech Center" OR "EKG Group") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22Kenwood+Tech+Center%22+OR+%22EKG+Group%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"Albany Bethlehem 115 kV Line #18" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22Albany+Bethlehem+115+kV+Line+%2318%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1754" OR Q1754 OR "Queue #1754" OR 1754 OR "Kenwood Tech Center")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231754%22+OR+Q1754+OR+%22Queue+%231754%22+OR+1754+OR+%22Kenwood+Tech+Center%22%29) |

### 105. NYISO 1721 — Brookhaven Logistics Center · 176.6 MW · NY

| | |
|---|---|
| Status (as published) | Facilities Study |
| Developer (as published) | WF Industrial XII LLC — Developer Not Matched To Known List |
| Point of interconnection | 138-872 Holbrook to Sills Rd |
| Location field | county field "Suffolk", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("Brookhaven Logistics Center" OR "WF Industrial XII") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22Brookhaven+Logistics+Center%22+OR+%22WF+Industrial+XII%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("Brookhaven Logistics Center" OR "WF Industrial XII") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22Brookhaven+Logistics+Center%22+OR+%22WF+Industrial+XII%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("Brookhaven Logistics Center" OR "WF Industrial XII") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22Brookhaven+Logistics+Center%22+OR+%22WF+Industrial+XII%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("Brookhaven Logistics Center" OR "WF Industrial XII") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22Brookhaven+Logistics+Center%22+OR+%22WF+Industrial+XII%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"138-872 Holbrook to Sills Rd" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22138-872+Holbrook+to+Sills+Rd%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1721" OR Q1721 OR "Queue #1721" OR 1721 OR "Brookhaven Logistics Center")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231721%22+OR+Q1721+OR+%22Queue+%231721%22+OR+1721+OR+%22Brookhaven+Logistics+Center%22%29) |

### 106. AESO P3152 — Keephills Data Centre Phase 1.2 · 165 MW · AB

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | AESO planning area "Wabamun" (a hub named for a town, not a municipality boundary) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "municipal planning commission" OR "development authority") minutes "Keephills Data Centre" Alberta`](https://www.google.com/search?q=%28council+OR+%22municipal+planning+commission%22+OR+%22development+authority%22%29+minutes+%22Keephills+Data+Centre%22+Alberta) |
| Municipal · Zoning & development applications | [`("development permit" OR "land use bylaw" OR redesignation OR "area structure plan") "Keephills Data Centre" Alberta`](https://www.google.com/search?q=%28%22development+permit%22+OR+%22land+use+bylaw%22+OR+redesignation+OR+%22area+structure+plan%22%29+%22Keephills+Data+Centre%22+Alberta) |
| Environmental / regulator · Environmental registry / permits | [`"Alberta Environment and Protected Areas" (EPEA OR "environmental impact assessment" OR approval) "Keephills Data Centre" Alberta`](https://www.google.com/search?q=%22Alberta+Environment+and+Protected+Areas%22+%28EPEA+OR+%22environmental+impact+assessment%22+OR+approval%29+%22Keephills+Data+Centre%22+Alberta) |
| Environmental / regulator · Utility-commission / siting filings | [`site:auc.ab.ca "Keephills Data Centre" Alberta`](https://www.google.com/search?q=site%3Aauc.ab.ca+%22Keephills+Data+Centre%22+Alberta) |
| Substation · RTO / ISO documents | [`site:aeso.ca (P3152 OR "Keephills Data Centre Phase 1.2")`](https://www.google.com/search?q=site%3Aaeso.ca+%28P3152+OR+%22Keephills+Data+Centre+Phase+1.2%22%29) |

### 107. NYISO 1733 — Cayuga Data · 162 MW · NY

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | Cayuga Operating Company, LLC — Developer Not Matched To Known List |
| Point of interconnection | Milliken 115kV Substation |
| Location field | county field "Tompkins", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("Cayuga Data" OR "Cayuga Operating") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22Cayuga+Data%22+OR+%22Cayuga+Operating%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("Cayuga Data" OR "Cayuga Operating") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22Cayuga+Data%22+OR+%22Cayuga+Operating%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("Cayuga Data" OR "Cayuga Operating") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22Cayuga+Data%22+OR+%22Cayuga+Operating%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("Cayuga Data" OR "Cayuga Operating") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22Cayuga+Data%22+OR+%22Cayuga+Operating%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"Milliken 115kV Substation" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22Milliken+115kV+Substation%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1733" OR Q1733 OR "Queue #1733" OR 1733 OR "Cayuga Data")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231733%22+OR+Q1733+OR+%22Queue+%231733%22+OR+1733+OR+%22Cayuga+Data%22%29) |

### 108. IESO 2025-856 — Richmond Hill MTS #3 · 153 MW · ON

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | ALECTRA UTILITIES CORPORATION — Developer Not Matched To Known List |
| Point of interconnection | not published by the source register |
| Location field | IESO electrical zone "Toronto" (a grid region, not a municipality) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "planning committee" OR "committee of the whole") minutes ("Richmond Hill MTS #3" OR "ALECTRA UTILITIES") Ontario`](https://www.google.com/search?q=%28council+OR+%22planning+committee%22+OR+%22committee+of+the+whole%22%29+minutes+%28%22Richmond+Hill+MTS+%233%22+OR+%22ALECTRA+UTILITIES%22%29+Ontario) |
| Municipal · Zoning & development applications | [`("zoning by-law amendment" OR "official plan amendment" OR "site plan" OR "minister's zoning order") ("Richmond Hill MTS #3" OR "ALECTRA UTILITIES") Ontario`](https://www.google.com/search?q=%28%22zoning+by-law+amendment%22+OR+%22official+plan+amendment%22+OR+%22site+plan%22+OR+%22minister%27s+zoning+order%22%29+%28%22Richmond+Hill+MTS+%233%22+OR+%22ALECTRA+UTILITIES%22%29+Ontario) |
| Environmental / regulator · Environmental registry / permits | [`site:ero.ontario.ca ("Richmond Hill MTS #3" OR "ALECTRA UTILITIES") Ontario`](https://www.google.com/search?q=site%3Aero.ontario.ca+%28%22Richmond+Hill+MTS+%233%22+OR+%22ALECTRA+UTILITIES%22%29+Ontario) |
| Environmental / regulator · Utility-commission / siting filings | [`site:oeb.ca ("Richmond Hill MTS #3" OR "ALECTRA UTILITIES") Ontario`](https://www.google.com/search?q=site%3Aoeb.ca+%28%22Richmond+Hill+MTS+%233%22+OR+%22ALECTRA+UTILITIES%22%29+Ontario) |
| Substation · RTO / ISO documents | [`site:ieso.ca ("2025-856" OR "Richmond Hill MTS #3")`](https://www.google.com/search?q=site%3Aieso.ca+%28%222025-856%22+OR+%22Richmond+Hill+MTS+%233%22%29) |

### 109. IESO 2025-832 — Enova #11 TS: Waterloo MTS3 Expansion · 150 MW · ON

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | ENOVA POWER CORP. — Developer Not Matched To Known List |
| Point of interconnection | not published by the source register |
| Location field | IESO electrical zone "Southwest" (a grid region, not a municipality) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "planning committee" OR "committee of the whole") minutes ("Enova #11 TS: Waterloo MTS3 Expansion" OR "ENOVA POWER") Ontario`](https://www.google.com/search?q=%28council+OR+%22planning+committee%22+OR+%22committee+of+the+whole%22%29+minutes+%28%22Enova+%2311+TS%3A+Waterloo+MTS3+Expansion%22+OR+%22ENOVA+POWER%22%29+Ontario) |
| Municipal · Zoning & development applications | [`("zoning by-law amendment" OR "official plan amendment" OR "site plan" OR "minister's zoning order") ("Enova #11 TS: Waterloo MTS3 Expansion" OR "ENOVA POWER") Ontario`](https://www.google.com/search?q=%28%22zoning+by-law+amendment%22+OR+%22official+plan+amendment%22+OR+%22site+plan%22+OR+%22minister%27s+zoning+order%22%29+%28%22Enova+%2311+TS%3A+Waterloo+MTS3+Expansion%22+OR+%22ENOVA+POWER%22%29+Ontario) |
| Environmental / regulator · Environmental registry / permits | [`site:ero.ontario.ca ("Enova #11 TS: Waterloo MTS3 Expansion" OR "ENOVA POWER") Ontario`](https://www.google.com/search?q=site%3Aero.ontario.ca+%28%22Enova+%2311+TS%3A+Waterloo+MTS3+Expansion%22+OR+%22ENOVA+POWER%22%29+Ontario) |
| Environmental / regulator · Utility-commission / siting filings | [`site:oeb.ca ("Enova #11 TS: Waterloo MTS3 Expansion" OR "ENOVA POWER") Ontario`](https://www.google.com/search?q=site%3Aoeb.ca+%28%22Enova+%2311+TS%3A+Waterloo+MTS3+Expansion%22+OR+%22ENOVA+POWER%22%29+Ontario) |
| Substation · RTO / ISO documents | [`site:ieso.ca ("2025-832" OR "Enova #11 TS: Waterloo MTS3 Expansion")`](https://www.google.com/search?q=site%3Aieso.ca+%28%222025-832%22+OR+%22Enova+%2311+TS%3A+Waterloo+MTS3+Expansion%22%29) |

### 110. IESO 2026-873 — Bell AI - Sovereign Canadian Data Center · 150 MW · ON

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | TrueNorth Sustainable Infrastructure Inc. — Developer Not Matched To Known List |
| Point of interconnection | not published by the source register |
| Location field | IESO electrical zone "West" (a grid region, not a municipality) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "planning committee" OR "committee of the whole") minutes ("Bell AI - Sovereign Canadian Data Center" OR "TrueNorth Sustainable Infrastructure") Ontario`](https://www.google.com/search?q=%28council+OR+%22planning+committee%22+OR+%22committee+of+the+whole%22%29+minutes+%28%22Bell+AI+-+Sovereign+Canadian+Data+Center%22+OR+%22TrueNorth+Sustainable+Infrastructure%22%29+Ontario) |
| Municipal · Zoning & development applications | [`("zoning by-law amendment" OR "official plan amendment" OR "site plan" OR "minister's zoning order") ("Bell AI - Sovereign Canadian Data Center" OR "TrueNorth Sustainable Infrastructure") Ontario`](https://www.google.com/search?q=%28%22zoning+by-law+amendment%22+OR+%22official+plan+amendment%22+OR+%22site+plan%22+OR+%22minister%27s+zoning+order%22%29+%28%22Bell+AI+-+Sovereign+Canadian+Data+Center%22+OR+%22TrueNorth+Sustainable+Infrastructure%22%29+Ontario) |
| Environmental / regulator · Environmental registry / permits | [`site:ero.ontario.ca ("Bell AI - Sovereign Canadian Data Center" OR "TrueNorth Sustainable Infrastructure") Ontario`](https://www.google.com/search?q=site%3Aero.ontario.ca+%28%22Bell+AI+-+Sovereign+Canadian+Data+Center%22+OR+%22TrueNorth+Sustainable+Infrastructure%22%29+Ontario) |
| Environmental / regulator · Utility-commission / siting filings | [`site:oeb.ca ("Bell AI - Sovereign Canadian Data Center" OR "TrueNorth Sustainable Infrastructure") Ontario`](https://www.google.com/search?q=site%3Aoeb.ca+%28%22Bell+AI+-+Sovereign+Canadian+Data+Center%22+OR+%22TrueNorth+Sustainable+Infrastructure%22%29+Ontario) |
| Substation · RTO / ISO documents | [`site:ieso.ca ("2026-873" OR "Bell AI - Sovereign Canadian Data Center")`](https://www.google.com/search?q=site%3Aieso.ca+%28%222026-873%22+OR+%22Bell+AI+-+Sovereign+Canadian+Data+Center%22%29) |

### 111. MISO S1052 — (no project name published) · 150 MW · IL

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | Neoga South 138kV |
| Location field | county field "Cumberland", Illinois |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "Neoga South 138kV" "Cumberland" County Illinois ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22Neoga+South+138kV%22+%22Cumberland%22+County+Illinois+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "Neoga South 138kV" "Cumberland" County Illinois ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22Neoga+South+138kV%22+%22Cumberland%22+County+Illinois+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`site:epa.illinois.gov "Cumberland" County Illinois ("data center" OR "large load")`](https://www.google.com/search?q=site%3Aepa.illinois.gov+%22Cumberland%22+County+Illinois+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`site:icc.illinois.gov "Neoga South 138kV" "Cumberland" County Illinois ("data center" OR "large load")`](https://www.google.com/search?q=site%3Aicc.illinois.gov+%22Neoga+South+138kV%22+%22Cumberland%22+County+Illinois+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"Neoga South 138kV" (substation OR interconnection OR "facilities study" OR "system impact study") Illinois`](https://www.google.com/search?q=%22Neoga+South+138kV%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Illinois) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1052`](https://www.google.com/search?q=site%3Amisoenergy.org+S1052) |

### 112. MISO S1068 — (no project name published) · 150 MW · MI

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | Cronk Road |
| Location field | county field "Hillsdale", Michigan |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "Cronk Road" "Hillsdale" County Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22Cronk+Road%22+%22Hillsdale%22+County+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "Cronk Road" "Hillsdale" County Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22Cronk+Road%22+%22Hillsdale%22+County+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`(EGLE OR "Michigan Department of Environment, Great Lakes, and Energy") ("air permit" OR "construction permit" OR "environmental assessment") "Hillsdale" County Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28EGLE+OR+%22Michigan+Department+of+Environment%2C+Great+Lakes%2C+and+Energy%22%29+%28%22air+permit%22+OR+%22construction+permit%22+OR+%22environmental+assessment%22%29+%22Hillsdale%22+County+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`("Michigan Public Service Commission" OR MPSC) ("certificate of public convenience" OR siting OR "large load") "Cronk Road" "Hillsdale" County Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28%22Michigan+Public+Service+Commission%22+OR+MPSC%29+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+%22Cronk+Road%22+%22Hillsdale%22+County+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"Cronk Road" (substation OR interconnection OR "facilities study" OR "system impact study") Michigan`](https://www.google.com/search?q=%22Cronk+Road%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Michigan) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1068`](https://www.google.com/search?q=site%3Amisoenergy.org+S1068) |

### 113. MISO S1137 — (no project name published) · 150 MW · LA

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | county not published, Louisiana |
| Transmission owner | ENTERGY LOUISIANA, LLC |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes Louisiana ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+Louisiana+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") Louisiana ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+Louisiana+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`site:deq.louisiana.gov Louisiana ("data center" OR "large load")`](https://www.google.com/search?q=site%3Adeq.louisiana.gov+Louisiana+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`site:lpsc.louisiana.gov Louisiana ("data center" OR "large load")`](https://www.google.com/search?q=site%3Alpsc.louisiana.gov+Louisiana+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1137`](https://www.google.com/search?q=site%3Amisoenergy.org+S1137) |
| Substation · Transmission-owner filings | [`"ENTERGY LOUISIANA, LLC" ("large load" OR "data center" OR interconnection OR substation) Louisiana`](https://www.google.com/search?q=%22ENTERGY+LOUISIANA%2C+LLC%22+%28%22large+load%22+OR+%22data+center%22+OR+interconnection+OR+substation%29+Louisiana) |

### 114. MISO S1154 — (no project name published) · 150 MW · MN

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | county not published, Minnesota |
| Transmission owner | GREAT RIVER ENERGY |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes Minnesota ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+Minnesota+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") Minnesota ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+Minnesota+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`("Minnesota Pollution Control Agency" OR MPCA) ("air permit" OR "construction permit" OR "environmental assessment") Minnesota ("data center" OR "large load")`](https://www.google.com/search?q=%28%22Minnesota+Pollution+Control+Agency%22+OR+MPCA%29+%28%22air+permit%22+OR+%22construction+permit%22+OR+%22environmental+assessment%22%29+Minnesota+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`"Minnesota Public Utilities Commission" ("certificate of public convenience" OR siting OR "large load") Minnesota ("data center" OR "large load")`](https://www.google.com/search?q=%22Minnesota+Public+Utilities+Commission%22+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+Minnesota+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1154`](https://www.google.com/search?q=site%3Amisoenergy.org+S1154) |
| Substation · Transmission-owner filings | [`"GREAT RIVER ENERGY" ("large load" OR "data center" OR interconnection OR substation) Minnesota`](https://www.google.com/search?q=%22GREAT+RIVER+ENERGY%22+%28%22large+load%22+OR+%22data+center%22+OR+interconnection+OR+substation%29+Minnesota) |

### 115. MISO S1160 — (no project name published) · 150 MW · SD

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | county not published, South Dakota |
| Transmission owner | OTTER TAIL POWER COMPANY |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes South Dakota ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+South+Dakota+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") South Dakota ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+South+Dakota+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`site:danr.sd.gov South Dakota ("data center" OR "large load")`](https://www.google.com/search?q=site%3Adanr.sd.gov+South+Dakota+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`site:puc.sd.gov South Dakota ("data center" OR "large load")`](https://www.google.com/search?q=site%3Apuc.sd.gov+South+Dakota+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1160`](https://www.google.com/search?q=site%3Amisoenergy.org+S1160) |
| Substation · Transmission-owner filings | [`"OTTER TAIL POWER COMPANY" ("large load" OR "data center" OR interconnection OR substation) South Dakota`](https://www.google.com/search?q=%22OTTER+TAIL+POWER+COMPANY%22+%28%22large+load%22+OR+%22data+center%22+OR+interconnection+OR+substation%29+South+Dakota) |

### 116. NYISO 1760 — iPark 84 Data Center Interconnection · 150 MW · NY

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | iPark East Fishkill LLC — Developer Not Matched To Known List |
| Point of interconnection | New 115kV line from CHG&E East Fishkill Substation |
| Location field | county field "Dutchess", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("iPark 84 Data Center Interconnection" OR "iPark East Fishkill") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22iPark+84+Data+Center+Interconnection%22+OR+%22iPark+East+Fishkill%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("iPark 84 Data Center Interconnection" OR "iPark East Fishkill") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22iPark+84+Data+Center+Interconnection%22+OR+%22iPark+East+Fishkill%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("iPark 84 Data Center Interconnection" OR "iPark East Fishkill") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22iPark+84+Data+Center+Interconnection%22+OR+%22iPark+East+Fishkill%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("iPark 84 Data Center Interconnection" OR "iPark East Fishkill") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22iPark+84+Data+Center+Interconnection%22+OR+%22iPark+East+Fishkill%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"New 115kV line from CHG&E East Fishkill Substation" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22New+115kV+line+from+CHG%26E+East+Fishkill+Substation%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1760" OR Q1760 OR "Queue #1760" OR 1760 OR "iPark 84 Data Center Interconnection")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231760%22+OR+Q1760+OR+%22Queue+%231760%22+OR+1760+OR+%22iPark+84+Data+Center+Interconnection%22%29) |

### 117. NYISO 1761 — NYISO Load Interconnection Process - Data Center Inquiry · 150 MW · NY

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | URI TALY — Developer Not Matched To Known List |
| Point of interconnection | Broad Street 34.5 kV Line 93 |
| Location field | county field "Horseheads", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("NYISO Load Interconnection Process - Data" OR "URI TALY") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22NYISO+Load+Interconnection+Process+-+Data%22+OR+%22URI+TALY%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("NYISO Load Interconnection Process - Data" OR "URI TALY") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22NYISO+Load+Interconnection+Process+-+Data%22+OR+%22URI+TALY%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("NYISO Load Interconnection Process - Data" OR "URI TALY") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22NYISO+Load+Interconnection+Process+-+Data%22+OR+%22URI+TALY%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("NYISO Load Interconnection Process - Data" OR "URI TALY") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22NYISO+Load+Interconnection+Process+-+Data%22+OR+%22URI+TALY%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"Broad Street 34.5 kV Line 93" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22Broad+Street+34.5+kV+Line+93%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1761" OR Q1761 OR "Queue #1761" OR 1761 OR "NYISO Load Interconnection Process - Data Center Inquiry")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231761%22+OR+Q1761+OR+%22Queue+%231761%22+OR+1761+OR+%22NYISO+Load+Interconnection+Process+-+Data+Center+Inquiry%22%29) |

### 118. NYISO 1681 — Niagara Digital Campus · 140 MW · NY

| | |
|---|---|
| Status (as published) | Facilities Study |
| Developer (as published) | Niagara Falls Redevelopment LLC — Developer Not Matched To Known List |
| Point of interconnection | Adams to Packard 115kV lines 187 and 188 |
| Location field | county field "Niagara", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("Niagara Digital Campus" OR "Niagara Falls Redevelopment") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22Niagara+Digital+Campus%22+OR+%22Niagara+Falls+Redevelopment%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("Niagara Digital Campus" OR "Niagara Falls Redevelopment") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22Niagara+Digital+Campus%22+OR+%22Niagara+Falls+Redevelopment%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("Niagara Digital Campus" OR "Niagara Falls Redevelopment") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22Niagara+Digital+Campus%22+OR+%22Niagara+Falls+Redevelopment%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("Niagara Digital Campus" OR "Niagara Falls Redevelopment") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22Niagara+Digital+Campus%22+OR+%22Niagara+Falls+Redevelopment%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"Adams to Packard 115kV lines 187 and 188" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22Adams+to+Packard+115kV+lines+187+and+188%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1681" OR Q1681 OR "Queue #1681" OR 1681 OR "Niagara Digital Campus")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231681%22+OR+Q1681+OR+%22Queue+%231681%22+OR+1681+OR+%22Niagara+Digital+Campus%22%29) |

### 119. MISO S1152 — (no project name published) · 139 MW · MO

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | county not published, Missouri |
| Transmission owner | AMEREN MISSOURI |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes Missouri ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+Missouri+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") Missouri ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+Missouri+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`site:dnr.mo.gov Missouri ("data center" OR "large load")`](https://www.google.com/search?q=site%3Adnr.mo.gov+Missouri+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`site:psc.mo.gov Missouri ("data center" OR "large load")`](https://www.google.com/search?q=site%3Apsc.mo.gov+Missouri+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1152`](https://www.google.com/search?q=site%3Amisoenergy.org+S1152) |
| Substation · Transmission-owner filings | [`"AMEREN MISSOURI" ("large load" OR "data center" OR interconnection OR substation) Missouri`](https://www.google.com/search?q=%22AMEREN+MISSOURI%22+%28%22large+load%22+OR+%22data+center%22+OR+interconnection+OR+substation%29+Missouri) |

### 120. MISO S1143 — (no project name published) · 135 MW · IL

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | county not published, Illinois |
| Transmission owner | AMEREN ILLINOIS |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes Illinois ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+Illinois+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") Illinois ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+Illinois+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`site:epa.illinois.gov Illinois ("data center" OR "large load")`](https://www.google.com/search?q=site%3Aepa.illinois.gov+Illinois+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`site:icc.illinois.gov Illinois ("data center" OR "large load")`](https://www.google.com/search?q=site%3Aicc.illinois.gov+Illinois+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1143`](https://www.google.com/search?q=site%3Amisoenergy.org+S1143) |
| Substation · Transmission-owner filings | [`"AMEREN ILLINOIS" ("large load" OR "data center" OR interconnection OR substation) Illinois`](https://www.google.com/search?q=%22AMEREN+ILLINOIS%22+%28%22large+load%22+OR+%22data+center%22+OR+interconnection+OR+substation%29+Illinois) |

### 121. MISO S1147 — (no project name published) · 132 MW · MI

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | county not published, Michigan |
| Transmission owner | METC |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`(EGLE OR "Michigan Department of Environment, Great Lakes, and Energy") ("air permit" OR "construction permit" OR "environmental assessment") Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28EGLE+OR+%22Michigan+Department+of+Environment%2C+Great+Lakes%2C+and+Energy%22%29+%28%22air+permit%22+OR+%22construction+permit%22+OR+%22environmental+assessment%22%29+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`("Michigan Public Service Commission" OR MPSC) ("certificate of public convenience" OR siting OR "large load") Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28%22Michigan+Public+Service+Commission%22+OR+MPSC%29+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1147`](https://www.google.com/search?q=site%3Amisoenergy.org+S1147) |
| Substation · Transmission-owner filings | [`"METC" ("large load" OR "data center" OR interconnection OR substation) Michigan`](https://www.google.com/search?q=%22METC%22+%28%22large+load%22+OR+%22data+center%22+OR+interconnection+OR+substation%29+Michigan) |

### 122. IESO 2025-854 — CPXP Sarnia Hydrogen Facility · 130 MW · ON

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | Canadian Power to X Partners — Developer Not Matched To Known List |
| Point of interconnection | not published by the source register |
| Location field | IESO electrical zone "West" (a grid region, not a municipality) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "planning committee" OR "committee of the whole") minutes ("CPXP Sarnia Hydrogen Facility" OR "Canadian Power to X Partners") Ontario`](https://www.google.com/search?q=%28council+OR+%22planning+committee%22+OR+%22committee+of+the+whole%22%29+minutes+%28%22CPXP+Sarnia+Hydrogen+Facility%22+OR+%22Canadian+Power+to+X+Partners%22%29+Ontario) |
| Municipal · Zoning & development applications | [`("zoning by-law amendment" OR "official plan amendment" OR "site plan" OR "minister's zoning order") ("CPXP Sarnia Hydrogen Facility" OR "Canadian Power to X Partners") Ontario`](https://www.google.com/search?q=%28%22zoning+by-law+amendment%22+OR+%22official+plan+amendment%22+OR+%22site+plan%22+OR+%22minister%27s+zoning+order%22%29+%28%22CPXP+Sarnia+Hydrogen+Facility%22+OR+%22Canadian+Power+to+X+Partners%22%29+Ontario) |
| Environmental / regulator · Environmental registry / permits | [`site:ero.ontario.ca ("CPXP Sarnia Hydrogen Facility" OR "Canadian Power to X Partners") Ontario`](https://www.google.com/search?q=site%3Aero.ontario.ca+%28%22CPXP+Sarnia+Hydrogen+Facility%22+OR+%22Canadian+Power+to+X+Partners%22%29+Ontario) |
| Environmental / regulator · Utility-commission / siting filings | [`site:oeb.ca ("CPXP Sarnia Hydrogen Facility" OR "Canadian Power to X Partners") Ontario`](https://www.google.com/search?q=site%3Aoeb.ca+%28%22CPXP+Sarnia+Hydrogen+Facility%22+OR+%22Canadian+Power+to+X+Partners%22%29+Ontario) |
| Substation · RTO / ISO documents | [`site:ieso.ca ("2025-854" OR "CPXP Sarnia Hydrogen Facility")`](https://www.google.com/search?q=site%3Aieso.ca+%28%222025-854%22+OR+%22CPXP+Sarnia+Hydrogen+Facility%22%29) |

### 123. MISO S1146 — (no project name published) · 125 MW · MI

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | DU PONT - WHITE LAKE 138.0kV |
| Location field | county field "Muskegon", Michigan |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "DU PONT - WHITE LAKE 138.0kV" "Muskegon" County Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22DU+PONT+-+WHITE+LAKE+138.0kV%22+%22Muskegon%22+County+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "DU PONT - WHITE LAKE 138.0kV" "Muskegon" County Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22DU+PONT+-+WHITE+LAKE+138.0kV%22+%22Muskegon%22+County+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`(EGLE OR "Michigan Department of Environment, Great Lakes, and Energy") ("air permit" OR "construction permit" OR "environmental assessment") "Muskegon" County Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28EGLE+OR+%22Michigan+Department+of+Environment%2C+Great+Lakes%2C+and+Energy%22%29+%28%22air+permit%22+OR+%22construction+permit%22+OR+%22environmental+assessment%22%29+%22Muskegon%22+County+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`("Michigan Public Service Commission" OR MPSC) ("certificate of public convenience" OR siting OR "large load") "DU PONT - WHITE LAKE 138.0kV" "Muskegon" County Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28%22Michigan+Public+Service+Commission%22+OR+MPSC%29+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+%22DU+PONT+-+WHITE+LAKE+138.0kV%22+%22Muskegon%22+County+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"DU PONT - WHITE LAKE 138.0kV" (substation OR interconnection OR "facilities study" OR "system impact study") Michigan`](https://www.google.com/search?q=%22DU+PONT+-+WHITE+LAKE+138.0kV%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Michigan) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1146`](https://www.google.com/search?q=site%3Amisoenergy.org+S1146) |

### 124. SPP GEN-2025-SR13 — (no project name published) · 125 MW · OK

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | Seminole 138 kV Substation |
| Location field | county field "Konawa", Oklahoma |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "Seminole 138 kV Substation" "Konawa" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22Seminole+138+kV+Substation%22+%22Konawa%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "Seminole 138 kV Substation" "Konawa" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22Seminole+138+kV+Substation%22+%22Konawa%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`("Oklahoma Department of Environmental Quality" OR "Oklahoma DEQ") ("air permit" OR "construction permit" OR "environmental assessment") "Konawa" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%28%22Oklahoma+Department+of+Environmental+Quality%22+OR+%22Oklahoma+DEQ%22%29+%28%22air+permit%22+OR+%22construction+permit%22+OR+%22environmental+assessment%22%29+%22Konawa%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`"Oklahoma Corporation Commission" ("certificate of public convenience" OR siting OR "large load") "Seminole 138 kV Substation" "Konawa" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%22Oklahoma+Corporation+Commission%22+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+%22Seminole+138+kV+Substation%22+%22Konawa%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"Seminole 138 kV Substation" (substation OR interconnection OR "facilities study" OR "system impact study") Oklahoma`](https://www.google.com/search?q=%22Seminole+138+kV+Substation%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Oklahoma) |
| Substation · RTO / ISO documents | [`site:spp.org "GEN-2025-SR13"`](https://www.google.com/search?q=site%3Aspp.org+%22GEN-2025-SR13%22) |

### 125. SPP GEN-2025-SR15 — (no project name published) · 125 MW · OK

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | McClain Substation |
| Location field | county field "Newcastle", Oklahoma |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "McClain Substation" "Newcastle" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22McClain+Substation%22+%22Newcastle%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "McClain Substation" "Newcastle" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22McClain+Substation%22+%22Newcastle%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`("Oklahoma Department of Environmental Quality" OR "Oklahoma DEQ") ("air permit" OR "construction permit" OR "environmental assessment") "Newcastle" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%28%22Oklahoma+Department+of+Environmental+Quality%22+OR+%22Oklahoma+DEQ%22%29+%28%22air+permit%22+OR+%22construction+permit%22+OR+%22environmental+assessment%22%29+%22Newcastle%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`"Oklahoma Corporation Commission" ("certificate of public convenience" OR siting OR "large load") "McClain Substation" "Newcastle" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%22Oklahoma+Corporation+Commission%22+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+%22McClain+Substation%22+%22Newcastle%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"McClain Substation" (substation OR interconnection OR "facilities study" OR "system impact study") Oklahoma`](https://www.google.com/search?q=%22McClain+Substation%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Oklahoma) |
| Substation · RTO / ISO documents | [`site:spp.org "GEN-2025-SR15"`](https://www.google.com/search?q=site%3Aspp.org+%22GEN-2025-SR15%22) |

### 126. IESO 2025-865 — GTAA MTS · 120 MW · ON

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | ALECTRA UTILITIES CORPORATION — Developer Not Matched To Known List |
| Point of interconnection | not published by the source register |
| Location field | IESO electrical zone "Toronto" (a grid region, not a municipality) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "planning committee" OR "committee of the whole") minutes ("GTAA MTS" OR "ALECTRA UTILITIES") Ontario`](https://www.google.com/search?q=%28council+OR+%22planning+committee%22+OR+%22committee+of+the+whole%22%29+minutes+%28%22GTAA+MTS%22+OR+%22ALECTRA+UTILITIES%22%29+Ontario) |
| Municipal · Zoning & development applications | [`("zoning by-law amendment" OR "official plan amendment" OR "site plan" OR "minister's zoning order") ("GTAA MTS" OR "ALECTRA UTILITIES") Ontario`](https://www.google.com/search?q=%28%22zoning+by-law+amendment%22+OR+%22official+plan+amendment%22+OR+%22site+plan%22+OR+%22minister%27s+zoning+order%22%29+%28%22GTAA+MTS%22+OR+%22ALECTRA+UTILITIES%22%29+Ontario) |
| Environmental / regulator · Environmental registry / permits | [`site:ero.ontario.ca ("GTAA MTS" OR "ALECTRA UTILITIES") Ontario`](https://www.google.com/search?q=site%3Aero.ontario.ca+%28%22GTAA+MTS%22+OR+%22ALECTRA+UTILITIES%22%29+Ontario) |
| Environmental / regulator · Utility-commission / siting filings | [`site:oeb.ca ("GTAA MTS" OR "ALECTRA UTILITIES") Ontario`](https://www.google.com/search?q=site%3Aoeb.ca+%28%22GTAA+MTS%22+OR+%22ALECTRA+UTILITIES%22%29+Ontario) |
| Substation · RTO / ISO documents | [`site:ieso.ca ("2025-865" OR "GTAA MTS")`](https://www.google.com/search?q=site%3Aieso.ca+%28%222025-865%22+OR+%22GTAA+MTS%22%29) |

### 127. MISO S1047 — (no project name published) · 120 MW · SD

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | Big Stone South 230kV |
| Location field | county field "Codington", South Dakota |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "Big Stone South 230kV" "Codington" County South Dakota ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22Big+Stone+South+230kV%22+%22Codington%22+County+South+Dakota+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "Big Stone South 230kV" "Codington" County South Dakota ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22Big+Stone+South+230kV%22+%22Codington%22+County+South+Dakota+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`site:danr.sd.gov "Codington" County South Dakota ("data center" OR "large load")`](https://www.google.com/search?q=site%3Adanr.sd.gov+%22Codington%22+County+South+Dakota+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`site:puc.sd.gov "Big Stone South 230kV" "Codington" County South Dakota ("data center" OR "large load")`](https://www.google.com/search?q=site%3Apuc.sd.gov+%22Big+Stone+South+230kV%22+%22Codington%22+County+South+Dakota+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"Big Stone South 230kV" (substation OR interconnection OR "facilities study" OR "system impact study") South Dakota`](https://www.google.com/search?q=%22Big+Stone+South+230kV%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+South+Dakota) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1047`](https://www.google.com/search?q=site%3Amisoenergy.org+S1047) |

### 128. NYISO 1315 — SDC St. Lawrence · 120 MW · NY

| | |
|---|---|
| Status (as published) | Facilities Study |
| Developer (as published) | Sabey Data Center Properties, LLC — Developer Not Matched To Known List |
| Point of interconnection | Moses-Reynolds MRG-1 and Moses-Reynolds MRG-2 at 115kV |
| Location field | county field "St. Lawrence", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("SDC St. Lawrence" OR "Sabey Data Center Properties") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22SDC+St.+Lawrence%22+OR+%22Sabey+Data+Center+Properties%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("SDC St. Lawrence" OR "Sabey Data Center Properties") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22SDC+St.+Lawrence%22+OR+%22Sabey+Data+Center+Properties%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("SDC St. Lawrence" OR "Sabey Data Center Properties") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22SDC+St.+Lawrence%22+OR+%22Sabey+Data+Center+Properties%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("SDC St. Lawrence" OR "Sabey Data Center Properties") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22SDC+St.+Lawrence%22+OR+%22Sabey+Data+Center+Properties%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"Moses-Reynolds MRG-1 and Moses-Reynolds MRG-2 at 115kV" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22Moses-Reynolds+MRG-1+and+Moses-Reynolds+MRG-2+at+115kV%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1315" OR Q1315 OR "Queue #1315" OR 1315 OR "SDC St. Lawrence")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231315%22+OR+Q1315+OR+%22Queue+%231315%22+OR+1315+OR+%22SDC+St.+Lawrence%22%29) |

### 129. MISO S1166 — (no project name published) · 108.9 MW · MN

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | county not published, Minnesota |
| Transmission owner | NORTHERN STATES POWER COMPANY |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes Minnesota ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+Minnesota+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") Minnesota ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+Minnesota+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`("Minnesota Pollution Control Agency" OR MPCA) ("air permit" OR "construction permit" OR "environmental assessment") Minnesota ("data center" OR "large load")`](https://www.google.com/search?q=%28%22Minnesota+Pollution+Control+Agency%22+OR+MPCA%29+%28%22air+permit%22+OR+%22construction+permit%22+OR+%22environmental+assessment%22%29+Minnesota+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`"Minnesota Public Utilities Commission" ("certificate of public convenience" OR siting OR "large load") Minnesota ("data center" OR "large load")`](https://www.google.com/search?q=%22Minnesota+Public+Utilities+Commission%22+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+Minnesota+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1166`](https://www.google.com/search?q=site%3Amisoenergy.org+S1166) |
| Substation · Transmission-owner filings | [`"NORTHERN STATES POWER COMPANY" ("large load" OR "data center" OR interconnection OR substation) Minnesota`](https://www.google.com/search?q=%22NORTHERN+STATES+POWER+COMPANY%22+%28%22large+load%22+OR+%22data+center%22+OR+interconnection+OR+substation%29+Minnesota) |

### 130. SPP GEN-2024-003 — (no project name published) · 102.2 MW · AR

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | Fitzhugh 161kV |
| Location field | county field "Franklin", Arkansas |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "Fitzhugh 161kV" "Franklin" County Arkansas ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22Fitzhugh+161kV%22+%22Franklin%22+County+Arkansas+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "Fitzhugh 161kV" "Franklin" County Arkansas ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22Fitzhugh+161kV%22+%22Franklin%22+County+Arkansas+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`("Arkansas Division of Environmental Quality" OR ADEQ) ("air permit" OR "construction permit" OR "environmental assessment") "Franklin" County Arkansas ("data center" OR "large load")`](https://www.google.com/search?q=%28%22Arkansas+Division+of+Environmental+Quality%22+OR+ADEQ%29+%28%22air+permit%22+OR+%22construction+permit%22+OR+%22environmental+assessment%22%29+%22Franklin%22+County+Arkansas+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`"Arkansas Public Service Commission" ("certificate of public convenience" OR siting OR "large load") "Fitzhugh 161kV" "Franklin" County Arkansas ("data center" OR "large load")`](https://www.google.com/search?q=%22Arkansas+Public+Service+Commission%22+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+%22Fitzhugh+161kV%22+%22Franklin%22+County+Arkansas+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"Fitzhugh 161kV" (substation OR interconnection OR "facilities study" OR "system impact study") Arkansas`](https://www.google.com/search?q=%22Fitzhugh+161kV%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Arkansas) |
| Substation · RTO / ISO documents | [`site:spp.org "GEN-2024-003"`](https://www.google.com/search?q=site%3Aspp.org+%22GEN-2024-003%22) |

### 131. MISO S1059 — (no project name published) · 100.3 MW · MI

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | Dixon 120kV - Bus # 265182 |
| Location field | county field "Tuscola", Michigan |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "Dixon 120kV - Bus # 265182" "Tuscola" County Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22Dixon+120kV+-+Bus+%23+265182%22+%22Tuscola%22+County+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "Dixon 120kV - Bus # 265182" "Tuscola" County Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22Dixon+120kV+-+Bus+%23+265182%22+%22Tuscola%22+County+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`(EGLE OR "Michigan Department of Environment, Great Lakes, and Energy") ("air permit" OR "construction permit" OR "environmental assessment") "Tuscola" County Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28EGLE+OR+%22Michigan+Department+of+Environment%2C+Great+Lakes%2C+and+Energy%22%29+%28%22air+permit%22+OR+%22construction+permit%22+OR+%22environmental+assessment%22%29+%22Tuscola%22+County+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`("Michigan Public Service Commission" OR MPSC) ("certificate of public convenience" OR siting OR "large load") "Dixon 120kV - Bus # 265182" "Tuscola" County Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28%22Michigan+Public+Service+Commission%22+OR+MPSC%29+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+%22Dixon+120kV+-+Bus+%23+265182%22+%22Tuscola%22+County+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"Dixon 120kV - Bus # 265182" (substation OR interconnection OR "facilities study" OR "system impact study") Michigan`](https://www.google.com/search?q=%22Dixon+120kV+-+Bus+%23+265182%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Michigan) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1059`](https://www.google.com/search?q=site%3Amisoenergy.org+S1059) |

### 132. IESO 2024-812 — IBM Markham CTS - Load Increase · 100 MW · ON

| | |
|---|---|
| Status (as published) | IA in Progress |
| Developer (as published) | TDI 3600 Steeles East Inc. — Developer Not Matched To Known List |
| Point of interconnection | not published by the source register |
| Location field | IESO electrical zone "Toronto" (a grid region, not a municipality) |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`(council OR "planning committee" OR "committee of the whole") minutes ("IBM Markham CTS" OR "TDI 3600 Steeles East") Ontario`](https://www.google.com/search?q=%28council+OR+%22planning+committee%22+OR+%22committee+of+the+whole%22%29+minutes+%28%22IBM+Markham+CTS%22+OR+%22TDI+3600+Steeles+East%22%29+Ontario) |
| Municipal · Zoning & development applications | [`("zoning by-law amendment" OR "official plan amendment" OR "site plan" OR "minister's zoning order") ("IBM Markham CTS" OR "TDI 3600 Steeles East") Ontario`](https://www.google.com/search?q=%28%22zoning+by-law+amendment%22+OR+%22official+plan+amendment%22+OR+%22site+plan%22+OR+%22minister%27s+zoning+order%22%29+%28%22IBM+Markham+CTS%22+OR+%22TDI+3600+Steeles+East%22%29+Ontario) |
| Environmental / regulator · Environmental registry / permits | [`site:ero.ontario.ca ("IBM Markham CTS" OR "TDI 3600 Steeles East") Ontario`](https://www.google.com/search?q=site%3Aero.ontario.ca+%28%22IBM+Markham+CTS%22+OR+%22TDI+3600+Steeles+East%22%29+Ontario) |
| Environmental / regulator · Utility-commission / siting filings | [`site:oeb.ca ("IBM Markham CTS" OR "TDI 3600 Steeles East") Ontario`](https://www.google.com/search?q=site%3Aoeb.ca+%28%22IBM+Markham+CTS%22+OR+%22TDI+3600+Steeles+East%22%29+Ontario) |
| Substation · RTO / ISO documents | [`site:ieso.ca ("2024-812" OR "IBM Markham CTS - Load Increase")`](https://www.google.com/search?q=site%3Aieso.ca+%28%222024-812%22+OR+%22IBM+Markham+CTS+-+Load+Increase%22%29) |

### 133. MISO S1053 — (no project name published) · 100 MW · MN

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | Chisago County Substation |
| Location field | county field "Chisago", Minnesota |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "Chisago County Substation" "Chisago" County Minnesota ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22Chisago+County+Substation%22+%22Chisago%22+County+Minnesota+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "Chisago County Substation" "Chisago" County Minnesota ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22Chisago+County+Substation%22+%22Chisago%22+County+Minnesota+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`("Minnesota Pollution Control Agency" OR MPCA) ("air permit" OR "construction permit" OR "environmental assessment") "Chisago" County Minnesota ("data center" OR "large load")`](https://www.google.com/search?q=%28%22Minnesota+Pollution+Control+Agency%22+OR+MPCA%29+%28%22air+permit%22+OR+%22construction+permit%22+OR+%22environmental+assessment%22%29+%22Chisago%22+County+Minnesota+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`"Minnesota Public Utilities Commission" ("certificate of public convenience" OR siting OR "large load") "Chisago County Substation" "Chisago" County Minnesota ("data center" OR "large load")`](https://www.google.com/search?q=%22Minnesota+Public+Utilities+Commission%22+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+%22Chisago+County+Substation%22+%22Chisago%22+County+Minnesota+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"Chisago County Substation" (substation OR interconnection OR "facilities study" OR "system impact study") Minnesota`](https://www.google.com/search?q=%22Chisago+County+Substation%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Minnesota) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1053`](https://www.google.com/search?q=site%3Amisoenergy.org+S1053) |

### 134. MISO S1075 — (no project name published) · 100 MW · IN

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | Hinshaw 345 kV |
| Location field | county field "Jasper and Starke", Indiana |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "Hinshaw 345 kV" "Jasper and Starke" County Indiana ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22Hinshaw+345+kV%22+%22Jasper+and+Starke%22+County+Indiana+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "Hinshaw 345 kV" "Jasper and Starke" County Indiana ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22Hinshaw+345+kV%22+%22Jasper+and+Starke%22+County+Indiana+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`(IDEM OR "Indiana Department of Environmental Management") ("air permit" OR "construction permit" OR "environmental assessment") "Jasper and Starke" County Indiana ("data center" OR "large load")`](https://www.google.com/search?q=%28IDEM+OR+%22Indiana+Department+of+Environmental+Management%22%29+%28%22air+permit%22+OR+%22construction+permit%22+OR+%22environmental+assessment%22%29+%22Jasper+and+Starke%22+County+Indiana+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`("Indiana Utility Regulatory Commission" OR IURC) ("certificate of public convenience" OR siting OR "large load") "Hinshaw 345 kV" "Jasper and Starke" County Indiana ("data center" OR "large load")`](https://www.google.com/search?q=%28%22Indiana+Utility+Regulatory+Commission%22+OR+IURC%29+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+%22Hinshaw+345+kV%22+%22Jasper+and+Starke%22+County+Indiana+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"Hinshaw 345 kV" (substation OR interconnection OR "facilities study" OR "system impact study") Indiana`](https://www.google.com/search?q=%22Hinshaw+345+kV%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Indiana) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1075`](https://www.google.com/search?q=site%3Amisoenergy.org+S1075) |

### 135. MISO S1136 — (no project name published) · 100 MW · MI

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | county not published, Michigan |
| Transmission owner | METC |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`(EGLE OR "Michigan Department of Environment, Great Lakes, and Energy") ("air permit" OR "construction permit" OR "environmental assessment") Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28EGLE+OR+%22Michigan+Department+of+Environment%2C+Great+Lakes%2C+and+Energy%22%29+%28%22air+permit%22+OR+%22construction+permit%22+OR+%22environmental+assessment%22%29+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`("Michigan Public Service Commission" OR MPSC) ("certificate of public convenience" OR siting OR "large load") Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28%22Michigan+Public+Service+Commission%22+OR+MPSC%29+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1136`](https://www.google.com/search?q=site%3Amisoenergy.org+S1136) |
| Substation · Transmission-owner filings | [`"METC" ("large load" OR "data center" OR interconnection OR substation) Michigan`](https://www.google.com/search?q=%22METC%22+%28%22large+load%22+OR+%22data+center%22+OR+interconnection+OR+substation%29+Michigan) |

### 136. MISO S1138 — (no project name published) · 100 MW · MI

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | county not published, Michigan |
| Transmission owner | METC |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`(EGLE OR "Michigan Department of Environment, Great Lakes, and Energy") ("air permit" OR "construction permit" OR "environmental assessment") Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28EGLE+OR+%22Michigan+Department+of+Environment%2C+Great+Lakes%2C+and+Energy%22%29+%28%22air+permit%22+OR+%22construction+permit%22+OR+%22environmental+assessment%22%29+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`("Michigan Public Service Commission" OR MPSC) ("certificate of public convenience" OR siting OR "large load") Michigan ("data center" OR "large load")`](https://www.google.com/search?q=%28%22Michigan+Public+Service+Commission%22+OR+MPSC%29+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+Michigan+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1138`](https://www.google.com/search?q=site%3Amisoenergy.org+S1138) |
| Substation · Transmission-owner filings | [`"METC" ("large load" OR "data center" OR interconnection OR substation) Michigan`](https://www.google.com/search?q=%22METC%22+%28%22large+load%22+OR+%22data+center%22+OR+interconnection+OR+substation%29+Michigan) |

### 137. MISO S1159 — (no project name published) · 100 MW · WI

| | |
|---|---|
| Status (as published) | Active |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | not published by the source register |
| Location field | county not published, Wisconsin |
| Transmission owner | AMERICAN TRANSMISSION COMPANY |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes Wisconsin ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+Wisconsin+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") Wisconsin ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+Wisconsin+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`site:dnr.wisconsin.gov Wisconsin ("data center" OR "large load")`](https://www.google.com/search?q=site%3Adnr.wisconsin.gov+Wisconsin+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`site:psc.wi.gov Wisconsin ("data center" OR "large load")`](https://www.google.com/search?q=site%3Apsc.wi.gov+Wisconsin+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · RTO / ISO documents | [`site:misoenergy.org S1159`](https://www.google.com/search?q=site%3Amisoenergy.org+S1159) |
| Substation · Transmission-owner filings | [`"AMERICAN TRANSMISSION COMPANY" ("large load" OR "data center" OR interconnection OR substation) Wisconsin`](https://www.google.com/search?q=%22AMERICAN+TRANSMISSION+COMPANY%22+%28%22large+load%22+OR+%22data+center%22+OR+interconnection+OR+substation%29+Wisconsin) |

### 138. NYISO 1735 — Remington Factory Redevelopment · 100 MW · NY

| | |
|---|---|
| Status (as published) | Under Study |
| Developer (as published) | Turin Management LLC — Developer Not Matched To Known List |
| Point of interconnection | Ilion Municipal 115kV substation |
| Location field | county field "Herkimer", New York |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning board" OR "town board" OR "zoning board of appeals" OR "county legislature") minutes ("Remington Factory Redevelopment" OR "Turin Management") New York`](https://www.google.com/search?q=%28%22planning+board%22+OR+%22town+board%22+OR+%22zoning+board+of+appeals%22+OR+%22county+legislature%22%29+minutes+%28%22Remington+Factory+Redevelopment%22+OR+%22Turin+Management%22%29+New+York) |
| Municipal · Zoning & development applications | [`("site plan" OR "special use permit" OR rezoning OR IDA OR PILOT) ("Remington Factory Redevelopment" OR "Turin Management") New York`](https://www.google.com/search?q=%28%22site+plan%22+OR+%22special+use+permit%22+OR+rezoning+OR+IDA+OR+PILOT%29+%28%22Remington+Factory+Redevelopment%22+OR+%22Turin+Management%22%29+New+York) |
| Environmental / regulator · Environmental registry / permits | [`site:dec.ny.gov ("Remington Factory Redevelopment" OR "Turin Management") New York`](https://www.google.com/search?q=site%3Adec.ny.gov+%28%22Remington+Factory+Redevelopment%22+OR+%22Turin+Management%22%29+New+York) |
| Environmental / regulator · Utility-commission / siting filings | [`site:dps.ny.gov ("Remington Factory Redevelopment" OR "Turin Management") New York`](https://www.google.com/search?q=site%3Adps.ny.gov+%28%22Remington+Factory+Redevelopment%22+OR+%22Turin+Management%22%29+New+York) |
| Substation · Substation / point of interconnection | [`"Ilion Municipal 115kV substation" (substation OR interconnection OR "facilities study" OR "system impact study") New York`](https://www.google.com/search?q=%22Ilion+Municipal+115kV+substation%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+New+York) |
| Substation · RTO / ISO documents | [`site:nyiso.com ("Q#1735" OR Q1735 OR "Queue #1735" OR 1735 OR "Remington Factory Redevelopment")`](https://www.google.com/search?q=site%3Anyiso.com+%28%22Q%231735%22+OR+Q1735+OR+%22Queue+%231735%22+OR+1735+OR+%22Remington+Factory+Redevelopment%22%29) |

### 139. SPP GEN-2025-SR19 — (no project name published) · 100 MW · OK

| | |
|---|---|
| Status (as published) | IA in Progress |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | Maid 161kV substation |
| Location field | county field "Chouteau", Oklahoma |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "Maid 161kV substation" "Chouteau" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22Maid+161kV+substation%22+%22Chouteau%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "Maid 161kV substation" "Chouteau" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22Maid+161kV+substation%22+%22Chouteau%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`("Oklahoma Department of Environmental Quality" OR "Oklahoma DEQ") ("air permit" OR "construction permit" OR "environmental assessment") "Chouteau" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%28%22Oklahoma+Department+of+Environmental+Quality%22+OR+%22Oklahoma+DEQ%22%29+%28%22air+permit%22+OR+%22construction+permit%22+OR+%22environmental+assessment%22%29+%22Chouteau%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`"Oklahoma Corporation Commission" ("certificate of public convenience" OR siting OR "large load") "Maid 161kV substation" "Chouteau" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%22Oklahoma+Corporation+Commission%22+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+%22Maid+161kV+substation%22+%22Chouteau%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"Maid 161kV substation" (substation OR interconnection OR "facilities study" OR "system impact study") Oklahoma`](https://www.google.com/search?q=%22Maid+161kV+substation%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Oklahoma) |
| Substation · RTO / ISO documents | [`site:spp.org "GEN-2025-SR19"`](https://www.google.com/search?q=site%3Aspp.org+%22GEN-2025-SR19%22) |

### 140. SPP GEN-2025-SR22 — (no project name published) · 100 MW · OK

| | |
|---|---|
| Status (as published) | IA in Progress |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | Horseshoe Lake 138kV Substation |
| Location field | county field "Harrah", Oklahoma |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "Horseshoe Lake 138kV Substation" "Harrah" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22Horseshoe+Lake+138kV+Substation%22+%22Harrah%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "Horseshoe Lake 138kV Substation" "Harrah" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22Horseshoe+Lake+138kV+Substation%22+%22Harrah%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`("Oklahoma Department of Environmental Quality" OR "Oklahoma DEQ") ("air permit" OR "construction permit" OR "environmental assessment") "Harrah" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%28%22Oklahoma+Department+of+Environmental+Quality%22+OR+%22Oklahoma+DEQ%22%29+%28%22air+permit%22+OR+%22construction+permit%22+OR+%22environmental+assessment%22%29+%22Harrah%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`"Oklahoma Corporation Commission" ("certificate of public convenience" OR siting OR "large load") "Horseshoe Lake 138kV Substation" "Harrah" County Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%22Oklahoma+Corporation+Commission%22+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+%22Horseshoe+Lake+138kV+Substation%22+%22Harrah%22+County+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"Horseshoe Lake 138kV Substation" (substation OR interconnection OR "facilities study" OR "system impact study") Oklahoma`](https://www.google.com/search?q=%22Horseshoe+Lake+138kV+Substation%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Oklahoma) |
| Substation · RTO / ISO documents | [`site:spp.org "GEN-2025-SR22"`](https://www.google.com/search?q=site%3Aspp.org+%22GEN-2025-SR22%22) |

### 141. SPP GEN-2025-SR23 — (no project name published) · 100 MW · OK

| | |
|---|---|
| Status (as published) | IA in Progress |
| Developer (as published) | not published by the source register — Developer Not Disclosed |
| Point of interconnection | Mustang 138kV Substation |
| Location field | county field "Oklahoma City", Oklahoma |

**Search leads** (nothing below has been fetched or verified)

| Lead | Query (click to search) |
|---|---|
| Municipal · Council / commission minutes | [`("planning commission" OR "county commissioners" OR "board of supervisors" OR "city council") minutes "Mustang 138kV Substation" "Oklahoma City" Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%28%22planning+commission%22+OR+%22county+commissioners%22+OR+%22board+of+supervisors%22+OR+%22city+council%22%29+minutes+%22Mustang+138kV+Substation%22+%22Oklahoma+City%22+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Municipal · Zoning & development applications | [`(rezoning OR "conditional use permit" OR "special use permit" OR "site plan") "Mustang 138kV Substation" "Oklahoma City" Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%28rezoning+OR+%22conditional+use+permit%22+OR+%22special+use+permit%22+OR+%22site+plan%22%29+%22Mustang+138kV+Substation%22+%22Oklahoma+City%22+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Environmental registry / permits | [`("Oklahoma Department of Environmental Quality" OR "Oklahoma DEQ") ("air permit" OR "construction permit" OR "environmental assessment") "Oklahoma City" Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%28%22Oklahoma+Department+of+Environmental+Quality%22+OR+%22Oklahoma+DEQ%22%29+%28%22air+permit%22+OR+%22construction+permit%22+OR+%22environmental+assessment%22%29+%22Oklahoma+City%22+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Environmental / regulator · Utility-commission / siting filings | [`"Oklahoma Corporation Commission" ("certificate of public convenience" OR siting OR "large load") "Mustang 138kV Substation" "Oklahoma City" Oklahoma ("data center" OR "large load")`](https://www.google.com/search?q=%22Oklahoma+Corporation+Commission%22+%28%22certificate+of+public+convenience%22+OR+siting+OR+%22large+load%22%29+%22Mustang+138kV+Substation%22+%22Oklahoma+City%22+Oklahoma+%28%22data+center%22+OR+%22large+load%22%29) |
| Substation · Substation / point of interconnection | [`"Mustang 138kV Substation" (substation OR interconnection OR "facilities study" OR "system impact study") Oklahoma`](https://www.google.com/search?q=%22Mustang+138kV+Substation%22+%28substation+OR+interconnection+OR+%22facilities+study%22+OR+%22system+impact+study%22%29+Oklahoma) |
| Substation · RTO / ISO documents | [`site:spp.org "GEN-2025-SR23"`](https://www.google.com/search?q=site%3Aspp.org+%22GEN-2025-SR23%22) |

## Overrides audit

No overrides were loaded.
