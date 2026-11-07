#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,datetime,io
from pathlib import Path
import pandas as pd
import requests

URL="https://www.misoenergy.org/api/giqueue/getprojects"
UA="Continental-Large-Load-Registry/1.0"

def fetch():
    r=requests.get(URL,headers="",timeout=60)
    r.raise_for_status()
    return r.json()

def clean(v):
    if v is None:return None
    if isinstance(v,(datetime.date,datetime.datetime)):return v.isoformat()
    try:return v.item()
    except Exception:return v

def build(raw):
    if isinstance(raw,dict):
        rows=raw.get("data") if isinstance(raw.get("data"),list) else raw.get("projects") if isinstance(raw.get("projects"),list) else [raw]
    else: rows=raw
    out=[]
    for i,row in enumerate(rows):
        if not isinstance(row,dict): continue
        raw_row={k:clean(v) for k,v in row.items()}
        summer=row.get("summerNetMW"); winter=row.get("winterNetMW")
        try: cap=max(float(summer or 0),float(winter or 0)) if summer is not None or winter is not None else None
        except Exception: cap=None
        out.append({
            "source_row_number":i+1,
            "normalized":{
                "queue_id":clean(row.get("projectNumber")),
                "county":clean(row.get("county")),
                "state":clean(row.get("state")),
                "transmission_owner":clean(row.get("transmissionOwner")),
                "poi":clean(row.get("poiName")),
                "queue_date":clean(row.get("queueDate")),
                "withdrawn_date":clean(row.get("withdrawnDate")),
                "status":clean(row.get("applicationStatus")),
                "capacity_mw":cap,
                "summer_net_mw":clean(summer),
                "winter_net_mw":clean(winter),
                "proposed_completion_date":clean(row.get("negInService")),
                "generation_type":clean(row.get("fuelType")),
                "facility_type":clean(row.get("facilityType")),
                "post_gia_status":clean(row.get("postGIAStatus")),
                "approval_date":clean(row.get("doneDate")),
                "in_service":clean(row.get("inService")),
                "gia_to_execute":clean(row.get("giaToExec")),
                "study_cycle":clean(row.get("studyCycle")),
                "study_group":clean(row.get("studyGroup")),
                "study_phase":clean(row.get("studyPhase")),
                "service_type":clean(row.get("svcType")),
                "dp1_eris_mw":clean(row.get("dp1ErisMw")),
                "dp1_nris_mw":clean(row.get("dp1NrisMw")),
                "dp2_eris_mw":clean(row.get("dp2ErisMw")),
                "dp2_nris_mw":clean(row.get("dp2NrisMw")),
                "sis_phase1":clean(row.get("sisPhase1"))
            },
            "raw":raw_row
        })
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--selftest",action="store_true"); ap.add_argument("--output-dir",default="data"); a=ap.parse_args()
    if a.selftest:
        x=build([{"projectNumber":"TEST","state":"MO","county":"Test","summerNetMW":250,"winterNetMW":200,"poiName":"X"}])
        assert len(x)==1 and x[0]["normalized"]["capacity_mw"]==250
        assert x[0]["raw"]["projectNumber"]=="TEST"
        print("PASS: MISO parser self-test"); return
    rows=build(fetch()); root=Path(a.output_dir); root.mkdir(parents=True,exist_ok=True)
    now=datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
    obj={"schema_version":1,"title":"MISO complete public interconnection queue","source_url":URL,"captured_at":now,"accounting":"Complete public generator-interconnection queue layer; not added to the conservative large-load core.","record_count":len(rows),"records":rows}
    (root/"miso_public_queue.json").write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    flat=[]
    for r in rows:
        x=r["normalized"].copy(); x["source_row_number"]=r["source_row_number"]; x["raw_record_json"]=json.dumps(r["raw"],ensure_ascii=False,separators=(",",":")); flat.append(x)
    pd.DataFrame(flat).to_csv(root/"miso_public_queue.csv",index=False)
    unresolved=[]
    for r in rows:
        n=r["normalized"]
        if (n.get("capacity_mw") or 0)>=100 and (not n.get("state") or not n.get("county") or not n.get("poi")):
            unresolved.append({
                "queue_id":n.get("queue_id"),
                "capacity_mw":n.get("capacity_mw"),
                "status":n.get("status"),
                "queue_date":n.get("queue_date"),
                "study_cycle":n.get("study_cycle"),
                "study_phase":n.get("study_phase"),
                "research_query":"MISO " + str(n.get("queue_id") or "") + " large load data center",
                "source_url":URL,
                "reason":"Public queue response lacks one or more site-identity/location fields required for a site-level record."
            })
    (root/"miso_unresolved_large_loads.json").write_text(json.dumps({"schema_version":1,"source_url":URL,"captured_at":now,"record_count":len(unresolved),"records":unresolved},indent=2)+"\n",encoding="utf-8")
    summary={"source_url":URL,"captured_at":now,"record_count":len(rows),"records_ge_100mw":sum((r["normalized"].get("capacity_mw") or 0)>=100 for r in rows),"missing_ge_100_location":len(unresolved),"unresolved_worklist":"data/miso_unresolved_large_loads.json"}
    (root/"miso_public_queue_summary.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))
if __name__=="__main__": main()
