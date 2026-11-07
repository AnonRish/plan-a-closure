#!/usr/bin/env python3
"""Build normalized Track 3 public research-lead layer."""
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SRC=ROOT/"data/track3/site_missing_information_sweep_2026-09-27.json"
OUT=ROOT/"data/track3/public_research_leads.json"
def main()->int:
    d=json.loads(SRC.read_text(encoding="utf-8"))
    records=[]; seen=set()
    for site in d.get("records",[]):
        for lead in site.get("public_research_leads",[]):
            row={"epoch_id":site.get("epoch_id"),"site_name":site.get("site_name"),"country":site.get("country"),"state_province":site.get("state_province"),"field":lead.get("field"),"status":lead.get("status"),"finding":lead.get("finding"),"source":lead.get("source"),"source_url":lead.get("source_url") or None,"disposition":lead.get("status") if lead.get("status") in {"RETAINED_SOURCE","PUBLIC_SOURCE"} else "PUBLIC_LEAD_REVIEW_REQUIRED","semantics":"Discovery lead only. Not canonical evidence unless separately reviewed and promoted."}
            k=json.dumps(row,sort_keys=True,ensure_ascii=False,separators=(",",":"))
            if k in seen: continue
            seen.add(k); row["lead_id"]=f"LEAD-{len(records)+1:04d}"; records.append(row)
    out={"schema_version":1,"generated_on":"2026-09-27","title":"Track 3 public research lead layer","purpose":"Normalize targeted public-source leads from the 93-site missing-information sweep. Leads remain separate from canonical evidence unless independently reviewed and promoted.","accounting":{"lead_count":len(records),"site_count":len({x["epoch_id"] for x in records}),"by_status":{},"by_field":{}},"records":records}
    for x in records:
        out["accounting"]["by_status"][x["status"]]=out["accounting"]["by_status"].get(x["status"],0)+1
        out["accounting"]["by_field"][x["field"]]=out["accounting"]["by_field"].get(x["field"],0)+1
    OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\\n",encoding="utf-8")
    print(json.dumps(out["accounting"],indent=2))
    return 0
if __name__=="__main__": raise SystemExit(main())
