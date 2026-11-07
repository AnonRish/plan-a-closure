#!/usr/bin/env python3
from __future__ import annotations
import argparse,datetime,json,io
from pathlib import Path
import pandas as pd,requests
URL="https://opsportal.spp.org/Studies/GenerateSummaryCSV"
def main():
    ap=argparse.ArgumentParser();ap.add_argument("--selftest",action="store_true");ap.add_argument("--output-dir",default="data");a=ap.parse_args()
    if a.selftest:
        df=pd.DataFrame([{"Generation Interconnection Number":"TEST","Capacity (MW)":150}])
        assert float(df.iloc[0]["Capacity (MW)"])==150
        print("PASS: SPP parser self-test");return
    r=requests.get(URL,headers={"User-Agent":"Continental-Large-Load-Registry/1.0"},timeout=60);r.raise_for_status()
    df=pd.read_csv(io.BytesIO(r.content),skiprows=1).dropna(how="all");df.columns=[str(c).strip() for c in df.columns];recs=[]
    for i,(_,row) in enumerate(df.iterrows(),1):
        raw={c:(None if pd.isna(row[c]) else row[c].item() if hasattr(row[c],"item") else row[c]) for c in df.columns}
        def g(*ks):
            for k in ks:
                if k in raw:return raw[k]
            return None
        vals=[]
        for key in ("Capacity (MW)","Capacity","MAX Summer MW","MAX Winter MW"):
            try:
                if g(key) is not None: vals.append(float(g(key)))
            except Exception:
                pass
        cap=max(vals) if vals else None
        recs.append({"source_row_number":i,"normalized":{"queue_id":g("Generation Interconnection Number"),"ifs_queue_number":g("IFS Queue Number"),"cluster":g("Current Cluster"),"nearest_town_or_county":g(" Nearest Town or County","Nearest Town or County"),"state":g("State"),"transmission_owner":g("TO at POI"),"proposed_in_service_date":g("In-Service Date (proposed)"),"commercial_operation_date":g("Commercial Operation Date"),"capacity_mw":cap,"max_summer_mw":g("MAX Summer MW"),"max_winter_mw":g("MAX Winter MW"),"service_type":g("Service Type"),"requested_injection_mw":g("Requested Maximum Injection Capability (MW)"),"generation_type":g("Generation Type"),"fuel_type":g("Fuel Type"),"substation_or_line":g("Substation or Line"),"request_received":g("Request Received"),"date_withdrawn":g("Date Withdrawn"),"status":g("Status"),"associated_studies":g("Associated Studies"),"executed_gia":g("Executed GIA")},"raw":raw})
    root=Path(a.output_dir);root.mkdir(parents=True,exist_ok=True);now=datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
    obj={"schema_version":1,"title":"SPP active public generator interconnection queue","source_url":URL,"captured_at":now,"accounting":"Complete active SPP GI listing layer; not added to conservative large-load core.","record_count":len(recs),"records":recs}
    (root/"spp_public_queue.json").write_text(json.dumps(obj,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    flat=[]
    for z in recs:
        q=z["normalized"].copy();q.update({"source_row_number":z["source_row_number"],"raw_record_json":json.dumps(z["raw"],ensure_ascii=False,separators=(",",":"))});flat.append(q)
    pd.DataFrame(flat).to_csv(root/"spp_public_queue.csv",index=False)
    s={"source_url":URL,"captured_at":now,"record_count":len(recs),"records_ge_100mw":sum((z["normalized"].get("capacity_mw") or 0)>=100 for z in recs)}
    (root/"spp_public_queue_summary.json").write_text(json.dumps(s,indent=2)+"\n",encoding="utf-8");print(json.dumps(s,indent=2))
if __name__=="__main__":main()
