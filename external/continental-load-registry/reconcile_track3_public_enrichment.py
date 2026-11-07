#!/usr/bin/env python3
"""Reconcile source-captured public enrichment into Track 3 gap artifacts.

This step is deliberately conservative:
- it closes only publisher fields that have an explicit retained public-web record
- it never upgrades a domain from a source URL alone
- it never interprets NO_PUBLIC_RECORD as absence
- it rebuilds the machine-readable coverage register from current canonical status
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SWEEP = ROOT / "data/track3/site_missing_information_sweep_2026-09-27.json"
ENRICH = ROOT / "data/track3/public_web_enrichment_2026-09-27.json"
SITE_STATUS = ROOT / "data/track3/site_status.json"
MATRIX = ROOT / "data/track3/track3_completeness_matrix.json"
OUT = ROOT / "data/track3/coverage_gap_register_2026-09-27.json"
LEADS = ROOT / "data/track3/public_research_leads.json"

PUBLISHER_FIELDS = {
    "project", "investors", "construction_companies", "energy_companies",
    "owner", "users", "address", "chip_quantities",
}
OPEN_STATES = {
    "NOT_INGESTED", "NOT_ASSESSED", "UNKNOWN", "RESEARCH_QUEUE",
    "PENDING_RESEARCH",
}

def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def main() -> int:
    sweep = load(SWEEP)
    enrich = load(ENRICH)
    site_status = load(SITE_STATUS)
    matrix = load(MATRIX)
    leads = load(LEADS)

    fields_by_site: dict[str, set[str]] = {}
    for row in enrich.get("records", []):
        sid = str(row.get("epoch_id") or "")
        field = str(row.get("field") or "")
        if sid and field in PUBLISHER_FIELDS:
            fields_by_site.setdefault(sid, set()).add(field)

    removed = 0
    for rec in sweep.get("records", []):
        sid = str(rec.get("epoch_id") or "")
        found = fields_by_site.get(sid, set())
        old = list(rec.get("effective_unresolved_publisher_fields") or [])
        next_fields = [f for f in old if f not in found]
        removed += len(old) - len(next_fields)
        rec["effective_unresolved_publisher_fields"] = next_fields
        # Canonical domain state lives in site_status; keep the sweep aligned with it.
        rec["open_track3_domains"] = [
            domain
            for domain, state_counts in site_status.get("summary", {}).get("domain_status_counts", {}).items()
            if rec.get("domain_state_snapshot", {}).get(domain) in OPEN_STATES
        ] if rec.get("domain_state_snapshot") else rec.get("open_track3_domains", [])
        rec["remaining_unresolved_publisher_fields"] = [
            f for f in (rec.get("remaining_unresolved_publisher_fields") or [])
            if f not in found
        ]
        rec["public_enrichment_resolved_fields"] = sorted(
            set(rec.get("public_enrichment_resolved_fields") or []) | found
        )
        for field in found:
            if field in (rec.get("publisher_field_reconciliation") or {}):
                rec["publisher_field_reconciliation"][field]["public_enrichment_present"] = True
                rec["publisher_field_reconciliation"][field]["status"] = "PUBLIC_VALUE_OR_LEAD"

    effective_counts: dict[str, int] = {}
    for rec in sweep.get("records", []):
        for field in rec.get("effective_unresolved_publisher_fields", []):
            effective_counts[field] = effective_counts.get(field, 0) + 1

    site_by_id = {str(x.get("epoch_id")): x for x in site_status.get("records", [])}
    for rec in sweep.get("records", []):
        sid = str(rec.get("epoch_id") or "")
        status_rec = site_by_id.get(sid)
        if not status_rec:
            continue
        rec["domain_state_snapshot"] = {
            domain: status_rec.get("domains", {}).get(domain, {}).get("status", "UNKNOWN")
            for domain in site_status.get("summary", {}).get("domain_status_counts", {})
        }
        rec["open_track3_domains"] = [
            domain for domain, state in rec["domain_state_snapshot"].items()
            if state in OPEN_STATES
        ]

    summary = sweep.setdefault("summary", {})
    summary["effective_unresolved_publisher_fields"] = sum(effective_counts.values())
    summary["effective_unresolved_field_counts"] = effective_counts
    summary["public_web_enrichment_records"] = len(enrich.get("records", []))
    summary["public_web_enrichment_sites"] = len({
        x.get("epoch_id") for x in enrich.get("records", []) if x.get("epoch_id")
    })
    summary["reconciliation_updated_on"] = "2026-09-27"

    # Build a current site/domain closure view from canonical site_status.
    domain_status_counts = site_status.get("summary", {}).get("domain_status_counts", {})
    domain_summary = []
    for domain, counts in domain_status_counts.items():
        open_count = sum(v for state, v in counts.items() if state in OPEN_STATES)
        total = sum(counts.values())
        domain_summary.append({
            "domain": domain,
            "site_count": total,
            "resolved_site_count": total - open_count,
            "open_site_count": open_count,
            "status_counts": counts,
            "open_site_ids": [
                rec["epoch_id"]
                for rec in site_status.get("records", [])
                if (rec.get("domains", {}).get(domain, {}).get("status") in OPEN_STATES)
            ],
        })

    site_rows = []
    for rec in site_status.get("records", []):
        open_domains = [
            domain for domain in domain_status_counts
            if rec.get("domains", {}).get(domain, {}).get("status") in OPEN_STATES
        ]
        site_rows.append({
            "epoch_id": rec.get("epoch_id"),
            "site_name": rec.get("site_name"),
            "country": rec.get("country"),
            "state_province": rec.get("state_province"),
            "current_it_power_mw": rec.get("current_it_power_mw"),
            "open_domains": open_domains,
            "statuses": {
                domain: rec.get("domains", {}).get(domain, {}).get("status", "UNKNOWN")
                for domain in domain_status_counts
            },
            "evidence_counts": {
                "public_web": rec.get("public_web_evidence_count", 0),
                "remote_sensing": rec.get("domains", {}).get("remote_sensing", {}).get("observation_count", 0),
            },
        })

    matrix_rows = matrix.get("rows", [])
    out = {
        "schema_version": 1,
        "generated_on": "2026-09-27",
        "title": "Track 3 coverage gap register",
        "purpose": "Machine-readable closure register for every canonical site/domain and unresolved publisher field.",
        "basis": {
            "canonical_site_count": len(site_status.get("records", [])),
            "domain_count": len(domain_summary),
            "requirement_count": len(matrix_rows),
            "site_status_source": "data/track3/site_status.json",
            "publisher_sweep_source": "data/track3/site_missing_information_sweep_2026-09-27.json",
            "enrichment_source": "data/track3/public_web_enrichment_2026-09-27.json",
            "matrix_source": "data/track3/track3_completeness_matrix.json",
            "public_research_leads_source": "data/track3/public_research_leads.json",
        },
        "summary": {
            "effective_unresolved_publisher_fields": summary["effective_unresolved_publisher_fields"],
            "open_domain_cells": sum(x["open_site_count"] for x in domain_summary),
            "resolved_domain_cells": sum(x["resolved_site_count"] for x in domain_summary),
            "public_web_enrichment_records": len(enrich.get("records", [])),
            "public_web_enrichment_sites": len({
                x.get("epoch_id") for x in enrich.get("records", []) if x.get("epoch_id")
            }),
            "reconciled_field_closures_this_run": removed,
            "total_public_research_leads": leads.get("accounting", {}).get("lead_count"),
            "sites_with_public_research_leads": leads.get("accounting", {}).get("site_count"),
        },
        "publisher": {
            "summary": summary,
            "tasks": [
                {
                    "epoch_id": rec.get("epoch_id"),
                    "site_name": rec.get("site_name"),
                    "missing_publisher_fields": rec.get("effective_unresolved_publisher_fields", []),
                    "open_track3_domains": rec.get("open_track3_domains", []),
                    "next_research_action": rec.get("next_research_action"),
                }
                for rec in sweep.get("records", [])
            ],
        },
        "domain_summary": domain_summary,
        "sites": site_rows,
        "closure_rules": [
            "Close a publisher-field gap only when a retained source record explicitly supports that field.",
            "Location without a precise address remains location evidence and does not fabricate an address.",
            "NO_PUBLIC_RECORD is a documented search outcome, not evidence of absence.",
            "Queue capacity is not measured electricity demand.",
            "A physical observation is evidence about the observed scene, not automatic proof of compute.",
            "Two records in the same source family are not automatically independent corroboration.",
        ],
    }

    write_json(SWEEP, sweep)
    write_json(OUT, out)

    print(
        "PASS: reconciled public enrichment",
        f"enrichment_records={len(enrich.get('records', []))}",
        f"enrichment_sites={len({x.get('epoch_id') for x in enrich.get('records', []) if x.get('epoch_id')})}",
        f"closures={removed}",
        f"publisher_open={summary['effective_unresolved_publisher_fields']}",
        f"domain_open={out['summary']['open_domain_cells']}",
    )
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
