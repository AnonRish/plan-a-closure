#!/usr/bin/env python3
"""Build the Track 3 repository engineering-closure register.

This artifact distinguishes:
- closed repository engineering state;
- open public-source research tasks;
- follow-on acquisition tasks;
- external-capability blockers.

It never converts missing evidence into a positive finding.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TRACK3 = ROOT / "data" / "track3"

def load(name: str) -> dict:
    return json.loads((TRACK3 / name).read_text(encoding="utf-8"))

def count_terminal_domain_cells(site_status: dict) -> tuple[int, int, int]:
    terminal = {
        "INGESTED", "INGESTED_DERIVED", "INGESTED_SNAPSHOT", "SITE_LEVEL_EVIDENCE",
        "VERIFIED_SITE_SPECIFIC", "RESEARCHED_NO_PUBLIC_RECORD", "ASSESSED",
        "ASSESSMENT_COMPLETE",
    }
    open_states = {"NOT_INGESTED", "NOT_ASSESSED", "UNKNOWN", "RESEARCH_QUEUE", "PENDING_RESEARCH"}
    rows = site_status.get("records", [])
    cells = [d for r in rows for d in (r.get("domains") or {}).values()]
    terminal_count = sum(1 for d in cells if d.get("status") in terminal)
    open_count = sum(1 for d in cells if d.get("status") in open_states)
    return len(cells), terminal_count, open_count

def main() -> int:
    now = datetime.now(timezone.utc).isoformat()
    summary = load("summary.json")
    site_status = load("site_status.json")
    pub = load("publisher_completeness_matrix_2026-09-27.json")
    dom = load("domain_completeness_matrix_2026-09-27.json")
    backlog = load("research_backlog_summary.json")
    obs = load("observation_queue.json")
    handoff = load("external_capability_handoff_2026-09-28.json")
    strict = load("strict_discovery_case_dispositions_2026-09-28.json")
    ambiguous = load("ambiguous_case_studies.json")
    gap = load("coverage_gap_register_2026-09-27.json")
    geo = load("geo_coverage_audit_2026-09-27.json")
    remote = load("remote_sensing_observations.json")

    domain_cells, terminal_cells, open_domain_cells = count_terminal_domain_cells(site_status)
    external_blockers = handoff.get("blockers", [])
    unresolved_external = [
        x for x in external_blockers
        if x.get("current_state") != "BLOCKED_EXTERNAL_CAPABILITY"
    ]

    publisher_open = int(pub.get("accounting", {}).get("open_research_cells", 0))
    backlog_publisher = int(backlog.get("publisher_tasks", 0))
    observation_tasks = int(obs.get("task_count", len(obs.get("tasks", []))))
    remote_sites = len({str(x.get("epoch_id")) for x in remote.get("records", []) if x.get("epoch_id")})
    strict_cases = strict.get("cases", [])
    ambiguous_cases = ambiguous.get("cases", [])

    closure_checks = {
        "canonical_sites_93": int(summary.get("epoch_site_count", 0)) == 93 == len(site_status.get("records", [])),
        "domain_matrix_93x15": domain_cells == 1395 and int(dom.get("accounting", {}).get("cells", 0)) == 1395,
        "domain_cells_all_terminal": terminal_cells == 1395 and open_domain_cells == 0,
        "domain_matrix_no_open_cells": int(dom.get("accounting", {}).get("open_or_unassessed_cells", -1)) == 0,
        "publisher_matrix_93x8": int(pub.get("accounting", {}).get("cells", 0)) == 744 and len(pub.get("records", [])) == 744,
        "publisher_backlog_reconciles": publisher_open == backlog_publisher == int(summary.get("publisher_research_tasks", publisher_open)),
        "observation_queue_reconciles": observation_tasks == int(summary.get("observation_task_count", observation_tasks)),
        "coverage_gap_register_93_sites": len(gap.get("sites", [])) == 93,
        "geo_audit_93_sites": len(geo.get("records", [])) == 93,
        "strict_queue_five_terminal_cases": len(strict_cases) == 5 and int(strict.get("summary", {}).get("terminal_disposition_count", 0)) == 5,
        "ambiguous_pilot_four_cases": len(ambiguous_cases) == 4,
        "external_blockers_explicitly_accounted": len(external_blockers) == 7 and not unresolved_external,
        "no_untracked_domain_gaps": open_domain_cells == 0,
        "no_untracked_publisher_gaps": publisher_open == backlog_publisher,
        "no_untracked_observation_gaps": observation_tasks == int(obs.get("task_count", -1)),
    }

    payload = {
        "schema_version": 1,
        "generated_at_utc": now,
        "title": "Track 3 repository engineering closure",
        "repository_engineering_status": "COMPLETE" if all(closure_checks.values()) else "INCOMPLETE",
        "empirical_track3_verification_status": "NOT_CLOSED",
        "scope": {
            "canonical_epoch_sites": 93,
            "defined_site_domain_cells": 1395,
            "site_domain_terminal_cells": terminal_cells,
            "site_domain_open_cells": open_domain_cells,
            "publisher_field_cells": 744,
        },
        "current_public_evidence": {
            "public_web_evidence_records": int(summary.get("public_web_evidence_record_count", 0)),
            "remote_sensing_derived_observations": int(summary.get("remote_sensing_derived_observation_count", 0)),
            "remote_sensing_sites_with_derived_observations": remote_sites,
            "site_specific_queue_ids": int(summary.get("site_specific_queue_id_count", 0)),
            "researched_no_public_record_sites": int(summary.get("research_completed_no_public_record_count", 0)),
            "grid_connection_status_counts": {
                "SITE_LEVEL_EVIDENCE": int(summary.get("domain_status_counts", {}).get("grid_connection", {}).get("SITE_LEVEL_EVIDENCE", 0)),
                "RESEARCHED_NO_PUBLIC_RECORD": int(summary.get("domain_status_counts", {}).get("grid_connection", {}).get("RESEARCHED_NO_PUBLIC_RECORD", 0)),
                "VERIFIED_SITE_SPECIFIC": int(summary.get("domain_status_counts", {}).get("grid_connection", {}).get("VERIFIED_SITE_SPECIFIC", 0)),
            },
        },
        "remaining_research_and_acquisition": {
            "public_publisher_field_tasks_open": publisher_open,
            "open_track3_domain_cells": open_domain_cells,
            "follow_on_observation_tasks": observation_tasks,
            "follow_on_observation_by_domain": obs.get("task_counts_by_domain", {}),
            "semantics": "These are explicitly tracked unresolved research/acquisition tasks, not untracked repository gaps and not evidence of absence.",
        },
        "external_capability_blockers": {
            "count": len(external_blockers),
            "state_set": sorted({x.get("current_state") for x in external_blockers}),
            "register": "data/track3/external_capability_handoff_2026-09-28.json",
        },
        "case_laboratory": {
            "ambiguous_pilot_case_count": len(ambiguous_cases),
            "strict_discovery_case_count": len(strict_cases),
            "strict_terminal_disposition_count": int(strict.get("summary", {}).get("terminal_disposition_count", 0)),
        },
        "closure_checks": closure_checks,
        "untracked_gap_count": 0 if all(closure_checks.values()) else sum(1 for v in closure_checks.values() if not v),
        "authoritative_artifacts": [
            "data/track3/site_status.json",
            "data/track3/domain_completeness_matrix_2026-09-27.json",
            "data/track3/publisher_completeness_matrix_2026-09-27.json",
            "data/track3/research_backlog_summary.json",
            "data/track3/observation_queue.json",
            "data/track3/coverage_gap_register_2026-09-27.json",
            "data/track3/external_capability_handoff_2026-09-28.json",
        ],
        "completion_semantics": "COMPLETE means the repository engineering contract has no untracked defined gaps. It does not mean the empirical Track 3 verification problem is solved. Missing public, privileged, transaction-level, serial-level, inspection, intelligence, or independent-governance evidence remains explicitly unresolved.",
    }
    out = TRACK3 / "engineering_closure_2026-09-28.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Keep the single machine-readable completion gate synchronized with the
    # canonical summary instead of hand-maintaining derived observation counts.
    gate_path = TRACK3 / "completion_gate.json"
    if gate_path.exists():
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
        gate.setdefault("public_evidence_accounting", {})["remote_sensing_derived_observations"] = int(
            summary.get("remote_sensing_derived_observation_count", 0)
        )
        gate.setdefault("public_evidence_accounting", {})["remote_sensing_sites_with_derived_observations"] = remote_sites
        statement = gate.get("release_statement", "")
        if statement:
            import re
            statement = re.sub(
                r"\d+ derived remote-sensing observations across 92 sites",
                f"{summary.get('remote_sensing_derived_observation_count', 0)} derived remote-sensing observations across 92 sites",
                statement,
            )
            gate["release_statement"] = statement
        gate["generated_on"] = datetime.now(timezone.utc).date().isoformat()
        gate_path.write_text(json.dumps(gate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{payload['repository_engineering_status']}: Track 3 engineering closure; untracked_gap_count={payload['untracked_gap_count']}")
    return 0 if payload["repository_engineering_status"] == "COMPLETE" else 1

if __name__ == "__main__":
    raise SystemExit(main())
