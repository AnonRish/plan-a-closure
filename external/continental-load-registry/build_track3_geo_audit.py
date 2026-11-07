#!/usr/bin/env python3
"""Build a machine-readable 93-site physical-coordinate coverage audit."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
COORDS=ROOT/"data/track3/physical_site_coordinates.json"
TARGETS=ROOT/"data/track3/remote_sensing_observation_targets.json"
OBS=ROOT/"data/track3/remote_sensing_observations.json"
OUT=ROOT/"data/track3/geo_coverage_audit_2026-09-27.json"

def load(p): return json.loads(p.read_text(encoding="utf-8"))

def main()->int:
    coords=load(COORDS)
    targets=load(TARGETS)
    obs=load(OBS)
    coord_by={str(x.get("epoch_id")):x for x in coords.get("records",[])}
    observed={}
    for r in obs.get("records",[]):
        if r.get("status")!="INGESTED_DERIVED": continue
        eid=str(r.get("epoch_id"))
        mod=str(r.get("modality") or "").lower()
        observed.setdefault(eid,{})[mod]=observed.setdefault(eid,{}).get(mod,0)+1
    rows=[]
    for t in targets.get("records",[]):
        eid=str(t["epoch_id"])
        c=coord_by.get(eid,{})
        rows.append({
            "epoch_id":eid,
            "site_name":t.get("site_name"),
            "address":t.get("address"),
            "coordinate_status":"RESOLVED" if c.get("lat") is not None and c.get("lon") is not None else "UNRESOLVED",
            "coordinate_precision":c.get("precision"),
            "coordinate_method":c.get("geocode_method"),
            "coordinate_source_url":c.get("source_url") or c.get("geocode_query"),
            "latitude":c.get("lat") if c.get("lat") is not None else None,
            "longitude":c.get("lon") if c.get("lon") is not None else None,
            "derived_observations":{
                "optical":observed.get(eid,{}).get("optical",0),
                "tir":observed.get(eid,{}).get("tir",0),
                "sar":observed.get(eid,{}).get("sar",0),
            },
        })
    total=len(rows)
    resolved=sum(x["coordinate_status"]=="RESOLVED" for x in rows)
    unresolved=[x for x in rows if x["coordinate_status"]=="UNRESOLVED"]
    by_method={}
    for x in rows:
        if x["coordinate_status"]=="RESOLVED":
            by_method[x["coordinate_method"] or "unknown"] = by_method.get(x["coordinate_method"] or "unknown",0)+1
    out={
        "schema_version":1,
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "scope":{
            "epoch_reference_sites":total,
            "coordinate_target_sites":total,
            "remote_sensing_target_modalities":["optical","tir","sar"],
        },
        "summary":{
            "resolved_sites":resolved,
            "unresolved_sites":len(unresolved),
            "coordinate_coverage_fraction":(resolved/total if total else 0),
            "sites_with_any_derived_remote_observation":sum(any(v>0 for v in x["derived_observations"].values()) for x in rows),
            "derived_observations_total":sum(sum(x["derived_observations"].values()) for x in rows),
            "resolved_by_method":by_method,
            "semantics":"RESOLVED includes both canonical geocodes and source-backed coordinate overrides. Precision is preserved per record. A coordinate does not by itself prove facility identity, energization, compute activity, or covert status.",
        },
        "unresolved_sites":unresolved,
        "records":rows,
    }
    OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(out["summary"],indent=2))
    return 0
if __name__=="__main__": raise SystemExit(main())
