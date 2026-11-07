#!/usr/bin/env python3
"""Apply source-backed Track 3 coordinate overrides before physical acquisition.

Overrides are deliberately separate from the main geocoder output so provenance
for a manually researched coordinate remains visible. They never overwrite a
coordinate that has already been established by the canonical acquisition cache.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OVERRIDES=ROOT/"data/track3/coordinate_overrides_2026-09-27.json"
TARGET=ROOT/"data/track3/physical_site_coordinates.json"

def main()->int:
    ov=json.loads(OVERRIDES.read_text(encoding="utf-8"))
    target=json.loads(TARGET.read_text(encoding="utf-8")) if TARGET.exists() else {"schema_version":1,"records":[]}
    by_id={str(x.get("epoch_id")):x for x in target.get("records",[])}
    applied=[]
    skipped_existing=[]
    for x in ov.get("records",[]):
        eid=str(x["epoch_id"])
        cur=by_id.get(eid)
        if cur and cur.get("lat") is not None and cur.get("lon") is not None:
            skipped_existing.append(eid)
            continue
        rec=dict(cur or {"epoch_id":eid,"site_name":x.get("site_name")})
        rec.update({
            "site_name":x.get("site_name") or rec.get("site_name"),
            "status":"GEOCODED",
            "precision":x["precision"],
            "lat":float(x["latitude"]),
            "lon":float(x["longitude"]),
            "latitude":float(x["latitude"]),
            "longitude":float(x["longitude"]),
            "geocoder":"curated public-source override",
            "geocode_query":x.get("source_url"),
            "geocode_method":"source-backed-coordinate-override",
            "source_url":x.get("source_url"),
            "source_note":x.get("source_note"),
            "captured_on":datetime.now(timezone.utc).date().isoformat(),
        })
        by_id[eid]=rec
        applied.append(eid)
    records=sorted(by_id.values(),key=lambda x:str(x.get("epoch_id")))
    TARGET.write_text(json.dumps({
        "schema_version":1,
        "source":"OpenStreetMap Nominatim plus curated public-source overrides",
        "attribution":"© OpenStreetMap contributors where applicable; see per-record source_url for overrides",
        "record_count":len(records),
        "override_count":len(ov.get("records",[])),
        "applied_override_count":len(applied),
        "skipped_existing_count":len(skipped_existing),
        "records":records,
    },indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"applied":len(applied),"skipped_existing":len(skipped_existing),"record_count":len(records)},indent=2))
    return 0
if __name__=="__main__":
    raise SystemExit(main())
