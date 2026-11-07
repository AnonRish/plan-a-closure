#!/usr/bin/env python3
"""Rebuild public Track 3 API and crosswalk exports from current repository data."""
from __future__ import annotations
import csv,json
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
API=ROOT/"api"/"v1"
NOW=datetime.now(timezone.utc).date().isoformat()

def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))

def csv_escape(v):
    s=str(v if v is not None else "")
    return '"'+s.replace('"','""')+'"'

def main():
    epoch_map=load("data/epoch_ai_map.json")
    sites=load("data/track3/site_status.json")["records"]
    by={x["epoch_id"]:x for x in sites}
    records=[]
    for x in epoch_map["records"]:
        s=by.get(x["id"],{}); g=s.get("grid",{})
        records.append({
          "facility_id":x["id"],"facility_name":x["site_name"],"country":x.get("country"),
          "state_province":s.get("state_province"),"address":x.get("address"),
          "latitude":x.get("lat"),"longitude":x.get("lon"),"coordinate_precision":x.get("precision"),
          "developer_or_owner":x.get("owner"),"users":x.get("users"),"project":x.get("project"),
          "current_it_power_mw":x.get("current_power_mw"),"current_h100_equivalents":x.get("current_h100_equivalents"),
          "grid_jurisdiction":x.get("grid_jurisdiction") or g.get("jurisdiction"),
          "grid_status":x.get("grid_status"),"site_queue_id":x.get("site_queue_id") or g.get("site_specific_queue_id"),
          "site_level_evidence_count":x.get("site_level_evidence_count",0),
          "combined_evidence_count":s.get("combined_site_level_evidence_count"),
          "detail_url":"facility.html?facility="+x["id"],"source_urls":[u for u in [x.get("epoch_source_url"),x.get("grid_evidence_url")] if u]
        })
    records.sort(key=lambda x:x["facility_name"] or "")
    payload={"schema_version":1,"api_version":"v1","title":"Continental Registry public static API","generated_on":NOW,
      "semantics":"Static GET API. Values are point-in-time repository outputs; source-specific measurements are not silently merged.",
      "endpoints":{"facilities_json":"/api/v1/facilities.json","facilities_csv":"/api/v1/facilities.csv","facility_records_index":"/data/facility_records/index.json","facility_record_shards":"/data/facility_records/{RTO}/{shard}.json","epoch_crosswalk_csv":"/data/external/epoch_ai/crosswalk.csv","epoch_crosswalk_json":"/data/external/epoch_ai/crosswalk.json","evidence":"/data/track3/evidence_records.json","provenance":"/data/track3/facility_provenance.json","verification":"/data/track3/verification_results.json"},
      "record_count":len(records),"records":records}
    API.mkdir(parents=True,exist_ok=True)
    (API/"facilities.json").write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    cols=list(records[0].keys())
    (API/"facilities.csv").write_text(",".join(cols)+"\n"+"\n".join(",".join(csv_escape(r.get(c)) for c in cols) for r in records)+"\n",encoding="utf-8")
    cr=ROOT/"data"/"external"/"epoch_ai"/"crosswalk.csv"
    if cr.exists():
      with cr.open(encoding="utf-8-sig",newline="") as fh: cross=list(csv.DictReader(fh))
      cross_payload={"schema_version":1,"title":"Epoch AI facility registry crosswalk","generated_on":NOW,"record_count":len(cross),"fields":list(cross[0].keys()) if cross else [],"records":cross}
      cr.with_suffix(".json").write_text(json.dumps(cross_payload,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"facility_count":len(records),"generated_on":NOW,"crosswalk_json":cr.with_suffix(".json").exists()},indent=2))
if __name__=="__main__": main()
