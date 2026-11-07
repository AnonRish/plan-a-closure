#!/usr/bin/env python3
"""Build a local company/facility snapshot from AI Data Center Index public endpoints."""
from __future__ import annotations

import concurrent.futures
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
API="https://aidatacenterindex.com/api/operators.json"
BASE="https://aidatacenterindex.com/operators/"

def get_json(url:str, retries:int=3):
    last=None
    for attempt in range(retries):
        try:
            req=Request(url,headers={"User-Agent":"continental-load-registry-company-sync/1.0"})
            with urlopen(req,timeout=45) as r:
                raw=r.read()
            return json.loads(raw.decode("utf-8"))
        except Exception as exc:
            last=exc
            if attempt+1<retries: time.sleep(1.5*(attempt+1))
    raise RuntimeError(f"{url}: {last}")

def slugify(s:str)->str:
    s=str(s or "").lower()
    s=re.sub(r"[^a-z0-9]+","-",s).strip("-")
    return s

def name(o): return o.get("name") or o.get("operator") or o.get("title") or o.get("company") or ""
def slug(o): return o.get("slug") or o.get("id") or slugify(name(o))

def load_one(o):
    s=slug(o)
    url=BASE+quote(s,safe="")+"/index.json"
    try:
        j=get_json(url)
        items=j.get("items") or j.get("records") or j.get("facilities") or j.get("data") or []
        if not isinstance(items,list): items=[]
        return {"name":name(o),"slug":s,"summary":o,"source_url":url,
                "loaded":True,"facility_count_loaded":len(items),
                "taxonomy":j.get("taxonomy") if isinstance(j,dict) else None,
                "items":items}
    except Exception as exc:
        return {"name":name(o),"slug":s,"summary":o,"source_url":url,
                "loaded":False,"facility_count_loaded":0,"error":str(exc),"items":[]}

def main():
    operators_payload=get_json(API)
    operators=operators_payload if isinstance(operators_payload,list) else operators_payload.get("operators") or operators_payload.get("items") or operators_payload.get("data") or []
    if not operators: raise SystemExit("operator API returned no operators")

    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        portfolios=list(ex.map(load_one, operators))

    facilities={}
    relationships=[]
    for p in portfolios:
        for item in p["items"]:
            fid=str(item.get("id") or item.get("url") or item.get("title") or "").strip()
            if not fid: continue
            if fid not in facilities:
                facilities[fid]={"id":fid,"source_variants":[]}
            facilities[fid]["source_variants"].append({
                "operator":p["name"],"operator_slug":p["slug"],"record":item,"source_url":p["source_url"]
            })
            relationships.append({"operator":p["name"],"operator_slug":p["slug"],"facility_id":fid})

    payload={
        "schema_version":1,
        "generated_at":datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source":{"name":"AI Data Center Index","operators_api":API,"operator_base":BASE,
                  "license":"CC BY 4.0","published_operator_count":operators_payload.get("total_operators") if isinstance(operators_payload,dict) else len(operators)},
        "operator_count":len(operators),
        "operator_loaded_count":sum(1 for p in portfolios if p["loaded"]),
        "facility_reference_count":sum(len(p["items"]) for p in portfolios),
        "unique_facility_key_count":len(facilities),
        "operators":portfolios,
        "facility_index":list(facilities.values()),
        "relationships":relationships
    }
    out=ROOT/"data/company_operator_universe_2026-09-27.json"
    out.parent.mkdir(parents=True,exist_ok=True)
    tmp=out.with_suffix(out.suffix+".tmp")
    tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    tmp.replace(out)

    status={
        "generated_at":payload["generated_at"],
        "published_operator_count":payload["source"]["published_operator_count"],
        "operator_count":payload["operator_count"],
        "operator_loaded_count":payload["operator_loaded_count"],
        "facility_reference_count":payload["facility_reference_count"],
        "unique_facility_key_count":payload["unique_facility_key_count"],
        "failed_operators":[{"name":p["name"],"slug":p["slug"],"error":p.get("error")} for p in portfolios if not p["loaded"]]
    }
    (ROOT/"data/company_operator_universe_status.json").write_text(json.dumps(status,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(status,indent=2))

if __name__=="__main__":
    main()
