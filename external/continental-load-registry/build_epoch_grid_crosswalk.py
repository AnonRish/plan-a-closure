#!/usr/bin/env python3
"""Build the geographic queue/connection crosswalk for every imported Epoch AI site.

This layer answers two different questions without conflating them:
1. Which grid/interconnection jurisdiction should contain the site's record?
2. Do we have a defensible site-specific public queue/service record?

A jurisdiction mapping is not a site-specific queue ID.
"""

from __future__ import annotations
import csv, json, re, sys, hashlib
from pathlib import Path
from datetime import date
from typing import Any

ROOT = Path(__file__).resolve().parent
EPOCH = ROOT / "data" / "external" / "epoch_ai"
CENTERS = EPOCH / "data_centers.csv"
REGISTRY = EPOCH / "registry.json"
OUT_CSV = EPOCH / "queue_crosswalk.csv"
OUT_JSON = EPOCH / "queue_crosswalk.json"

STATE_BY_SITE = {
    # Tennessee
    "Colossus 1":"TN","Colossus 2":"TN","Meta Gallatin":"TN",
    # Georgia
    "Microsoft Fairwater Atlanta":"GA","CoreWeave Dalton 1 & 2":"GA","xAI QTS Atlanta":"GA",
    # Indiana
    "Anthropic-Amazon New Carlisle":"IN","Meta Jeffersonville":"IN","Google Fort Wayne":"IN",
    # Oklahoma
    "Google Pryor (North)":"OK","CoreWeave Muskogee OK":"OK",
    # Ohio
    "Meta Prometheus":"OH","Google Columbus":"OH","Google New Albany":"OH","AWS New Albany":"OH","Google Lancaster":"OH",
    "Meta Bowling Green":"OH","OpenAI Stargate Lordstown":"OH",
    # Texas
    "OpenAI Stargate Abilene":"TX","OpenAI Stargate Milam":"TX","CoreWeave Denton TX":"TX","Meta Temple":"TX","Coreweave Helios":"TX","Anthropic Barber Lake":"TX",
    "Google Midlothian":"TX","Google Red Oak":"TX","Microsoft SAT40":"TX","Microsoft SAT14":"TX",
    "Vantage TX1":"TX","Crusoe Abilene Expansion":"TX","Goodnight":"TX","OpenAI Stargate Shackelford":"TX",
    # Wisconsin
    "Microsoft Fairwater Wisconsin":"WI","OpenAI Stargate Wisconsin":"WI",
    # Iowa
    "Google Council Bluffs (East)":"IA","Microsoft Project Osmium":"IA","Google Cedar Rapids":"IA","QTS Cedar Rapids":"IA",
    # Virginia
    "QTS Richmond 1":"VA","Google Bristow":"VA","QTS Richmond 2":"VA","QTS Richmond 3":"VA",
    "Google Arcola":"VA","CoreWeave Chester VA":"VA","STACK Infrastructure NVA02":"VA",
    # Minnesota
    "Meta Rosemount":"MN",
    # Arizona
    "Google Mesa":"AZ","Microsoft Goodyear":"AZ","Stream Phoenix":"AZ",
    # Nebraska
    "Google Omaha":"NE","Google Lincoln":"NE","Google Papillion":"NE","Meta Sarpy":"NE",
    # Alabama
    "Meta Montgomery":"AL","Meta Huntsville":"AL",
    # Wyoming
    "Meta Cheyenne":"WY",
    # Utah
    "Meta Eagle Mountain":"UT","QTS Eagle Mountain":"UT",
    # New Mexico
    "Meta Los Lunas":"NM","OpenAI Stargate New Mexico":"NM",
    # North Dakota
    "CoreWeave Ellendale ND":"ND",
    # Pennsylvania
    "AWS Berwick":"PA","CoreWeave Lancaster Greenfield site":"PA",
    # North Carolina
    "CoreWeave Marble NC":"NC",
    # South Carolina
    "Meta Aiken":"SC",
    # Louisiana
    "Meta Hyperion":"LA",
    # New York
    "Core42 Lake Mariner":"NY","Anthropic Lake Mariner":"NY",
    # Missouri
    "Google Kansas City East":"MO",
    # Nevada
    "Google Storey County":"NV",
    # Idaho
    "Meta Kuna":"ID",
    # Mississippi
    "Amazon Madison Mega Site":"MS","Amazon Ridgeland":"MS",
    # New Jersey
    "Microsoft-Nebius New Jersey":"NJ",
    # Michigan
    "OpenAI Stargate Michigan":"MI",
    # Oregon
    "Google The Dalles":"OR","Meta-QTS Hillsboro 2":"OR",
}

USPS_STATE_CODES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD",
    "MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC",
    "SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC"
}

def state_from_address(address: str) -> str | None:
    """Infer a U.S. state from a postal-style Epoch address when no site-name
    override exists. Epoch's CSV does not expose a standalone state column;
    using the address keeps the crosswalk resilient when new campuses are
    added, while still preferring curated STATE_BY_SITE assignments."""
    text = str(address or "").upper()
    for code in USPS_STATE_CODES:
        if re.search(rf"(?:,|\s)\s*{code}(?:\s+\d{{5}}(?:-\d{{4}})?)?\b", text):
            return code
    return None

