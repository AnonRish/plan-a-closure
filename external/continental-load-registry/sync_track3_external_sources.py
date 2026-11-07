#!/usr/bin/env python3
"""Download public Epoch AI global compute-accounting CSV snapshots for Track 3."""
from __future__ import annotations
import argparse, csv, hashlib, json, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parent
EPOCH=ROOT/"data"/"external"/"epoch_ai"
SOURCE_STACK=ROOT/"data"/"track3_source_stack.json"
MANIFEST=ROOT/"data"/"track3"/"external_download_manifest.json"
UA="continental-load-registry/track3-source-sync (public research)"

GROUPS={
 "epoch-chip-sales":{
   "files":["ai_chip_sales_chip_types.csv","ai_chip_sales_organizations.csv","ai_chip_sales_timelines_by_chip.csv"],
   "urls":{f:"https://epoch.ai/data/"+f for f in ["ai_chip_sales_chip_types.csv","ai_chip_sales_organizations.csv","ai_chip_sales_timelines_by_chip.csv"]}},
 "epoch-chip-owners":{
   "files":["ai_chip_owners_cumulative_by_designer.csv","ai_chip_owners_quarters_by_chip_type.csv","ai_chip_owners_cumulative_by_chip_type.csv"],
   "urls":{f:"https://epoch.ai/data/"+f for f in ["ai_chip_owners_cumulative_by_designer.csv","ai_chip_owners_quarters_by_chip_type.csv","ai_chip_owners_cumulative_by_chip_type.csv"]}},
 "epoch-chip-users":{
   "files":["ai_chip_users_year_end_by_lab.csv","ai_chip_users_intermediates_by_lab.csv"],
   "urls":{f:"https://epoch.ai/data/"+f for f in ["ai_chip_users_year_end_by_lab.csv","ai_chip_users_intermediates_by_lab.csv"]}},
 "epoch-gpu-clusters":{
   "files":["gpu_clusters.csv"],
   "urls":{"gpu_clusters.csv":"https://epoch.ai/data/gpu_clusters.csv"}},
 "epoch-chip-components":{
   "files":["ai_chip_components_quarterly_by_chip.csv","ai_chip_components_quarterly_by_designer.csv","ai_chip_components_supply_denominators.csv"],
   "urls":{f:"https://epoch.ai/data/"+f for f in ["ai_chip_components_quarterly_by_chip.csv","ai_chip_components_quarterly_by_designer.csv","ai_chip_components_supply_denominators.csv"]}},
}

def fetch(url:str,retries:int=4)->bytes:
    last=None
    for attempt in range(retries):
        try:
            req=Request(url,headers={"User-Agent":UA,"Accept":"text/csv,text/plain;q=0.9,*/*;q=0.5"})
            with urlopen(req,timeout=45) as r:
                data=r.read()
            if len(data)<20: raise RuntimeError("response body is unexpectedly small")
            if b"<html" in data[:500].lower() or b"<!doctype" in data[:500].lower(): raise RuntimeError("received HTML instead of CSV")
            return data
        except (HTTPError,URLError,TimeoutError,RuntimeError) as exc:
            last=exc
            if attempt+1<retries: time.sleep(2**attempt)
    raise RuntimeError(f"download failed: {url}: {last}")

def csv_meta(data:bytes)->tuple[int,list[str]]:
    text=data.decode("utf-8-sig")
    rows=csv.reader(text.splitlines())
    header=next(rows,[])
    if len(header)<2: raise RuntimeError("CSV has fewer than two columns")
    count=sum(1 for _ in rows)
    return count,header

def sha256(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--selftest",action="store_true")
    args=ap.parse_args()
    if args.selftest:
        assert all(g["files"] for g in GROUPS.values())
        assert len({f for g in GROUPS.values() for f in g["files"]})==12
        print("PASS: Track 3 external source map self-test")
        return 0
    EPOCH.mkdir(parents=True,exist_ok=True)
    (ROOT/"data"/"track3").mkdir(parents=True,exist_ok=True)
    now=datetime.now(timezone.utc).isoformat()
    manifest={"schema_version":1,"generated_at_utc":now,"sources":[]}
    stack=json.loads(SOURCE_STACK.read_text(encoding="utf-8"))
    stack_by_id={s.get("id"):s for s in stack.get("sources",[])}
    for group_id,group in GROUPS.items():
        group_ok=True; group_entries=[]
        for filename in group["files"]:
            path=EPOCH/filename; url=group["urls"][filename]
            capture="downloaded"; error=None
            try:
                data=fetch(url)
                rows,columns=csv_meta(data)
                tmp=path.with_suffix(path.suffix+".tmp")
                tmp.write_bytes(data); tmp.replace(path)
            except Exception as exc:
                if path.exists() and path.stat().st_size>0:
                    data=path.read_bytes(); rows,columns=csv_meta(data); capture="reused_existing"; error=str(exc); group_ok=True
                else:
                    group_ok=False; group_entries.append({"file":filename,"url":url,"status":"FAILED","error":str(exc)}); continue
            item={"file":filename,"url":url,"status":capture,"captured_at_utc":now,"bytes":len(data),"sha256":sha256(data),"row_count":rows,"columns":columns}
            if error: item["refresh_error"]=error
            group_entries.append(item)
        source=stack_by_id.get(group_id)
        if source is not None:
            source["status"]="INGESTED_SNAPSHOT" if group_ok and all((EPOCH/f).exists() and (EPOCH/f).stat().st_size>0 for f in group["files"]) else "SOURCE_AVAILABLE_NOT_INGESTED"
            source["snapshot_files"]=list(group["files"])
            source["last_captured_utc"]=now
        manifest["sources"].append({"id":group_id,"status":"INGESTED_SNAPSHOT" if group_ok else "PARTIAL_OR_FAILED","files":group_entries})
    SOURCE_STACK.write_text(json.dumps(stack,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    MANIFEST.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    failed=[x for x in manifest["sources"] if x["status"]!="INGESTED_SNAPSHOT"]
    print(json.dumps(manifest,indent=2))
    if failed and any(x["status"]=="FAILED" for g in failed for x in g.get("files",[])): return 1
    return 0

if __name__=="__main__": raise SystemExit(main())
