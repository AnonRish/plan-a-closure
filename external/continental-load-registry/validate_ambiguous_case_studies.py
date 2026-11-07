#!/usr/bin/env python3
"""Validate Track 3 ambiguous-load closure case studies against the declared protocol."""

from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
CASES=ROOT/"data/track3/ambiguous_case_studies.json"
PHYSICAL=ROOT/"data/track3/ambiguous_case_physical_observations.json"

ALLOWED={
    "CONFIRMED_DATA_CENTER",
    "CONFIRMED_OTHER_LARGE_LOAD",
    "CONFIRMED_MANUFACTURING_OR_INDUSTRIAL",
    "INCONCLUSIVE_AFTER_SEARCH",
    "RULED_OUT_DUPLICATE_WITHDRAWN_OR_DATA_ERROR",
}
REQUIRED={"case_id","rto","queue_id","project_name","capacity_mw","pilot_role","initial_registry_classification",
          "queue","entity_resolution","location","public_evidence","physical_observations",
          "transformer_check","adjudication","closure_state","unresolved_items","methods_note","last_verified_on"}
REQUIRED_QUEUE={"status","source_url","details","project_type","classification_basis"}
REQUIRED_ENTITY={"status"}
REQUIRED_LOCATION={"status","precision"}
REQUIRED_TRANSFORMER={"status","summary"}

def load(p:Path):
    return json.loads(p.read_text(encoding="utf-8"))

def main()->int:
    cases=load(CASES)
    physical=load(PHYSICAL)
    records=physical.get("records",[])
    physical_by={}
    for r in records:
        physical_by.setdefault(str(r.get("case_id")),[]).append(r)
    errors=[]
    rows=cases.get("cases",[])
    if len(rows)!=4:
        errors.append(f"expected 4 closure cases, got {len(rows)}")
    for c in rows:
        cid=str(c.get("case_id"))
        missing=sorted(REQUIRED-set(c))
        if missing: errors.append(f"{cid}: missing {missing}")
        if c.get("adjudication") not in ALLOWED:
            errors.append(f"{cid}: invalid adjudication {c.get('adjudication')!r}")
        project_type=str((c.get("queue") or {}).get("project_type") or "").strip().lower()
        if project_type not in {"load","new load facility","increase load"}:
            errors.append(f"{cid}: strict load-admission gate failed for project_type={project_type!r}")
        for group,key in ((REQUIRED_QUEUE,"queue"),(REQUIRED_ENTITY,"entity_resolution"),(REQUIRED_LOCATION,"location"),(REQUIRED_TRANSFORMER,"transformer_check")):
            obj=c.get(key) or {}
            miss=sorted(group-set(obj))
            if miss: errors.append(f"{cid}: {key} missing {miss}")
        ev=c.get("public_evidence") or []
        if not ev: errors.append(f"{cid}: no public evidence records")
        for i,e in enumerate(ev,1):
            if not e.get("source") or not e.get("url") or not e.get("what_it_proves"):
                errors.append(f"{cid}: public_evidence[{i}] incomplete")
        phys=c.get("physical_observations") or {}
        actual=physical_by.get(cid,[])
        actual_derived=[r for r in actual if r.get("status")=="INGESTED_DERIVED"]
        declared=int(phys.get("derived_observation_count") or 0)
        if declared != len(actual_derived):
            errors.append(f"{cid}: declared physical count {declared} != retained derived records {len(actual_derived)}")
        if declared and not phys.get("scene_ids"):
            errors.append(f"{cid}: derived observations declared but no scene_ids")
        if c.get("last_verified_on")!="2026-09-27":
            errors.append(f"{cid}: unexpected last_verified_on {c.get('last_verified_on')!r}")
        if not (c.get("unresolved_items") or []):
            errors.append(f"{cid}: no unresolved/boundary items recorded")
    if physical.get("observation_count") != len(records):
        errors.append("physical observation_count does not match records length")
    if physical.get("derived_observation_count") != sum(r.get("status")=="INGESTED_DERIVED" for r in records):
        errors.append("physical derived_observation_count does not match retained records")
    if errors:
        print("\n".join("ERROR: "+e for e in errors))
        return 1
    print("PASS: 4 closure cases validated")
    print("PASS: physical artifact counts reconcile")
    for c in rows:
        cid=c["case_id"]; n=sum(r.get("status")=="INGESTED_DERIVED" for r in physical_by.get(cid,[]))
        print(f"PASS: {cid} adjudication={c['adjudication']} derived_observations={n} closure={c['closure_state']}")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