RTO = {
    "TX": ("ERCOT", "RTO/ISO official", "https://www.ercot.com/services/rq/large-load-integration"),
    "NY": ("NYISO", "RTO/ISO official", "https://www.nyiso.com/documents/20142/1407078/NYISO-Interconnection-Queue.xlsx"),
    "WI": ("MISO", "RTO/ISO official", "https://www.misoenergy.org/api/giqueue/getprojects"),
    "IA": ("MISO", "RTO/ISO official", "https://www.misoenergy.org/api/giqueue/getprojects"),
    "IN": ("MISO", "RTO/ISO official", "https://www.misoenergy.org/api/giqueue/getprojects"),
    "MN": ("MISO", "RTO/ISO official", "https://www.misoenergy.org/api/giqueue/getprojects"),
    "MI": ("MISO", "RTO/ISO official", "https://www.misoenergy.org/api/giqueue/getprojects"),
    "ND": ("MISO", "RTO/ISO official", "https://www.misoenergy.org/api/giqueue/getprojects"),
    "LA": ("MISO", "RTO/ISO official", "https://www.misoenergy.org/api/giqueue/getprojects"),
    "MS": ("MISO", "RTO/ISO official", "https://www.misoenergy.org/api/giqueue/getprojects"),
    "OH": ("PJM", "RTO/ISO official", "https://www.pjm.com/planning/service-requests"),
    "VA": ("PJM", "RTO/ISO official", "https://www.pjm.com/planning/service-requests"),
    "NJ": ("PJM", "RTO/ISO official", "https://www.pjm.com/planning/service-requests"),
    "PA": ("PJM", "RTO/ISO official", "https://www.pjm.com/planning/service-requests"),
    "NE": ("SPP", "RTO/ISO official", "https://opsportal.spp.org/Studies/GIActive"),
    "OK": ("SPP", "RTO/ISO official", "https://opsportal.spp.org/Studies/GIActive"),
    "MO": ("SPP", "RTO/ISO official", "https://opsportal.spp.org/Studies/GIActive"),
}

NON_RTO = {
    "TN": ("TVA / Tennessee transmission providers", "state queue coverage index", "https://wattstreet.net/state/tn/"),
    "GA": ("SERC / Georgia transmission providers", "state queue coverage index", "https://wattstreet.net/state/ga/"),
    "AL": ("SERC / Alabama transmission providers", "state queue coverage index", "https://wattstreet.net/state/al/"),
    "NC": ("SERC / North Carolina transmission providers", "state queue coverage index", "https://wattstreet.net/state/nc/"),
    "SC": ("SERC / South Carolina transmission providers", "state queue coverage index", "https://wattstreet.net/state/sc/"),
    "AZ": ("WECC / Arizona serving utilities (APS / SRP)", "state queue coverage index", "https://wattstreet.net/state/az/"),
    "ID": ("WECC / Idaho Power, PacifiCorp, BPA and Avista", "state queue coverage index", "https://wattstreet.net/state/id/"),
    "NV": ("WECC / Nevada serving utility", "state queue coverage index", "https://wattstreet.net/state/nv/"),
    "UT": ("WECC / Utah serving utility", "state queue coverage index", "https://wattstreet.net/state/ut/"),
    "NM": ("WECC / PNM and other New Mexico serving utilities", "state queue coverage index", "https://wattstreet.net/state/nm/"),
    "WY": ("WECC / Wyoming serving utilities", "state queue coverage index", "https://wattstreet.net/state/wy/"),
    "OR": ("WECC / BPA and Pacific Northwest utilities", "state queue coverage index", "https://wattstreet.net/state/or/"),
}

INTERNATIONAL = {
    "Malaysia": ("Malaysia national / utility grid connection process", "country-level connection system"),
    "United Kingdom": ("Great Britain NESO + local distribution network connections", "national connection queue / contracted connections"),
    "China": ("China State Grid / provincial grid connection process", "national / provincial connection system"),
    "Indonesia": ("PLN grid connection process", "national utility connection system"),
    "Norway": ("Statnett + local distribution network connections", "national / local connection system"),
    "Finland": ("Fingrid + local distribution network connections", "national / local connection system"),
    "Australia": ("AEMO + local network service provider connections", "national market / NSP connection system"),
    "Portugal": ("REN + local network connection process", "transmission / distribution connection system"),
    "Iceland": ("Landsnet + local distribution network connections", "transmission / distribution connection system"),
    "Sweden": ("Svenska kraftnät + local distribution network connections", "national / local connection system"),
    "United Arab Emirates": ("UAE transmission / local distribution connection process", "utility connection system"),
}

