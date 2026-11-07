#!/usr/bin/env python3
"""Refresh source-manifest capture metadata from successful adapter outputs.

This script never invents a capture date. A failed source updates only its
last-attempt fields; the last successful capture remains intact.
"""
from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"

def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def file_sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

def parse_auxiliary(stdout: str):
    try:
        obj = json.loads(stdout)
        return obj.get("sources", []) if isinstance(obj, dict) else []
    except Exception:
        return []

def main():
    manifest_path = DATA / "source_manifest.json"
    manifest = load(manifest_path)
    sources = manifest.setdefault("sources", {})
    updated = []

    summary_files = {
        "CAISO": "caiso_public_queue_summary.json",
        "MISO": "miso_public_queue_summary.json",
        "SPP": "spp_public_queue_summary.json",
        "PJM": "pjm_cycle_public_queue_summary.json",
    }
    for key, filename in summary_files.items():
        path = DATA / filename
        if not path.exists():
            continue
        obj = load(path)
        captured = obj.get("captured_at")
        if not captured:
            continue
        rec = sources.setdefault(key, {})
        rec["capture_date"] = captured
        rec["capture_precision"] = "timestamp"
        rec["capture_basis"] = "Latest successful public queue snapshot retained by the registry pipeline."
        snap = {
            "CAISO": DATA / "caiso_public_queue.json",
            "MISO": DATA / "miso_public_queue.json",
            "SPP": DATA / "spp_public_queue.json",
            "PJM": DATA / "pjm_cycle_public_queue.json",
        }[key]
        h = file_sha(snap)
        if h:
            rec["source_sha256"] = h
        updated.append(key)

    nyiso_status = DATA / "nyiso_public_queue_status.json"
    if nyiso_status.exists():
        obj = load(nyiso_status)
        rec = sources.setdefault("NYISO", {})
        rec["last_attempt_at"] = obj.get("captured_at")
        rec["last_attempt_status"] = obj.get("status")
        if obj.get("status") != "SOURCE_UNAVAILABLE_AT_CAPTURE":
            rec["capture_basis"] = "Latest successful public queue snapshot retained by the registry pipeline."

    report_path = DATA / "automation" / "adapter_run_report.json"
    if report_path.exists():
        report = load(report_path)
        for run in report.get("runs", []):
            if run.get("source") != "ERCOT / ISO-NE / IESO / AESO raw source capture":
                continue
            for item in parse_auxiliary(run.get("stdout_tail", "")):
                sid = item.get("source_id", "")
                key = {"ERCOT-GIS":"ERCOT","ISO-NE":"ISO-NE","IESO":"IESO","AESO":"AESO"}.get(sid)
                if not key or item.get("status") != "RAW_CAPTURED":
                    continue
                rec = sources.setdefault(key, {})
                rec["capture_date"] = item.get("captured_at_utc")
                rec["capture_precision"] = "timestamp"
                rec["capture_basis"] = "Latest successful raw publisher capture retained by the registry pipeline."
                if item.get("sha256"):
                    rec["source_sha256"] = item["sha256"]
                updated.append(key)

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
    manifest["generated_on"] = now
    manifest["last_metadata_refresh_utc"] = now
    manifest["metadata_refresh_policy"] = "Successful captures update capture metadata; failed sources update last_attempt fields only."
    manifest["metadata_refresh_updated_sources"] = sorted(set(updated))
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"updated_sources": sorted(set(updated)), "generated_on": now}, indent=2))

if __name__ == "__main__":
    main()
