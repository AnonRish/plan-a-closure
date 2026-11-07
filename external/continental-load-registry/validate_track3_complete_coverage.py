#!/usr/bin/env python3
"""Validate the complete Track 3 repository coverage contract."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

REQUIRED_ARTIFACTS = [
    "data/track3/track3_completeness_matrix.json",
    "data/track3/global_compute_supply_chain.json",
    "data/track3/public_global_source_observations.json",
    "data/track3/public_web_claims.json",
    "data/track3/certificate_model.json",
    "data/track3/audit_population_protocol.json",
    "data/track3/sampling_protocol.json",
    "data/track3/inspection_protocol.json",
    "data/track3/serial_continuity_protocol.json",
    "data/track3/decommissioning_protocol.json",
    "data/track3/untraced_compute_pool.json",
    "data/track3/disclosure_protocol.json",
    "data/track3/remote_sensing_observation_targets.json",
    "data/track3/remote_sensing_observations.json",
    "data/track3/geo_coverage_audit_2026-09-27.json",
    "data/track3/observation_queue.json",
    "data/track3/site_status.json",
    "TRACK3_COMPLETE_COVERAGE.md",
    "CLOSED_CASE_PROTOCOL.md",
    "track3_certificate.py",
    "reconcile_track3_public_enrichment.py",
    "data/track3/coverage_gap_register_2026-09-27.json",
    "data/track3/research_assessments_2026-09-27.json",
    "data/track3/engineering_closure_2026-09-28.json",
    "build_track3_engineering_closure.py",
]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main() -> int:
    errors: list[str] = []

    for rel in REQUIRED_ARTIFACTS:
        path = ROOT / rel
        if not path.exists() or path.stat().st_size == 0:
            errors.append(f"missing or empty artifact: {rel}")

    if errors:
        print("\n".join("ERROR: " + e for e in errors))
        return 1

    closure = load("data/track3/engineering_closure_2026-09-28.json")
    if closure.get("repository_engineering_status") != "COMPLETE":
        errors.append("engineering closure status is not COMPLETE")
    if closure.get("empirical_track3_verification_status") != "NOT_CLOSED":
        errors.append("empirical Track 3 verification must remain NOT_CLOSED")
    if closure.get("untracked_gap_count") != 0:
        errors.append("engineering closure reports untracked repository gaps")
    matrix = load("data/track3/track3_completeness_matrix.json")
    rows = matrix.get("rows", [])
    if len(rows) < 17:
        errors.append(f"expected at least 17 Track 3 matrix rows, got {len(rows)}")

    for row in rows:
        for key in ("id", "requirement", "implementation", "status", "evidence", "blocking_gap"):
            if not row.get(key):
                errors.append(f"{row.get('id', 'UNKNOWN')}: missing matrix field {key}")

    phys = load("data/track3/remote_sensing_observations.json")
    if phys.get("observation_count", 0) < phys.get("derived_observation_count", 0):
        errors.append("remote-sensing derived count exceeds observation count")

    geo = load("data/track3/geo_coverage_audit_2026-09-27.json")
    if geo.get("scope", {}).get("epoch_reference_sites") != 93:
        errors.append("physical-coordinate audit scope is not 93")
    if len(geo.get("records", [])) != 93:
        errors.append("physical-coordinate audit is not exactly 93 records")
    if geo.get("summary", {}).get("resolved_sites", -1) + geo.get("summary", {}).get("unresolved_sites", -1) != 93:
        errors.append("physical-coordinate audit resolved/unresolved counts do not reconcile")

    targets = load("data/track3/remote_sensing_observation_targets.json")
    if targets.get("record_count") != 93 or len(targets.get("records", [])) != 93:
        errors.append("remote-sensing target universe is not exactly 93 records")
    if targets.get("summary", {}).get("derived_observation_count") != phys.get("derived_observation_count"):
        errors.append("remote-sensing target summary does not reconcile with observation ledger")

    sites = load("data/track3/site_status.json")
    if sites.get("summary", {}).get("epoch_site_count") != 93:
        errors.append("site-status epoch universe is not 93")

    assessment = load("data/track3/research_assessments_2026-09-27.json")
    assessment_rows = assessment.get("records", [])
    if assessment.get("record_count") != len(assessment_rows):
        errors.append("research assessment record_count does not match records")
    assessment_ids = [str(x.get("assessment_id")) for x in assessment_rows]
    if len(assessment_ids) != len(set(assessment_ids)) or any(not x or x == "None" for x in assessment_ids):
        errors.append("research assessment IDs are missing or duplicated")
    site_ids = {str(x.get("epoch_id")) for x in sites.get("records", [])}
    assessment_pairs = {(str(x.get("epoch_id")), str(x.get("domain"))) for x in assessment_rows}
    if len(assessment_pairs) != len(assessment_rows):
        errors.append("research assessments contain duplicate site/domain pairs")
    if not assessment_pairs.issubset({(sid, domain) for sid in site_ids for domain in [
        "site_identity","construction","chip_inventory","grid_connection","service_or_contract",
        "regulatory","compute_tenancy","power_telemetry","remote_sensing","cooling",
        "transformer_supply_chain","chip_ownership","chip_users","chip_shipments","independent_corroboration"
    ]}):
        errors.append("research assessments reference an unknown site/domain")
    terminal_states = {"INGESTED","INGESTED_DERIVED","INGESTED_SNAPSHOT","SITE_LEVEL_EVIDENCE",
                       "VERIFIED_SITE_SPECIFIC","RESEARCHED_NO_PUBLIC_RECORD","ASSESSED","ASSESSMENT_COMPLETE"}
    open_states = {"NOT_INGESTED","NOT_ASSESSED","UNKNOWN","RESEARCH_QUEUE","PENDING_RESEARCH"}
    all_domain_rows = [x.get("domains", {}) for x in sites.get("records", [])]
    open_cells = sum(
        1 for domains in all_domain_rows for state in domains.values()
        if state.get("status") in open_states
    )
    nonterminal_cells = sum(
        1 for domains in all_domain_rows for state in domains.values()
        if state.get("status") not in terminal_states
    )
    if open_cells:
        errors.append(f"site/domain matrix still contains {open_cells} open cells")
    if nonterminal_cells:
        errors.append(f"site/domain matrix contains {nonterminal_cells} non-terminal cells")
    if len(all_domain_rows) == 93 and sum(len(d) for d in all_domain_rows) != 93 * 15:
        errors.append("site/domain matrix does not contain exactly 1,395 domain cells")
    sweep = load("data/track3/site_missing_information_sweep_2026-09-27.json")
    if sweep.get("summary", {}).get("open_track3_domain_cells") != 0:
        errors.append("research sweep still reports open Track 3 domain cells")

    domain_matrix = load("data/track3/domain_completeness_matrix_2026-09-27.json")
    dm_rows = domain_matrix.get("records", [])
    if domain_matrix.get("accounting", {}).get("cells") != len(dm_rows):
        errors.append("domain completeness matrix record count does not reconcile")
    if domain_matrix.get("accounting", {}).get("cells") != 1395:
        errors.append("domain completeness matrix is not 93x15")
    if domain_matrix.get("accounting", {}).get("open_or_unassessed_cells") != 0:
        errors.append("domain completeness matrix still contains open cells")
    if sum(domain_matrix.get("accounting", {}).get("status_counts", {}).values()) != 1395:
        errors.append("domain completeness matrix status counts do not sum to 1,395")

    publisher_matrix = load("data/track3/publisher_completeness_matrix_2026-09-27.json")
    backlog = load("data/track3/research_backlog_summary.json")
    observations = load("data/track3/observation_queue.json")
    if closure.get("remaining_research_and_acquisition", {}).get("public_publisher_field_tasks_open") != backlog.get("publisher_tasks"):
        errors.append("engineering closure publisher backlog does not reconcile")
    if closure.get("remaining_research_and_acquisition", {}).get("follow_on_observation_tasks") != observations.get("task_count"):
        errors.append("engineering closure observation queue does not reconcile")
    pm_rows = publisher_matrix.get("records", [])
    if publisher_matrix.get("accounting", {}).get("cells") != len(pm_rows):
        errors.append("publisher completeness matrix record count does not reconcile")
    if publisher_matrix.get("accounting", {}).get("cells") != 744:
        errors.append("publisher completeness matrix is not 93x8")
    if publisher_matrix.get("accounting", {}).get("open_research_cells") != sweep.get("summary", {}).get("effective_unresolved_publisher_fields"):
        errors.append("publisher completeness matrix open count does not reconcile with sweep")

    coord_status = {str(x.get("epoch_id")): x.get("coordinate_status") for x in geo.get("records", [])}
    for x in geo.get("records", []):
        if x.get("coordinate_status") == "RESOLVED":
            if x.get("latitude") is None or x.get("longitude") is None:
                errors.append(f"{x.get('epoch_id')}: RESOLVED coordinate lacks lat/lon")
        elif x.get("coordinate_status") == "UNRESOLVED":
            if x.get("latitude") is not None or x.get("longitude") is not None:
                errors.append(f"{x.get('epoch_id')}: UNRESOLVED coordinate contains lat/lon")

    accounting = load("data/track3/global_compute_supply_chain.json")
    if accounting.get("current", {}).get("global_transaction_level_closure") != "UNKNOWN":
        errors.append("global transaction-level closure must remain explicitly UNKNOWN")

    residual = load("data/track3/untraced_compute_pool.json")
    if residual.get("current_snapshot", {}).get("status") != "UNKNOWN":
        errors.append("untraced pool must remain UNKNOWN until transaction inputs close")

    inspection = load("data/track3/inspection_protocol.json")
    if inspection.get("current_observation_count") != 0:
        errors.append("inspection count changed without an independently retained inspection ledger")

    certificate = load("data/track3/certificate_model.json")
    if certificate.get("status") != "FRAMEWORK_IMPLEMENTED":
        errors.append("certificate model status changed unexpectedly")

    public_claims = load("data/track3/public_web_claims.json")
    enrichment = load("data/track3/public_web_enrichment_2026-09-27.json")
    epoch_registry = load("data/external/epoch_ai/registry.json")
    canonical_site_names = {
        str(x.get("epoch_id")): str((x.get("normalized") or {}).get("name") or "")
        for x in epoch_registry.get("records", [])
    }
    claim_rows = public_claims.get("claims", [])
    enrichment_rows = enrichment.get("records", [])
    if enrichment.get("record_count") != len(enrichment_rows):
        errors.append("public-web enrichment top-level record_count does not reconcile")
    if enrichment.get("accounting", {}).get("record_count") != len(enrichment_rows):
        errors.append("public-web enrichment accounting.record_count does not reconcile")
    disposition_counts = enrichment.get("accounting", {}).get("disposition_counts", {})
    if disposition_counts and sum(int(v) for v in disposition_counts.values()) != len(enrichment_rows):
        errors.append("public-web enrichment disposition counts do not reconcile")
    if public_claims.get("accounting", {}).get("claim_count") != len(claim_rows):
        errors.append("public-web claim count does not reconcile")
    if len(claim_rows) != len(enrichment_rows):
        errors.append("public-web claim layer is not 1:1 with enrichment records")
    claim_ids = [str(x.get("claim_id")) for x in claim_rows]
    if len(claim_ids) != len(set(claim_ids)):
        errors.append("public-web claim IDs are not unique")

    def source_key(x):
        payload = {
            "site_name": x.get("site_name"),
            "field": x.get("field"),
            "value": x.get("value"),
            "relationship": x.get("relationship"),
            "source": x.get("source"),
            "source_urls": x.get("source_urls") or [],
            "publication_date": x.get("publication_date"),
            "source_record_id": x.get("evidence_id") or x.get("source_record_id") or None,
        }
        import hashlib
        return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()

    enrichment_keys = [source_key(x) for x in enrichment_rows]
    claim_keys = [source_key(x) for x in claim_rows]
    if len(enrichment_keys) != len(set(enrichment_keys)):
        errors.append("public-web enrichment source keys are not unique")
    if len(claim_keys) != len(set(claim_keys)):
        errors.append("public-web claim source keys are not unique")
    if set(enrichment_keys) != set(claim_keys):
        errors.append("public-web claims do not reconcile 1:1 with enrichment records")

    for x in enrichment_rows:
        eid = str(x.get("epoch_id") or "")
        site_name = str(x.get("site_name") or "")
        canonical = canonical_site_names.get(eid)
        if eid and site_name and canonical and site_name != canonical:
            errors.append(
                f"public-web enrichment site_name mismatch for {eid}: "
                f"{site_name!r} != canonical {canonical!r}"
            )

    for x in claim_rows:
        eid = str(x.get("epoch_id") or "")
        site_name = str(x.get("site_name") or "")
        canonical = canonical_site_names.get(eid)
        if eid and site_name and canonical and site_name != canonical:
            errors.append(
                f"public-web claim site_name mismatch for {eid}: "
                f"{site_name!r} != canonical {canonical!r}"
            )
        if not x.get("claim_id") or not x.get("field"):
            errors.append("public-web claim missing claim_id or field")
        if x.get("claim_scope") == "site_level_public_web" and not x.get("epoch_id"):
            errors.append(f"site-scoped public-web claim {x.get('claim_id')} missing epoch_id")
        if not (x.get("source_urls") or []):
            errors.append(f"public-web claim {x.get('claim_id')} has no retained source URL")
    if public_claims.get("accounting", {}).get("claim_count", 0) < 400:
        errors.append("public-web claim layer is missing retained enrichment claims at the current 400-record baseline")

    leads = load("data/track3/public_research_leads.json")
    lead_rows = leads.get("records", [])
    lead_accounting = leads.get("accounting", {})
    unique_lead_ids = {x.get("lead_id") for x in lead_rows}
    unique_lead_sites = {x.get("epoch_id") for x in lead_rows if x.get("epoch_id")}
    assert isinstance(lead_accounting.get("lead_count"), int)
    assert lead_accounting.get("lead_count") == len(lead_rows)
    assert isinstance(lead_accounting.get("site_count"), int)
    assert lead_accounting.get("site_count") == len(unique_lead_sites)
    assert len(unique_lead_ids) == len(lead_rows)
    assert all(x.get("lead_id") and x.get("epoch_id") and x.get("field") and x.get("finding") for x in lead_rows)
    assert all(x.get("status") in {"PUBLIC_LEAD_REVIEW_REQUIRED","RETAINED_SOURCE","PUBLIC_SOURCE"} for x in lead_rows)

    gap_register = load("data/track3/coverage_gap_register_2026-09-27.json")
    if len(gap_register.get("sites", [])) != 93:
        errors.append("coverage gap register is not exactly 93 sites")
    if len(gap_register.get("domain_summary", [])) != 15:
        errors.append("coverage gap register is not exactly 15 evidence domains")
    if gap_register.get("summary", {}).get("public_web_enrichment_records") != enrichment.get("record_count"):
        errors.append("coverage gap register public-enrichment count does not reconcile")
    if gap_register.get("summary", {}).get("total_public_research_leads") != lead_accounting.get("lead_count"):
        errors.append("coverage gap register public-research-lead count does not reconcile")
    if gap_register.get("summary", {}).get("sites_with_public_research_leads") != lead_accounting.get("site_count"):
        errors.append("coverage gap register public-research-lead site count does not reconcile")
    enrichment_site_count = enrichment.get("accounting", {}).get("site_count")
    if enrichment_site_count is None:
        enrichment_site_count = enrichment.get("accounting", {}).get("sites_with_findings")
    if gap_register.get("summary", {}).get("public_web_enrichment_sites") != enrichment_site_count:
        errors.append("coverage gap register public-enrichment site count does not reconcile")

    global_sources = load("data/track3/public_global_source_observations.json")
    if len(global_sources.get("observations", [])) < 6:
        errors.append("global public source observation inventory is incomplete")

    if errors:
        print("\n".join("ERROR: " + e for e in errors))
        return 1

    print(f"PASS: complete Track 3 coverage contract validated ({len(rows)} matrix rows, 93-site reference universe)")
    print("PASS: explicit UNKNOWN states retained where public/authorized evidence is not available")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
