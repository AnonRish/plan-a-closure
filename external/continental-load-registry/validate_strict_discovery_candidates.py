#!/usr/bin/env python3
"""Validate the strict admitted-load discovery candidate contract."""

from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANDIDATES = ROOT / "data/track3/strict_discovery_candidates.json"
PACKETS = ROOT / "data/track3/strict_discovery_research_packets.json"

ALLOWED_RTO = {"AESO", "NYISO", "IESO", "MISO", "SPP", "PJM", "ERCOT", "CAISO", "ISO-NE"}
ALLOWED_LOAD = {"PUBLICLY_CLASSIFIED_LOAD"}
REQUIRED_CANDIDATE = {
    "case_id", "queue_id", "rto", "project_name", "capacity_mw",
    "county_or_area", "poi", "load_status", "identity_gap", "physical_gap",
    "research_role"
}
REQUIRED_PACKET = {
    "case_id", "queue_id", "rto", "project_name", "capacity_mw",
    "public_load_classification", "geographic_context",
    "current_identity_gap", "current_physical_gap",
    "novelty_boundary", "source_ladder", "next_gates"
}

def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def main() -> int:
    candidates = load(CANDIDATES)
    packets = load(PACKETS)
    rows = candidates.get("candidates", [])
    packet_rows = packets.get("candidates", [])

    errors: list[str] = []

    if not 4 <= len(rows) <= 5:
        errors.append(f"expected 4-5 strict candidates, got {len(rows)}")
    if len(rows) != len(packet_rows):
        errors.append("candidate and packet counts differ")

    ids = [str(r.get("queue_id")) for r in rows]
    if len(ids) != len(set(ids)):
        errors.append("duplicate queue IDs in strict candidate set")

    packet_by = {str(r.get("queue_id")): r for r in packet_rows}

    for r in rows:
        cid = str(r.get("case_id"))
        missing = sorted(REQUIRED_CANDIDATE - set(r))
        if missing:
            errors.append(f"{cid}: missing candidate fields {missing}")
        if r.get("rto") not in ALLOWED_RTO:
            errors.append(f"{cid}: unsupported RTO {r.get('rto')!r}")
        if r.get("load_status") not in ALLOWED_LOAD:
            errors.append(f"{cid}: candidate is not explicitly admitted as load")
        try:
            if float(r.get("capacity_mw")) < 100:
                errors.append(f"{cid}: capacity below strict threshold")
        except (TypeError, ValueError):
            errors.append(f"{cid}: invalid capacity_mw")

        p = packet_by.get(str(r.get("queue_id")))
        if not p:
            errors.append(f"{cid}: no matching research packet")
            continue
        missing_p = sorted(REQUIRED_PACKET - set(p))
        if missing_p:
            errors.append(f"{cid}: missing packet fields {missing_p}")
        if str(p.get("public_load_classification") or "").strip().lower() not in {"load", "industrial load", "new load facility", "increase load"}:
            errors.append(f"{cid}: packet does not state an allowed public load classification")
        if not p.get("source_ladder"):
            errors.append(f"{cid}: empty source ladder")
        if not p.get("next_gates"):
            errors.append(f"{cid}: empty next-gates list")
        if not p.get("novelty_boundary"):
            errors.append(f"{cid}: missing novelty boundary")
        for i, s in enumerate(p.get("source_ladder", []), 1):
            if not s.get("kind") or not s.get("status"):
                errors.append(f"{cid}: source_ladder[{i}] missing kind/status")

    if errors:
        print("\n".join("ERROR: " + e for e in errors))
        return 1

    print(f"PASS: {len(rows)} strict discovery candidates validated")
    for r in rows:
        print(
            f"PASS: {r['queue_id']} {r['project_name']} "
            f"{r['capacity_mw']} MW · {r['rto']} · load-admitted"
        )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