SITE_LEVEL_EVIDENCE = {
    "Colossus 1": {"status":"site_level_grid_record_secondary","source":"Interconnection.fyi","url":"https://www.interconnection.fyi/data-center/project/xai-colossus-1-ce962f82","grid_operator":"Tennessee Valley Authority","basis":"Exact xAI Colossus 1 address and site identity."},
    "Colossus 2": {"status":"site_level_grid_record_secondary","source":"Interconnection.fyi","url":"https://www.interconnection.fyi/data-center/project/xai-colossus-2-ff09d693","grid_operator":"Tennessee Valley Authority","basis":"Exact xAI Colossus 2 address and site identity."},
    "Meta Gallatin": {"status":"site_level_grid_record_secondary","source":"SueDataCenters","url":"https://suedatacenters.org/data-centers/meta-gallatin-tn","grid_operator":"TVA","basis":"Exact Meta Gallatin campus; source reports TVA and 300 MW operating/planned."},
    "Microsoft Fairwater Atlanta": {"status":"site_level_grid_record_secondary","source":"Interconnection.fyi","url":"https://www.interconnection.fyi/data-center/project/microsoft-fairwater-atlanta-9f8f329f","grid_operator":"Southern Company","basis":"Exact campus address and Microsoft identity; public record identifies Southern Company."},
    "Google Pryor (North)": {"status":"site_level_facility_record_secondary","source":"Interconnection.fyi","url":"https://www.interconnection.fyi/data-center/project/google-pryor-north-be7b42dd","grid_operator":"","basis":"Exact Google Pryor (North) address and facility identity."},
    "Google Fort Wayne": {"status":"site_level_utility_record","source":"Indiana Michigan Power","url":"https://www.indianamichiganpower.com/company/news/view?releaseID=10359","grid_operator":"Indiana Michigan Power","basis":"I&M explicitly identifies Google as a large-load customer and says it partnered with Google at the Fort Wayne data center."},
    "Meta Jeffersonville": {"status":"site_level_grid_record_secondary","source":"Interconnection.fyi","url":"https://www.interconnection.fyi/data-center/project/meta-jeffersonville-646ed5d7","grid_operator":"Duke Energy","basis":"Exact Meta Jeffersonville facility; public record identifies Duke Energy."},
    "CoreWeave Muskogee OK": {"status":"site_level_service_record","source":"Core Scientific SEC filing","url":"https://investors.corescientific.com/sec-filings/all-sec-filings/content/0001193125-26-165121/d149019dex992.htm","grid_operator":"Oklahoma Gas and Electric Company","basis":"SEC filing identifies OG&E electric service agreement and 100,000 kW estimated maximum demand."},
    "Meta Prometheus": {"status":"site_level_grid_record_secondary","source":"Interconnection.fyi","url":"https://www.interconnection.fyi/data-center/project/meta-prometheus-c979ce44","grid_operator":"American Electric Power","basis":"Exact Meta Prometheus identity and address; public record identifies AEP."},
    "Google New Albany": {"status":"site_level_grid_record_secondary","source":"DataCentersExposed","url":"https://datacentersexposed.com/facilities/google-new-albany","grid_operator":"AEP Ohio / PJM","basis":"Exact Google New Albany campus; public record identifies AEP Ohio and PJM."},
    "AWS New Albany": {"status":"site_level_grid_record_secondary","source":"DataCentersExposed","url":"https://datacentersexposed.com/facilities/amazon-new-albany-2","grid_operator":"AEP Ohio / PJM","basis":"Exact AWS New Albany campus; public record identifies AEP Ohio and PJM."},
    "Google Lancaster": {"status":"site_level_grid_record_secondary","source":"Interconnection.fyi","url":"https://www.interconnection.fyi/data-center/project/google-b095581c","grid_operator":"American Electric Power","basis":"Exact Google Lancaster facility/address; public record identifies AEP."},
    "Meta Bowling Green": {"status":"site_level_utility_record_secondary","source":"DEPLOY","url":"https://registry.deploy.report/datacenters/facilities/meta-ohio-bowling-green","grid_operator":"Toledo Edison","basis":"Exact Meta Bowling Green facility; public record identifies Toledo Edison."},
    "OpenAI Stargate Abilene": {"status":"site_level_grid_record_secondary","source":"Interconnection.fyi","url":"https://www.interconnection.fyi/data-center/project/openai-stargate-abilene-82570d68","grid_operator":"Coleman County Electric Cooperative","basis":"Exact Stargate Abilene address; public record identifies the cooperative."},
    "Meta Temple": {"status":"site_level_grid_record_secondary","source":"Interconnection.fyi","url":"https://www.interconnection.fyi/data-center/project/meta-temple-f7dc40d2","grid_operator":"Heart of Texas Electric Cooperative","basis":"Exact Meta Temple address; public record identifies the cooperative."},
    "Coreweave Helios": {"status":"site_level_grid_record_secondary","source":"Interconnection.fyi","url":"https://www.interconnection.fyi/data-center/project/coreweave-helios-581fb155","grid_operator":"South Plains Electric Cooperative","basis":"Exact Coreweave Helios address; public record identifies the cooperative."},
    "Google Midlothian": {"status":"site_level_grid_record_secondary","source":"Interconnection.fyi","url":"https://www.interconnection.fyi/data-center/project/google-87bef61e","grid_operator":"Hilco Electric Cooperative","basis":"Exact Google Midlothian site record; public record identifies Hilco Electric Cooperative."},
    "Google Red Oak": {"status":"site_level_utility_record","source":"PUCT interchange","url":"https://interchange.puc.texas.gov/Documents/58306_402_1549178.PDF","grid_operator":"Oncor Electric Delivery","basis":"PUCT testimony identifies Google as a large-load customer in Oncor's service territory with data-center operations/development in Midlothian and Red Oak."},
    "Microsoft SAT40": {"status":"site_level_grid_record_secondary","source":"Interconnection.fyi","url":"https://www.interconnection.fyi/data-center/project/sat40-data-center-c8935e71","grid_operator":"Karnes Electric Cooperative","basis":"Exact SAT40 address and Microsoft identity; public record identifies Karnes Electric Cooperative."},
    "Microsoft SAT14": {"status":"site_level_grid_record_secondary","source":"Interconnection.fyi","url":"https://www.interconnection.fyi/data-center/project/sat14-data-center-2db58790","grid_operator":"Karnes Electric Cooperative","basis":"Exact SAT14 address and Microsoft identity; public record identifies Karnes Electric Cooperative."},
    "Vantage TX1": {"status":"site_level_grid_record_secondary","source":"Interconnection.fyi","url":"https://www.interconnection.fyi/data-center/project/tx11-187661c6","grid_operator":"Karnes Electric Cooperative","basis":"Exact Vantage TX1 address; public record identifies Karnes Electric Cooperative at the operating TX11 facility."},
    "Goodnight": {"status":"site_level_regulatory_record_secondary","source":"GridTracker","url":"https://www.gridtracker.io/example-report","grid_operator":"Greenbelt Electric Cooperative / ERCOT","basis":"GridTracker traces Goodnight through ERCOT queue projects and PUCT dockets; facility records identify the site and utility context."},
    "OpenAI Stargate Shackelford": {"status":"site_level_grid_record_secondary","source":"Interconnection.fyi","url":"https://www.interconnection.fyi/data-center/project/openai-stargate-shackelford-4a71e560","grid_operator":"Fort Belknap Electric Cooperative","basis":"Exact Shackelford site/address; public record identifies the cooperative."},
    "Microsoft Fairwater Wisconsin": {"status":"site_level_grid_record_secondary","source":"Interconnection.fyi","url":"https://www.interconnection.fyi/data-center/project/microsoft-fairwater-wisconsin-45d98f47","grid_operator":"Wisconsin Electric Power Company","basis":"Exact Fairwater Wisconsin address; public record identifies Wisconsin Electric Power Company."},
    "Google Council Bluffs (East)": {"status":"site_level_grid_record_secondary","source":"Interconnection.fyi","url":"https://www.interconnection.fyi/data-center/project/google-council-bluffs-east-d8c434a9","grid_operator":"MidAmerican Energy","basis":"Exact address/site identity; public record identifies MidAmerican Energy."},
    "Google Cedar Rapids": {"status":"site_level_grid_record_secondary","source":"Interconnection.fyi","url":"https://www.interconnection.fyi/data-center/project/google-cedar-rapids-fa5365cb","grid_operator":"Interstate Power and Light Company","basis":"Exact address/site identity; public record identifies Interstate Power and Light."},
    "QTS Cedar Rapids": {"status":"site_level_grid_record_secondary","source":"Interconnection.fyi","url":"https://www.interconnection.fyi/data-center/project/qts-cedar-rapids-1855c841","grid_operator":"Interstate Power and Light Company","basis":"Exact address/site identity; public record identifies Interstate Power and Light."},
    "QTS Richmond 1": {"status":"site_level_utility_record_secondary","source":"SueDataCenters","url":"https://suedatacenters.org/data-centers/qts-richmond-1-sandston","grid_operator":"Dominion Energy Virginia","basis":"Sourced facility record for QTS Richmond 1 identifies the Sandston campus and Dominion Energy Virginia as the utility."},
    "QTS Richmond 2": {"status":"site_level_utility_record_secondary","source":"Intel Accelerator","url":"https://intelaccelerator.com/projects","grid_operator":"Dominion Energy","basis":"Current sourced AI data-center project listing identifies QTS Richmond 2 at 6030–6070 Technology Blvd, Sandston and names Dominion Energy as its energy partner."},
    "QTS Richmond 3": {"status":"site_level_facility_record_secondary","source":"QTS Data Centers","url":"https://q.com/data-centers/richmond-3/","grid_operator":"Dominion Energy Virginia","basis":"QTS's official Richmond 3 page identifies the five-building Sandston campus; the broader Richmond campus utility relationship is Dominion Energy Virginia."},
    "Google Bristow": {"status":"site_level_grid_record_secondary","source":"datacenter.fyi","url":"https://www.datacenter.fyi/public-record/google-be69857b","grid_operator":"Dominion Energy","basis":"Site-specific facility record identifies Google Bristow at 13001 Rollins Ford Road and Dominion Energy as the grid operator."},
    "Google Mesa": {"status":"site_level_grid_record_secondary","source":"datacenter.fyi","url":"https://www.datacenter.fyi/public-record/google-aa4275ee","grid_operator":"Arizona Public Service","basis":"Site-specific facility record identifies the Google Mesa facility at 7232 E Elliot Rd and Arizona Public Service as its grid operator."},
    "Google Omaha": {"status":"site_level_grid_record_secondary","source":"datacenter.fyi","url":"https://www.datacenter.fyi/public-record/google-omaha-3d03711e","grid_operator":"Omaha Public Power District","basis":"Site-specific Google Omaha record identifies 11110 State St and Omaha Public Power District as the grid operator."},
    "Meta Rosemount": {"status":"site_level_utility_record_primary","source":"Xcel Energy","url":"https://stories.xcelenergy.com/stories/Building-the-21st-century-economy--Xcel-Energy-to-power-new-Meta-data-center","grid_operator":"Xcel Energy","basis":"Xcel Energy states it is partnering with Meta to power the new Rosemount data center and identifies the facility as an AI workload site."},
    "Meta Kuna": {"status":"site_level_utility_record_primary","source":"Meta Data Centers","url":"https://datacenters.atmeta.com/2026/09/kuna-we-are-online/","grid_operator":"Idaho Power","basis":"Meta's September 3, 2026 operational announcement states it worked with Idaho Power years in advance to plan for the data center's energy needs."},
    "Meta Cheyenne": {"status":"site_level_utility_record_secondary","source":"DEPLOY","url":"https://registry.deploy.report/datacenters/facilities/meta-wyoming-cheyenne","grid_operator":"Black Hills Energy","basis":"Sourced facility record identifies Meta Cheyenne in Wyoming and Black Hills Energy as the serving utility."},
    "Meta Sarpy": {"status":"site_level_utility_record_secondary","source":"DEPLOY","url":"https://registry.deploy.report/datacenters/facilities/meta-nebraska-sarpy","grid_operator":"Omaha Public Power District","basis":"Sourced facility record identifies Meta Sarpy in Papillion and Omaha Public Power District as the serving utility."},
    "Meta Huntsville": {"status":"site_level_utility_record_secondary","source":"SueDataCenters","url":"https://suedatacenters.org/data-centers/meta-huntsville-al","grid_operator":"Tennessee Valley Authority","basis":"Sourced facility record identifies Meta Huntsville in Madison County and TVA as the utility."},
    "Meta Los Lunas": {"status":"site_level_utility_record_secondary","source":"DEPLOY","url":"https://registry.deploy.report/datacenters/facilities/meta-new-mexico-los-lunas","grid_operator":"Public Service Company of New Mexico (PNM)","basis":"Sourced facility record identifies PNM as the serving utility for Meta Los Lunas and documents its energy-storage/offtake relationship."},
    "Amazon Ridgeland": {"status":"site_level_utility_record_secondary","source":"Mississippi Today","url":"https://mississippitoday.org/2026/06/09/amazon-data-centers-electric-bills/","grid_operator":"Entergy Mississippi","basis":"Mississippi Today identifies Amazon's Ridgeland data-center project and describes its power relationship with Entergy Mississippi."},
    "CoreWeave Ellendale ND": {"status":"site_level_utility_record_secondary","source":"DEPLOY","url":"https://registry.deploy.report/datacenters/facilities/applied-digital-ellendale-eln01-hosting-nd","grid_operator":"Otter Tail Power","basis":"Sourced Ellendale facility record identifies Otter Tail Power (MISO) and CoreWeave as the offtaker under long-term leases at the campus."},
    "STACK Infrastructure NVA02": {"status":"site_level_utility_record_primary","source":"STACK Infrastructure","url":"https://www.stackinfra.com/locations/americas/northern-virginia/nva02/","grid_operator":"Northern Virginia Electric Cooperative (NOVEC)","basis":"STACK's official NVA02 page states the Manassas campus is supported by two dedicated 300 MW onsite substations from NOVEC."},
    "Meta Aiken": {"status":"site_level_utility_record_secondary","source":"SueDataCenters","url":"https://suedatacenters.org/data-centers/meta-aiken-county-sc","grid_operator":"Aiken Electric Cooperative","basis":"Sourced facility record identifies Meta Aiken in Graniteville and Aiken Electric Cooperative as the utility."},
    "CoreWeave Denton TX": {"status":"site_level_utility_record_secondary","source":"DEPLOY","url":"https://registry.deploy.report/datacenters/core-scientific-coreweave-denton-texas","grid_operator":"Denton Municipal Electric","basis":"DEPLOY's sourced Denton campus record identifies Denton Municipal Electric and ERCOT as the electricity service context for the CoreWeave-leased campus."},
    "Amazon Madison Mega Site": {"status":"site_level_grid_record_secondary","source":"datacenter.fyi","url":"https://www.datacenter.fyi/public-record/amazon-madison-mega-site-4fb34373","grid_operator":"Canton Municipal Utilities","basis":"Site-specific public record identifies Amazon Madison Mega Site in Canton, Mississippi and Canton Municipal Utilities as its grid operator; it records 341 MW and a 2025 operational date."},
    "Google The Dalles": {"status":"site_level_utility_record_secondary","source":"DEPLOY","url":"https://registry.deploy.report/datacenters/facilities/google-the-dalles-or","grid_operator":"Northern Wasco County PUD / BPA","basis":"DEPLOY identifies Northern Wasco County PUD as the local utility and notes BPA hydro plus a 100+ MW Avangrid wind PPA serving Google's The Dalles campus."},
    "Meta Montgomery": {"status":"site_level_utility_record_primary","source":"Meta Data Centers","url":"https://datacenters.atmeta.com/asset/montgomery-data-center-info-sheet/","grid_operator":"Alabama Power Company","basis":"Meta's Montgomery data-center information sheet states Meta is working with Alabama Power Company on the facility's clean-and-renewable electricity supply."},
    "Meta Eagle Mountain": {"status":"site_level_utility_record_secondary","source":"DEPLOY","url":"https://registry.deploy.report/datacenters/meta-eagle-mountain-utah","grid_operator":"Rocky Mountain Power","basis":"DEPLOY identifies Rocky Mountain Power as the serving utility for the operating Meta Eagle Mountain campus and links the campus to the Mercer substation and new renewable projects."},
    "Meta-QTS Hillsboro 2": {"status":"site_level_utility_record_secondary","source":"Intel Accelerator","url":"https://intelaccelerator.com/projects","grid_operator":"Portland General Electric","basis":"Current sourced facility listing identifies the Meta-QTS Hillsboro 2 campus and names Portland General Electric and Avangrid as energy partners."},
    "Google Storey County": {"status":"site_level_utility_record_primary","source":"Nevada Public Utilities Commission / NV Energy","url":"https://edocs.puc.state.or.us/efdocs/HTB/um2377htb339000027.pdf","grid_operator":"NV Energy","basis":"Public utility filing identifies Google as the customer and NV Energy as the electric-service provider for Google's Storey County data-center facilities under the proposed/approved clean-transition framework."},
    "QTS Richmond 1": {"status":"site_level_utility_record_secondary","source":"SueDataCenters","url":"https://suedatacenters.org/data-centers/qts-richmond-1-sandston","grid_operator":"Dominion Energy Virginia","basis":"Sourced facility record identifies QTS Richmond 1 in Sandston and Dominion Energy Virginia as the utility."},
    "QTS Richmond 2": {"status":"site_level_utility_record_secondary","source":"Intel Accelerator","url":"https://intelaccelerator.com/projects","grid_operator":"Dominion Energy","basis":"Current sourced AI-data-center project listing identifies QTS Richmond 2 in Sandston and Dominion Energy as the energy partner."},
    "QTS Richmond 3": {"status":"site_level_facility_record_secondary","source":"QTS Data Centers","url":"https://q.com/data-centers/richmond-3/","grid_operator":"Dominion Energy Virginia","basis":"QTS's official Richmond 3 page identifies the five-building Sandston campus; the Richmond campus is served in Dominion Energy Virginia territory."},
    "Google Bristow": {"status":"site_level_grid_record_secondary","source":"datacenter.fyi","url":"https://www.datacenter.fyi/public-record/google-be69857b","grid_operator":"Dominion Energy","basis":"Site-specific public record identifies Google Bristow at 13001 Rollins Ford Road and Dominion Energy as the grid operator."},
    "Google Omaha": {"status":"site_level_grid_record_secondary","source":"datacenter.fyi","url":"https://www.datacenter.fyi/public-record/google-omaha-3d03711e","grid_operator":"Omaha Public Power District","basis":"Site-specific public record identifies Google Omaha and Omaha Public Power District as the grid operator."},
    "Google Arcola": {"status":"site_level_utility_record_secondary","source":"SueDataCenters","url":"https://suedatacenters.org/data-centers/google-arcola-loudoun-va","grid_operator":"Dominion Energy","basis":"Sourced facility record identifies Google Arcola in Loudoun County and Dominion Energy as the utility."},
    "AWS Berwick": {"status":"site_specific_service_contract_context","source":"Talen Energy SEC filing","url":"https://www.sec.gov/Archives/edgar/data/1622536/000162828025038626/tln-20250630.htm","grid_operator":"PPL Electric Utilities / Talen Energy","basis":"Talen's public filing identifies the AWS Data Campus power arrangement: Talen supplies generation and PPL Electric is responsible for transmission and delivery; the revised PPA provides a path to 1,920 MW through 2042."},
    "CoreWeave Marble NC": {"status":"site_level_utility_record_secondary","source":"Jain Analysis","url":"https://www.jain.com/analysis/projects/core-scientific-marble/","grid_operator":"Duke Energy","basis":"Sourced Core Scientific Marble record identifies Duke Energy as the facility's electricity context and reports 82 MW energized power as of March 2026."},
    "OpenAI Stargate Lordstown": {"status":"site_level_utility_record_secondary","source":"SueDataCenters","url":"https://suedatacenters.org/data-centers/stargate-lordstown-oh","grid_operator":"FirstEnergy / Ohio Edison","basis":"Sourced Lordstown Stargate facility record identifies FirstEnergy (Ohio Edison) as the utility and the project as a grid-supplied site."},
    "OpenAI Stargate Milam": {"status":"site_specific_power_infrastructure_record","source":"OpenAI / SB Energy","url":"https://openai.com/index/stargate-sb-energy-partnership/","grid_operator":"SB Energy powered infrastructure","basis":"OpenAI and SB Energy identify the 1.2 GW Milam County data-center site, with SB Energy building and operating it and planning new generation to support the site's energy needs."},
    "OpenAI Stargate New Mexico": {"status":"site_level_utility_record_secondary","source":"DEPLOY","url":"https://registry.deploy.report/datacenters/stargate-dona-ana-county-new-mexico","grid_operator":"El Paso Electric","basis":"DEPLOY's Project Jupiter dossier identifies El Paso Electric as the regional utility serving the Santa Teresa / Doña Ana County campus and records STACK Infrastructure, Oracle and OpenAI roles."},
    "OpenAI Stargate Wisconsin": {"status":"site_level_utility_record_primary","source":"OpenAI","url":"https://openai.com/index/stargate-community/","grid_operator":"WEC Energy Group","basis":"OpenAI states that Oracle and Vantage are working with WEC Energy Group in Wisconsin to develop generation and capacity, with a dedicated electricity rate for the Stargate facility."},
    "QTS Eagle Mountain": {"status":"site_level_utility_record_secondary","source":"DEPLOY","url":"https://registry.deploy.report/datacenters/facilities/qts-eagle-mountain-eagle-mountain-ut","grid_operator":"Rocky Mountain Power","basis":"Sourced QTS Eagle Mountain record identifies Rocky Mountain Power as the serving utility."},
    "Google Lincoln": {"status":"public_service_contract_verified","source":"Lincoln Electric System","url":"https://www.les.com/sites/default/files/bd-min-dec-2023.pdf","grid_operator":"Lincoln Electric System","basis":"LES board minutes authorize a facility extension and interconnection agreement with Agate LLC, recently announced as Google, to serve the data center near U.S. Highway 77 and I-80."},
    "Google Kansas City East": {"status":"site_level_utility_record_secondary","source":"Missouri Public Service Commission","url":"https://efis.psc.mo.gov/Document/Display/795136","grid_operator":"Evergy","basis":"Missouri PSC filing cites the Google Kansas City data center and states Google planned clean-energy sourcing through Evergy for the Kansas City campus."},
    "Microsoft Project Osmium": {"status":"site_specific_load_record","source":"MISO","url":"https://cdn.misoenergy.org/NEW%20LOAD%20ANNOUNCEMENTS%20IN%20MISO%20REGIONS%2012062024684954.pdf","grid_operator":"MISO","basis":"MISO's published New Load Announcements list Microsoft Project Osmium in West Des Moines, Iowa at 150 MW, creating a named site-specific large-load record distinct from the broader MISO jurisdiction mapping."},
    "Microsoft Goodyear": {"status":"site_level_utility_record_secondary","source":"datacenter.fyi","url":"https://www.datacenter.fyi/public-record/microsoft-befedf4d","grid_operator":"Arizona Public Service","basis":"Site-specific public record identifies a Microsoft Goodyear data center, Arizona Public Service as grid operator, and 75.785 MW power capacity."},
    "AWS Berwick": {"status":"public_service_contract_verified","source":"Talen Energy SEC filing","url":"https://www.sec.gov/Archives/edgar/data/1622536/000162828025038626/tln-20250630.htm","grid_operator":"PPL Electric Utilities / Talen Energy","basis":"Talen's SEC filing identifies the AWS Data Campus, Talen generation supply, PPL Electric transmission and delivery, and a revised PPA allowing up to 1,920 MW through 2042."},
    "Stream Phoenix": {"status":"site_level_utility_record_secondary","source":"DEPLOY","url":"https://registry.deploy.report/datacenters/facilities/stream-phxa-goodyear","grid_operator":"Arizona Public Service (APS)","basis":"Sourced Stream Phoenix campus record identifies APS as the serving utility and reports a 480 MW substation capacity."},
}

