#!/usr/bin/env python3
"""Acquire physical observations for strict admitted-load candidates with defensible coordinates."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from acquire_physical_verification import process_site

ROOT = Path(__file__).resolve().parent
TARGETS = ROOT / "data/track3/strict_discovery_physical_targets.json"
OUT = ROOT / "data/track3/strict_discovery_physical_observations.json"
CSV = ROOT / "data/track3/strict_discovery_physical_observations.csv"


def main() -> int:
    manifest = json.loads(TARGETS.read_text(encoding="utf-8"))
    rows = []
    coords = []
    for target in manifest.get("targets", []):
        coord = {
            "case_id": target["case_id"],
            "latitude": target.get("latitude"),
            "longitude": target.get("longitude"),
            "precision": target.get("coordinate_precision"),
        }
        coords.append(coord)
        if coord["latitude"] is None or coord["longitude"] is None:
            rows.append({
                "case_id": target["case_id"],
                "queue_id": target["queue_id"],
                "project_name": target["project_name"],
                "status": "PHYSICAL_TARGET_UNRESOLVED",
                "coordinate_precision": coord["precision"],
            })
            continue

        site = {
            "epoch_id": target["case_id"],
            "normalized": {
                "name": target["project_name"],
                "address": target["address"],
            },
        }
        for record in process_site(site, {"lat": coord["latitude"], "lon": coord["longitude"]}, 2):
            record["case_id"] = target["case_id"]
            record["queue_id"] = target["queue_id"]
            record["project_status"] = target.get("project_status")
            rows.append(record)

    derived = [r for r in rows if r.get("status") == "INGESTED_DERIVED"]
    result = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "target_count": len(manifest.get("targets", [])),
        "coordinate_records": coords,
        "observation_count": len(rows),
        "derived_observation_count": len(derived),
        "records": rows,
        "semantics": "Derived public remote-sensing observations describe the observed scene only. They do not establish AI compute, operator identity, energization, or covert status by themselves.",
    }
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    fields = [
        "case_id", "queue_id", "project_name", "modality", "sensor", "scene_id",
        "observed_on", "stac_item_url", "source_collection", "cloud_cover_pct",
        "status", "quality_flag", "processing_version", "latitude", "longitude",
        "coordinate_precision", "metrics_json", "error",
    ]
    with CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in rows:
            row = {k: record.get(k) for k in fields if k != "metrics_json"}
            row["metrics_json"] = json.dumps(record.get("metrics") or {}, sort_keys=True)
            writer.writerow(row)

    print(json.dumps({
        "targets": len(manifest.get("targets", [])),
        "observations": len(rows),
        "derived_observations": len(derived),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
