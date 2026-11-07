#!/usr/bin/env python3
"""Ingest BPA Line/Load large-load requests from the official workbook.

The parser is deliberately conservative:
- load requests are identified by BPA L-series request IDs;
- requested MW is kept as requested load, never converted to energized/contracted demand;
- existing display geometry is carried forward only when the same request ID already
  has retained geometry in the repository;
- no geocoding or coordinate inference is performed;
- source-row provenance (sheet + row) and workbook SHA-256 are retained.

Usage:
  python ingest_bpa_large_loads.py --selftest
  python ingest_bpa_large_loads.py
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import re
import tempfile
from pathlib import Path
from typing import Any, Iterable

import openpyxl
import requests

OFFICIAL_XLSX_URL = "https://www.bpa.gov/-/media/Aep/transmission-media-documents/InterconnectionQueueOutput.xlsx"
MIN_LOAD_MW = 100.0
DEFAULT_JSON = Path("data/bpa_large_load_registry.json")
DEFAULT_CSV = Path("data/bpa_large_load_registry.csv")
MAP_MANIFEST = Path("data/map_layer_manifest.json")
MAP_MANIFEST_CSV = Path("data/map_layer_manifest.csv")
MARKET_MANIFEST = Path("data/market_universe_manifest.json")
MARKET_MANIFEST_CSV = Path("data/market_universe_manifest.csv")
CATALOG = Path("data/public_data_catalog.json")
CHECKLIST = Path("data/data_universe_checklist.json")
CHECKLIST_CSV = Path("data/data_universe_checklist.csv")
INDEX_HTML = Path("index.html")

ID_RE = re.compile(r"\bL\d{4,6}\b", re.I)
NUM_RE = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?")
TERMINAL_STATUSES = {
    "WITHDRAWN", "WITHDRAW", "TERMINATED", "DECOMMISSIONED", "CANCELLED",
    "CANCELED", "CLOSED", "RETIRED",
}


def norm(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip()).lower()


def clean_key(value: Any) -> str:
    s = norm(value)
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def parse_num(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    m = NUM_RE.search(str(value).replace("MW", "").replace("mw", ""))
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def parse_date(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, (dt.datetime, dt.date)):
        return value.strftime("%Y-%m")
    s = str(value).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y/%m/%d"):
        try:
            return dt.datetime.strptime(s[:10], fmt).strftime("%Y-%m")
        except ValueError:
            pass
    m = re.search(r"(20\d{2})[-/](0?[1-9]|1[0-2])", s)
    return f"{m.group(1)}-{int(m.group(2)):02d}" if m else None


def header_score(row: list[Any]) -> int:
    text = " | ".join(norm(x) for x in row if x not in (None, ""))
    score = 0
    for terms, pts in (
        (("request id", "request number", "queue id", "request"), 4),
        (("project",), 2),
        (("mw", "megawatt", "load"), 2),
        (("status",), 1),
        (("county",), 1),
        (("point of interconnection", "poi", "substation"), 1),
    ):
        if any(t in text for t in terms):
            score += pts
    return score


def detect_header(ws: Any, max_rows: int = 40) -> tuple[int, list[str]]:
    best = (-1, -1, [])
    for idx, row in enumerate(ws.iter_rows(min_row=1, max_row=max_rows, values_only=True), start=1):
        vals = list(row)
        score = header_score(vals)
        if score > best[0]:
            keys = []
            seen: dict[str, int] = {}
            for cell in vals:
                base = clean_key(cell) or "column"
                seen[base] = seen.get(base, 0) + 1
                keys.append(base if seen[base] == 1 else f"{base}_{seen[base]}")
            best = (score, idx, keys)
    if best[1] < 1 or best[0] < 4:
        raise ValueError(f"Could not identify a BPA load-request header in sheet {ws.title!r}")
    return best[1], best[2]


def first_key(headers: list[str], *needles: str) -> str | None:
    for h in headers:
        hn = h.lower()
        if any(n in hn for n in needles):
            return h
    return None


def pick_capacity(row: dict[str, Any]) -> tuple[float | None, str | None]:
    headers = list(row)
    preferred = sorted(
        headers,
        key=lambda h: (
            0 if "requested" in h else 1,
            0 if "load" in h else 1,
            0 if "mw" in h or "megawatt" in h else 1,
            0 if "capacity" in h else 1,
        ),
    )
    for h in preferred:
        hn = h.lower()
        if not any(x in hn for x in ("mw", "megawatt", "capacity", "load")):
            continue
        n = parse_num(row.get(h))
        if n is not None:
            return n, h
    return None, None


def pick_request_id(row: dict[str, Any]) -> str | None:
    for value in row.values():
        m = ID_RE.search(str(value)) if value not in (None, "") else None
        if m:
            return m.group(0).upper()
    return None


def materialize_record(
    row: dict[str, Any],
    *,
    sheet: str,
    row_number: int,
    old_by_queue: dict[str, dict[str, Any]],
    capture_date: str,
    source_sha256: str,
) -> dict[str, Any] | None:
    queue_id = pick_request_id(row)
    if not queue_id:
        return None

    project_key = first_key(list(row), "project_name", "project")
    status_key = first_key(list(row), "status", "stage")
    customer_key = first_key(list(row), "customer", "developer", "requester", "applicant", "company")
    county_key = first_key(list(row), "county", "location")
    state_key = first_key(list(row), "state", "province")
    poi_key = first_key(list(row), "point_of_interconnection", "point_of_interconnection", "poi", "substation")
    date_key = first_key(list(row), "request_date", "received_date", "date_received", "request", "date")
    cap_mw, cap_key = pick_capacity(row)

    project = row.get(project_key) if project_key else None
    status = row.get(status_key) if status_key else None
    customer = row.get(customer_key) if customer_key else None
    county = row.get(county_key) if county_key else None
    state = row.get(state_key) if state_key else None
    poi = row.get(poi_key) if poi_key else None
    filed_month = parse_date(row.get(date_key)) if date_key else None

    parts = [str(county).strip() if county not in (None, "") else None,
             str(state).strip() if state not in (None, "") else None]
    parts = [p for p in parts if p]
    location = ", ".join(parts) if parts else None
    jurisdiction = f"{str(state).strip()}, US" if state not in (None, "") else "US"

    old = old_by_queue.get(queue_id, {})
    old_map = old.get("map_point")
    map_point = old_map if isinstance(old_map, list) and len(old_map) == 2 else None
    map_precision = old.get("map_precision") if map_point else None
    map_provenance = None
    if map_point:
        existing_provenance = old.get("map_provenance")
        if isinstance(existing_provenance, dict) and existing_provenance.get("source_url"):
            map_provenance = existing_provenance
        else:
            map_provenance = {
                "type": "carried_forward_existing_repository_geometry",
                "source_url": old.get("source_url"),
                "source_capture_date": old.get("capture_date"),
                "precision": map_precision,
            }

    raw_fields = {k: v for k, v in row.items() if v not in (None, "")}
    raw_value = str(row.get(cap_key)).strip() if cap_key and row.get(cap_key) not in (None, "") else (
        f"{cap_mw:g} MW" if cap_mw is not None else None
    )

    notes = (
        "Official BPA Line/Load workbook row. Requested MW is the requester's filed load "
        "request, not a study result, entitlement, contracted demand or measured load. "
        "Coordinates are carried forward only from an existing repository record with the "
        "same BPA request ID; no new geocoding or location inference is performed."
    )

    return {
        "id": f"BPA-{queue_id}",
        "evidence_type": "official_large_load_request_record",
        "project_name": str(project).strip() if project not in (None, "") else queue_id,
        "customer_or_developer": str(customer).strip() if customer not in (None, "") else None,
        "utility_or_provider": "Bonneville Power Administration",
        "jurisdiction": jurisdiction,
        "location": location,
        "county_or_zone": str(county).strip() if county not in (None, "") else None,
        "queue_id": queue_id,
        "status": str(status).strip().upper() if status not in (None, "") else None,
        "filed_month": filed_month,
        "capacity_claims": (
            [{
                "value_mw": cap_mw,
                "unit": "MW",
                "raw_value": raw_value,
                "qualifier": "BPA Line/Load request MW as filed",
                "source_url": OFFICIAL_XLSX_URL,
                "capture_date": capture_date,
            }] if cap_mw is not None else []
        ),
        "source_authority": "official BPA Line/Load Interconnection workbook",
        "source_url": OFFICIAL_XLSX_URL,
        "capture_date": capture_date,
        "source_scope": "BPA InterconnectionQueueOutput.xlsx — Line/Load load requests",
        "map_point": map_point,
        "map_precision": map_precision,
        "map_provenance": map_provenance,
        "notes": notes,
        "poi_substation": str(poi).strip() if poi not in (None, "") else None,
        "source_provenance": {
            "workbook_sha256": source_sha256,
            "sheet": sheet,
            "source_row": row_number,
            "capacity_source_column": cap_key,
            "raw_fields": raw_fields,
        },
    }


def parse_workbook_bytes(
    data: bytes,
    old_by_queue: dict[str, dict[str, Any]],
    capture_date: str,
) -> tuple[list[dict[str, Any]], str, int]:
    sha256 = hashlib.sha256(data).hexdigest()
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    by_queue: dict[str, dict[str, Any]] = {}

    for ws in wb.worksheets:
        try:
            header_row, headers = detect_header(ws)
        except ValueError:
            continue
        for row_number, values in enumerate(ws.iter_rows(min_row=header_row + 1, values_only=True), start=header_row + 1):
            row = {}
            for idx, key in enumerate(headers):
                row[key] = values[idx] if idx < len(values) else None
            record = materialize_record(
                row,
                sheet=ws.title,
                row_number=row_number,
                old_by_queue=old_by_queue,
                capture_date=capture_date,
                source_sha256=sha256,
            )
            if not record:
                continue
            qid = record["queue_id"]
            # Prefer the row with more populated fields if a workbook has duplicate
            # presentations across sheets.
            existing = by_queue.get(qid)
            score = sum(v not in (None, "", []) for v in record.values())
            if existing is None or score > sum(v not in (None, "", []) for v in existing.values()):
                by_queue[qid] = record

    all_records = sorted(by_queue.values(), key=lambda r: (
        -float(r["capacity_claims"][0]["value_mw"]) if r["capacity_claims"] else 0,
        r["queue_id"],
    ))
    if not all_records:
        raise RuntimeError("Official BPA workbook was downloaded, but no L-series load-request rows were parsed.")

    records = [
        r for r in all_records
        if r.get("capacity_claims")
        and float(r["capacity_claims"][0]["value_mw"]) >= MIN_LOAD_MW
    ]
    if not records:
        raise RuntimeError(
            f"Official BPA workbook contained {len(all_records)} L-series rows but none met the "
            f"{MIN_LOAD_MW:g} MW large-load threshold."
        )
    return records, sha256, len(all_records)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def atomic_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)


def write_outputs(
    records: list[dict[str, Any]],
    source_sha256: str,
    capture_date: str,
    raw_source_bytes: int,
    raw_l_series_count: int,
) -> None:
    mapped = [r for r in records if r.get("map_point")]
    live = [r for r in records if (r.get("status") or "").upper() not in TERMINAL_STATUSES]

    obj = {
        "schema_version": 1,
        "generated_on": capture_date,
        "title": "BPA Large-Load Request Registry — normalized official workbook layer",
        "purpose": "Non-additive normalization of BPA Line/Load interconnection request records. Requested MW remain requests-as-filed; existing display geometry is preserved only by matching BPA request ID.",
        "threshold_mw": MIN_LOAD_MW,
        "additive_to_core": False,
        "source": {
            "id": "BPA-LARGE-LOAD",
            "name": "BPA Line/Load Interconnection Request Queue",
            "official_source_url": "https://www.bpa.gov/energy-and-services/transmission/interconnection",
            "official_workbook_url": OFFICIAL_XLSX_URL,
            "secondary_source_urls": [
                "https://substationscout.com/large-load-registry/",
                "https://www.wattstreet.net/load-ledger/",
            ],
            "source_authority": "official BPA workbook with secondary reproductions retained for corroboration",
            "official_publisher": "Bonneville Power Administration",
            "source_capture_dates": [capture_date],
            "raw_official_snapshot_retained": False,
            "raw_official_snapshot_sha256": source_sha256,
            "raw_official_snapshot_bytes": raw_source_bytes,
            "raw_source_semantics": "The official workbook linked by BPA is fetched at refresh time. The binary is not committed; SHA-256 is retained to fingerprint the exact downloaded source.",
            "source_population_accounting": {
                "source_last_updated": capture_date,
                "raw_l_series_rows_on_record": raw_l_series_count,
                "eligible_rows_at_threshold_mw": len(records),
                "threshold_mw": MIN_LOAD_MW,
                "requests_on_record_at_source": len(records),
                "live_requests_at_source_computed": len(live),
                "repository_retained_records": len(records),
                "repository_retained_live_rows": len(live),
                "repository_retained_mapped_rows": len(mapped),
                "coverage_statement": (
                    f"The official workbook exposed {raw_l_series_count} L-series rows; this dedicated "
                    f"large-load layer retains only rows with filed load MW >= {MIN_LOAD_MW:g}. It is not "
                    "presented as a data-center-only population because BPA does not publish a reliable "
                    "end-use classification."
                ),
            },
        },
        "record_count": len(records),
        "mapped_record_count": len(mapped),
        "unmapped_record_count": len(records) - len(mapped),
        "records": records,
    }
    atomic_text(DEFAULT_JSON, json.dumps(obj, indent=2, ensure_ascii=False, default=str) + "\n")

    rows = []
    for r in records:
        mw = r["capacity_claims"][0]["value_mw"] if r.get("capacity_claims") else ""
        rows.append({
            "id": r["id"],
            "project_name": r["project_name"],
            "queue_id": r["queue_id"],
            "status": r["status"] or "",
            "jurisdiction": r["jurisdiction"],
            "location": r["location"] or "",
            "capacity_mw": mw,
            "raw_capacity": r["capacity_claims"][0]["raw_value"] if r.get("capacity_claims") else "",
            "poi_substation": r["poi_substation"] or "",
            "source_url": r["source_url"],
            "capture_date": r["capture_date"],
            "source_scope": r["source_scope"],
            "map_lat": r["map_point"][0] if r.get("map_point") else "",
            "map_lon": r["map_point"][1] if r.get("map_point") else "",
            "map_precision": r["map_precision"] or "",
            "map_source_url": (r.get("map_provenance") or {}).get("source_url") or "",
            "map_source_capture_date": (r.get("map_provenance") or {}).get("source_capture_date") or "",
            "source_authority": r["source_authority"],
            "source_sheet": r["source_provenance"]["sheet"],
            "source_row": r["source_provenance"]["source_row"],
        })
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    atomic_text(DEFAULT_CSV, buf.getvalue())


def update_manifests(records: list[dict[str, Any]], capture_date: str, source_sha256: str) -> None:
    count = len(records)
    mapped = sum(bool(r.get("map_point")) for r in records)
    unmapped_ids = [r["id"] for r in records if not r.get("map_point")]
    live = sum((r.get("status") or "").upper() not in TERMINAL_STATUSES for r in records)

    manifest = load_json(MARKET_MANIFEST)
    bpa = next(x for x in manifest["markets"] if x["id"] == "BPA")
    bpa.update({
        "status": "official_row_level_load_snapshot_ingested",
        "core_rows": 0,
        "project_records": count,
        "captured": capture_date,
        "row_level_snapshot": "data/bpa_large_load_registry.json",
        "notes": (
            f"Official BPA InterconnectionQueueOutput.xlsx load-request snapshot parsed at refresh time: "
            f"{count} L-series rows ({live} non-terminal by published status), {mapped} with retained display geometry, "
            f"{len(unmapped_ids)} without display geometry. This layer remains non-additive to the nine-market core."
        ),
        "source_urls": [
            "https://www.bpa.gov/energy-and-services/transmission/interconnection",
            OFFICIAL_XLSX_URL,
            "https://substationscout.com/large-load-registry/",
            "https://www.wattstreet.net/load-ledger/",
        ],
    })
    atomic_text(MARKET_MANIFEST, json.dumps(manifest, indent=2, ensure_ascii=False, default=str) + "\n")

    mm = list(csv.DictReader(MARKET_MANIFEST_CSV.open("r", encoding="utf-8", newline="")))
    for row in mm:
        if row.get("id") == "BPA":
            row["status"] = "official_row_level_load_snapshot_ingested"
            row["core_rows"] = "0"
            row["source_urls"] = ";".join(bpa["source_urls"])
            row["scope"] = bpa.get("scope", "")
            row["captured"] = capture_date
            row["notes"] = bpa["notes"]
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=mm[0].keys())
    writer.writeheader(); writer.writerows(mm)
    atomic_text(MARKET_MANIFEST_CSV, out.getvalue())

    mapm = load_json(MAP_MANIFEST)
    layer = next(x for x in mapm["layers"] if x["id"] == "BPA_LARGE_LOAD")
    layer.update({
        "records": count,
        "mapped_records": mapped,
        "unlocated_records": unmapped_ids,
        "source_capture_date": capture_date,
        "file": "data/bpa_large_load_registry.json",
        "status": (
            f"official BPA workbook snapshot; {count} parsed L-series load requests; "
            f"{mapped} retain display geometry by prior request-ID match"
        ),
        "source_sha256": source_sha256,
    })
    atomic_text(MAP_MANIFEST, json.dumps(mapm, indent=2, ensure_ascii=False) + "\n")

    map_csv = list(csv.DictReader(MAP_MANIFEST_CSV.open("r", encoding="utf-8", newline="")))
    for row in map_csv:
        if row.get("id") == "BPA_LARGE_LOAD":
            row["records"] = str(count)
            row["mapped_records"] = str(mapped)
            row["source_capture_date"] = capture_date
            row["file"] = "data/bpa_large_load_registry.json"
            row["status"] = layer["status"]
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=map_csv[0].keys())
    writer.writeheader(); writer.writerows(map_csv)
    atomic_text(MAP_MANIFEST_CSV, out.getvalue())

    cat = load_json(CATALOG)
    for dataset in cat.get("datasets", []):
        if dataset.get("path") in ("data/bpa_large_load_registry.json", "data/bpa_large_load_registry.csv"):
            dataset["record_count"] = count
            dataset["public_page"] = f"https://anonrish.github.io/continental-load-registry/{dataset['path']}"
            dataset["notes"] = (
                f"{count} normalized BPA large-load request rows from the official workbook at the latest refresh. "
                f"{mapped} retain prior display geometry; {count - mapped} have no retained display geometry."
            )
    atomic_text(CATALOG, json.dumps(cat, indent=2, ensure_ascii=False) + "\n")
    checklist = load_json(CHECKLIST)
    entry = next((x for x in checklist["records"] if x["id"] == "BPA"), None)
    if entry:
        entry["status"] = "official_row_level_snapshot_ingested"
        entry["what_is_published"] = (
            f"Official BPA Line/Load workbook normalized to {count} L-series request rows at {capture_date}; "
            f"{mapped} retain prior display geometry and {len(unmapped_ids)} remain unmapped."
        )
        entry["next_blocker"] = (
            "Refresh against the official workbook as it changes. Do not infer end use from BPA requests; "
            "retain request MW as filed and keep unsupported geometry null."
        )
    atomic_text(CHECKLIST, json.dumps(checklist, indent=2, ensure_ascii=False, default=str) + "\n")

    checklist_csv = list(csv.DictReader(CHECKLIST_CSV.open("r", encoding="utf-8", newline="")))
    for row in checklist_csv:
        if row.get("id") == "BPA":
            row["status"] = "official_row_level_snapshot_ingested"
            row["what_is_published"] = entry["what_is_published"] if entry else row.get("what_is_published", "")
            row["next_blocker"] = entry["next_blocker"] if entry else row.get("next_blocker", "")
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=checklist_csv[0].keys())
    writer.writeheader(); writer.writerows(checklist_csv)
    atomic_text(CHECKLIST_CSV, out.getvalue())

    # Keep obvious user-facing counts from becoming stale when the official source
    # refresh changes the row population.
    html = INDEX_HTML.read_text(encoding="utf-8")
    html = re.sub(
        r'<div class="p-4"><p class="mono text-xl">\d+</p><p class="text-xs mt-1" style="color:var\(--ink-faint\);">BPA large-load request records</p></div>',
        f'<div class="p-4"><p class="mono text-xl">{count}</p><p class="text-xs mt-1" style="color:var(--ink-faint);">BPA large-load request records</p></div>',
        html,
    )
    html = re.sub(
        r'id="mapInventoryBpaCount">[^<]+',
        f'id="mapInventoryBpaCount">{count} / {mapped}',
        html,
    )
    atomic_text(INDEX_HTML, html)


def download(url: str) -> bytes:
    r = requests.get(
        url,
        timeout=60,
        headers={"User-Agent": "continental-load-registry/bpa-refresh (+public-research-pipeline)"},
    )
    r.raise_for_status()
    data = r.content
    if len(data) < 10_000:
        raise RuntimeError(f"BPA workbook response is unexpectedly small ({len(data)} bytes)")
    return data


def selftest() -> None:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Line and Load"
    ws.append(["Request ID", "Project Name", "Requested MW", "County", "State", "Status", "POI", "Request Date"])
    ws.append(["L0705", "Open Range", 3300, "Adams County", "WA", "RECEIVED", "Substation A", dt.date(2026, 8, 1)])
    ws.append(["L0706", "Test Below Threshold", 50, "Benton County", "WA", "WITHDRAWN", "Substation B", dt.date(2025, 3, 1)])
    buf = io.BytesIO(); wb.save(buf)
    old = {"L0705": {"map_point": [46.99, -117.16], "map_precision": "county display point", "source_url": "https://example.invalid/legacy-source", "capture_date": "2026-09-23"}}
    records, sha, raw_count = parse_workbook_bytes(buf.getvalue(), old, "2026-09-28")
    assert raw_count == 2
    assert len(records) == 1
    first = next(r for r in records if r["queue_id"] == "L0705")
    assert first["capacity_claims"][0]["value_mw"] == 3300
    assert first["map_point"] == [46.99, -117.16]
    assert first["map_provenance"]["source_url"] == "https://example.invalid/legacy-source"
    assert first["map_provenance"]["source_capture_date"] == "2026-09-23"
    assert first["source_provenance"]["sheet"] == "Line and Load"
    assert first["source_provenance"]["source_row"] == 2
    assert sha
    assert first["capacity_claims"][0]["value_mw"] >= MIN_LOAD_MW
    assert all(r["capacity_claims"] and r["capacity_claims"][0]["value_mw"] >= MIN_LOAD_MW for r in records)
    assert sum((r["status"] or "") not in TERMINAL_STATUSES for r in records) == 1
    print("PASS: BPA workbook parser self-test")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=OFFICIAL_XLSX_URL)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return

    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    old_by_queue: dict[str, dict[str, Any]] = {}
    if DEFAULT_JSON.exists():
        old = load_json(DEFAULT_JSON)
        old_by_queue = {
            str(r.get("queue_id")): r
            for r in old.get("records", [])
            if r.get("queue_id")
        }

    data = download(args.url)
    records, sha256, raw_l_series_count = parse_workbook_bytes(data, old_by_queue, today)
    write_outputs(records, sha256, today, len(data), raw_l_series_count)
    update_manifests(records, today, sha256)

    mapped = sum(bool(r.get("map_point")) for r in records)
    live = sum((r.get("status") or "").upper() not in TERMINAL_STATUSES for r in records)
    print(
        f"PASS: BPA official workbook ingested: {len(records)} L-series rows; "
        f"{live} non-terminal; {mapped} mapped; {len(records)-mapped} unmapped; sha256={sha256}"
    )


if __name__ == "__main__":
    main()
