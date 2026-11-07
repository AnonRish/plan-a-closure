#!/usr/bin/env python3
"""Build/check the broad ambiguity-pool classification summary."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INDEX_HTML = ROOT / "index.html"
OUT = ROOT / "data/track3/broad_ambiguity_classification_summary.json"
RTOS = ["AESO", "CAISO", "ERCOT", "IESO", "ISO-NE", "MISO", "NYISO", "PJM", "SPP"]
UNRESOLVED_ENTITY = {"Developer Not Matched To Known List", "Developer Not Disclosed"}

def load_index_registry() -> list[dict]:
    html = INDEX_HTML.read_text(encoding="utf-8")
    match = re.search(r"const REGISTRY_DATA = (\[[\s\S]*?\]);\s*\n", html)
    if not match:
        raise RuntimeError("REGISTRY_DATA not found in index.html")
    return json.loads(match.group(1))

def load_records() -> dict[tuple[str, str], dict]:
    reg = load_index_registry()
    wanted = {
        (str(x.get("rto")), str(x.get("id")))
        for x in reg
        if x.get("tier") == "Genuinely Ambiguous / Unclassified Large Load"
        and float(x.get("mw") or 0) >= 100
        and x.get("ent") in UNRESOLVED_ENTITY
    }
    result: dict[tuple[str, str], dict] = {}
    for rto in RTOS:
        idx_path = ROOT / f"data/facility_records/{rto}/index.json"
        if not idx_path.exists():
            continue
        idx = json.loads(idx_path.read_text(encoding="utf-8"))
        needed = {
            str(qid): path for qid, path in (idx.get("lookup") or {}).items()
            if (rto, str(qid)) in wanted
        }
        by_file: dict[str, list[str]] = {}
        for qid, path in needed.items():
            by_file.setdefault(path, []).append(qid)
        for rel_path, qids in by_file.items():
            payload = json.loads((ROOT / rel_path).read_text(encoding="utf-8"))
            for rec in payload.get("records", []):
                rid = str(rec.get("record_id"))
                if rid in qids:
                    result[(rto, rid)] = rec
    return result

def classify(rec: dict) -> str:
    n = rec.get("normalized") or {}
    tech = str(n.get("raw_fuel_technology") or "").strip().lower()
    project = str(n.get("project_name") or "").strip().lower()
    combined = tech + " " + project
    if "load" not in tech:
        return "blank_or_unknown"
    if re.search(r"data center|data centre|data load|ai hub|a\.i\.|compute|digital|technology park|cloud", combined):
        return "data_center_or_digital"
    if re.search(r"factory|manufactur|industrial|plant|steel|graphite|aluminum|alcoa|micron|microchip", combined):
        return "industrial_or_manufacturing"
    return "other_explicit_load"

def build() -> dict:
    reg = load_index_registry()
    pool = [
        x for x in reg
        if x.get("tier") == "Genuinely Ambiguous / Unclassified Large Load"
        and float(x.get("mw") or 0) >= 100
        and x.get("ent") in UNRESOLVED_ENTITY
    ]
    records = load_records()
    groups: dict[str, dict[str, float]] = {}
    explicit = 0
    explicit_mw = 0.0
    unknown = 0
    unknown_mw = 0.0
    for x in pool:
        key = (str(x.get("rto")), str(x.get("id")))
        rec = records.get(key)
        if rec is None:
            raise RuntimeError(f"missing retained facility record for {key}")
        category = classify(rec)
        mw = float(x.get("mw") or 0)
        g = groups.setdefault(category, {"records": 0, "capacity_gw": 0.0})
        g["records"] += 1
        g["capacity_gw"] += mw / 1000
        if category == "blank_or_unknown":
            unknown += 1
            unknown_mw += mw
        else:
            explicit += 1
            explicit_mw += mw
    out = {
        "schema_version": 1,
        "generated_on": "2026-09-27",
        "title": "Broad ambiguity pool classification summary",
        "broad_pool": {
            "records": len(pool),
            "capacity_gw": round(sum(float(x.get("mw") or 0) for x in pool) / 1000, 4),
            "definition": "Records meeting the dashboard's broad ambiguity filter: >=100 MW, Genuinely Ambiguous / Unclassified Large Load tier, and unresolved/disclosed-to-unknown developer category."
        },
        "retained_field_pass": {
            "explicit_load_records": explicit,
            "explicit_load_capacity_gw": round(explicit_mw / 1000, 4),
            "blank_or_unknown_load_technology_records": unknown,
            "blank_or_unknown_load_technology_capacity_gw": round(unknown_mw / 1000, 4),
            "note": "This is a retained-field classification pass, not independent external adjudication of every project. Blank technology fields require source-level project-type review before load-discovery admission."
        },
        "explicit_load_breakdown": [
            {"label": "data_center_or_digital", "records": int(groups.get("data_center_or_digital", {}).get("records", 0)), "capacity_gw": round(groups.get("data_center_or_digital", {}).get("capacity_gw", 0), 3)},
            {"label": "industrial_or_manufacturing", "records": int(groups.get("industrial_or_manufacturing", {}).get("records", 0)), "capacity_gw": round(groups.get("industrial_or_manufacturing", {}).get("capacity_gw", 0), 3)},
            {"label": "other_explicit_load", "records": int(groups.get("other_explicit_load", {}).get("records", 0)), "capacity_gw": round(groups.get("other_explicit_load", {}).get("capacity_gw", 0), 3)}
        ],
        "strict_admission_rule": "Only records with explicit public evidence that the underlying request is Load, New Load Facility, Increase Load, or equivalent load-side type can enter the strict load-discovery queue. Generation, Surplus, Transmission, Replacement, Upgrade, storage-only, and other non-load records are excluded unless a separate retained source establishes the specific load component under investigation.",
        "current_strict_candidate_count": len(json.loads((ROOT / "data/track3/strict_discovery_candidates.json").read_text(encoding="utf-8")).get("candidates", [])),
        "current_strict_candidate_ids": [
            x.get("queue_id")
            for x in json.loads((ROOT / "data/track3/strict_discovery_candidates.json").read_text(encoding="utf-8")).get("candidates", [])
        ],
        "interpretation": "The broad ambiguity pool is a research universe, not a discovery count. Blank/unknown technology records require source-classification work before load-discovery admission."
    }
    return out

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    generated = build()
    if args.write:
        OUT.write_text(json.dumps(generated, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {OUT}")
        return 0
    if args.check or not args.write:
        current = json.loads(OUT.read_text(encoding="utf-8"))
        if current != generated:
            raise SystemExit("ERROR: broad_ambiguity_classification_summary.json is stale; run with --write")
        print("PASS: broad ambiguity classification summary reconciles with retained registry/facility records")
        return 0

if __name__ == "__main__":
    raise SystemExit(main())
