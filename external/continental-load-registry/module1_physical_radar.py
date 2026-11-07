#!/usr/bin/env python3
"""Validate and summarize Module 1: the Multi-Modal Physical Radar.

This script is deliberately evidence-conservative:
- it validates the existing 9-market registry rather than pretending it is a
  complete utility/load census;
- it computes the requested three-scenario physical bound for every row;
- it verifies the status and entity-resolution invariants in source code;
- it treats missing voltage, remote-sensing telemetry, and transformer evidence
  as UNKNOWN/NOT_INGESTED instead of converting absence into PASS.

Usage:
  python module1_physical_radar.py --selftest
  python module1_physical_radar.py --audit
  python module1_physical_radar.py --selftest --audit
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
INDEX = ROOT / "index.html"
SPEC = ROOT / "data" / "module1_radar_spec.json"
EPOCH_REGISTRY = ROOT / "data" / "external" / "epoch_ai" / "registry.json"
EPOCH_EVIDENCE = ROOT / "data" / "external" / "epoch_ai" / "site_level_connection_evidence.json"
INGEST = ROOT / "ingest_grid_queues.py"
COMPUTE = ROOT / "compute_anomaly_detector.py"
OUTPUT = ROOT / "data" / "module1_radar_summary.json"

EXPECTED_RTOs = ["PJM", "ERCOT", "SPP", "MISO", "CAISO", "NYISO", "ISO-NE", "IESO", "AESO"]
THRESHOLD_FLOPS = 1.0e26
# 1,979 is the H100 SXM FP16/BF16 peak WITH 2:4 sparsity; dense is 989.5 (see dense_sensitivity()).
H100_TFLOPS = 1979.0
H100_TFLOPS_DENSE = 989.5
RUN_SECONDS = 90 * 86400

SCENARIOS = {
    "reference": {"pue": 1.25, "rack_kw": 35.0, "mfu": 0.40},
    "conservative": {"pue": 1.40, "rack_kw": 20.0, "mfu": 0.25},
    "aggressive": {"pue": 1.15, "rack_kw": 50.0, "mfu": 0.50},
}


def load_registry() -> list[dict[str, Any]]:
    html = INDEX.read_text(encoding="utf-8")
    match = re.search(r"const REGISTRY_DATA = (\[.*?\]);\s*\n\s*const FILINGS", html, re.S)
    if not match:
        raise RuntimeError("REGISTRY_DATA array not found in index.html")
    rows = json.loads(match.group(1))
    if not isinstance(rows, list):
        raise RuntimeError("REGISTRY_DATA is not a list")
    return rows


def parse_voltage_kv(poi: Any) -> float | None:
    values = [
        float(x)
        for x in re.findall(r"(?<![\d.])(\d+(?:\.\d+)?)\s*kV\b", str(poi or ""), re.I)
    ]
    return max(values) if values else None


def compute_scenario(capacity_mw: float, pue: float, rack_kw: float, mfu: float, tflops: float | None = None) -> dict[str, float]:
    it_kw = capacity_mw * 1000.0 / pue
    racks = it_kw / rack_kw
    gpus = racks * 8.0
    chip_tflops = H100_TFLOPS if tflops is None else tflops
    flops = gpus * (chip_tflops * 1.0e12) * RUN_SECONDS * mfu
    return {"it_kw": it_kw, "racks": racks, "gpus": gpus, "flops_90d": flops}


def dense_sensitivity() -> dict[str, Any]:
    """The same three scenarios at the dense FP16/BF16 peak instead of the with-sparsity peak."""
    at_100 = {name: compute_scenario(100.0, tflops=H100_TFLOPS_DENSE, **values)["flops_90d"] for name, values in SCENARIOS.items()}
    needed = {name: 100.0 * THRESHOLD_FLOPS / flops for name, flops in at_100.items()}
    return {
        "chip_tflops": H100_TFLOPS_DENSE,
        "basis": "H100 SXM FP16/BF16 dense peak; the 1,979 baseline is the same chip with 2:4 structured sparsity",
        "flops_90d_at_100mw": at_100,
        "clears_1e26_at_100mw_all_scenarios": all(v >= THRESHOLD_FLOPS for v in at_100.values()),
        "capacity_mw_needed_to_clear_1e26": needed,
        "capacity_mw_needed_all_scenarios": max(needed.values()),
    }


def physical_row(row: dict[str, Any]) -> dict[str, Any]:
    mw = float(row.get("mw") or 0.0)
    kv = parse_voltage_kv(row.get("poi"))
    scenarios = {name: compute_scenario(mw, **values) for name, values in SCENARIOS.items()}
    if mw < 100.0:
        electrical_gate = "FAIL"
    elif kv is None:
        electrical_gate = "UNKNOWN"
    elif kv >= 115.0:
        electrical_gate = "PASS"
    else:
        electrical_gate = "FAIL"
    clears_all = all(v["flops_90d"] >= THRESHOLD_FLOPS for v in scenarios.values())
    return {
        "queue_id": str(row.get("id") or ""),
        "rto": row.get("rto"),
        "state": row.get("st"),
        "county": row.get("co"),
        "capacity_mw": mw,
        "voltage_kv": kv,
        "electrical_capacity_pass": mw >= 100.0,
        "electrical_voltage_pass": kv is not None and kv >= 115.0,
        "electrical_gate": electrical_gate,
        "module1_tier": (
            "Tier 3: Confirmed Grid-Scale Storage (BESS)"
            if row.get("tier") == "Confirmed Grid-Scale Storage (BESS)"
            else "Tier 1: Confirmed Hyperscaler"
            if row.get("ent") == "Confirmed Hyperscaler"
            else "Tier 2: Wholesale Colocation Developer"
            if row.get("ent") == "Wholesale Colocation Developer"
            else "Tier 4: Genuinely Ambiguous / Unclassified Large Load"
        ),
        "reference_gpus": round(scenarios["reference"]["gpus"]),
        "flops_90d_reference": scenarios["reference"]["flops_90d"],
        "flops_90d_conservative": scenarios["conservative"]["flops_90d"],
        "flops_90d_aggressive": scenarios["aggressive"]["flops_90d"],
        "clears_1e26_flops_all_scenarios": clears_all,
        "heat_rejection_mw": mw,
        "water_l_day_low": mw * 1000.0 * 24.0 * 1.5,
        "water_l_day_high": mw * 1000.0 * 24.0 * 3.0,
        "review_priority": bool(row.get("flag")),
    }


def validate_epoch() -> dict[str, Any]:
    registry = json.loads(EPOCH_REGISTRY.read_text(encoding="utf-8"))
    evidence = json.loads(EPOCH_EVIDENCE.read_text(encoding="utf-8"))
    if registry.get("record_count") != 93 or len(registry.get("records", [])) != 93:
        raise AssertionError("Epoch registry must contain exactly 93 records")
    if evidence.get("record_count") != 93 or len(evidence.get("records", [])) != 93:
        raise AssertionError("Epoch evidence layer must contain exactly 93 records")
    reg_ids = {r.get("epoch_id") for r in registry["records"]}
    ev_ids = {r.get("epoch_id") for r in evidence["records"]}
    if reg_ids != ev_ids:
        raise AssertionError("Epoch registry/evidence IDs do not match exactly")
    if evidence.get("summary", {}).get("total") != 93:
        raise AssertionError("Epoch evidence summary.total must equal 93")
    return {
        "record_count": 93,
        "site_level_evidence_count": int(evidence.get("summary", {}).get("evidence_found", 0)),
        "site_specific_queue_ids": int(evidence.get("summary", {}).get("site_queue_ids", 0)),
        "pending_site_specific_search": int(evidence.get("summary", {}).get("pending", 0)),
    }


def validate_source_invariants() -> None:
    ingest = INGEST.read_text(encoding="utf-8")
    compute = COMPUTE.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")

    status_start = ingest.find("def classify_status")
    status_end = ingest.find("_OTHER_KEYWORD_RE", status_start)
    status_block = ingest[status_start:status_end if status_end >= 0 else None]
    reject_pos = status_block.find("reject_patterns =")
    active_pos = status_block.find("fuzzy_map =")
    inactive_pos = status_block.find('r"\\bINACTIVE\\b"')
    if reject_pos < 0 or inactive_pos < 0 or active_pos < 0 or not reject_pos < active_pos or not inactive_pos < active_pos:
        raise AssertionError("Status exclusion gate or INACTIVE guard is not placed before accept matching")

    if "_OTHER_KEYWORD_RE = re.compile(r\"\\bother\\b(?!\\s+than)\")" not in ingest:
        raise AssertionError("Missing OTHER-THAN regex guard")

    if "fuzz.WRatio" not in compute or "FUZZY_MATCH_THRESHOLD = 88.0" not in compute or "FUZZY_GRAY_ZONE_FLOOR = 70.0" not in compute:
        raise AssertionError("RapidFuzz WRatio thresholds are not enforced")

    if "Math.max(5.0,Math.sqrt(r.mw)*0.35)" not in index:
        raise AssertionError("Ambiguous marker radius invariant is not implemented")
    if "kind==='bess'?3.0" not in index:
        raise AssertionError("BESS radius invariant is not implemented")
    if "kind==='bess'?0.35" not in index:
        raise AssertionError("BESS opacity invariant is not implemented")
    if "window.refreshRegistryMap" not in index:
        raise AssertionError("Map/table synchronization hook is missing")


def build_summary(rows: list[dict[str, Any]], epoch: dict[str, Any]) -> dict[str, Any]:
    evaluations = [physical_row(r) for r in rows]
    tier_counts: dict[str, int] = {}
    for e in evaluations:
        tier_counts[e["module1_tier"]] = tier_counts.get(e["module1_tier"], 0) + 1

    explicit_voltage = [e for e in evaluations if e["voltage_kv"] is not None]
    voltage_pass = [e for e in explicit_voltage if e["voltage_kv"] >= 115.0]
    voltage_fail = [e for e in explicit_voltage if e["voltage_kv"] < 115.0]
    total_mw = sum(e["capacity_mw"] for e in evaluations)

    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "as_of": "2026-09-26",
        "module": "Module 1: Multi-Modal Physical Radar",
        "registry_record_count": len(rows),
        "registry_capacity_mw": total_mw,
        "domains": {
            "domain_1_physics": {
                "capacity_floor_pass_count": sum(e["electrical_capacity_pass"] for e in evaluations),
                "voltage_explicit_count": len(explicit_voltage),
                "voltage_pass_count": len(voltage_pass),
                "voltage_fail_count": len(voltage_fail),
                "voltage_unknown_count": len(evaluations) - len(explicit_voltage),
                "all_scenarios_1e26_pass_count": sum(e["clears_1e26_flops_all_scenarios"] for e in evaluations),
                "dense_fp16_bf16_sensitivity": dense_sensitivity(),
                "heat_signature_is_computable_from_capacity": True,
                "site_specific_cooling_telemetry_ingested": False
            },
            "domain_2_ingestion": {
                "required_market_count": len(EXPECTED_RTOs),
                "present_market_count": len({r.get("rto") for r in rows}),
                "markets_present": sorted({r.get("rto") for r in rows}),
                "epoch": epoch,
                "satellite_tir_sar_numeric_status": "NOT_INGESTED",
                "transformer_supply_chain_status": "NOT_INGESTED"
            },
            "domain_3_entity_resolution": {
                "tier_counts": tier_counts,
                "review_priority_count": sum(1 for r in rows if r.get("flag")),
                "wratio_thresholds": {"auto_confirm": 88.0, "gray_zone_floor": 70.0},
                "storage_tier_isolated": True
            },
            "domain_4_interface": {
                "leaflet_map": True,
                "table_to_map_rto_sync": True,
                "ambiguous_radius_formula": "max(5.0, sqrt(capacity_mw) * 0.35)",
                "bess_radius_px": 3.0,
                "bess_opacity": 0.35,
                "country_and_state_boundaries": True
            },
            "domain_5_governance": {
                "references_documented": True,
                "rebuttable_presumption_status": "PROPOSED_RESEARCH_FRAMEWORK_ONLY",
                "ceii_to_bis_transfer_status": "PROPOSED_RESEARCH_PROTOCOL_ONLY"
            }
        },
        "five_domain_gate": "UNVERIFIED_PENDING_REMOTE_SENSING_AND_TRANSFORMER_EVIDENCE",
        "note": "The radar never treats a missing queue field, missing voltage, missing imagery, or missing procurement evidence as proof of absence. Queue capacity, Epoch IT power, and calculated FLOPs remain separate measurements."
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--audit", action="store_true")
    args = parser.parse_args()

    rows = load_registry()
    if not rows:
        raise SystemExit("No registry rows found")

    checks: list[tuple[str, bool]] = [
        ("registry has rows", len(rows) > 0),
        ("capacity floor is enforced in the current registry", all(float(r.get("mw") or 0) >= 100.0 for r in rows)),
        ("all nine required market labels are present", {r.get("rto") for r in rows} == set(EXPECTED_RTOs)),
        ("100 MW reference scenario is 1.125573778e26 FLOPs", math.isclose(compute_scenario(100.0, **SCENARIOS["reference"])["flops_90d"], 1.1255737782857143e26, rel_tol=1e-12, abs_tol=1e10)),
        ("100 MW conservative scenario is 1.099193142e26 FLOPs", math.isclose(compute_scenario(100.0, **SCENARIOS["conservative"])["flops_90d"], 1.099193142857143e26, rel_tol=1e-12, abs_tol=1e10)),
        ("100 MW aggressive scenario is 1.070518539e26 FLOPs", math.isclose(compute_scenario(100.0, **SCENARIOS["aggressive"])["flops_90d"], 1.070518539130435e26, rel_tol=1e-12, abs_tol=1e10)),
    ]

    for name, passed in checks:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")
    ok = all(passed for _, passed in checks)

    try:
        validate_epoch()
        validate_source_invariants()
        print("[PASS] Epoch 93-record integrity and source-code invariants")
        ok = ok and True
    except Exception as exc:
        print(f"[FAIL] {exc}")
        ok = False

    if args.audit:
        epoch = validate_epoch()
        summary = build_summary(rows, epoch)
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {OUTPUT}")

    print("ALL MODULE 1 CHECKS PASSED" if ok else "MODULE 1 CHECKS FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
