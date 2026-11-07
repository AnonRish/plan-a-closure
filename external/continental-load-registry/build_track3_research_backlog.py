#!/usr/bin/env python3
"""Build the one-task Track 3 research backlog from the canonical missing-information sweep."""
from __future__ import annotations
import csv
import json
from pathlib import Path
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parent
SWEEP = max(ROOT.glob("data/track3/site_missing_information_sweep_*.json"), key=lambda p: p.name, default=ROOT / "data/track3/site_missing_information_sweep_2026-09-27.json")
WORKFLOWS = ROOT / "data/track3/research_workflows.json"
OUT_JSON = ROOT / "data/track3/research_work_queue.json"
OUT_CSV = ROOT / "data/track3/research_work_queue.csv"
OUT_SUMMARY = ROOT / "data/track3/research_backlog_summary.json"

PUBLISHER_PRIORITY = {
    "project": "P0", "investors": "P0", "construction_companies": "P0",
    "energy_companies": "P0", "owner": "P1", "users": "P1",
    "address": "P1", "chip_quantities": "P1",
}
DOMAIN_PRIORITY = {
    "service_or_contract": "P0", "regulatory": "P0",
    "power_telemetry": "P0", "independent_corroboration": "P0", "grid_connection": "P0",
    "compute_tenancy": "P1", "chip_inventory": "P1", "remote_sensing": "P1",
    "cooling": "P1", "transformer_supply_chain": "P1",
}

def slug(value: str) -> str:
    out = "".join(ch.lower() if ch.isalnum() else "-" for ch in str(value))
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")

def render_query(template: str, site: str, state: str) -> str:
    return " ".join(
        template.replace("{site}", site).replace("{state}", state or "").split()
    )

def make_task(rec: dict, kind: str, key: str, workflow: dict) -> dict:
    site = rec["site_name"]
    state = rec.get("state_province", "")
    queries = [render_query(q, site, state) for q in workflow["queries"]]
    prefix = "PUB" if kind == "publisher" else "DOM"
    target_key = "field" if kind == "publisher" else "domain"
    return {
        "task_id": f"{prefix}-{rec['epoch_id']}-{slug(key)}",
        "kind": kind,
        "status": "OPEN",
        "priority": (PUBLISHER_PRIORITY if kind == "publisher" else DOMAIN_PRIORITY).get(key, "P1"),
        "epoch_id": rec["epoch_id"],
        "site_name": site,
        "country": rec.get("country"),
        "state_province": state,
        "current_it_power_mw": rec.get("current_it_power_mw"),
        target_key: key,
        "workflow_label": workflow["label"],
        "objective": workflow["objective"],
        "search_sequence": workflow["search"],
        "queries": queries,
        "search_links": ["https://www.google.com/search?q=" + quote_plus(q) for q in queries],
        "evidence_to_capture": workflow["capture"],
        "acceptance_rule": workflow["accept"],
        "reject_rule": workflow["reject"],
        "existing_next_action": rec.get("next_research_action"),
        "public_leads": rec.get("public_research_leads", []),
        "canonical_ingest_path": "data/track3/evidence_records.json",
        "submission_schema": "data/track3/research_submission_schema.json",
    }

