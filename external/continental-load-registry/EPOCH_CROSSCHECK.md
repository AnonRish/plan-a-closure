# Epoch AI Frontier Data Centers cross-check

Audit date: 2026-09-26

## Implemented repository integration

The complete current Epoch AI AI Data Centers dataset is now imported under
[data/external/epoch_ai/](data/external/epoch_ai/). The September 24, 2026
snapshot contains 93 data-center rows, 545 timeline rows and 227 chip-quantity
rows. The dashboard exposes all 93 Epoch sites in a searchable secondary
evidence table, with raw source fields and a crosswalk back to this registry.

Current conservative crosswalk result: **2 of 93 Epoch sites have a direct
queue-record relationship recorded by the repository's human-reviewed
overrides (the two Lake Mariner records map to NYISO Q1670).** The remaining
sites are intentionally not force-matched.

## What is being compared

Epoch AI's current AI Data Centers dataset was updated September 24, 2026 and covers 93 sites, about 14.0 million H100-equivalents and 13.5 GW of IT power. Epoch describes the database as an independently researched set built from satellite imagery, permits, company disclosures, regulatory filings and other public evidence.

Source: https://epoch.ai/data/ai-data-centers
Documentation: https://epoch.ai/data/data-centers-documentation

The comparison is not apples-to-apples:
- Epoch tracks AI data-center campuses, including operational sites and selected projects under construction.
- This registry tracks public interconnection/connection queue rows at >=100 MW across nine selected organized electricity markets.
- A queue row can represent a phase, expansion, or grid-service request rather than an entire physical campus.
- An Epoch site below 100 MW is outside the registry threshold.
- A major AI site can exist in a balancing area or utility outside the nine organized markets covered here.
- Some underlying public sources do not publish the ultimate load applicant, so a developer-name match is not required for a legitimate facility overlap.

Therefore, a non-match is not evidence that either source is wrong.

## Facility-level cross-checks

| Epoch AI site | Epoch current / projected IT power | Registry cross-check | Result |
|---|---:|---|---|
| Anthropic Lake Mariner / Core42 Lake Mariner, Barker NY | 42-58 MW current; 378 MW projected | NYISO Q1670 Lake Mariner Data II, Niagara County, 250 MW | Strong campus/phase match. The queue project name and location align directly with Epoch's Lake Mariner site, but the 250 MW queue request should not be substituted for Epoch's 58 MW current IT-power estimate or 378 MW projected site total. |
| OpenAI Stargate Abilene, Abilene TX | 421 MW current; 843 MW projected in Q4 2026 | ERCOT Taylor County rows in current registry are five BESS requests from 143 to 208.8 MW; no Stargate/OpenAI/Oracle row and no Taylor County row matching the Epoch site | Not represented as an identifiable match in the current registry. This is a material gap worth investigating through ERCOT's dedicated Large Load Integration / Batch Zero material rather than assuming the GIS queue is complete for load. |
| Google Midlothian, Midlothian TX | 103 MW current | ERCOT Ellis County currently has eight rows, all labeled storage/BESS, with no Google/Midlothian project identity | No direct match identified. The 103 MW Epoch site is above this registry threshold, so this is a useful ERCOT large-load coverage check. |
| Meta Temple, Temple TX | 152 MW current; 178 MW projected | ERCOT Bell County currently has six rows, all labeled storage/BESS, with no Meta/Temple AI-data-center identity | No direct match identified. |
| CoreWeave Denton TX | 262 MW current; 282 MW projected | ERCOT Denton County currently has one 201 MW row, Oakley BESS, with a different project identity | No direct match identified. |
| Microsoft Fairwater Wisconsin, Mount Pleasant WI | 369 MW current; 2,263 MW projected | No current MISO row in the registry identified by Racine County / Mount Pleasant identity | No direct match identified. Epoch's site is clearly within Wisconsin, but the current queue layer is not a complete load-project register. |
| OpenAI Stargate Michigan, Benton MI | 0 MW current; 988 MW projected | No current MISO row identified in Berrien County by the Epoch site identity | No direct match identified. Epoch cites a Michigan Public Service Commission contract approval reporting 1,383 MW site capacity, showing why utility/regulatory evidence can contain information not present in a base queue row. |
| Google Lincoln, Lincoln NE | 141 MW current; 283 MW projected | SPP has a 225 MW GEN-2026-SR20 row in Lincoln, Nebraska, but it is classified in this registry as a BESS row and does not publish Google as applicant | Not an identity match. Geographic overlap alone is insufficient to equate the projects. |
| Google Papillion, Papillion NE | 237 MW current | No SPP registry row currently identified by Sarpy County / Papillion identity | No direct match identified. |
| Google Council Bluffs (East), Council Bluffs IA | 237 MW current | No MISO or SPP registry row currently identified by Pottawattamie County / Council Bluffs identity | No direct match identified. |
| Amazon New Carlisle, New Carlisle IN | 213 MW current; 338 MW projected | No MISO registry row currently identified by St. Joseph County / New Carlisle identity | No direct match identified. |
| AWS Berwick, Berwick PA | 108 MW current; 169 MW projected | No PJM registry row currently identified in Columbia County / Berwick; a similarly named registry row found in the search is an Ohio project and is unrelated | No direct match identified. |
| Google Bristow, Bristow VA | 238 MW current | No PJM registry row identified by Bristow / Prince William County identity | No direct match identified. |

