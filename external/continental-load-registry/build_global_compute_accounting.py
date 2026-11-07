#!/usr/bin/env python3
"""Build the global public-source compute-accounting evidence summary."""

from __future__ import annotations
import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
EXT=ROOT/"data/external/epoch_ai"

FILES={
 "owners":EXT/"ai_chip_owners_cumulative_by_designer.csv",
 "users":EXT/"ai_chip_users_year_end_by_lab.csv",
 "sales_orgs":EXT/"ai_chip_sales_organizations.csv",
 "sales_types":EXT/"ai_chip_sales_chip_types.csv",
 "sales_timeline":EXT/"ai_chip_sales_timelines_by_chip.csv",
 "components_chip":EXT/"ai_chip_components_quarterly_by_chip.csv",
 "components_designer":EXT/"ai_chip_components_quarterly_by_designer.csv",
 "supply":EXT/"ai_chip_components_supply_denominators.csv",
}

def rows(path: Path):
    with path.open("r",encoding="utf-8",newline="") as f:
        return list(csv.DictReader(f))

def uniq(xs): return sorted({x for x in xs if x})

def main():
    data={k:rows(v) for k,v in FILES.items()}
    sales_timeline=data["sales_timeline"]
    existing={}
    out_path=ROOT/"data/track3/global_compute_supply_chain.json"
    if out_path.exists():
        try: existing=json.loads(out_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError: existing={}
    out={
      "schema_version":1,
      "generated_on":"2026-09-27",
      "title":"Global AI-compute supply-chain evidence layer",
      "current":{
        "owner_cumulative_rows":len(data["owners"]),
        "distinct_owners":len(uniq([r.get("Owner","") for r in data["owners"]])),
        "distinct_chip_manufacturers":len(uniq([r.get("Chip manufacturer","") for r in data["owners"]])),
        "user_year_end_rows":len(data["users"]),
        "distinct_labs":len(uniq([r.get("Lab","") for r in data["users"]])),
        "sales_organization_rows":len(data["sales_orgs"]),
        "sales_chip_type_rows":len(data["sales_types"]),
        "sales_timeline_rows":len(sales_timeline),
        "distinct_chip_types":len(uniq([r.get("Chip type","") for r in sales_timeline])),
        "component_by_chip_rows":len(data["components_chip"]),
        "component_by_designer_rows":len(data["components_designer"]),
        "supply_denominator_rows":len(data["supply"]),
        "global_transaction_level_closure":"UNKNOWN",
        "current_untraced_pool":"UNKNOWN"
      },
      "source_layers": existing.get("source_layers", [
        {"id":"EPOCH_OWNER_CUMULATIVE","status":"INGESTED_SNAPSHOT","repository_paths":["data/external/epoch_ai/ai_chip_owners_cumulative_by_designer.csv","data/external/epoch_ai/ai_chip_owners_cumulative_by_chip_type.csv"],"role":"Aggregate organization/owner snapshots; cumulative rows overlap in time and must not be summed across dates."},
        {"id":"EPOCH_SALES_TIMELINE","status":"INGESTED_SNAPSHOT","repository_path":"data/external/epoch_ai/ai_chip_sales_timelines_by_chip.csv","role":"Estimated chip-sales timeline; not serial/invoice accounting."},
        {"id":"EPOCH_COMPONENTS","status":"INGESTED_SNAPSHOT","repository_paths":["data/external/epoch_ai/ai_chip_components_quarterly_by_chip.csv","data/external/epoch_ai/ai_chip_components_quarterly_by_designer.csv","data/external/epoch_ai/ai_chip_components_supply_denominators.csv"],"role":"Upstream component/supply constraints."},
        {"id":"NVIDIA_SEC_FY2026","status":"PUBLIC_OFFICIAL_SOURCE","url":"https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm","role":"Vendor customer-channel and concentration disclosure."},
        {"id":"NVIDIA_SEC_Q2_FY2027","status":"PUBLIC_OFFICIAL_SOURCE","url":"https://www.sec.gov/Archives/edgar/data/1045810/000104581026000075/nvda-20260726.htm","role":"Current direct/indirect customer structure disclosure."},
        {"id":"TSMC_2025","status":"PUBLIC_OFFICIAL_SOURCE","url":"https://investor.tsmc.com/static/annualReports/2025/english/index.html","role":"Manufacturing and production-capacity context."},
        {"id":"GLEIF_2026-09-25","status":"PUBLIC_OFFICIAL_SOURCE","url":"https://www.gleif.org/en/lei-data/gleif-concatenated-file/download-the-concatenated-file","role":"Global legal-entity and parent-relationship data."},
        {"id":"US_CENSUS_TRADE","status":"PUBLIC_OFFICIAL_SOURCE","url":"https://www.census.gov/data/developers/data-sets/international-trade.html","role":"Commodity-flow and shipping statistics."},
        {"id":"EU_WEEE","status":"PUBLIC_OFFICIAL_SOURCE","url":"https://environment.ec.europa.eu/topics/waste-and-recycling/waste-electrical-and-electronic-equipment-weee/implementation-weee-directive_en","role":"End-of-life reporting context."}
      ]),
      "source_files":{
        "owners":"data/external/epoch_ai/ai_chip_owners_cumulative_by_designer.csv",
        "users":"data/external/epoch_ai/ai_chip_users_year_end_by_lab.csv",
        "sales_organizations":"data/external/epoch_ai/ai_chip_sales_organizations.csv",
        "sales_chip_types":"data/external/epoch_ai/ai_chip_sales_chip_types.csv",
        "sales_timeline":"data/external/epoch_ai/ai_chip_sales_timelines_by_chip.csv",
        "components_by_chip":"data/external/epoch_ai/ai_chip_components_quarterly_by_chip.csv",
        "components_by_designer":"data/external/epoch_ai/ai_chip_components_quarterly_by_designer.csv",
        "supply_denominators":"data/external/epoch_ai/ai_chip_components_supply_denominators.csv"
      },
      "reconciliation_rules":[
        "Cumulative owner snapshots overlap in time and cannot be summed into inventory.",
        "Sales estimates cannot be treated as serial-numbered shipment records.",
        "Organization-level ownership does not establish physical end use.",
        "Component supply denominators constrain plausibility but do not identify exact accelerator units.",
        "Residual compute remains UNKNOWN until the transaction/inspection chain is closed."
      ]
    }
    path=ROOT/"data/track3/global_compute_supply_chain.json"
    path.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("WROTE",path)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
