#!/usr/bin/env python3
"""Rebuild/check the retained-artifact section of Track 3 provenance."""
from __future__ import annotations
import argparse, csv, hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
MANIFEST=ROOT/"data/track3/physical_source_manifest.json"

ARTIFACT_ROLES={
 "data/track3/remote_sensing_observations.json":"Canonical derived scene ledger",
 "data/track3/remote_sensing_observations.csv":"Flattened derived scene ledger",
 "data/track3/building_footprints_index.json":"93-site footprint acquisition/index manifest",
 "data/physical_verification_layer.json":"Aggregate physical-verification state layer",
 "data/track3/physical_site_coordinates.json":"Geocoding/coordinate provenance cache",
}

def digest(path:Path)->tuple[str,int]:
    h=hashlib.sha256(); n=0
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            n+=len(chunk); h.update(chunk)
    return h.hexdigest(),n

def retained_entry(rel:str)->dict:
    path=ROOT/rel
    if not path.exists() or path.stat().st_size==0:
        raise SystemExit(f"missing/empty retained artifact: {rel}")
    sha,n=digest(path)
    entry={"path":rel,"role":ARTIFACT_ROLES[rel],"sha256":sha,"bytes":n}
    if rel.endswith("remote_sensing_observations.json"):
        data=json.loads(path.read_text(encoding="utf-8"))
        entry["record_count"]=len(data.get("records",[]))
    elif rel.endswith("remote_sensing_observations.csv"):
        with path.open("r",encoding="utf-8",newline="") as f:
            entry["record_count"]=max(0,sum(1 for _ in csv.reader(f))-1)
    elif rel.endswith("building_footprints_index.json"):
        data=json.loads(path.read_text(encoding="utf-8"))
        entry["record_count"]=len(data.get("records",[]))
        entry["polygon_site_count"]=int(data.get("sites_with_polygon_files",0))
        entry["polygon_file_count"]=int(data.get("polygon_file_count",data.get("sites_with_polygon_files",0)))
    elif rel.endswith("physical_verification_layer.json"):
        data=json.loads(path.read_text(encoding="utf-8"))
        entry["site_record_count"]=len(data.get("site_records",data.get("sites",data.get("records",[]))))
    elif rel.endswith("physical_site_coordinates.json"):
        data=json.loads(path.read_text(encoding="utf-8"))
        entry["record_count"]=len(data.get("records",[]))
    return entry

def replacement_manifest()->dict:
    obj=json.loads(MANIFEST.read_text(encoding="utf-8"))
    obj["retained_artifacts"]=[retained_entry(rel) for rel in ARTIFACT_ROLES]
    obs=json.loads((ROOT/"data/track3/remote_sensing_observations.json").read_text(encoding="utf-8"))
    foot=json.loads((ROOT/"data/track3/building_footprints_index.json").read_text(encoding="utf-8"))
    coord=json.loads((ROOT/"data/track3/physical_site_coordinates.json").read_text(encoding="utf-8"))
    ao=obj.setdefault("acquisition_outputs",{})
    ao["remote_sensing_derived_observation_count"]=int(obs.get("derived_observation_count",0))
    ao["building_footprint_polygon_site_count"]=int(foot.get("sites_with_polygon_files",0))
    ao["building_footprint_geojson_file_count"]=int(foot.get("polygon_file_count",foot.get("sites_with_polygon_files",0)))
    ao["epoch_site_geocoded_count"]=sum(1 for x in coord.get("records",[]) if x.get("lat") is not None and x.get("lon") is not None)
    ao["epoch_site_unresolved_coordinate_count"]=int(ao["epoch_site_target_count"])-ao["epoch_site_geocoded_count"]
    obj["last_reconciled_on"]="2026-09-28"
    return obj

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--check",action="store_true")
    args=ap.parse_args()
    current=json.loads(MANIFEST.read_text(encoding="utf-8"))
    rebuilt=replacement_manifest()
    same=current==rebuilt
    if args.check:
        print("PASS: physical provenance manifest is reproducible." if same else "FAIL: physical provenance manifest is stale.")
        return 0 if same else 1
    MANIFEST.write_text(json.dumps(rebuilt,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("WROTE:",MANIFEST)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
