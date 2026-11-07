#!/usr/bin/env python3
"""Build the 93-site x 8-field Track 3 publisher completeness matrix."""
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SRC=ROOT/"data/track3/public_site_enrichment_merged_2026-09-27.json"
OUT=ROOT/"data/track3/publisher_field_completeness_2026-09-27.json"
FIELDS=["owner","users","project","address","investors","construction_companies","energy_companies","chip_quantities"]
def main()->int:
    d=json.loads(SRC.read_text(encoding="utf-8")); records=[]
    for site in d["records"]:
        fm={}
        for f in FIELDS:
            x=site.get("fields",{}).get(f,{})
            fm[f]={"status":x.get("status","NOT_CAPTURED"),"epoch_value":x.get("epoch_value"),"bridge_value":x.get("bridge_value"),"fresh_public_values":x.get("fresh_public_values",[])}
        records.append({"epoch_id":site["epoch_id"],"site_name":site["site_name"],"country":site.get("country"),"state_province":site.get("state_province"),"epoch_it_power_mw":site.get("epoch_it_power_mw"),"field_matrix":fm,"fresh_public_record_count":site.get("fresh_public_record_count",0),"fresh_public_sources":site.get("fresh_public_sources",[])})
    out={"schema_version":1,"generated_on":"2026-09-27","title":"Track 3 publisher-field completeness matrix","purpose":"93-site x 8-field normalized view of publisher enrichment. Captured values remain provenance-bound; unresolved fields remain explicit.","scope":{"sites":len(records),"fields":FIELDS},"accounting":{"site_count":len(records),"cell_count":len(records)*len(FIELDS),"status_counts":{},"field_status_counts":{}},"records":records}
    for r in records:
        for f in FIELDS:
            st=r["field_matrix"][f]["status"]; out["accounting"]["status_counts"][st]=out["accounting"]["status_counts"].get(st,0)+1
            out["accounting"]["field_status_counts"].setdefault(f,{})[st]=out["accounting"]["field_status_counts"].setdefault(f,{}).get(st,0)+1
    OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(out["accounting"],indent=2))
    return 0
if __name__=="__main__": raise SystemExit(main())
