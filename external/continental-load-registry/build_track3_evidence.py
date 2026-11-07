#!/usr/bin/env python3
"""
Build Track 3 evidence artifacts from the preserved Epoch site universe and
site-level research layer.

The builder never interprets a missing record as evidence of absence.\n# 2026-09-27 integrity refresh: regenerate canonical evidence/provenance artifacts from retained source layers.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
EPOCH = ROOT / "data" / "external" / "epoch_ai"
OUT = ROOT / "data" / "track3"

SOURCE_STACK = ROOT / "data" / "track3_source_stack.json"
EVIDENCE = EPOCH / "site_level_connection_evidence.json"
REGISTRY = EPOCH / "registry.json"
GAP = EPOCH / "queue_gap_analysis.csv"
POWER_OBSERVATIONS = OUT / "power_observations.json"
COOLING_OBSERVATIONS = OUT / "cooling_observations.json"
REMOTE_OBSERVATIONS = OUT / "remote_sensing_observations.json"
TRANSFORMER_EVENTS = OUT / "transformer_supply_chain_events.json"
PUBLIC_WEB_ENRICHMENT = OUT / "public_web_enrichment_2026-09-27.json"
RESEARCH_ASSESSMENTS = OUT / "research_assessments_2026-09-27.json"

SITE_DOMAINS = (
    "site_identity",
    "construction",
    "chip_inventory",
    "grid_connection",
    "service_or_contract",
    "regulatory",
    "compute_tenancy",
    "power_telemetry",
    "remote_sensing",
    "cooling",
    "transformer_supply_chain",
    "chip_ownership",
    "chip_users",
    "chip_shipments",
    "independent_corroboration",
)

def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

EXTERNAL_SOURCE_FILES = {
    "chip_ownership": [
        "ai_chip_owners_cumulative_by_designer.csv",
        "ai_chip_owners_quarters_by_chip_type.csv",
        "ai_chip_owners_cumulative_by_chip_type.csv",
    ],
    "chip_users": [
        "ai_chip_users_year_end_by_lab.csv",
        "ai_chip_users_intermediates_by_lab.csv",
    ],
    "chip_shipments": [
        "ai_chip_sales_chip_types.csv",
        "ai_chip_sales_organizations.csv",
        "ai_chip_sales_timelines_by_chip.csv",
    ],
    "gpu_clusters": [
        "gpu_clusters.csv",
    ],
    "chip_components": [
        "ai_chip_components_quarterly_by_chip.csv",
        "ai_chip_components_quarterly_by_designer.csv",
        "ai_chip_components_supply_denominators.csv",
    ],
    "cooling": [
        "data_center_chillers.csv",
        "data_center_cooling_towers.csv",
    ],
}

def external_snapshot_available(domain: str) -> bool:
    return all((EPOCH / name).exists() and (EPOCH / name).stat().st_size > 0
               for name in EXTERNAL_SOURCE_FILES[domain])

def site_status(rec: dict[str, Any], domain: str, power_observations_by_site: dict[str, list[dict[str, Any]]] | None = None, cooling_observations_by_site: dict[str, list[dict[str, Any]]] | None = None, remote_observations_by_site: dict[str, list[dict[str, Any]]] | None = None, transformer_events_by_site: dict[str, list[dict[str, Any]]] | None = None, manual_public_by_site: dict[str, list[dict[str, Any]]] | None = None, research_assessments_by_site: dict[str, dict[str, dict[str, Any]]] | None = None) -> dict[str, Any]:
    ev = rec.get("site_level_connection_evidence") or []
    grid = rec.get("grid_crosswalk") or {}
    manual_public = (manual_public_by_site or {}).get(str(rec.get("epoch_id")), [])
    manual_fields = {str(x.get("field") or "") for x in manual_public}
    research_assessment = ((research_assessments_by_site or {}).get(str(rec.get("epoch_id")), {}) or {}).get(domain)
    crosswalk_ev = grid.get("site_level_public_evidence") or {}
    crosswalk_status = str(crosswalk_ev.get("status") or "").lower()
    if domain == "site_identity":
        return {
            "status": "INGESTED",
            "basis": "Epoch AI site record imported."
        }
    if domain == "construction":
        return {
            "status": "INGESTED" if rec.get("timeline_record_count", 0) > 0 or "construction_companies" in manual_fields else "UNKNOWN",
            "basis": "Epoch AI dated timeline records and/or retained site-specific construction-company evidence are preserved."
            if rec.get("timeline_record_count", 0) > 0 or "construction_companies" in manual_fields else "No retained Epoch timeline rows or site-specific construction-company record."
        }
    if domain == "chip_inventory":
        if rec.get("chip_quantity_record_count", 0) > 0 or "chip_quantities" in manual_fields:
            return {
                "status": "INGESTED",
                "basis": "Epoch AI site-level chip-quantity records and/or retained public chip/accelerator evidence are preserved."
            }
        if research_assessment:
            return {"status": research_assessment.get("status", "ASSESSMENT_COMPLETE"), "basis": research_assessment.get("basis", "The current public evidence layer has no qualifying retained record for this domain."), "assessment_id": research_assessment.get("assessment_id")}
        return {"status": "UNKNOWN", "basis": "No retained site-level chip-quantity rows."}
    if domain == "service_or_contract":
        types = {"site_specific_service_contract","site_specific_service","site_specific_energy_contract","site_specific_utility_planning","site_specific_behind_the_meter_service_evidence"}
        type_lower = {str(x).lower() for x in types}
        matches = [x for x in ev if str(x.get("type") or "").lower() in type_lower]
        crosswalk_service = bool(
            crosswalk_ev and any(token in crosswalk_status for token in ("service", "contract", "planning", "energy"))
        )
        if matches or crosswalk_service or "service_or_contract" in manual_fields:
            return {"status":"SITE_LEVEL_EVIDENCE","basis":"A site-specific service, utility-planning, energy-contract, or public service/contract/planning record is attached; it is kept separate from queue-ID verification."}
        if research_assessment:
            return {"status": research_assessment.get("status", "ASSESSMENT_COMPLETE"), "basis": research_assessment.get("basis", "The current public evidence layer has no qualifying retained record for this domain."), "assessment_id": research_assessment.get("assessment_id")}
        return {"status":"NOT_INGESTED","basis":"No site-specific service or energy-contract evidence is currently attached."}
    if domain == "compute_tenancy":
        matches = [x for x in ev if x.get("type") in {"site_specific_compute_tenancy","site_specific_compute_contract","site_specific_lease"}]
        if matches:
            return {"status":"INGESTED_SNAPSHOT","basis":"A site-specific compute-tenancy or capacity contract is preserved; this does not establish utility connection or measured load."}
        if research_assessment:
            return {"status": research_assessment.get("status", "ASSESSMENT_COMPLETE"), "basis": research_assessment.get("basis", "The current public evidence layer has no qualifying retained record for this domain."), "assessment_id": research_assessment.get("assessment_id")}
        return {"status":"UNKNOWN","basis":"No site-specific compute-tenancy contract has been attached in the current evidence layer."}
    if domain == "regulatory":
        matches = [x for x in ev if "regulatory" in str(x.get("type") or "").lower()]
        if matches or "regulatory" in manual_fields:
            return {
                "status": "INGESTED",
                "basis": "Site-level regulatory evidence is preserved in the Track 3 evidence layer."
            }
        if research_assessment:
            return {"status": research_assessment.get("status", "ASSESSMENT_COMPLETE"), "basis": research_assessment.get("basis", "The current public evidence layer has no qualifying retained record for this domain."), "assessment_id": research_assessment.get("assessment_id")}
        return {
            "status": "NOT_ASSESSED",
            "basis": "No site-level regulatory evidence has been separately assessed in the current Track 3 layer."
        }
    if domain == "grid_connection":
        connection_types = {"site_specific_queue", "site_specific_utility_relationship", "site_specific_utility", "site_specific_service", "site_specific_service_contract", "site_specific_power_request", "site_specific_load_request", "site_specific_utility_capacity_record", "site_specific_grid_facility_record", "site_specific_utility_power", "site_specific_facility_utility_relationship", "site_specific_utility_facility_record", "site_specific_utility_planning", "site_specific_utility_service", "site_specific_facility_utility_evidence", "site_specific_regulatory", "site_specific_regulatory_support", "site_specific_behind_the_meter_service_evidence", "site_specific_grid_identity_no_queue"}
        connection_type_lower = {str(x).lower() for x in connection_types}
        connection_evidence = [x for x in ev if str(x.get("type") or "").lower() in connection_type_lower]
        # Public-web enrichment can supply site-specific electrical evidence even when
        # no queue ID is public. Only explicit grid/substation/transmission language
        # qualifies; a generic commercial capacity/lease record does not.
        public_grid_terms = (
            "grid", "substation", "transmission", "high-voltage", "110kv", "220kv",
            "420kv", "132kv", "33kv", "power infrastructure", "electricity supply",
            "electricity network", "power grid", "directly draws electricity",
            "direct and redundant connections", "transformer station",
        )
        public_grid_evidence = []
        for item in manual_public:
            field_name = str(item.get("field") or "").lower()
            claim_text = " ".join([
                str(item.get("value") or ""),
                str(item.get("relationship") or ""),
                str(item.get("scope_note") or ""),
            ]).lower()
            if field_name == "energy_companies" or (
                field_name == "service_or_contract" and any(term in claim_text for term in public_grid_terms)
            ):
                public_grid_evidence.append(item)
        crosswalk_connection_evidence = bool(crosswalk_ev)
        if grid.get("site_specific_queue_id"):
            return {
                "status": "VERIFIED_SITE_SPECIFIC",
                "basis": "A site-specific queue/connection ID is present in the preserved crosswalk."
            }
        if any(x.get("type") == "site_specific_queue" for x in connection_evidence):
            return {
                "status": "VERIFIED_SITE_SPECIFIC",
                "basis": "Site-level queue evidence is attached to the Epoch record."
            }
        if connection_evidence or crosswalk_connection_evidence or public_grid_evidence or "energy_companies" in manual_fields:
            return {
                "status": "SITE_LEVEL_EVIDENCE",
                "basis": "At least one site-level utility, service, power-request, load-request, regulatory, or explicit public grid/substation/transmission record is attached; no queue ID is asserted."
            }
        if any(x.get("type") == "NO_MATCH_FOUND_SITE_SPECIFIC_QUEUE_OR_SERVICE" for x in ev):
            return {
                "status": "RESEARCHED_NO_PUBLIC_RECORD",
                "basis": "A documented site-specific search was performed and no public queue/service record was retained. This is a research outcome, not evidence that the site lacks grid service."
            }
        return {
            "status": "PENDING_RESEARCH",
            "basis": "No site-level connection/service evidence or documented no-match search is currently attached."
        }
    if domain == "power_telemetry":
        observations = (power_observations_by_site or {}).get(str(rec.get("epoch_id")), [])
        if observations:
            return {
                "status": "INGESTED_SNAPSHOT",
                "basis": "A site-specific annual electricity-consumption observation is preserved. This does not satisfy the separate interval-demand telemetry target."
            }
        if research_assessment:
            return {"status": research_assessment.get("status", "ASSESSMENT_COMPLETE"), "basis": research_assessment.get("basis", "The current public evidence layer has no qualifying retained record for this domain."), "assessment_id": research_assessment.get("assessment_id")}
        return {
            "status": "NOT_INGESTED",
            "basis": "The public repository currently specifies this evidence stream but does not ingest site-level interval measurements."
        }
    if domain == "cooling":
        observations = (cooling_observations_by_site or {}).get(str(rec.get("epoch_id")), [])
        if observations or "cooling" in manual_fields:
            return {
                "status": "INGESTED_SNAPSHOT",
                "basis": "A site-level cooling-equipment observation is preserved. This is supporting infrastructure evidence, not direct thermal telemetry."
            }
        if research_assessment:
            return {"status": research_assessment.get("status", "ASSESSMENT_COMPLETE"), "basis": research_assessment.get("basis", "The current public evidence layer has no qualifying retained record for this domain."), "assessment_id": research_assessment.get("assessment_id")}
        return {
            "status": "NOT_INGESTED",
            "basis": "The public repository currently specifies this evidence stream but does not ingest site-level cooling-equipment measurements."
        }
    if domain == "remote_sensing":
        observations = [
            x for x in (remote_observations_by_site or {}).get(str(rec.get("epoch_id")), [])
            if x.get("status") == "INGESTED_DERIVED"
        ]
        if observations:
            return {
                "status": "INGESTED_DERIVED",
                "observation_count": len(observations),
                "modalities": sorted({str(x.get("modality")) for x in observations}),
                "basis": "Public satellite COG windows were processed into site-level observations with scene provenance."
            }
        if research_assessment:
            return {"status": research_assessment.get("status", "ASSESSMENT_COMPLETE"), "basis": research_assessment.get("basis", "The current public evidence layer has no qualifying retained record for this domain."), "assessment_id": research_assessment.get("assessment_id")}
        return {
            "status": "NOT_INGESTED",
            "basis": "No site-level remote-sensing observations have been successfully processed yet."
        }
    if domain == "transformer_supply_chain":
        events = (transformer_events_by_site or {}).get(str(rec.get("epoch_id")), [])
        if events:
            return {
                "status": "INGESTED",
                "event_count": len(events),
                "basis": "Source-backed HV-transformer procurement, delivery, installation, or assignment events are retained."
            }
        if research_assessment:
            return {"status": research_assessment.get("status", "ASSESSMENT_COMPLETE"), "basis": research_assessment.get("basis", "The current public evidence layer has no qualifying retained record for this domain."), "assessment_id": research_assessment.get("assessment_id")}
        return {
            "status": "RESEARCH_QUEUE",
            "event_count": 0,
            "basis": "A structured transformer-event research target exists, but no public event has been retained yet."
        }
    if domain == "independent_corroboration":
        independent = [x for x in ev if x.get("independent_of_other_source") is True]
        if independent:
            return {
                "status": "INGESTED",
                "basis": "At least one attached evidence record is explicitly marked independent of another source."
            }
        if "independent_corroboration" in manual_fields:
            return {
                "status": "ASSESSED",
                "basis": "A retained public-web corroboration record documents materially independent public sources for this site."
            }
        if research_assessment:
            return {"status": research_assessment.get("status", "RESEARCHED_NO_PUBLIC_RECORD"), "basis": research_assessment.get("basis", "A dated targeted public-source assessment produced no qualifying public record for this domain."), "assessment_id": research_assessment.get("assessment_id")}
        return {
            "status": "NOT_ASSESSED",
            "basis": "Independent corroboration has not yet been assessed as a separate evidence relationship in the public Track 3 layer."
        }
    if domain in {"chip_ownership", "chip_users", "chip_shipments"}:
        if external_snapshot_available(domain):
            return {
                "status": "INGESTED_SNAPSHOT",
                "basis": "The corresponding Epoch global compute-accounting source is preserved as a raw snapshot; it is not attributed to this site unless a separate site-level linkage exists."
            }
        return {
            "status": "SOURCE_AVAILABLE_NOT_INGESTED",
            "basis": "The relevant Epoch global compute-accounting source is cataloged, but its raw snapshot is not present in this build."
        }
    raise KeyError(domain)

def evidence_domain(ev: dict[str, Any]) -> str:
    t = str(ev.get("type") or "")
    if t in {"site_specific_energy_contract","site_specific_service_contract","site_specific_service","site_specific_utility_planning"}:
        return "service_or_contract"
    if t in {"site_specific_compute_tenancy","site_specific_compute_contract","site_specific_lease"}:
        return "compute_tenancy"
    if t in {"site_specific_facility_record", "site_specific_project_record"}:
        return "site_identity"
    if t == "site_specific_regulatory" or "regulatory" in t:
        return "regulatory"
    if t in {"site_specific_utility_relationship", "site_specific_utility", "site_specific_power_request", "site_specific_load_request", "site_specific_queue", "site_specific_utility_capacity_record", "site_specific_grid_facility_record", "site_specific_utility_power", "site_specific_facility_utility_relationship", "site_specific_utility_facility_record", "site_specific_utility_service", "site_specific_facility_utility_evidence"}:
        return "grid_connection"
    return "grid_connection"

def build_evidence_index(evidence: dict[str, Any], registry: dict[str, Any], power_observations: list[dict[str, Any]] | None = None, cooling_observations: list[dict[str, Any]] | None = None, remote_observations: list[dict[str, Any]] | None = None, transformer_events: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    rows = []
    registry_by_id = {x["epoch_id"]: x for x in registry["records"]}
    for rec in evidence["records"]:
        for idx, ev in enumerate(rec.get("site_level_evidence") or [], start=1):
            raw = {
                "epoch_id": rec["epoch_id"],
                "epoch_name": rec.get("epoch_name"),
                "evidence_index": idx,
                "evidence": ev,
            }
            eid = "EVID-" + hashlib.sha256(
                json.dumps(raw, sort_keys=True, ensure_ascii=False).encode("utf-8")
            ).hexdigest()[:20]
            item = {
                "evidence_id": eid,
                "target_type": "epoch_site",
                "target_id": rec["epoch_id"],
                "target_name": rec.get("epoch_name"),
                "domain": evidence_domain(ev),
                "evidence_type": ev.get("type"),
                "claim_scope": "site_level",
                "status": "VERIFIED_SITE_SPECIFIC" if ev.get("type") == "site_specific_queue" else "SITE_LEVEL_EVIDENCE",
                "source_kind": ev.get("source_kind"),
                "source_name": ev.get("authority"),
                "source_url": ev.get("source_url"),
                "observed_on": None,
                "captured_on": evidence.get("generated_on"),
                "confidence": ev.get("confidence"),
                "basis": ev.get("basis"),
                "record_id": ev.get("record_id"),
                "authority": ev.get("authority"),
                "capacity_mw": ev.get("capacity_mw"),
                "site_specific": bool(ev.get("type") == "site_specific_queue"),
                "independent_of_other_source": None,
                "review_state": "PUBLISHED_RECORD",
            }
            rows.append(item)

    # Preserve the public grid/facility evidence embedded in the queue
    # crosswalk as its own provenance layer. These values are source-specific
    # and are never silently promoted to a queue ID or measured load.
    for rec in registry["records"]:
        grid = rec.get("grid_crosswalk") or {}
        ev = grid.get("site_level_public_evidence")
        if not ev:
            continue
        raw = {
            "epoch_id": rec["epoch_id"],
            "source": ev.get("source"),
            "url": ev.get("url"),
            "status": ev.get("status"),
        }
        eid = "EVID-XW-" + rec["epoch_id"]
        status = str(ev.get("status") or "").lower()
        domain = "grid_connection" if any(
            token in status for token in ("grid_record", "utility_record", "service_record", "regulatory_record", "power_request", "load_request")
        ) else "site_identity"
        rows.append({
            "evidence_id": eid,
            "target_type": "epoch_site",
            "target_id": rec["epoch_id"],
            "target_name": rec.get("normalized", {}).get("name"),
            "domain": domain,
            "evidence_type": ev.get("status"),
            "claim_scope": "site_level",
            "status": "SITE_LEVEL_EVIDENCE",
            "source_kind": "queue crosswalk public evidence",
            "source_name": ev.get("source") or ev.get("authority"),
            "source_url": ev.get("url"),
            "observed_on": None,
            "captured_on": grid.get("source_date") or evidence.get("generated_on"),
            "confidence": None,
            "basis": ev.get("basis"),
            "record_id": ev.get("record_id"),
            "authority": ev.get("grid_operator") or ev.get("authority"),
            "capacity_mw": None,
            "site_specific": False,
            "independent_of_other_source": None,
            "review_state": "PUBLISHED_CROSSWALK_EVIDENCE",
        })
    for obs in power_observations or []:
        rows.append({
            "evidence_id": "EVID-POWER-" + str(obs["observation_id"]),
            "target_type": "epoch_site",
            "target_id": obs["epoch_id"],
            "target_name": obs["site_name"],
            "domain": "power_telemetry",
            "evidence_type": obs.get("measurement_type"),
            "claim_scope": "site_level",
            "status": obs.get("status", "INGESTED_SNAPSHOT"),
            "source_kind": (obs.get("source") or {}).get("source_kind") or "company sustainability report",
            "source_name": (obs.get("source") or {}).get("source_name") or "Meta",
            "source_url": (obs.get("source") or {}).get("source_url"),
            "observed_on": obs.get("observed_period"),
            "captured_on": obs.get("source", {}).get("captured_on"),
            "confidence": obs.get("confidence"),
            "basis": obs.get("basis"),
            "record_id": None,
            "authority": (obs.get("source") or {}).get("publisher"),
            "raw_value": obs.get("raw_value"),
            "normalized_value": obs.get("normalized_value"),
            "units": obs.get("units"),
            "site_specific": bool(obs.get("site_specific")),
            "independent_of_other_source": False,
            "review_state": "PUBLISHED_RECORD",
        })
    for obs in remote_observations or []:
        rows.append({
            "evidence_id": "EVID-REMOTE-" + hashlib.sha256(
                json.dumps(obs, sort_keys=True, ensure_ascii=False).encode("utf-8")
            ).hexdigest()[:20],
            "target_type": "epoch_site",
            "target_id": obs.get("epoch_id"),
            "target_name": obs.get("site_name"),
            "domain": "remote_sensing",
            "evidence_type": obs.get("modality"),
            "claim_scope": "site_level",
            "status": obs.get("status", "INGESTED_DERIVED"),
            "source_kind": "public satellite STAC + raw COG processing",
            "source_name": obs.get("sensor"),
            "source_url": obs.get("stac_item_url") or obs.get("source_catalog"),
            "observed_on": obs.get("observed_on"),
            "captured_on": obs.get("observed_on"),
            "confidence": "derived_measurement",
            "basis": "Compact metrics computed from a raw COG window around the geocoded public site address.",
            "record_id": obs.get("scene_id"),
            "authority": obs.get("source_collection"),
            "raw_value": None,
            "normalized_value": obs.get("metrics"),
            "units": None,
            "site_specific": True,
            "independent_of_other_source": True,
            "review_state": "AUTOMATED_PUBLIC_SOURCE_PROCESSING",
        })
    for event in transformer_events or []:
        rows.append({
            "evidence_id": event.get("evidence_id") or "EVID-TX-" + hashlib.sha256(
                json.dumps(event, sort_keys=True, ensure_ascii=False).encode("utf-8")
            ).hexdigest()[:20],
            "target_type": "epoch_site",
            "target_id": event.get("epoch_id"),
            "target_name": event.get("site_name"),
            "domain": "transformer_supply_chain",
            "evidence_type": event.get("event_type"),
            "claim_scope": "site_level",
            "status": event.get("status", "INGESTED"),
            "source_kind": event.get("source_kind") or event.get("source_tier"),
            "source_name": event.get("source_name") or event.get("source_publisher") or event.get("source_party"),
            "source_url": event.get("source_url"),
            "observed_on": event.get("observed_on"),
            "captured_on": event.get("captured_on") or TRANSFORMER_EVENTS.exists() and load_json(TRANSFORMER_EVENTS).get("generated_on"),
            "confidence": event.get("confidence"),
            "basis": event.get("basis") or event.get("linkage_basis") or event.get("evidence_quote") or event.get("semantics"),
            "record_id": event.get("record_id"),
            "authority": event.get("authority"),
            "raw_value": event.get("raw_value"),
            "normalized_value": event.get("rating_mva"),
            "units": "MVA",
            "site_specific": True,
            "independent_of_other_source": event.get("independent_of_other_source"),
            "event_type": event.get("event_type"),
            "rating_mva": event.get("rating_mva"),
            "primary_kv": event.get("primary_kv"),
            "secondary_kv": event.get("secondary_kv"),
            "buyer": event.get("buyer"),
            "destination": event.get("destination"),
            "seller": event.get("seller"),
            "manufacturer": event.get("manufacturer"),
            "model": event.get("model"),
            "review_state": "PUBLISHED_RECORD",
        })
    for obs in cooling_observations or []:
        rows.append({
            "evidence_id": "EVID-COOLING-" + str(obs["observation_id"]),
            "target_type": "epoch_site",
            "target_id": obs["epoch_id"],
            "target_name": obs["site_name"],
            "domain": "cooling",
            "evidence_type": obs.get("measurement_type"),
            "claim_scope": "site_level",
            "status": obs.get("status", "INGESTED_SNAPSHOT"),
            "source_kind": "secondary facility research dataset",
            "source_name": (obs.get("source") or {}).get("source_name") or "Epoch AI",
            "source_url": (obs.get("source") or {}).get("source_url"),
            "observed_on": obs.get("observed_on"),
            "captured_on": (obs.get("source") or {}).get("captured_on"),
            "confidence": obs.get("confidence"),
            "basis": obs.get("basis"),
            "record_id": None,
            "authority": (obs.get("source") or {}).get("publisher"),
            "raw_value": obs.get("capacity"),
            "normalized_value": obs.get("capacity"),
            "units": obs.get("capacity_units"),
            "equipment_type": obs.get("equipment_type"),
            "manufacturer": obs.get("manufacturer"),
            "model": obs.get("model"),
            "site_specific": bool(obs.get("site_assignment")),
            "independent_of_other_source": False,
            "review_state": "PUBLISHED_RECORD",
        })
    return rows

def build_observation_queue(site_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    task_definitions = {
        "power_telemetry": ("P0", "Acquire interval electricity-demand evidence from the serving utility, ISO/RTO telemetry publication, public filing, or meter-derived source. An annual company-reported snapshot does not close this task.", ["observed_on", "measurement_interval", "demand_mw", "metering_authority", "source_url", "quality_flag"]),
        "remote_sensing": ("P0", "Acquire multi-temporal TIR, SAR, and/or high-resolution optical observations and derive site-specific physical activity or thermal measurements.", ["observed_on", "sensor", "scene_id", "latitude", "longitude", "baseline_value", "observed_value", "delta", "quality_flag", "source_url"]),
        "cooling": ("P1", "Acquire site-level cooling-equipment records and link equipment capacity/type to the physical campus.", ["observed_on", "equipment_type", "manufacturer", "model", "capacity", "units", "site_assignment", "source_url"]),
        "transformer_supply_chain": ("P0", "Acquire HV-transformer procurement, delivery, installation, and site-assignment evidence.", ["observed_on", "event_type", "manufacturer", "model", "rating_mva", "primary_kv", "secondary_kv", "buyer", "destination", "source_url"]),
        "chip_ownership": ("P1", "Acquire global ownership snapshots and preserve them as aggregate evidence until a separate site linkage is defensible.", ["observed_on", "owner", "chip_type", "quantity", "source_url", "source_kind"]),
        "chip_users": ("P1", "Acquire compute-use estimates and preserve them as organization-level evidence unless a site link is separately established.", ["observed_on", "organization", "chip_type", "quantity_or_compute", "source_url", "source_kind"]),
        "chip_shipments": ("P1", "Acquire accelerator sales/shipment records and test organization-to-site assignment only when independently supportable.", ["observed_on", "buyer", "seller", "chip_type", "quantity", "destination", "source_url", "source_kind"]),
    }
    tasks = []
    gap_by_id = {str(row.get("epoch_id")): row for row in list(csv.DictReader(GAP.open("r", encoding="utf-8-sig", newline="")))}
    for site in site_records:
        gap = gap_by_id.get(str(site["epoch_id"]), {})
        for domain, (priority, action, required_fields) in task_definitions.items():
            state = (site.get("domains") or {}).get(domain, {}).get("status", "UNKNOWN")
            if state in {"NOT_INGESTED", "SOURCE_AVAILABLE_NOT_INGESTED", "UNKNOWN", "PENDING_RESEARCH"} or (domain in {"power_telemetry", "cooling"} and state == "INGESTED_SNAPSHOT"):
                tasks.append({
                    "task_id": f"{site['epoch_id']}::{domain}",
                    "epoch_id": site["epoch_id"],
                    "site_name": site.get("site_name"),
                    "country": site.get("country"),
                    "state_province": site.get("state_province"),
                    "domain": domain,
                    "current_state": state,
                    "priority": priority,
                    "action": action,
                    "required_fields": required_fields,
                    "next_action_from_site": site.get("next_action"),
                    "grid_primary_source_url": gap.get("primary_source_url") or None,
                    "grid_source_type": gap.get("source_type") or None,
                    "grid_source_date": gap.get("source_date") or None,
                    "next_research_sources": gap.get("next_research_sources") or None,
                    "supporting_snapshot_note": "Annual site-level electricity snapshot exists; interval telemetry acquisition remains open." if domain == "power_telemetry" and state == "INGESTED_SNAPSHOT" else ("A site-level cooling-equipment snapshot exists; broader equipment coverage remains open." if domain == "cooling" and state == "INGESTED_SNAPSHOT" else None),
                })
    return tasks

def refresh_website_completeness_audit(summary: dict[str, Any], evidence_count: int) -> None:
    """Keep the public audit synchronized with generated Track 3 artifacts."""
    path = ROOT / "data" / "website_completeness_audit.json"
    if not path.exists():
        return
    audit = load_json(path)
    large_scope_path = ROOT / "data" / "large_load_scope.json"
    if large_scope_path.exists():
        scope = load_json(large_scope_path)
        definitions = scope.get("definitions") or {}
        core = (
            scope.get("current_core_scope")
            or scope.get("current_core_registry")
            or definitions.get("current_row_level", {})
        )
        broad = scope.get("expanded_known_scope") or definitions.get("expanded_known_scope", {})
        audit.setdefault("summary", {}).update({
            "current_core_registry_rows": core.get("records"),
            "current_core_capacity_gw": core.get("capacity_gw"),
            "broader_known_scope_rows": broad.get("records"),
            "broader_known_scope_capacity_gw": broad.get("capacity_gw"),
            "project_records": (scope.get("definitions", {}).get("project_level_extractions", {}) or {}).get("records"),
            "current_epoch_sites": summary.get("epoch_site_count"),
        })
    s = audit.setdefault("summary", {})
    s["current_epoch_sites"] = summary.get("epoch_site_count")
    s["track3_evidence_records"] = evidence_count
    s["remote_sensing_processed"] = summary.get("remote_sensing_derived_observation_count", 0)
    s["transformer_events"] = summary.get("transformer_event_count", 0)
    s["public_web_enrichment_records"] = summary.get("public_web_evidence_record_count", 0)
    s["public_web_enrichment_sites"] = summary.get("public_web_evidence_site_count", 0)
    s["researched_no_public_record"] = summary.get("research_completed_no_public_record_count", 0)
    physical_path = ROOT / "data" / "physical_verification_layer.json"
    if physical_path.exists():
        physical = load_json(physical_path)
        ps = physical.get("summary", {})
        for key in ("optical_sites", "tir_sites", "sar_sites", "raw_optical_scenes_ingested",
                    "raw_tir_numeric_observations", "raw_sar_numeric_observations",
                    "building_footprint_polygon_site_count", "building_footprint_polygon_count",
                    "substation_evidence_count", "transmission_evidence_count"):
            if key in ps:
                s["physical_" + key] = ps[key]
    p = next((x for x in audit.get("sections", []) if x.get("section") == "Physical verification layer"), None)
    if p is not None:
        p["status"] = "POPULATED"
        p["artifact"] = "data/physical_verification_layer.json + data/track3/remote_sensing_observations.json + data/track3/building_footprints_index.json"
        p["detail"] = (
            f"{summary.get('epoch_site_count')} Epoch sites targeted; "
            f"{summary.get('remote_sensing_derived_observation_count', 0)} retained derived remote-sensing observations; "
            f"{summary.get('transformer_event_count', 0)} transformer events; "
            "unresolved geocoding and unavailable public records remain explicit."
        )
    audit["generated_on"] = datetime.now(timezone.utc).date().isoformat()
    path.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    reg = load_json(REGISTRY)
    evidence = load_json(EVIDENCE)
    source_stack = load_json(SOURCE_STACK)
    power_payload = load_json(POWER_OBSERVATIONS) if POWER_OBSERVATIONS.exists() else {"records": []}
    power_observations = power_payload.get("records", [])
    cooling_payload = load_json(COOLING_OBSERVATIONS) if COOLING_OBSERVATIONS.exists() else {"records": []}
    cooling_observations = cooling_payload.get("records", [])
    remote_payload = load_json(REMOTE_OBSERVATIONS) if REMOTE_OBSERVATIONS.exists() else {"records": []}
    remote_observations = remote_payload.get("records", [])
    transformer_payload = load_json(TRANSFORMER_EVENTS) if TRANSFORMER_EVENTS.exists() else {"records": []}
    transformer_events = transformer_payload.get("records", [])
    public_web_payload = load_json(PUBLIC_WEB_ENRICHMENT) if PUBLIC_WEB_ENRICHMENT.exists() else {"records": []}
    public_web_records = public_web_payload.get("records", [])
    research_assessment_payload = load_json(RESEARCH_ASSESSMENTS) if RESEARCH_ASSESSMENTS.exists() else {"records": []}
    research_assessment_records = research_assessment_payload.get("records", [])
    power_by_site: dict[str, list[dict[str, Any]]] = {}
    remote_by_site: dict[str, list[dict[str, Any]]] = {}
    transformer_by_site: dict[str, list[dict[str, Any]]] = {}
    cooling_by_site: dict[str, list[dict[str, Any]]] = {}
    manual_public_by_site: dict[str, list[dict[str, Any]]] = {}
    research_assessments_by_site: dict[str, dict[str, dict[str, Any]]] = {}
    for item in public_web_records:
        sid = str(item.get("epoch_id") or "")
        if sid:
            manual_public_by_site.setdefault(sid, []).append(item)
    for item in research_assessment_records:
        sid = str(item.get("epoch_id") or "")
        domain_name = str(item.get("domain") or "")
        if sid and domain_name:
            research_assessments_by_site.setdefault(sid, {})[domain_name] = item
    for obs in power_observations:
        power_by_site.setdefault(str(obs.get("epoch_id")), []).append(obs)
    for obs in cooling_observations:
        cooling_by_site.setdefault(str(obs.get("epoch_id")), []).append(obs)
    for obs in remote_observations:
        remote_by_site.setdefault(str(obs.get("epoch_id")), []).append(obs)
    for event in transformer_events:
        transformer_by_site.setdefault(str(event.get("epoch_id")), []).append(event)
    gaps = list(csv.DictReader(GAP.open("r", encoding="utf-8-sig", newline="")))
    crosswalk_path = EPOCH / "queue_crosswalk.json"
    crosswalk_payload = load_json(crosswalk_path) if crosswalk_path.exists() else {"records": []}
    crosswalk_by_id = {str(x.get("epoch_id")): x for x in crosswalk_payload.get("records", [])}

    epoch_ids = {str(x["epoch_id"]) for x in reg["records"]}
    evidence_ids = {str(x["epoch_id"]) for x in evidence["records"]}
    if len(epoch_ids) != 93 or epoch_ids != evidence_ids:
        raise SystemExit("Epoch registry and evidence layer must match 1:1 across 93 sites.")
    if len(gaps) != 93:
        raise SystemExit(f"Expected 93 gap-analysis rows, got {len(gaps)}.")

    evidence_by_id = {x["epoch_id"]: x for x in evidence["records"]}
    site_records = []
    status_counts: dict[str, dict[str, int]] = {d: {} for d in SITE_DOMAINS}

    for rec in reg["records"]:
        ev = evidence_by_id[rec["epoch_id"]]
        domains = {}
        for domain in SITE_DOMAINS:
            s = site_status(
                {
                    **rec,
                    "site_level_connection_evidence": ev.get("site_level_evidence") or [],
                    "grid_crosswalk": crosswalk_by_id.get(str(rec["epoch_id"])) or rec.get("grid_crosswalk") or {},
                },
                domain,
                power_by_site,
                cooling_by_site,
                remote_by_site,
                transformer_by_site,
                manual_public_by_site,
                research_assessments_by_site,
            )
            domains[domain] = s
            status_counts[domain][s["status"]] = status_counts[domain].get(s["status"], 0) + 1

        base_evidence_count = len(ev.get("site_level_evidence") or [])
        manual_public_evidence_count = len(manual_public_by_site.get(str(rec["epoch_id"]), []))
        crosswalk = crosswalk_by_id.get(str(rec["epoch_id"])) or rec.get("grid_crosswalk") or {}
        crosswalk_evidence_count = 1 if crosswalk.get("site_level_public_evidence") else 0
        site_records.append({
            "epoch_id": rec["epoch_id"],
            "site_name": rec.get("normalized", {}).get("name"),
            "country": rec.get("normalized", {}).get("country"),
            "state_province": crosswalk.get("state_province")
            or rec.get("normalized", {}).get("region_inferred_from_address"),
            "state_province_source": "grid_crosswalk" if crosswalk.get("state_province") else "epoch_address_inference",
            "epoch_region_inferred_from_address": rec.get("normalized", {}).get("region_inferred_from_address"),
            "current_it_power_mw": rec.get("normalized", {}).get("current_power_mw"),
            "current_h100_equivalents": rec.get("normalized", {}).get("current_h100_equivalents"),
            "domains": domains,
            "site_level_evidence_count": base_evidence_count,
            "public_web_evidence_count": manual_public_evidence_count,
            "crosswalk_public_evidence_count": crosswalk_evidence_count,
            "combined_site_level_evidence_count": base_evidence_count + manual_public_evidence_count + crosswalk_evidence_count,
            "next_action": ev.get("next_action"),
        })

    evidence_index = build_evidence_index(
        evidence, reg, power_observations, cooling_observations, remote_observations, transformer_events
    )
    existing_evidence_ids = {str(x.get("evidence_id")) for x in evidence_index if x.get("evidence_id")}
    manual_domain_map = {
        "project": "site_identity",
        "address": "site_identity",
        "owner": "site_identity",
        "users": "site_identity",
        "construction_companies": "construction",
        "energy_companies": "grid_connection",
        "service_or_contract": "service_or_contract",
        "regulatory": "regulatory",
        "cooling": "cooling",
        "chip_quantities": "chip_inventory",
        "investment": "site_identity",
        "investors": "site_identity",
        "capacity_record": "site_identity",
        "operational_status": "site_identity",
    }
    for item in public_web_records:
        sid = str(item.get("epoch_id") or "")
        if sid not in epoch_ids:
            continue
        eid = str(item.get("evidence_id") or ("EVID-PWEB-" + hashlib.sha256(
            json.dumps(item, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()[:20]))
        if eid in existing_evidence_ids:
            continue
        evidence_index.append({
            "evidence_id": eid,
            "target_type": "epoch_site",
            "target_id": sid,
            "target_name": item.get("site_name"),
            "domain": manual_domain_map.get(str(item.get("field")), "site_identity"),
            "evidence_type": "public_web_enrichment",
            "claim_scope": "site_level",
            "status": "SITE_LEVEL_EVIDENCE",
            "source_kind": "public web enrichment",
            "source_name": item.get("source"),
            "source_url": (item.get("source_urls") or [None])[0],
            "source_urls": item.get("source_urls") or [],
            "observed_on": item.get("publication_date"),
            "captured_on": item.get("capture_date"),
            "confidence": "public_source_capture",
            "basis": item.get("scope_note") or "Site-specific public-source fact retained in additive enrichment ledger.",
            "record_id": item.get("field"),
            "authority": item.get("source"),
            "raw_value": item.get("value"),
            "normalized_value": item.get("value"),
            "site_specific": True,
            "independent_of_other_source": None,
            "review_state": "MANUAL_PUBLIC_WEB_CAPTURE",
            "public_field": item.get("field"),
            "relationship": item.get("relationship"),
        })

    pending = [x for x in site_records if x["domains"]["grid_connection"]["status"] == "PENDING_RESEARCH"]
    researched_no_public_record = [x for x in site_records if x["domains"]["grid_connection"]["status"] == "RESEARCHED_NO_PUBLIC_RECORD"]
    observation_queue = build_observation_queue(site_records)
    summary = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "epoch_site_count": len(site_records),
        "observation_task_count": len(observation_queue),
        "observation_task_counts_by_domain": {
            domain: sum(1 for task in observation_queue if task["domain"] == domain)
            for domain in sorted({task["domain"] for task in observation_queue})
        },
        "observation_task_counts_by_priority": {
            priority: sum(1 for task in observation_queue if task["priority"] == priority)
            for priority in sorted({task["priority"] for task in observation_queue})
        },
        "site_level_evidence_site_count": sum(1 for x in site_records if x["site_level_evidence_count"] > 0),
        "track3_evidence_record_count": len(evidence_index),
        "public_web_evidence_record_count": len(public_web_records),
        "public_web_evidence_site_count": len(manual_public_by_site),
        "combined_site_level_evidence_site_count": sum(
            1 for x in site_records
            if x["combined_site_level_evidence_count"] > 0
        ),
        "site_specific_queue_id_count": sum(1 for x in site_records if x["domains"]["grid_connection"]["status"] == "VERIFIED_SITE_SPECIFIC"),
        "pending_grid_connection_research_count": len(pending),
        "research_completed_no_public_record_count": len(researched_no_public_record),
        "domain_status_counts": status_counts,
        "source_stack_count": len(source_stack.get("sources", [])),
        "remote_sensing_derived_observation_count": sum(
            1 for x in remote_observations if x.get("status") == "INGESTED_DERIVED"
        ),
        "transformer_event_count": len(transformer_events),
        "source_stack_status_counts": {
            status: sum(1 for source in source_stack.get("sources", []) if source.get("status") == status)
            for status in sorted({source.get("status") for source in source_stack.get("sources", []) if source.get("status")})
        },
        "semantics": "PENDING and NOT_INGESTED are explicit states and are never interpreted as evidence of absence. RESEARCHED_NO_PUBLIC_RECORD means a site-specific search was performed and no public queue/service record was retained; it is not evidence that service is absent.",
    }

    (OUT / "site_status.json").write_text(json.dumps({
        "schema_version": 1,
        "summary": summary,
        "records": site_records,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    (OUT / "evidence_records.json").write_text(json.dumps({
        "schema_version": 1,
        "record_count": len(evidence_index),
        "records": evidence_index,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    (OUT / "research_queue.json").write_text(json.dumps({
        "schema_version": 1,
        "count": len(pending),
        "records": pending,
        "semantics": "A pending record means the registry has not attached site-specific grid/service evidence yet; it does not mean the site lacks a connection.",
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "research_complete_no_public_record.json").write_text(json.dumps({
        "schema_version": 1,
        "count": len(researched_no_public_record),
        "records": researched_no_public_record,
        "semantics": "These sites had a documented site-specific search and no public queue/service record was retained. This is not evidence of absence of grid service.",
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    task_counts_by_domain = {
        domain: sum(1 for task in observation_queue if task["domain"] == domain)
        for domain in sorted({task["domain"] for task in observation_queue})
    }
    task_counts_by_priority = {
        priority: sum(1 for task in observation_queue if task["priority"] == priority)
        for priority in sorted({task["priority"] for task in observation_queue})
    }
    (OUT / "observation_queue.json").write_text(json.dumps({
        "schema_version": 1,
        "generated_at_utc": summary["generated_at_utc"],
        "task_count": len(observation_queue),
        "task_counts_by_domain": task_counts_by_domain,
        "task_counts_by_priority": task_counts_by_priority,
        "tasks": observation_queue,
        "semantics": "Observation tasks describe missing acquisition work. They do not assert that the underlying physical condition is absent.",
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (OUT / "observation_queue.csv").open("w", encoding="utf-8", newline="") as f:
        base_headers = ["task_id", "epoch_id", "site_name", "country", "state_province", "domain", "current_state", "priority", "action", "required_fields", "next_action_from_site"]
        extra_headers = sorted({key for task in observation_queue for key in task} - set(base_headers))
        headers = base_headers + extra_headers
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for task in observation_queue:
            row = {key: task.get(key) for key in headers}
            row["required_fields"] = "; ".join(task["required_fields"])
            writer.writerow(row)


    external_audit = []
    for domain, filenames in EXTERNAL_SOURCE_FILES.items():
        for filename in filenames:
            path = EPOCH / filename
            row_count = 0
            columns = []
            if path.exists() and path.stat().st_size > 0:
                try:
                    with path.open("r", encoding="utf-8-sig", newline="") as f:
                        reader = csv.reader(f)
                        columns = next(reader, [])
                        row_count = sum(1 for _ in reader)
                except Exception:
                    row_count = -1
            external_audit.append({
                "domain": domain,
                "file": filename,
                "status": "INGESTED_SNAPSHOT" if row_count >= 0 and path.exists() and path.stat().st_size > 0 else "SOURCE_AVAILABLE_NOT_INGESTED",
                "row_count": row_count,
                "columns": columns,
            })
    (OUT / "external_source_snapshots.json").write_text(json.dumps({
        "schema_version": 1,
        "generated_at_utc": summary["generated_at_utc"],
        "records": external_audit,
        "semantics": "These are source snapshots, not site-attributed compute records."
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    (OUT / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    refresh_website_completeness_audit(summary, len(evidence_index))

    print(json.dumps(summary, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

# Canonical rebuild trigger: publish crosswalk-joined Track 3 statuses after completeness pass.
