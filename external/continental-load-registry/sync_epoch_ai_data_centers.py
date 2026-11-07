#!/usr/bin/env python3
"""
Sync Epoch AI's public AI data-center datasets into a secondary evidence layer.

The sync preserves Epoch's raw CSV values exactly and creates a normalized JSON
registry plus a conservative crosswalk to the current queue registry embedded in
index.html. Queue values remain authoritative for queue facts; Epoch values remain
authoritative only for Epoch's own estimates.

Usage:
  python sync_epoch_ai_data_centers.py --selftest
  python sync_epoch_ai_data_centers.py --sync
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import shutil
import sys
import tempfile
import unicodedata
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "external" / "epoch_ai"
INDEX_HTML = ROOT / "index.html"

URLS = {
    "data_centers.csv": "https://epoch.ai/data/data_centers/data_centers.csv",
    "data_center_timelines.csv": "https://epoch.ai/data/data_centers/data_center_timelines.csv",
    "data_centers_chip_quantities.csv": "https://epoch.ai/data/data_centers/data_centers_chip_quantities.csv",
}

# Additional public compute-accounting and cooling datasets. These remain
# source-specific snapshots; they are not silently joined into site facts.
EXTERNAL_URLS = {
    "ai_chip_owners_cumulative_by_designer.csv": "https://epoch.ai/data/ai_chip_owners_cumulative_by_designer.csv",
    "ai_chip_owners_quarters_by_chip_type.csv": "https://epoch.ai/data/ai_chip_owners_quarters_by_chip_type.csv",
    "ai_chip_owners_cumulative_by_chip_type.csv": "https://epoch.ai/data/ai_chip_owners_cumulative_by_chip_type.csv",
    "ai_chip_users_year_end_by_lab.csv": "https://epoch.ai/data/ai_chip_users_year_end_by_lab.csv",
    "ai_chip_users_intermediates_by_lab.csv": "https://epoch.ai/data/ai_chip_users_intermediates_by_lab.csv",
    "ai_chip_sales_chip_types.csv": "https://epoch.ai/data/ai_chip_sales_chip_types.csv",
    "ai_chip_sales_organizations.csv": "https://epoch.ai/data/ai_chip_sales_organizations.csv",
    "ai_chip_sales_timelines_by_chip.csv": "https://epoch.ai/data/ai_chip_sales_timelines_by_chip.csv",
    "data_center_chillers.csv": "https://epoch.ai/data/data_centers/data_center_chillers.csv",
    "data_center_cooling_towers.csv": "https://epoch.ai/data/data_centers/data_center_cooling_towers.csv",
}

ALIASES = {
    "name": ["Name"],
    "country": ["Country"],
    "address": ["Address"],
    "owner": ["Owner"],
    "users": ["Users"],
    "project": ["Project"],
    "current_h100_eq": ["Current H100 equivalents"],
    "current_power_mw": ["Current power (MW)", "Current IT power (MW)"],
    "current_capital_cost_b": ["Current total capital cost (2025 USD billions)", "Current capital cost (2025 USD billions)"],
    "selected_sources": ["Selected sources"],
    "calculations_sheet": ["Calculations sheet"],
    "investors": ["Investors"],
    "construction_companies": ["Construction companies"],
    "energy_companies": ["Energy companies"],
}

TIMELINE_ALIASES = {
    "data_center": ["Data center"],
    "date": ["Date"],
    "construction_status": ["Construction status"],
    "buildings_operational": ["Buildings operational"],
    "it_power_mw": ["IT power (MW)"],
    "power_mw": ["Power (MW)"],
    "h100_eq": ["H100 equivalents"],
    "performance_8bit_ops": ["Performance (8-bit OP/s)"],
    "total_capital_cost_b": ["Total capital cost (2025 USD billions)"],
    "compute_cost_b": ["Compute cost (2025 USD billions)"],
    "construction_cost_b": ["Construction cost (2025 USD billions)"],
    "annual_operating_cost_b": ["Annual operating cost (2025 USD billions)"],
    "water_mgd": ["Water use (MGD)"],
}

CHIP_ALIASES = {
    "data_center": ["Data center"],
    "date": ["Date"],
    "chip_type": ["Chip type"],
    "number_units": ["Number of Units"],
    "chip_type_source": ["Chip type source"],
    "number_units_source": ["Number of Units source"],
    "owner": ["Owner"],
    "user": ["User"],
    "notes": ["Notes"],
}

STATE_NAMES = {
    "alabama":"AL","alaska":"AK","arizona":"AZ","arkansas":"AR","california":"CA",
    "colorado":"CO","connecticut":"CT","delaware":"DE","florida":"FL","georgia":"GA",
    "hawaii":"HI","idaho":"ID","illinois":"IL","indiana":"IN","iowa":"IA","kansas":"KS",
    "kentucky":"KY","louisiana":"LA","maine":"ME","maryland":"MD","massachusetts":"MA",
    "michigan":"MI","minnesota":"MN","mississippi":"MS","missouri":"MO","montana":"MT",
    "nebraska":"NE","nevada":"NV","new hampshire":"NH","new jersey":"NJ","new mexico":"NM",
    "new york":"NY","north carolina":"NC","north dakota":"ND","ohio":"OH","oklahoma":"OK",
    "oregon":"OR","pennsylvania":"PA","rhode island":"RI","south carolina":"SC",
    "south dakota":"SD","tennessee":"TN","texas":"TX","utah":"UT","vermont":"VT",
    "virginia":"VA","washington":"WA","west virginia":"WV","wisconsin":"WI","wyoming":"WY",
    "district of columbia":"DC",
}
PROVINCE_CODES = {"ontario":"ON","alberta":"AB","british columbia":"BC","manitoba":"MB",
                  "saskatchewan":"SK","quebec":"QC","nova scotia":"NS","new brunswick":"NB",
                  "newfoundland and labrador":"NL","prince edward island":"PE",
                  "newfoundland":"NL","northwest territories":"NT","yukon":"YT","nunavut":"NU"}

GENERIC = {
    "the","data","center","centre","centers","campus","site","ai","artificial","intelligence",
    "facility","dc","llc","inc","corp","corporation","company","co","limited","power","park",
    "phase","north","south","east","west","new","project","hub","technology","cloud","compute",
    "labs","lab","holdings","group","infrastructure","advanced","digital","one","two","three"
}


def norm(value: Any) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKD", text).encode("ascii","ignore").decode("ascii")
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def tokens(value: Any) -> set[str]:
    return {t for t in norm(value).split() if len(t) >= 3 and t not in GENERIC and not t.isdigit()}


def pick(row: dict[str, Any], aliases: list[str]) -> Any:
    for a in aliases:
        if a in row:
            return row[a]
    return None


def numeric(value: Any) -> float | int | None:
    if value is None or value == "":
        return None
    s = str(value).replace(",", "").strip()
    try:
        f = float(s)
        if f.is_integer():
            return int(f)
        return f
    except ValueError:
        return None


def infer_region(address: str, country: str) -> str | None:
    """Infer a state/province without confusing street suffixes (Ct, Rd, etc.) for postal codes."""
    raw = str(address or "").strip()
    a = norm(raw)
    c = norm(country)

    # Prefer the postal-address token immediately before a US ZIP / Canadian postal code.
    # This avoids matching street abbreviations such as "Ct" (court) as Connecticut.
    if c in {"united states", "usa", "us"} or "united states" in c:
        m = re.search(r"(?:,|\s)\b([A-Z]{2})\b\s+\d{5}(?:-\d{4})?\s*$", raw)
        if m and m.group(1) in {v for v in STATE_NAMES.values()}:
            return m.group(1)
        for name, code in sorted(STATE_NAMES.items(), key=lambda kv: len(kv[0]), reverse=True):
            if re.search(r"\b" + re.escape(name.lower()) + r"\b", a):
                return code
    if c in {"canada"} or "canada" in c:
        m = re.search(r"(?:,|\s)\b([A-Z]{2})\b\s+[A-Z]\d[A-Z]\s*\d[A-Z]\d\s*$", raw, re.I)
        if m and m.group(1).upper() in {v for v in PROVINCE_CODES.values()}:
            return m.group(1).upper()
        for name, code in sorted(PROVINCE_CODES.items(), key=lambda kv: len(kv[0]), reverse=True):
            if re.search(r"\b" + re.escape(name.lower()) + r"\b", a):
                return code
    return None


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def parse_registry() -> list[dict[str, Any]]:
    html = INDEX_HTML.read_text(encoding="utf-8")
    m = re.search(r"const REGISTRY_DATA = (\[.*?\]);\n", html, re.S)
    if not m:
        raise RuntimeError("Could not find REGISTRY_DATA in index.html")
    rows = json.loads(m.group(1))
    if not isinstance(rows, list):
        raise RuntimeError("REGISTRY_DATA is not an array")
    return rows


def load_overrides() -> dict[str, Any]:
    p = OUT / "match_overrides.json"
    if not p.exists():
        return {}
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise RuntimeError("match_overrides.json must contain an object")
    return data


def conservative_matches(epoch: dict[str, Any], registry: list[dict[str, Any]], overrides: dict[str, Any]) -> list[dict[str, Any]]:
    name = str(epoch.get("name") or "")
    name_key = norm(name)
    if name_key in overrides:
        ov = overrides[name_key]
        ids = ov.get("registry_ids", []) if isinstance(ov, dict) else ov
        return [{
            "queue_id": str(qid),
            "relationship": (ov.get("relationship") if isinstance(ov, dict) else "same_campus_or_phase"),
            "match_confidence": (ov.get("match_confidence") if isinstance(ov, dict) else "manual"),
            "match_basis": (ov.get("match_basis") if isinstance(ov, dict) else "Manual override"),
        } for qid in ids]

    e_tokens = tokens(name) | tokens(epoch.get("owner")) | tokens(epoch.get("users"))
    region = infer_region(str(epoch.get("address") or ""), str(epoch.get("country") or ""))
    candidates = []
    for r in registry:
        hay = " ".join([str(r.get("proj","")), str(r.get("dev","")), str(r.get("poi","")), str(r.get("co","")), str(r.get("st",""))])
        hnorm = norm(hay)
        pnorm = norm(r.get("proj"))
        if name_key and (name_key == pnorm or name_key in hnorm):
            candidates.append({
                "queue_id": str(r.get("id")),
                "relationship": "possible_match",
                "match_confidence": "high",
                "match_basis": "Epoch site name has an exact/embedded match in project or registry fields.",
            })
            continue
        overlap = len(e_tokens & tokens(hay))
        region_bonus = 1 if region and norm(r.get("st")) == norm(region) else 0
        score = overlap * 20 + region_bonus * 20
        if overlap >= 3 and region_bonus:
            candidates.append({
                "queue_id": str(r.get("id")),
                "relationship": "possible_match",
                "match_confidence": "medium",
                "match_basis": f"{overlap} distinctive tokens overlap and state/province matches ({region}).",
                "_score": score,
            })
    candidates.sort(key=lambda x: x.get("_score", 1000), reverse=True)
    for c in candidates:
        c.pop("_score", None)
    return candidates[:5]



def validate_site_evidence(expected_epoch_ids: set[str]) -> dict[str, int]:
    """Validate the preserved secondary evidence layer against the freshly
    downloaded Epoch site IDs. The dashboard depends on this artifact having
    the same 1:1 site universe as data_centers.csv."""
    evidence_path = OUT / "site_level_connection_evidence.json"
    if not evidence_path.exists():
        raise RuntimeError(f"Missing Epoch site-evidence artifact: {evidence_path}")
    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    records = payload.get("records")
    if not isinstance(records, list):
        raise RuntimeError("Epoch site-evidence artifact has no records array")
    expected_count = len(expected_epoch_ids)
    if payload.get("record_count") != expected_count:
        raise RuntimeError(
            f"Epoch site-evidence record_count mismatch: {payload.get('record_count')!r} (expected {expected_count})"
        )
    if len(records) != expected_count:
        raise RuntimeError(
            f"Epoch site-evidence row count mismatch: {len(records)} (expected {expected_count})"
        )
    evidence_ids = {str(r.get("epoch_id") or "") for r in records}
    if evidence_ids != expected_epoch_ids:
        missing = sorted(expected_epoch_ids - evidence_ids)
        extra = sorted(evidence_ids - expected_epoch_ids)
        raise RuntimeError(
            f"Epoch site-evidence IDs do not match fresh Epoch dataset (missing={missing[:5]}, extra={extra[:5]})"
        )
    summary = payload.get("summary") or {}
    if summary.get("total") != expected_count:
        raise RuntimeError(
            f"Epoch site-evidence summary.total mismatch: {summary.get('total')!r} (expected {expected_count})"
        )
    return {
        "record_count": expected_count,
        "evidence_found": int(summary.get("evidence_found", 0) or 0),
        "site_queue_ids": int(summary.get("site_queue_ids", 0) or 0),
        "pending": int(summary.get("pending", 0) or 0),
    }


ENRICHMENT_PATH = ROOT / "data" / "track3" / "public_web_enrichment_2026-09-27.json"


def load_public_enrichment() -> dict[str, list[dict[str, Any]]]:
    if not ENRICHMENT_PATH.exists():
        return {}
    payload = json.loads(ENRICHMENT_PATH.read_text(encoding="utf-8"))
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in payload.get("records", []):
        eid = str(row.get("epoch_id") or "").strip()
        if eid:
            grouped.setdefault(eid, []).append(row)
    return grouped


def merge_public_enrichment(normalized: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Fill safe publisher fields from explicit public-source captures without overwriting raw Epoch data."""
    out = dict(normalized)
    provenance = list(out.get("public_enrichment") or [])
    safe_fields = {"project", "address", "owner", "users", "construction_companies", "energy_companies"}
    strict_investor = []

    def as_values(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        text = str(value).strip()
        return [text] if text else []

    def merge_value(field: str, value: Any) -> None:
        vals = as_values(value)
        if not vals:
            return
        # Enrichment is additive provenance. It fills an empty canonical field,
        # but it never rewrites or concatenates an existing Epoch value.
        current = as_values(out.get(field))
        if not current:
            out[field] = vals[0] if len(vals) == 1 else ", ".join(dict.fromkeys(vals))


    for row in rows:
        field = str(row.get("field") or "").strip()
        scope_note = str(row.get("scope_note") or "").lower()
        relationship = str(row.get("relationship") or "").lower()
        if field == "investors":
            if ("project-specific" in scope_note or "project specific" in scope_note) and "not project-specific" not in scope_note and "not project specific" not in scope_note:
                strict_investor.append(row)
            continue
        if field not in safe_fields:
            continue
        merge_value(field, row.get("value"))
        provenance.append({
            "field": field,
            "value": row.get("value"),
            "relationship": row.get("relationship"),
            "source": row.get("source"),
            "source_urls": row.get("source_urls") or [],
            "publication_date": row.get("publication_date"),
            "capture_date": row.get("capture_date"),
            "evidence_id": row.get("evidence_id"),
            "scope_note": row.get("scope_note"),
        })

    for row in strict_investor:
        merge_value("investors", row.get("value"))
        provenance.append({
            "field": "investors",
            "value": row.get("value"),
            "relationship": row.get("relationship"),
            "source": row.get("source"),
            "source_urls": row.get("source_urls") or [],
            "publication_date": row.get("publication_date"),
            "capture_date": row.get("capture_date"),
            "evidence_id": row.get("evidence_id"),
            "scope_note": row.get("scope_note"),
        })

    # De-duplicate provenance deterministically.
    seen = set()
    deduped = []
    for item in provenance:
        key = json.dumps(item, sort_keys=True, ensure_ascii=False)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    if deduped:
        out["public_enrichment"] = deduped
    return out


def selftest() -> None:
    assert norm("OpenAI Stargate Abilene, TX") == "openai stargate abilene tx"
    assert tokens("OpenAI Stargate Abilene") >= {"openai", "stargate", "abilene"}
    assert infer_region("5502 Spinks Rd, Abilene, TX 79601", "United States") == "TX"
    assert infer_region("5475 Cloud Ct, Lincoln, NE 68514", "United States") == "NE"
    assert infer_region("1600 Pennsylvania Ave NW, Washington, DC 20500", "United States") == "DC"
    rows = [{"id":"1670","rto":"NYISO","st":"NY","co":"Niagara","proj":"Lake Mariner Data II","dev":"Lake Mariner Data LLC","poi":"Kintigh 345kV"}]
    ep = {"name":"Anthropic Lake Mariner","owner":"Anthropic","users":"Anthropic","address":"Barker, NY","country":"United States"}
    assert conservative_matches(ep, rows, {"anthropic lake mariner":{"registry_ids":["1670"],"relationship":"same_phase","match_confidence":"high","match_basis":"Known NYISO Lake Mariner cross-check."}})[0]["queue_id"] == "1670"
    assert not conservative_matches({"name":"Google Columbus","owner":"Google","users":"Google","address":"Columbus, OH","country":"United States"}, rows, {})
    sample = {"project": "", "energy_companies": "", "investors": ""}
    merged = merge_public_enrichment(sample, [
        {"field":"project","value":"Demo Project","scope_note":"official project identity"},
        {"field":"energy_companies","value":["Utility A","Utility B"],"scope_note":"site utility"},
        {"field":"investors","value":["Company-level investor"],"relationship":"corporate financing context","scope_note":"not project-specific"},
        {"field":"investors","value":["Project Financier"],"relationship":"project-specific financing","scope_note":"project-specific investor"},
    ])
    assert merged["project"] == "Demo Project"
    assert merged["energy_companies"] == "Utility A, Utility B"
    assert merged["investors"] == "Project Financier"
    # The committed evidence artifact must remain a 1:1, 93-site layer.
    payload = json.loads((OUT / "site_level_connection_evidence.json").read_text(encoding="utf-8"))
    expected_ids = {str(r.get("epoch_id") or "") for r in payload.get("records", [])}
    validate_site_evidence(expected_ids)
    print("selftest: 6 checks passed")


def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent":"Continental-Load-Registry/2.4 (research)"})
    with urllib.request.urlopen(req, timeout=60) as resp, dest.open("wb") as f:
        shutil.copyfileobj(resp, f)


def sync() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    with tempfile.TemporaryDirectory(prefix="epoch-ai-") as tmp_s:
        tmp = Path(tmp_s)
        for filename, url in URLS.items():
            download(url, tmp / filename)
        for filename, url in EXTERNAL_URLS.items():
            download(url, tmp / filename)

        centers = load_csv(tmp / "data_centers.csv")
        timelines = load_csv(tmp / "data_center_timelines.csv")
        chips = load_csv(tmp / "data_centers_chip_quantities.csv")
        if len(centers) != 93:
            raise RuntimeError(f"Epoch AI data_centers.csv row count changed unexpectedly: {len(centers)} (expected 93)")
        if not centers or not pick(centers[0], ALIASES["name"]):
            raise RuntimeError("Epoch AI data centers dataset has no recognizable Name field")

        for filename in {**URLS, **EXTERNAL_URLS}:
            shutil.copy2(tmp / filename, OUT / filename)

        # Mark the cataloged external source snapshots as ingested only after
        # their bytes have successfully been downloaded and copied.
        stack_path = ROOT / "data" / "track3_source_stack.json"
        if stack_path.exists():
            stack = json.loads(stack_path.read_text(encoding="utf-8"))
            snapshot_ids = {
                "epoch-chip-sales": "ai_chip_sales_",
                "epoch-chip-owners": "ai_chip_owners_",
                "epoch-chip-users": "ai_chip_users_",
                "epoch-chillers": "data_center_chillers.csv",
                "epoch-cooling-towers": "data_center_cooling_towers.csv",
            }
            for source in stack.get("sources", []):
                sid = source.get("id")
                marker = snapshot_ids.get(sid)
                if marker and any(name.startswith(marker) or name == marker for name in EXTERNAL_URLS):
                    source["status"] = "INGESTED_SNAPSHOT"
                    source["capture_on"] = today
            stack_path.write_text(json.dumps(stack, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        timeline_by_center: dict[str, list[dict[str, str]]] = {}
        for row in timelines:
            key = norm(pick(row, TIMELINE_ALIASES["data_center"]))
            if key:
                timeline_by_center.setdefault(key, []).append(row)
        chip_by_center: dict[str, list[dict[str, str]]] = {}
        for row in chips:
            key = norm(pick(row, CHIP_ALIASES["data_center"]))
            if key:
                chip_by_center.setdefault(key, []).append(row)

        registry = parse_registry()
        public_enrichment_by_id = load_public_enrichment()
        overrides = load_overrides()
        expected_epoch_ids = {
            "EPOCH-" + hashlib.sha256(
                (str(pick(row, ALIASES["name"]) or "") + "|" +
                 str(pick(row, ALIASES["address"]) or "") + "|" +
                 str(pick(row, ALIASES["country"]) or "")).encode("utf-8")
            ).hexdigest()[:16]
            for row in centers
        }
        records = []
        crosswalk_rows = []

        for row in centers:
            name = pick(row, ALIASES["name"]) or ""
            country = pick(row, ALIASES["country"]) or ""
            address = pick(row, ALIASES["address"]) or ""
            epoch_id = "EPOCH-" + hashlib.sha256((str(name)+"|"+str(address)+"|"+str(country)).encode("utf-8")).hexdigest()[:16]
            tl = timeline_by_center.get(norm(name), [])
            tl_sorted = sorted(tl, key=lambda x: str(pick(x, TIMELINE_ALIASES["date"]) or ""))
            latest = tl_sorted[-1] if tl_sorted else None
            latest_chips = {}
            for cr in sorted(chip_by_center.get(norm(name), []), key=lambda x: str(pick(x, CHIP_ALIASES["date"]) or "")):
                ct = str(pick(cr, CHIP_ALIASES["chip_type"]) or "")
                if ct:
                    latest_chips[ct] = {
                        "chip_type": ct,
                        "date": pick(cr, CHIP_ALIASES["date"]),
                        "number_units": numeric(pick(cr, CHIP_ALIASES["number_units"])),
                        "chip_type_source": pick(cr, CHIP_ALIASES["chip_type_source"]),
                        "number_units_source": pick(cr, CHIP_ALIASES["number_units_source"]),
                        "owner": pick(cr, CHIP_ALIASES["owner"]),
                        "user": pick(cr, CHIP_ALIASES["user"]),
                    }

            normalized = {
                "epoch_id": epoch_id,
                "name": name,
                "country": country,
                "address": address,
                "region_inferred_from_address": infer_region(str(address), str(country)),
                "owner": pick(row, ALIASES["owner"]),
                "users": pick(row, ALIASES["users"]),
                "project": pick(row, ALIASES["project"]),
                "current_h100_equivalents": numeric(pick(row, ALIASES["current_h100_eq"])),
                "current_power_mw": numeric(pick(row, ALIASES["current_power_mw"])),
                "current_total_capital_cost_b_2025": numeric(pick(row, ALIASES["current_capital_cost_b"])),
                "selected_sources": pick(row, ALIASES["selected_sources"]),
                "calculations_sheet": pick(row, ALIASES["calculations_sheet"]),
                "investors": pick(row, ALIASES["investors"]),
                "construction_companies": pick(row, ALIASES["construction_companies"]),
                "energy_companies": pick(row, ALIASES["energy_companies"]),
                "latest_timeline": None,
                "latest_chip_quantities": list(latest_chips.values()),
            }
            normalized = merge_public_enrichment(normalized, public_enrichment_by_id.get(epoch_id, []))
            if latest:
                normalized["latest_timeline"] = {k: (numeric(pick(latest, aliases)) if k not in {"data_center","date","construction_status"} else pick(latest, aliases))
                    for k, aliases in TIMELINE_ALIASES.items()}

            epoch_obj = {
                "epoch_id": epoch_id,
                "normalized": normalized,
                "raw": row,
                "timeline_record_count": len(tl),
                "chip_quantity_record_count": len(chip_by_center.get(norm(name), [])),
                "source": {
                    "publisher": "Epoch AI",
                    "dataset": "AI data centers",
                    "dataset_url": URLS["data_centers.csv"],
                    "timelines_url": URLS["data_center_timelines.csv"],
                    "chip_quantities_url": URLS["data_centers_chip_quantities.csv"],
                    "accessed_on": today,
                    "license": "Creative Commons Attribution 4.0",
                },
            }
            matches = conservative_matches(normalized, registry, overrides)
            if matches:
                crosswalk_status = "matched_or_candidate"
                crosswalk_reason = "One or more conservative registry IDs were identified; inspect relationship and confidence."
            elif norm(country) not in {"united states", "usa", "us", "canada"}:
                crosswalk_status = "outside_registry_geographic_scope"
                crosswalk_reason = "Epoch site is outside the United States/Canada geographic scope of this queue registry."
            else:
                crosswalk_status = "no_direct_match"
                crosswalk_reason = "No conservative direct match was identified in the current nine-market queue registry fields."
            epoch_obj["registry_crosswalk"] = matches
            epoch_obj["registry_crosswalk_status"] = crosswalk_status
            epoch_obj["registry_crosswalk_reason"] = crosswalk_reason
            records.append(epoch_obj)
            crosswalk_rows.append({
                "epoch_id": epoch_id,
                "epoch_name": name,
                "epoch_country": country,
                "epoch_address": address,
                "registry_match_count": len(matches),
                "registry_queue_ids": ";".join(m["queue_id"] for m in matches),
                "crosswalk_status": crosswalk_status,
                "crosswalk_reason": crosswalk_reason,
                "relationship": ";".join(m["relationship"] for m in matches),
                "match_confidence": ";".join(m["match_confidence"] for m in matches),
                "match_basis": " | ".join(m["match_basis"] for m in matches),
            })

        # Validate the independent evidence artifact before publishing the refreshed
        # Epoch registry/crosswalk. A mismatch is a hard error rather than a
        # dashboard-visible partial import.
        evidence_summary = validate_site_evidence(expected_epoch_ids)

        (OUT / "registry.json").write_text(json.dumps({
            "schema_version": 1,
            "record_count": len(records),
            "source": {"publisher":"Epoch AI","dataset":"AI data centers","accessed_on":today,"data_centers_updated":"2026-09-24",
                       "data_centers_url":URLS["data_centers.csv"],"timelines_url":URLS["data_center_timelines.csv"],
                       "chip_quantities_url":URLS["data_centers_chip_quantities.csv"],
                       "license":"Creative Commons Attribution 4.0",
                       "raw_sha256": {name: sha256(OUT/name) for name in {**URLS, **EXTERNAL_URLS}},
                       "external_raw_sha256": {name: sha256(OUT/name) for name in EXTERNAL_URLS}},
            "records": records
        }, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")

        with (OUT / "crosswalk.csv").open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(crosswalk_rows[0].keys()))
            writer.writeheader()
            writer.writerows(crosswalk_rows)

        manifest = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "epoch_dataset_updated": "2026-09-24",
            "record_count": len(records),
            "timeline_record_count": len(timelines),
            "chip_quantity_record_count": len(chips),
            "current_registry_record_count": len(registry),
            "matched_epoch_records": sum(1 for r in records if r["registry_crosswalk"]),
            "no_direct_match_epoch_records": sum(1 for r in records if r["registry_crosswalk_status"] == "no_direct_match"),
            "outside_registry_geographic_scope_epoch_records": sum(1 for r in records if r["registry_crosswalk_status"] == "outside_registry_geographic_scope"),
            "manual_override_count": len(overrides),
            "site_evidence": evidence_summary,
            "raw_files": {name: {"url": {**URLS, **EXTERNAL_URLS}[name], "sha256": sha256(OUT/name), "bytes": (OUT/name).stat().st_size} for name in {**URLS, **EXTERNAL_URLS}},
            "external_raw_files": {name: {"url": EXTERNAL_URLS[name], "sha256": sha256(OUT/name), "bytes": (OUT/name).stat().st_size} for name in EXTERNAL_URLS},
            "method": "Raw Epoch rows preserved; normalized fields joined to latest available timeline and chip records; registry matching is conservative and does not overwrite queue facts."
        }
        (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")

        print(f"synced Epoch AI: {len(records)} data centers, {len(timelines)} timeline rows, {len(chips)} chip-quantity rows")
        print(f"crosswalk: {manifest['matched_epoch_records']} of {len(records)} Epoch records have one or more conservative registry matches")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--sync", action="store_true")
    args = ap.parse_args()
    if not args.selftest and not args.sync:
        ap.error("choose --selftest or --sync")
    if args.selftest:
        selftest()
    if args.sync:
        sync()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