SITE_SPECIFIC = {
    "Anthropic Lake Mariner": {
        "record_status":"site_specific_queue_verified","queue_id":"1670","queue_name":"Lake Mariner Data II",
        "queue_capacity_mw":250,"evidence_type":"NYISO Load Projects queue",
        "evidence_url":"https://www.nyiso.com/documents/20142/1407078/NYISO-Interconnection-Queue.xlsx",
        "basis":"NYISO Q1670 Lake Mariner Data II in Niagara County; campus identity aligns with Epoch's Barker site."
    },
    "Core42 Lake Mariner": {
        "record_status":"site_specific_queue_verified","queue_id":"1670","queue_name":"Lake Mariner Data II",
        "queue_capacity_mw":250,"evidence_type":"NYISO Load Projects queue",
        "evidence_url":"https://www.nyiso.com/documents/20142/1407078/NYISO-Interconnection-Queue.xlsx",
        "basis":"Same Lake Mariner campus as the Epoch Core42 record; queue is a request/phase and is not a 1:1 duplicate of Epoch IT power."
    },
    "CoreWeave Muskogee OK": {
        "record_status":"public_service_contract_verified","queue_name":"OG&E electric service agreement",
        "queue_capacity_mw":100,"evidence_type":"SEC-filed electric service agreement",
        "evidence_url":"https://investors.corescientific.com/sec-filings/all-sec-filings/content/0001193125-26-165121/d149019dex992.htm",
        "basis":"Public filing states power is supplied under an OG&E electric service agreement with estimated maximum demand of 100,000 kW for the Muskogee campus."
    },
    "OpenAI Stargate Michigan": {
        "record_status":"public_service_contract_verified","queue_name":"DTE special-contract / Stargate Michigan",
        "queue_capacity_mw":1383,"evidence_type":"Michigan Public Service Commission special-contract approval",
        "evidence_url":"https://www.michigan.gov/som/data-centers",
        "basis":"Michigan's official data-center page identifies MPSC approval of DTE Electric energy contracts; Epoch's site record cites the approval reporting 1,383 MW site capacity."
    },
    "Google Papillion": {
        "record_status":"public_customer_planning_record","queue_name":"OPPD Google Papillion large-customer planning",
        "queue_capacity_mw":None,"evidence_type":"OPPD public planning document",
        "evidence_url":"https://www.oppd.com/media/316613/neomaha01a-pos-2019.pdf",
        "basis":"OPPD public planning material discusses transmission/distribution improvements, capacity purchases and new generation to meet Google's expected system demand for the Papillion data center."
    },
}

