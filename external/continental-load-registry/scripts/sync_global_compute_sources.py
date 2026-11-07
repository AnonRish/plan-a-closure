#!/usr/bin/env python3
"""Refresh openly licensed external compute-universe snapshots.

This script intentionally stores source data separately. It does not infer missing
facts, and it does not collapse source populations into a false global census.
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]

SOURCES = [
    {
        "name": "Compute Atlas",
        "url": "https://www.compute-atlas.com/api/facilities",
        "path": ROOT / "data/external/compute_atlas/facilities.json",
        "shape": "object_facilities",
    },
    {
        "name": "Data Center Index",
        "url": "https://datacenterindex.ai/data/datacenterindex-campuses.json",
        "path": ROOT / "data/external/data_center_index/campuses.json",
        "shape": "array",
    },
]

def fetch(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "continental-load-registry/1.0"})
    with urlopen(req, timeout=60) as response:
        body = response.read()
        if not body:
            raise RuntimeError(f"{url}: empty response")
        # Validate without rewriting the publisher's JSON byte-for-byte.
        payload = json.loads(body.decode("utf-8"))
        if isinstance(payload, dict) and "facilities" in payload:
            if not isinstance(payload["facilities"], list):
                raise RuntimeError(f"{url}: facilities is not a list")
        elif isinstance(payload, list):
            pass
        else:
            raise RuntimeError(f"{url}: unexpected JSON shape")
        return body

def main() -> int:
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    meta = {
        "schema_version": 1,
        "generated_on": str(date.today()),
        "retrieved_at": retrieved_at,
        "sources": [],
    }

    for src in SOURCES:
        body = fetch(src["url"])
        src["path"].parent.mkdir(parents=True, exist_ok=True)
        old = src["path"].read_bytes() if src["path"].exists() else None
        if old != body:
            tmp = src["path"].with_suffix(src["path"].suffix + ".tmp")
            tmp.write_bytes(body)
            tmp.replace(src["path"])

        payload = json.loads(body.decode("utf-8"))
        records = payload["facilities"] if isinstance(payload, dict) and "facilities" in payload else payload
        meta["sources"].append(
            {
                "name": src["name"],
                "url": src["url"],
                "local_snapshot": str(src["path"].relative_to(ROOT)).replace("\\", "/"),
                "record_count": len(records),
                "retrieved_at": retrieved_at,
                "sha256": __import__("hashlib").sha256(body).hexdigest(),
            }
        )

    metadata_path = ROOT / "data/global_compute_universe_snapshot_status.json"
    metadata_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())
