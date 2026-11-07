#!/usr/bin/env python3
"""Reconcile remote-sensing target states with retained observations."""

from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "data/track3/remote_sensing_observation_targets.json"
OBS = ROOT / "data/track3/remote_sensing_observations.json"


def main() -> int:
    target = json.loads(TARGET.read_text(encoding="utf-8"))
    obs = json.loads(OBS.read_text(encoding="utf-8"))
    by_site = {}
    for row in obs.get("records", []):
        if row.get("status") != "INGESTED_DERIVED":
            continue
        site = str(row.get("epoch_id") or "")
        mod = str(row.get("modality") or "").lower()
        by_site.setdefault(site, {}).setdefault(mod, 0)
        by_site[site][mod] += 1

    for row in target["records"]:
        counts = by_site.get(row["epoch_id"], {})
        for mod, key in (("optical", "site_scene_count"), ("tir", "numeric_observation_count"), ("sar", "numeric_observation_count")):
            obj = row[mod]
            count = int(counts.get(mod, 0))
            obj["status"] = "INGESTED_DERIVED" if count else "SOURCE_AVAILABLE_NOT_INGESTED"
            obj[key] = count

    target["summary"] = {
        "site_count": len(target["records"]),
        "optical_target_count": len(target["records"]),
        "tir_target_count": len(target["records"]),
        "sar_target_count": len(target["records"]),
        "sites_with_any_derived_observation": len(by_site),
        "ingested_optical_scene_count": sum(v.get("optical", 0) for v in by_site.values()),
        "ingested_tir_observation_count": sum(v.get("tir", 0) for v in by_site.values()),
        "ingested_sar_observation_count": sum(v.get("sar", 0) for v in by_site.values()),
        "derived_observation_count": int(obs.get("derived_observation_count", obs.get("observation_count", 0))),
        "semantics": "SOURCE_AVAILABLE_NOT_INGESTED means a site-specific target exists but no retained derived observation exists for that modality. INGESTED_DERIVED means a retained processed observation exists. Neither status is evidence of AI compute by itself."
    }
    TARGET.write_text(json.dumps(target, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(target["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
