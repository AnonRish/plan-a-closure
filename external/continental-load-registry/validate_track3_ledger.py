#!/usr/bin/env python3
"""Validate the canonical Track 3 artifacts and their source-layer joins."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TRACK3 = ROOT / "data" / "track3"
EPOCH = ROOT / "data" / "external" / "epoch_ai"
ALLOWED = {"VERIFIED_SITE_SPECIFIC", "SITE_LEVEL_EVIDENCE", "PENDING_RESEARCH", "RESEARCHED_NO_PUBLIC_RECORD"}
EXPECTED_OBSERVATION_STATES = {"NOT_INGESTED", "SOURCE_AVAILABLE_NOT_INGESTED", "UNKNOWN", "PENDING_RESEARCH", "INGESTED_SNAPSHOT"}

def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def crosswalk_is_connection(item: dict | None) -> bool:
    text = str((item or {}).get("status") or "").lower()
    return any(x in text for x in ("grid_record", "utility_record", "service_record", "regulatory_record", "power_request", "load_request"))

def main() -> int:
    summary = load(TRACK3 / "summary.json")
    site_status = load(TRACK3 / "site_status.json")
    evidence = load(TRACK3 / "evidence_records.json")
    queue = load(TRACK3 / "research_queue.json")
    registry = load(EPOCH / "registry.json")
    source_evidence = load(EPOCH / "site_level_connection_evidence.json")
    crosswalk = load(EPOCH / "queue_crosswalk.json")
    source_stack = load(ROOT / "data" / "track3_source_stack.json")
    schema = load(ROOT / "data" / "track3_evidence_schema.json")
    observation = load(TRACK3 / "observation_queue.json")
    sites = site_status.get("records", [])
    ids = [x.get("epoch_id") for x in sites]
    if len(sites) != 93 or len(set(ids)) != 93 or any(not x for x in ids):
        raise SystemExit("FAIL: Track 3 site_status must contain 93 unique Epoch IDs")
    expected_domains = set(schema.get("domains", []))
    if not expected_domains:
        raise SystemExit("FAIL: Track 3 evidence schema has no domains")
    for rec in sites:
        actual_domains = set((rec.get("domains") or {}).keys())
        if actual_domains != expected_domains:
            raise SystemExit(
                f"FAIL: {rec.get('epoch_id')} domain set mismatch: "
                f"expected {sorted(expected_domains)}, got {sorted(actual_domains)}"
            )
    for payload, name in ((registry, "registry"), (source_evidence, "site evidence"), (crosswalk, "crosswalk")):
        if len(payload.get("records", [])) != 93:
            raise SystemExit(f"FAIL: {name} must contain 93 records")
    expected_ids = set(ids)
    if expected_ids != {x.get("epoch_id") for x in registry["records"]}:
        raise SystemExit("FAIL: site_status and Epoch registry IDs differ")
    if expected_ids != {x.get("epoch_id") for x in source_evidence["records"]}:
        raise SystemExit("FAIL: site_status and site-evidence IDs differ")
    if expected_ids != {x.get("epoch_id") for x in crosswalk["records"]}:
        raise SystemExit("FAIL: site_status and crosswalk IDs differ")
    grid_counts = {k: count for k, count in ((k, sum(1 for x in sites if x.get("domains", {}).get("grid_connection", {}).get("status") == k)) for k in ALLOWED) if count}
    if sum(grid_counts.values()) != 93:
        raise SystemExit(f"FAIL: grid-connection status counts do not sum to 93: {grid_counts}")
    if summary.get("domain_status_counts", {}).get("grid_connection") != grid_counts:
        raise SystemExit("FAIL: summary grid-connection counts do not match site_status")
    combined = sum(1 for x in sites if int(x.get("combined_site_level_evidence_count", 0)) > 0)
    if summary.get("combined_site_level_evidence_site_count") != combined:
        raise SystemExit("FAIL: combined site-evidence count does not match site_status")
    pending = [x for x in sites if x.get("domains", {}).get("grid_connection", {}).get("status") == "PENDING_RESEARCH"]
    researched_no_public = [x for x in sites if x.get("domains", {}).get("grid_connection", {}).get("status") == "RESEARCHED_NO_PUBLIC_RECORD"]
    if summary.get("research_completed_no_public_record_count") != len(researched_no_public):
        raise SystemExit("FAIL: researched-no-public-record count does not match site_status")
    if queue.get("count") != len(pending) or len(queue.get("records", [])) != len(pending):
        raise SystemExit("FAIL: research queue does not match pending grid research")
    # evidence_records.json is a canonical generated ledger. Its own record_count
    # and IDs are authoritative; source artifacts can legitimately gain new
    # evidence types without requiring this validator to predict generator output.
    evidence_records = evidence.get("records", [])
    if evidence.get("record_count") != len(evidence_records):
        raise SystemExit(
            f"FAIL: evidence record_count does not match evidence list length: "
            f"{evidence.get('record_count')} vs {len(evidence_records)}"
        )
    evidence_ids = [x.get("evidence_id") for x in evidence_records]
    if len(evidence_ids) != len(set(evidence_ids)) or any(not x for x in evidence_ids):
        raise SystemExit("FAIL: evidence IDs must be present and unique")
    unknown_targets = sorted({
        x.get("target_id")
        for x in evidence_records
        if x.get("target_id") and x.get("target_id") not in expected_ids
    })
    if unknown_targets:
        raise SystemExit(f"FAIL: evidence records reference unknown target IDs: {unknown_targets}")
    if summary.get("source_stack_count") != len(source_stack.get("sources", [])):
        raise SystemExit("FAIL: summary source_stack_count does not match catalog")
    for rec in sites:
        grid_state = (next((x.get("state_province") for x in crosswalk["records"] if x.get("epoch_id") == rec.get("epoch_id")), "") or "").strip()
        if grid_state and rec.get("state_province") != grid_state:
            raise SystemExit(
                f"FAIL: {rec.get('epoch_id')} state_province does not match curated crosswalk state"
            )

    if observation.get("task_count") != len(observation.get("tasks", [])):
        raise SystemExit("FAIL: observation queue task_count does not match task list length")
    observed_domain_counts = {}
    observed_priority_counts = {}
    for task in observation.get("tasks", []):
        state = task.get("current_state")
        if state not in EXPECTED_OBSERVATION_STATES:
            raise SystemExit(f"FAIL: invalid observation task state: {state}")
        observed_domain_counts[task.get("domain")] = observed_domain_counts.get(task.get("domain"), 0) + 1
        observed_priority_counts[task.get("priority")] = observed_priority_counts.get(task.get("priority"), 0) + 1
    if observation.get("task_counts_by_domain", {}) != observed_domain_counts:
        raise SystemExit("FAIL: observation queue domain counts do not match task list")
    if observation.get("task_counts_by_priority", {}) != observed_priority_counts:
        raise SystemExit("FAIL: observation queue priority counts do not match task list")
    if summary.get("observation_task_count") != observation.get("task_count"):
        raise SystemExit("FAIL: summary observation task count does not match observation queue")
    if summary.get("observation_task_counts_by_domain") != observed_domain_counts:
        raise SystemExit("FAIL: summary observation domain counts do not match observation queue")
    if summary.get("observation_task_counts_by_priority") != observed_priority_counts:
        raise SystemExit("FAIL: summary observation priority counts do not match observation queue")

    for rec in sites:
        state = rec.get("domains", {}).get("grid_connection", {}).get("status")
        if state not in ALLOWED:
            raise SystemExit(
                f"FAIL: invalid grid_connection state on {rec.get('epoch_id')}: {state}"
            )
        if rec.get("grid", {}).get("site_specific_queue_id") and state != "VERIFIED_SITE_SPECIFIC":
            raise SystemExit(
                f"FAIL: queue ID present without VERIFIED_SITE_SPECIFIC on {rec.get('epoch_id')}"
            )
    print("PASS: canonical Track 3 integrity checks passed")
    print(f"93 Epoch IDs aligned; grid states={grid_counts}; combined site evidence={combined}; evidence items={len(evidence_records)}; pending grid research={len(pending)}.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