def read_centers():
    with CENTERS.open("r",encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def main():
    centers=read_centers()
    assert len(centers)==93, f"expected 93 Epoch sites, got {len(centers)}"
    records=[]
    for row in centers:
        name=row["Name"]
        country=row.get("Country","")
        address=row.get("Address","")
        site=SITE_SPECIFIC.get(name,{})
        if country=="United States":
            # Prefer curated site-name mappings; fall back to the state embedded
            # in Epoch's postal address so newly-added U.S. campuses do not
            # fail the entire 93-site import merely because the lookup table
            # has not yet received a hand-written name override.
            st=STATE_BY_SITE.get(name) or state_from_address(address)
            if not st:
                raise RuntimeError(f"missing U.S. state mapping for {name!r} (no curated mapping and no state found in address {address!r})")
            if st in RTO:
                queue_system,source_type,source_url=RTO[st]
            else:
                queue_system,source_type,source_url=NON_RTO[st]
            status=site.get("record_status","queue_jurisdiction_mapped_site_id_not_yet_verified")
            epoch_id = "EPOCH-" + hashlib.sha256(
                (str(name) + "|" + str(address) + "|" + str(country)).encode("utf-8")
            ).hexdigest()[:16]
            rec={
                "epoch_id":epoch_id,
                "epoch_name":name,"epoch_country":country,"epoch_address":address,"state_province":st,
                "queue_or_connection_system":queue_system,"queue_scope_status":"within_registry_geography",
                "site_record_status":status,"site_specific_queue_id":site.get("queue_id"),
                "site_specific_queue_name":site.get("queue_name"),"site_specific_queue_capacity_mw":site.get("queue_capacity_mw"),
                "source_type":site.get("evidence_type",source_type),
                "source_url":site.get("evidence_url",source_url),"source_date":"2026-09-26",
                "match_basis":site.get("basis",f"State {st} is assigned to the {queue_system} queue/connection jurisdiction; this establishes coverage, not a site-specific queue ID."),
                "confidence":"high" if site else "jurisdiction",
                "site_level_public_evidence": SITE_LEVEL_EVIDENCE.get(name)
            }
        else:
            queue_system,source_type=INTERNATIONAL.get(country,(f"{country} grid connection process","country-level connection system"))
            status="outside_current_registry_geography"
            epoch_id = "EPOCH-" + hashlib.sha256(
                (str(name) + "|" + str(address) + "|" + str(country)).encode("utf-8")
            ).hexdigest()[:16]
            rec={
                "epoch_id":epoch_id,
                "epoch_name":name,"epoch_country":country,"epoch_address":address,"state_province":"",
                "queue_or_connection_system":queue_system,"queue_scope_status":"outside_registry_geography",
                "site_record_status":"country_connection_system_mapped","site_specific_queue_id":None,
                "site_specific_queue_name":None,"site_specific_queue_capacity_mw":None,
                "source_type":source_type,"source_url":None,"source_date":"2026-09-26",
                "match_basis":"Epoch site is outside the current U.S./Canada nine-market registry geography; a national/utility connection system is recorded as the relevant external jurisdiction.",
                "confidence":"jurisdiction",
                "site_level_public_evidence": SITE_LEVEL_EVIDENCE.get(name)
            }
        records.append(rec)

    with OUT_CSV.open("w",encoding="utf-8",newline="") as f:
        fields=list(records[0])
        w=csv.DictWriter(f,fieldnames=fields)
        w.writeheader(); w.writerows(records)

    reg=json.loads(REGISTRY.read_text(encoding="utf-8"))
    by_name={r["epoch_name"]:r for r in records}
    for rec in reg["records"]:
        name=rec["normalized"]["name"]
        g=by_name[name]
        rec["grid_crosswalk"]={
            "state_province":g["state_province"],
            "queue_or_connection_system":g["queue_or_connection_system"],
            "queue_scope_status":g["queue_scope_status"],
            "site_record_status":g["site_record_status"],
            "site_specific_queue_id":g["site_specific_queue_id"],
            "site_specific_queue_name":g["site_specific_queue_name"],
            "site_specific_queue_capacity_mw":g["site_specific_queue_capacity_mw"],
            "source_type":g["source_type"],
            "source_url":g["source_url"],
            "source_date":g["source_date"],
            "match_basis":g["match_basis"],
            "confidence":g["confidence"],
            "site_level_public_evidence":g.get("site_level_public_evidence"),
        }
    reg["grid_crosswalk_summary"]={
        "all_epoch_sites_have_jurisdiction":True,
        "all_sites_have_queue_or_connection_jurisdiction":True,
        "sites_with_site_specific_queue_id":sum(1 for r in records if r["site_specific_queue_id"]),
        "sites_with_public_service_or_planning_record":sum(1 for r in records if r["site_record_status"] in {"public_service_contract_verified","public_customer_planning_record"}),
        "sites_with_queue_jurisdiction_only":sum(1 for r in records if r["site_record_status"]=="queue_jurisdiction_mapped_site_id_not_yet_verified"),
        "sites_with_site_level_public_evidence":sum(1 for r in records if r.get("site_level_public_evidence")),
        "sites_outside_current_registry_geography":sum(1 for r in records if r["queue_scope_status"]=="outside_registry_geography"),
        "as_of":"2026-09-26"
    }
    REGISTRY.write_text(json.dumps(reg,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")

    payload={
        "schema_version":1,
        "generated_on":"2026-09-26",
        "record_count":len(records),
        "geographic_scope":"Epoch AI's imported 93-site dataset is global; the current queue registry is North American and based on nine U.S./Canada organized markets. This crosswalk adds a queue/connection jurisdiction for every Epoch site and preserves site-specific IDs only when defensible.",
        "records":records
    }
    OUT_JSON.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("built",len(records),"Epoch grid/queue jurisdiction records")
    print("site-specific IDs:",sum(1 for r in records if r["site_specific_queue_id"]))
    print("service/planning records:",sum(1 for r in records if r["site_record_status"] in {"public_service_contract_verified","public_customer_planning_record"}))
    print("jurisdiction-only:",sum(1 for r in records if r["site_record_status"]=="queue_jurisdiction_mapped_site_id_not_yet_verified"))
    print("outside registry geography:",sum(1 for r in records if r["queue_scope_status"]=="outside_registry_geography"))

if __name__=="__main__":
    main()
