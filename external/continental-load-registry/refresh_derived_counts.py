#!/usr/bin/env python3
"""Keep hand-copied counts in public artifacts in sync with the files they describe.

Two artifacts carry counts that other jobs change on every run. Both were edited by
hand, so they drifted after each automated refresh:

* data/public_data_catalog.json  record_count of generated ledgers
* data/map_layer_manifest.json   records of the four live queue layers, taken from
                                 data/queue_layer_status.json

    python refresh_derived_counts.py          # rewrite the counts
    python refresh_derived_counts.py --check  # exit 1 on drift or a catalog entry whose file is missing
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "data/public_data_catalog.json"
MAP_MANIFEST = ROOT / "data/map_layer_manifest.json"
QUEUE_STATUS = ROOT / "data/queue_layer_status.json"
# catalog path -> key inside the file that holds the authoritative count
DERIVED = {"data/track3/evidence_records.json": "record_count"}
QUEUE_LAYERS = {
    "MISO_COMPLETE_QUEUE": "MISO",
    "SPP_ACTIVE_QUEUE": "SPP",
    "CAISO_COMPLETE_QUEUE": "CAISO",
    "PJM_CYCLE_QUEUE": "PJM",
}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _dump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    problems: list[str] = []

    catalog = _load(CATALOG)
    catalog_dirty = False
    for d in catalog["datasets"]:
        path = ROOT / d["path"]
        if not path.exists():
            problems.append(f"catalog lists a file that does not exist: {d['path']}")
            continue
        key = DERIVED.get(d["path"])
        if key:
            actual = _load(path)[key]
            if d.get("record_count") != actual:
                problems.append(f"{d['path']}: catalog says {d.get('record_count')}, file says {actual}")
                d["record_count"] = actual
                catalog_dirty = True

    manifest = _load(MAP_MANIFEST)
    feeds = {x["id"]: x for x in _load(QUEUE_STATUS)["feeds"]}
    manifest_dirty = False
    for layer in manifest["layers"]:
        feed = feeds.get(QUEUE_LAYERS.get(layer["id"], ""))
        if feed and feed.get("snapshot_present") and layer.get("records") != feed["record_count"]:
            problems.append(
                f"{layer['id']}: map_layer_manifest says {layer.get('records')}, queue_layer_status says {feed['record_count']}"
            )
            layer["records"] = feed["record_count"]
            manifest_dirty = True

    if args.check:
        for msg in problems:
            print("DRIFT:", msg)
        return 1 if problems else 0
    if catalog_dirty:
        _dump(CATALOG, catalog)
    if manifest_dirty:
        _dump(MAP_MANIFEST, manifest)
    for msg in problems:
        print("NOTE:", msg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
