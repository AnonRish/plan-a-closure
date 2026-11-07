#!/usr/bin/env python3
"""Generate the machine-readable 93-site Epoch queue gap analysis."""
from __future__ import annotations
import csv,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
BASE=ROOT/"data/external/epoch_ai"
CROSS=BASE/"queue_crosswalk.json"
REG=BASE/"registry.json"
OUT_CSV=BASE/"queue_gap_analysis.csv"
OUT_JSON=BASE/"queue_gap_analysis.json"

SECONDARY={
 "United States":["GridTracker","Interconnection.fyi","Watt Street","FERC eLibrary","SueDataCenters / Compute Atlas","DataCenter.fyi"],
 "Texas":["ERCOT Large Load Integration","Texas AI Docket","PUCT filings","GridTracker","Interconnection.fyi","Watt Street"],
 "United Kingdom":["NESO Connections 360","NESO Connections Registers / TEC Register"],
 "Australia":["AEMO NEM Registration","AEMO connection process / scorecard"],
 "Finland":["Fingrid main-grid connection/open data"],
 "Sweden":["Svenska kraftnät connection queue"],
 "Norway":["Statnett connection process"],
 "Malaysia":["TNB grid/service records"],
 "Portugal":["REN","E-REDES"],
 "Iceland":["Landsnet"],
 "China":["State Grid / provincial grid"],
 "Indonesia":["PLN"],
 "United Arab Emirates":["EWEC / local network operators"],
}

def main():
    cross=json.loads(CROSS.read_text(encoding="utf-8"))
    reg=json.loads(REG.read_text(encoding="utf-8"))
    if len(cross["records"])!=93 or len(reg["records"])!=93:
        raise SystemExit("Expected 93 Epoch records in crosswalk and registry")
    if not all(r.get("epoch_id") for r in cross["records"]):
        raise SystemExit("Epoch crosswalk records must carry epoch_id")
    if len({r["epoch_id"] for r in cross["records"]}) != 93:
        raise SystemExit("Epoch crosswalk epoch_id values must be unique")
    by_name={r["normalized"]["name"]:r for r in reg["records"]}
    rows=[]
    for r in cross["records"]:
        er=by_name.get(r["epoch_name"])
        if not er:
            raise SystemExit(f"Registry record missing: {r['epoch_name']}")
        key=r["epoch_country"]
        sources=SECONDARY.get(key,[])
        status=r["site_record_status"]
        action=("Maintain primary-source citation and reconcile queue/service MW against Epoch IT MW."
                if r["site_specific_queue_id"]
                else ("Search the named national/transmission/distribution connection system plus regulator and utility records for a site-specific connection record."
                      if r["queue_scope_status"]=="outside_registry_geography"
                      else "Search the named queue family, then local utility/municipal/co-op records and state PUC/PSC filings for the site-specific request/connection record."))
        rows.append({
            "epoch_id":r["epoch_id"],"epoch_name":r["epoch_name"],"country":r["epoch_country"],
            "state_province":r["state_province"],"epoch_address":r["epoch_address"],
            "epoch_current_it_power_mw":er["normalized"].get("current_power_mw"),
            "epoch_current_h100_equivalents":er["normalized"].get("current_h100_equivalents"),
            "grid_or_queue_jurisdiction":r["queue_or_connection_system"],
            "scope":r["queue_scope_status"],"site_record_status":status,
            "site_specific_queue_id":r["site_specific_queue_id"] or "",
            "site_specific_queue_name":r["site_specific_queue_name"] or "",
            "site_specific_capacity_mw":r["site_specific_queue_capacity_mw"] if r["site_specific_queue_capacity_mw"] is not None else "",
            "primary_source_url":r.get("queue_source_url") or r.get("source_url") or "",
            "source_type":r["source_type"] or "","source_date":r["source_date"] or "",
            "next_research_sources":"; ".join(sources),
            "match_basis":r["match_basis"],"confidence":r["confidence"],"next_action":action
        })
    fields=list(rows[0])
    with OUT_CSV.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields)
        w.writeheader();w.writerows(rows)
    summary={
      "total":len(rows),
      "site_specific_queue_ids":sum(bool(r["site_specific_queue_id"]) for r in rows),
      "public_service_or_planning_records":sum(r["site_record_status"] in {"public_service_contract_verified","public_customer_planning_record"} for r in rows),
      "jurisdiction_only_us":sum(r["country"]=="United States" and r["site_record_status"]=="queue_jurisdiction_mapped_site_id_not_yet_verified" for r in rows),
      "outside_registry_geography":sum(r["scope"]=="outside_registry_geography" for r in rows),
      "all_sites_have_jurisdiction":all(bool(r["grid_or_queue_jurisdiction"]) for r in rows)
    }
    OUT_JSON.write_text(json.dumps({"schema_version":1,"generated_on":"2026-09-26","record_count":len(rows),"objective":"Close the gap from Epoch AI physical site to the most specific public electricity queue/connection record possible.","summary":summary,"records":rows},indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("generated",len(rows),"queue gap-analysis records")
    print(summary)

if __name__=="__main__":
    main()
