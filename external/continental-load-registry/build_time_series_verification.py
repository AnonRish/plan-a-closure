#!/usr/bin/env python3
"""Build the Track 3 facility time-series verification layer.

Sources are kept separate:
- Epoch AI dated data-center timeline events (site-level, irregular dates)
- published site-level annual electricity-consumption snapshots
- CAISO historical queue series
- PJM Load Analysis Subcommittee public material history
- current registry status counts when available

The output never converts missing observations into zeros and keeps future/predicted
Epoch timeline rows separate from observed rows.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
TIMELINE_CSV = ROOT / "data/external/epoch_ai/data_center_timelines.csv"
REGISTRY_JSON = ROOT / "data/external/epoch_ai/registry.json"
POWER_JSON = ROOT / "data/track3/power_observations.json"
CAISO_JSON = ROOT / "data/caiso_cluster_history.json"
PJM_JSON = ROOT / "data/pjm_large_load_submission_history.json"
RAW_REGISTRY_CSV = ROOT / "data/registry_raw.csv"
OUT_JSON = ROOT / "data/track3/time_series_verification.json"
OUT_CSV = ROOT / "data/track3/time_series_verification.csv"
SOURCE_URL = "https://epoch.ai/data/data-centers-documentation/records"


def parse_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def parse_float(v: Any) -> float | None:
    if v is None or str(v).strip() == "":
        return None
    try:
        return float(str(v).replace(",", ""))
    except ValueError:
        return None


def iso_date(v: str) -> date | None:
    try:
        return datetime.strptime(v.strip(), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def current_registry_counts() -> dict[str, Any]:
    if not RAW_REGISTRY_CSV.exists():
        return {"status": "SOURCE_NOT_PRESENT"}
    rows = parse_csv(RAW_REGISTRY_CSV)
    status_counts: dict[str, int] = defaultdict(int)
    for r in rows:
        status = (r.get("status") or "").strip()
        if status:
            status_counts[status] += 1
    cancelled = sum(
        n for s, n in status_counts.items()
        if any(token in s.lower() for token in ("cancel", "withdraw", "retire"))
    )
    return {
        "status": "CURRENT_SNAPSHOT_ONLY",
        "row_count": len(rows),
        "status_counts": dict(sorted(status_counts.items())),
        "cancelled_withdrawn_retired_status_rows": cancelled,
        "semantics": "Current status strings are not a complete historical cancellation/retirement series.",
    }


def main() -> int:
    today = datetime.now(timezone.utc).date()
    registry = json.loads(REGISTRY_JSON.read_text(encoding="utf-8"))
    sites = registry["records"]
    site_by_name = {
        str(x.get("normalized", {}).get("name") or "").strip(): x
        for x in sites
        if x.get("normalized", {}).get("name")
    }

    timeline_rows = parse_csv(TIMELINE_CSV)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unmatched = 0

    for row in timeline_rows:
        name = (row.get("Data center") or "").strip()
        d = iso_date(row.get("Date") or "")
        if not name or d is None:
            continue
        event = {
            "date": d.isoformat(),
            "temporal_status": "FUTURE_OR_PREDICTED" if d > today else "OBSERVED_OR_REPORTED",
            "construction_status": row.get("Construction status") or None,
            "buildings_operational": parse_float(row.get("Buildings operational")),
            "it_power_mw": parse_float(row.get("IT power (MW)")),
            "total_power_mw": parse_float(row.get("Power (MW)")),
            "h100_equivalents": parse_float(row.get("H100 equivalents")),
            "performance_8bit_ops": parse_float(row.get("Performance (8-bit OP/s)")),
        }
        if name in site_by_name:
            grouped[name].append(event)
        else:
            unmatched += 1

    site_timelines: list[dict[str, Any]] = []
    event_change_rows: list[dict[str, Any]] = []
    quarterly: dict[str, dict[str, float]] = defaultdict(lambda: {
        "it_power_delta_mw": 0.0,
        "total_power_delta_mw": 0.0,
        "building_delta": 0.0,
        "site_change_event_count": 0.0,
    })

    for site in sites:
        name = str(site.get("normalized", {}).get("name") or "").strip()
        events = sorted(grouped.get(name, []), key=lambda x: x["date"])
        observed = [x for x in events if x["temporal_status"] == "OBSERVED_OR_REPORTED"]
        future = [x for x in events if x["temporal_status"] == "FUTURE_OR_PREDICTED"]
        previous: dict[str, Any] | None = None
        for ev in observed:
            changed = {
                "date": ev["date"],
                "delta_it_power_mw": None,
                "delta_total_power_mw": None,
                "delta_buildings_operational": None,
            }
            if previous is not None:
                for key, delta_key in (
                    ("it_power_mw", "delta_it_power_mw"),
                    ("total_power_mw", "delta_total_power_mw"),
                    ("buildings_operational", "delta_buildings_operational"),
                ):
                    a, b = previous.get(key), ev.get(key)
                    if a is not None and b is not None:
                        changed[delta_key] = b - a
                period = ev["date"][:7]
                q = f"{ev['date'][:4]}-Q{((int(ev['date'][5:7])-1)//3)+1}"
                quarterly[q]["it_power_delta_mw"] += changed["delta_it_power_mw"] or 0.0
                quarterly[q]["total_power_delta_mw"] += changed["delta_total_power_mw"] or 0.0
                quarterly[q]["building_delta"] += changed["delta_buildings_operational"] or 0.0
                quarterly[q]["site_change_event_count"] += 1.0
            ev["change_from_previous_observed_event"] = changed
            event_change_rows.append({
                "epoch_id": site["epoch_id"],
                "site_name": name,
                **ev,
            })
            previous = ev
        site_timelines.append({
            "epoch_id": site["epoch_id"],
            "site_name": name,
            "country": site.get("normalized", {}).get("country"),
            "state_province": site.get("normalized", {}).get("state_province"),
            "observed_event_count": len(observed),
            "future_or_predicted_event_count": len(future),
            "first_observed_date": observed[0]["date"] if observed else None,
            "last_observed_date": observed[-1]["date"] if observed else None,
            "observed_events": observed,
            "future_or_predicted_events": future,
            "source": {
                "publisher": "Epoch AI",
                "dataset": "AI data centers / data center timelines",
                "source_url": SOURCE_URL,
            },
        })

    power = json.loads(POWER_JSON.read_text(encoding="utf-8"))
    power_records = []
    for r in power.get("records", []):
        x = dict(r)
        if x.get("normalized_value") is not None and x.get("units") == "MWh":
            x["annual_average_equivalent_mw"] = round(float(x["normalized_value"]) / 8760.0, 3)
            x["annual_average_note"] = "Annual MWh divided by 8,760 hours; this is an annual-average equivalent, not peak demand and not a load factor."
        power_records.append(x)

    caiso = json.loads(CAISO_JSON.read_text(encoding="utf-8"))
    pjm = json.loads(PJM_JSON.read_text(encoding="utf-8"))
    registry_counts = current_registry_counts()

    observed_event_count = sum(x["observed_event_count"] for x in site_timelines)
    future_event_count = sum(x["future_or_predicted_event_count"] for x in site_timelines)

    checklist = [
        {
            "id": "HISTORICAL_QUEUE_SNAPSHOTS",
            "item": "Historical queue snapshots",
            "status": "INGESTED_PARTIAL",
            "coverage": f"CAISO historical series has {len(caiso.get('records', []))} dated cluster-series records; PJM public LAS history has {len(pjm.get('records', []))} dated material records. This is not a complete historical snapshot for every market.",
        },
        {
            "id": "MONTHLY_QUARTERLY_MW_CHANGES",
            "item": "Monthly/quarterly MW changes",
            "status": "DERIVED_IRREGULAR_EVENT_SERIES",
            "coverage": f"{len(event_change_rows)} observed Epoch timeline events are retained with event-to-event MW deltas; quarterly aggregation is available, but the source is irregular dated observations rather than a uniform monthly meter series.",
        },
        {
            "id": "QUEUE_TO_OPERATION_TIMELINE",
            "item": "Queue entry → study → approval → construction → energization → operation timeline",
            "status": "PARTIAL",
            "coverage": "Queue/connection records and construction/power timeline records exist as separate evidence streams, but no universal site-level stage chain is asserted where an exact public stage identifier is absent.",
        },
        {
            "id": "FACILITY_OPERATING_STATUS",
            "item": "Facility operating-status timeline",
            "status": "INGESTED_PARTIAL",
            "coverage": f"{sum(1 for x in site_timelines if x['observed_event_count'] > 0)} of {len(sites)} Epoch sites have observed dated timeline events that include buildings-operational and/or construction status fields.",
        },
        {
            "id": "CAPACITY_ADDITIONS",
            "item": "Capacity additions over time",
            "status": "DERIVED_PARTIAL",
            "coverage": "Event-to-event IT-power and total-power changes are derived only when both source rows publish the corresponding values.",
        },
        {
            "id": "RETIREMENT_CANCELLATION",
            "item": "Retirement/cancellation tracking",
            "status": "CURRENT_STATUS_PARTIAL",
            "coverage": "Current queue status fields can be counted, but the repository does not yet have a complete historical cancellation/retirement event ledger across all markets.",
        },
        {
            "id": "ACTUAL_ELECTRICITY_CONSUMPTION",
            "item": "Actual electricity-consumption/load data where publicly available",
            "status": "INGESTED_SITE_SNAPSHOTS",
            "coverage": f"{len(power_records)} site-specific annual electricity-consumption snapshots are retained. They are annual aggregates, not interval demand telemetry.",
        },
        {
            "id": "MACRO_LOAD_FACTOR",
            "item": "Macro load-factor analysis",
            "status": "NOT_YET_RELIABLE",
            "coverage": "Annual-average equivalents are published for the available MWh snapshots, but a valid site load factor requires time-matched peak/contracted demand or interval data; the registry does not infer it.",
        },
        {
            "id": "EVENT_TRANSIENT_DETECTION",
            "item": "Event/transient detection where data permits",
            "status": "NOT_INGESTED",
            "coverage": "No interval site-demand series is currently retained, so transient/ramp detection is not claimed.",
        },
        {
            "id": "TRAINING_CHECKPOINTING",
            "item": "Training/checkpointing signal research",
            "status": "RESEARCH_QUEUE",
            "coverage": "No site-level operational trace currently links power transients to training/checkpointing events; this remains a research target requiring interval telemetry and independent workload evidence.",
        },
    ]

    out = {
        "schema_version": 1,
        "generated_on": datetime.now(timezone.utc).isoformat(),
        "today_utc": today.isoformat(),
        "title": "Track 3 time-series verification layer",
        "semantics": "This artifact separates observed source records, derived event-to-event changes, future/predicted records, aggregate historical queue material, and research gaps. Missing time-series evidence is not interpreted as absence.",
        "summary": {
            "epoch_site_count": len(sites),
            "timeline_source_row_count": len(timeline_rows),
            "timeline_rows_unmatched_to_epoch_site": unmatched,
            "sites_with_observed_timeline": sum(1 for x in site_timelines if x["observed_event_count"] > 0),
            "observed_timeline_event_count": observed_event_count,
            "future_or_predicted_timeline_event_count": future_event_count,
            "sites_with_multiple_observed_points": sum(1 for x in site_timelines if x["observed_event_count"] >= 2),
            "site_level_annual_power_snapshot_count": len(power_records),
            "caiso_historical_series_record_count": len(caiso.get("records", [])),
            "pjm_historical_material_record_count": len(pjm.get("records", [])),
        },
        "checklist": checklist,
        "quarterly_event_change_series": [
            {
                "quarter": q,
                "it_power_delta_mw": round(v["it_power_delta_mw"], 3),
                "total_power_delta_mw": round(v["total_power_delta_mw"], 3),
                "building_delta": round(v["building_delta"], 3),
                "site_change_event_count": int(v["site_change_event_count"]),
            }
            for q, v in sorted(quarterly.items())
        ],
        "annual_electricity_consumption_snapshots": power_records,
        "historical_queue_material": {
            "caiso_cluster_history": caiso.get("records", []),
            "pjm_load_analysis_subcommittee_history": pjm.get("records", []),
            "semantics": "Historical queue/material series are retained as dated public evidence and are not treated as additive facility load.",
        },
        "current_registry_status_snapshot": registry_counts,
        "site_timelines": site_timelines,
        "source_manifest": [
            {"path": str(TIMELINE_CSV.relative_to(ROOT)).replace("\\", "/"), "publisher": "Epoch AI", "role": "dated facility construction/power timeline"},
            {"path": str(POWER_JSON.relative_to(ROOT)).replace("\\", "/"), "publisher": "published company report snapshots", "role": "site-specific annual electricity consumption"},
            {"path": str(CAISO_JSON.relative_to(ROOT)).replace("\\", "/"), "publisher": "CAISO", "role": "historical queue series"},
            {"path": str(PJM_JSON.relative_to(ROOT)).replace("\\", "/"), "publisher": "PJM", "role": "dated large-load submission history"},
        ],
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    fields = [
        "epoch_id","site_name","country","state_province","date","temporal_status",
        "construction_status","buildings_operational","it_power_mw","total_power_mw",
        "delta_it_power_mw","delta_total_power_mw","delta_buildings_operational",
        "source_url",
    ]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for x in event_change_rows:
            c = x.get("change_from_previous_observed_event") or {}
            w.writerow({
                "epoch_id": x["epoch_id"], "site_name": x["site_name"],
                "country": next((s["country"] for s in site_timelines if s["epoch_id"] == x["epoch_id"]), None),
                "state_province": next((s["state_province"] for s in site_timelines if s["epoch_id"] == x["epoch_id"]), None),
                "date": x["date"], "temporal_status": x["temporal_status"],
                "construction_status": x["construction_status"],
                "buildings_operational": x["buildings_operational"],
                "it_power_mw": x["it_power_mw"], "total_power_mw": x["total_power_mw"],
                "delta_it_power_mw": c.get("delta_it_power_mw"),
                "delta_total_power_mw": c.get("delta_total_power_mw"),
                "delta_buildings_operational": c.get("delta_buildings_operational"),
                "source_url": SOURCE_URL,
            })

    print(json.dumps(out["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
