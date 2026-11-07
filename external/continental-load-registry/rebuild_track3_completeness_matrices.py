#!/usr/bin/env python3
"""Rebuild current Track 3 domain/publisher completeness matrices from canonical ledgers."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE_STATUS = ROOT / "data/track3/site_status.json"
SWEEP = ROOT / "data/track3/site_missing_information_sweep_2026-09-27.json"
ENRICH = ROOT / "data/track3/public_web_enrichment_2026-09-27.json"

DOMAINS = [
    "site_identity","construction","chip_inventory","grid_connection",
    "service_or_contract","regulatory","compute_tenancy","power_telemetry",
    "remote_sensing","cooling","transformer_supply_chain","chip_ownership",
    "chip_users","chip_shipments","independent_corroboration",
]
FIELDS = ["owner","users","project","address","investors","construction_companies","energy_companies","chip_quantities"]
OPEN_STATES = {"NOT_INGESTED","NOT_ASSESSED","UNKNOWN","RESEARCH_QUEUE","PENDING_RESEARCH"}

def write_json(path: Path, obj: dict) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def csv_escape(v: object) -> str:
    s = "" if v is None else str(v)
    return '"' + s.replace('"','""') + '"' if any(ch in s for ch in ',\r\n"') else s

def main() -> int:
    now = datetime.now(timezone.utc).isoformat()
    sites = json.loads(SITE_STATUS.read_text(encoding="utf-8"))
    sweep = json.loads(SWEEP.read_text(encoding="utf-8"))
    enrich = json.loads(ENRICH.read_text(encoding="utf-8"))
    site_rows = sites["records"]
    sweep_by_id = {str(x["epoch_id"]): x for x in sweep["records"]}
    fresh_by_id_field: dict[tuple[str,str], list[dict]] = {}
    for x in enrich.get("records", []):
        sid, field = str(x.get("epoch_id") or ""), str(x.get("field") or "")
        if sid and field:
            fresh_by_id_field.setdefault((sid, field), []).append(x)

    domain_rows = []
    domain_status_counts: dict[str,int] = {}
    for site in site_rows:
        sid = str(site["epoch_id"])
        for domain in DOMAINS:
            d = site.get("domains", {}).get(domain, {})
            status = str(d.get("status", "UNKNOWN"))
            row = {
                "epoch_id": sid, "site_name": site["site_name"], "country": site.get("country"),
                "state_province": site.get("state_province"), "domain": domain,
                "status": status, "basis": d.get("basis"),
                "observation_count": d.get("observation_count"),
                "research_task_id": None if status not in OPEN_STATES else f"DOM-{sid}-{domain}",
                "assessment_id": d.get("assessment_id"),
            }
            domain_rows.append(row)
            domain_status_counts[status] = domain_status_counts.get(status,0) + 1

    domain_obj = {
        "schema_version": 2,
        "generated_at_utc": now,
        "title": "93-site Track 3 domain completeness matrix",
        "scope": "15 Track 3 domains × 93 canonical Epoch AI sites",
        "accounting": {
            "cells": len(domain_rows),
            "sites": len(site_rows),
            "domains": len(DOMAINS),
            "status_counts": domain_status_counts,
            "terminal_cells": len(domain_rows) - sum(1 for r in domain_rows if r["status"] in OPEN_STATES),
            "open_or_unassessed_cells": sum(1 for r in domain_rows if r["status"] in OPEN_STATES),
            "assessment_complete_cells": sum(1 for r in domain_rows if r["status"] == "ASSESSMENT_COMPLETE"),
        },
        "records": domain_rows,
    }
    write_json(ROOT/"data/track3/domain_completeness_matrix_2026-09-27.json", domain_obj)

    publisher_rows=[]
    publisher_status_counts: dict[str,int] = {}
    field_status_counts: dict[str,dict[str,int]] = {f:{} for f in FIELDS}
    for site in site_rows:
        sid = str(site["epoch_id"])
        sw = sweep_by_id[sid]
        open_fields = set(sw.get("effective_unresolved_publisher_fields") or [])
        known = (sw.get("known_publisher_fields") or {})
        for field in FIELDS:
            fresh = fresh_by_id_field.get((sid, field), [])
            fresh_values = []
            fresh_sources = []
            for x in fresh:
                v = x.get("value")
                if isinstance(v, list):
                    fresh_values.extend(v)
                elif v not in (None,""):
                    fresh_values.append(v)
                fresh_sources.extend(x.get("source_urls") or [])
            fresh_values = list(dict.fromkeys(fresh_values))
            fresh_sources = list(dict.fromkeys(fresh_sources))
            if field in open_fields:
                status = "NOT_PUBLISHED_OR_NOT_RETAINED"
                task_id = f"PUB-{sid}-{field}"
                meaning = "No defensible value currently retained; corresponding research task is open."
            elif fresh:
                status = "FRESH_PUBLIC_WEB_CAPTURED"
                task_id = None
                meaning = "A source-backed public-web value is retained and no open publisher task remains."
            elif known.get(field) not in (None, "", [], {}):
                status = "CANONICAL_EPOCH_CAPTURED"
                task_id = None
                meaning = "A canonical Epoch/public-source value is retained and no open publisher task remains."
            else:
                status = "PUBLIC_ENRICHMENT_BRIDGE_CAPTURED"
                task_id = None
                meaning = "The field is not in the current effective-unresolved set; no fresh record was added in this matrix refresh."
            row = {
                "epoch_id": sid, "site_name": site["site_name"], "country": site.get("country"),
                "state_province": site.get("state_province"), "field": field, "status": status,
                "canonical_value": known.get(field), "existing_public_bridge_value": known.get(field),
                "fresh_public_values": fresh_values, "fresh_public_sources": fresh_sources,
                "research_task_id": task_id, "meaning": meaning,
            }
            publisher_rows.append(row)
            publisher_status_counts[status] = publisher_status_counts.get(status,0)+1
            field_status_counts[field][status] = field_status_counts[field].get(status,0)+1

    publisher_obj = {
        "schema_version": 2,
        "generated_at_utc": now,
        "title": "93-site publisher completeness matrix",
        "scope": "8 publisher-facing fields × 93 canonical Epoch AI sites",
        "accounting": {
            "cells": len(publisher_rows), "sites": len(site_rows), "fields_per_site": len(FIELDS),
            "status_counts": publisher_status_counts,
            "open_research_cells": sum(1 for r in publisher_rows if r["status"] == "NOT_PUBLISHED_OR_NOT_RETAINED"),
            "effective_unresolved_publisher_fields": sum(1 for r in publisher_rows if r["status"] == "NOT_PUBLISHED_OR_NOT_RETAINED"),
        },
        "records": publisher_rows,
    }
    write_json(ROOT/"data/track3/publisher_completeness_matrix_2026-09-27.json", publisher_obj)

    pf_records=[]
    pf_status_counts={}; pf_field_counts={f:{} for f in FIELDS}
    for site in site_rows:
        sid=str(site["epoch_id"]); sw=sweep_by_id[sid]
        open_fields=set(sw.get("effective_unresolved_publisher_fields") or [])
        field_matrix={}
        for f in FIELDS:
            fr=fresh_by_id_field.get((sid,f),[])
            if f in open_fields: st="NOT_CAPTURED"
            elif fr: st="FRESH_PUBLIC_WEB_CAPTURED"
            elif (sw.get("known_publisher_fields") or {}).get(f) not in (None,"",[],{}): st="CAPTURED"
            else: st="NO_NEW_CAPTURE"
            field_matrix[f]={"status":st,"epoch_value":(sw.get("known_publisher_fields") or {}).get(f),"bridge_value":(sw.get("known_publisher_fields") or {}).get(f),"fresh_public_values":[x.get("value") for x in fr]}
            pf_status_counts[st]=pf_status_counts.get(st,0)+1
            pf_field_counts[f][st]=pf_field_counts[f].get(st,0)+1
        pf_records.append({"epoch_id":sid,"site_name":site["site_name"],"country":site.get("country"),"state_province":site.get("state_province"),"epoch_it_power_mw":site.get("current_it_power_mw"),"field_matrix":field_matrix,"fresh_public_record_count":sum(len(fresh_by_id_field.get((sid,f),[])) for f in FIELDS),"fresh_public_sources":list(dict.fromkeys(u for f in FIELDS for x in fresh_by_id_field.get((sid,f),[]) for u in (x.get("source_urls") or [])))})
    pf_obj={"schema_version":2,"generated_at_utc":now,"title":"Track 3 publisher-field completeness matrix","purpose":"93-site × 8-field normalized view of current publisher evidence accounting.","scope":{"sites":len(site_rows),"fields":FIELDS},"accounting":{"site_count":len(site_rows),"cell_count":len(pf_records)*len(FIELDS),"status_counts":pf_status_counts,"field_status_counts":pf_field_counts},"records":pf_records}
    write_json(ROOT/"data/track3/publisher_field_completeness_2026-09-27.json",pf_obj)

    print(f"PASS: rebuilt matrices domain_cells={len(domain_rows)} domain_open={domain_obj['accounting']['open_or_unassessed_cells']} publisher_cells={len(publisher_rows)} publisher_open={publisher_obj['accounting']['open_research_cells']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