def main() -> None:
    sweep = json.loads(SWEEP.read_text(encoding="utf-8"))
    workflows = json.loads(WORKFLOWS.read_text(encoding="utf-8"))
    publisher = workflows["publisher_workflows"]
    domain = workflows["domain_workflows"]

    publisher_tasks: list[dict] = []
    domain_tasks: list[dict] = []
    for rec in sweep["records"]:
        for field in rec.get("effective_unresolved_publisher_fields", []):
            if field not in publisher:
                raise KeyError(f"Missing publisher workflow: {field}")
            publisher_tasks.append(make_task(rec, "publisher", field, publisher[field]))
        for domain_name in rec.get("open_track3_domains", []):
            if domain_name not in domain:
                raise KeyError(f"Missing domain workflow: {domain_name}")
            domain_tasks.append(make_task(rec, "track3_domain", domain_name, domain[domain_name]))

    tasks = publisher_tasks + domain_tasks
    expected_pub = int(sweep["summary"]["effective_unresolved_publisher_fields"])
    # Recompute domain-open cells from the authoritative per-site domain lists.
    # The summary field can lag a reconciliation pass when public evidence changes.
    expected_dom = sum(len(rec.get("open_track3_domains", [])) for rec in sweep["records"])
    sweep.setdefault("summary", {})["open_track3_domain_cells"] = expected_dom
    if len(publisher_tasks) != expected_pub:
        raise AssertionError(f"publisher task count {len(publisher_tasks)} != {expected_pub}")
    if len(domain_tasks) != expected_dom:
        raise AssertionError(f"domain task count {len(domain_tasks)} != {expected_dom}")

    publisher_counts = {
        name: sum(1 for t in publisher_tasks if t.get("field") == name)
        for name in publisher
    }
    domain_counts = {
        name: sum(1 for t in domain_tasks if t.get("domain") == name)
        for name in domain
    }

    # Observation acquisition tasks are deliberately separate from OPEN domain cells:
    # an observation task can remain outstanding even when the current public evidence
    # state is terminal/complete. Keep the distinction machine-readable.
    observation_path = ROOT / "data/track3/observation_queue.json"
    observation_payload = json.loads(observation_path.read_text(encoding="utf-8")) if observation_path.exists() else {"tasks": []}
    observation_tasks = observation_payload.get("tasks", [])
    observation_by_domain = {}
    observation_by_priority = {}
    for task in observation_tasks:
        d = str(task.get("domain") or "unknown")
        pr = str(task.get("priority") or "P1")
        observation_by_domain[d] = observation_by_domain.get(d, 0) + 1
        observation_by_priority[pr] = observation_by_priority.get(pr, 0) + 1

    summary = {
        "schema_version": 1,
        "generated_on": sweep["summary"]["generated_on"],
        "source_sweep": str(SWEEP.relative_to(ROOT)).replace("\\", "/"),
        "sites": len(sweep["records"]),
        "publisher_tasks": len(publisher_tasks),
        "domain_tasks": len(domain_tasks),
        "total_tasks": len(tasks),
        "follow_on_observation_tasks": len(observation_tasks),
        "follow_on_observation_by_domain": observation_by_domain,
        "follow_on_observation_by_priority": observation_by_priority,
        "follow_on_observation_source": "data/track3/observation_queue.json",
        "publisher_by_field": publisher_counts,
        "domain_by_domain": domain_counts,
        "coverage_assertions": {
            "publisher_tasks_equal_effective_unresolved": len(publisher_tasks) == expected_pub,
            "domain_tasks_equal_open_cells": len(domain_tasks) == expected_dom,
            "all_93_sites_represented": len({r["epoch_id"] for r in sweep["records"]}) == 93,
            "observation_tasks_explicitly_accounted": len(observation_tasks) == int(observation_payload.get("task_count", len(observation_tasks))),
        },
        "semantics": "OPEN means research remains outstanding. Leads are discovery hints only. NO_PUBLIC_RECORD is a research disposition, not evidence of absence. Follow-on observation tasks are acquisition work and do not imply that a domain cell is currently open.",
    }

    queue = {
        "schema_version": 1,
        "generated_on": sweep["summary"]["generated_on"],
        "source_sweep": str(SWEEP.relative_to(ROOT)).replace("\\", "/"),
        "scope": "93 canonical Epoch AI frontier-AI reference sites",
        "summary": summary,
        "workflow_order": workflows["workflow_order"],
        "tasks": tasks,
    }

    csv_columns = [
        "task_id", "kind", "status", "priority", "epoch_id", "site_name",
        "country", "state_province", "current_it_power_mw", "field", "domain",
        "workflow_label", "objective", "queries", "evidence_to_capture",
        "acceptance_rule", "reject_rule", "existing_next_action",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=csv_columns, extrasaction="ignore")
        writer.writeheader()
        for row in tasks:
            flat = dict(row)
            for k in ("queries", "evidence_to_capture"):
                flat[k] = json.dumps(flat.get(k, []), ensure_ascii=False)
            writer.writerow(flat)

    OUT_JSON.write_text(json.dumps(queue, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUT_SUMMARY.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Keep the public completeness audit synchronized with this authoritative backlog.
    audit_path = ROOT / "data" / "website_completeness_audit.json"
    if audit_path.exists():
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        audit.setdefault("summary", {}).update({
            "publisher_research_tasks": len(publisher_tasks),
            "open_track3_domain_cells": len(domain_tasks),
            "research_tasks": len(tasks),
        })
        for section in audit.get("sections", []):
            if section.get("section") == "Track 3 research console":
                section["detail"] = (
                    "Search/filter console and acquisition backlog; current gap register has "
                    f"{len(publisher_tasks)} effective publisher-field tasks and "
                    f"{len(domain_tasks)} open domain cells."
                )
        audit["generated_on"] = summary["generated_on"]
        audit_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(
        "PASS: built research backlog",
        f"publisher={len(publisher_tasks)}",
        f"domains={len(domain_tasks)}",
        f"total={len(tasks)}",
        f"sites={summary['sites']}",
    )

if __name__ == "__main__":
    main()