Epoch site pages used:
- https://epoch.ai/data/ai-data-centers/directory/anthropic-lake-mariner
- https://epoch.ai/data/ai-data-centers/directory/core42-lake-mariner
- https://epoch.ai/data/ai-data-centers/directory/openai-stargate-abilene
- https://epoch.ai/data/ai-data-centers/directory/google-midlothian
- https://epoch.ai/data/ai-data-centers/directory/meta-temple
- https://epoch.ai/data/ai-data-centers/directory/coreweave-denton-tx
- https://epoch.ai/data/ai-data-centers/directory/microsoft-fairwater-wisconsin
- https://epoch.ai/data/ai-data-centers/directory/openai-stargate-michigan
- https://epoch.ai/data/ai-data-centers/directory/google-lincoln
- https://epoch.ai/data/ai-data-centers/directory/google-papillion
- https://epoch.ai/data/ai-data-centers/directory/google-council-bluffs-east
- https://epoch.ai/data/ai-data-centers/directory/aws-berwick
- https://epoch.ai/data/ai-data-centers/directory/google-bristow

## Interpretation

### 1. Epoch is valuable as an independent facility validator
The clearest example is NYISO Q1670 / Lake Mariner Data II. NYISO public material identifies queue position 1670, project name, Niagara location and a 250 MW request. Epoch independently identifies Lake Mariner in Barker, New York and describes its physical campus, current IT power and projected expansion. These are different measurements of the same campus/phase rather than duplicate 1:1 values.

### 2. ERCOT needs a dedicated large-load layer
The absence of direct registry identities for Epoch's Abilene, Midlothian, Temple and Denton sites is particularly important because these are all in Texas and above or around the registry's 100 MW threshold. The present ERCOT layer is based on the GIS Report, while ERCOT separately publishes Large Load Integration / Batch Zero material. The two layers should be joined rather than assuming the GIS report is a complete large-load application census.

### 3. MISO, SPP and PJM queue rows are not an AI-facility census
Epoch's Wisconsin, Michigan, Nebraska, Indiana, Ohio and Virginia sites demonstrate that a physical AI campus can be absent from a basic public interconnection row, be represented under a different project/phase name, fall below 100 MW, or have an applicant that is not disclosed in the queue export.

### 4. Epoch adds fields the registry currently does not have
- AI-specific classification;
- physical campus/site name;
- current IT power;
- projected IT power;
- current and projected H100-equivalent compute;
- chip types and estimated quantities;
- owner and user, with Epoch's Likely/Speculative distinctions;
- construction status;
- construction and expansion timeline;
- capital-cost estimates;
- satellite/aerial evidence;
- public-document source trail.

These should be added as a secondary evidence layer, not overwrite queue-origin values.

## Recommended record semantics

The implemented external evidence layer keeps source-specific values separate
from queue-origin fields. Each generated Epoch record contains registry
crosswalk status/reason fields alongside the raw Epoch row, latest timeline
snapshot and latest chip quantities.

The normalized record stores fields such as:
- source / dataset metadata;
- Epoch site name, address, country, owner and users;
- current H100-equivalents and current IT power;
- latest available timeline record;
- latest chip quantities by chip type;
- the full original Epoch data-center row under raw;
- registry crosswalk IDs, relationship, confidence and basis.

The queue record should remain authoritative for the public queue fields, and Epoch should remain authoritative only for its own estimates.

## Bottom line

Epoch AI is a useful independent cross-check for this project, but it also demonstrates why the phrase 'all publicly available information' should not be attached to the current queue-only dataset.

The repository therefore has a complete Epoch AI secondary registry now. The
crosswalk remains deliberately conservative: Lake Mariner is the currently
documented direct queue overlap, while the other 91 sites are retained as
separate Epoch records rather than being assigned speculative queue IDs. This
makes the difference between “not matched in this nine-market queue layer” and
“not a real data center” explicit.