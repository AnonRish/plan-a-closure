#!/usr/bin/env python3
"""Fail CI when canonical registry counts drift across public artifacts."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load(rel: str):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))


def assert_close(a: float, b: float, eps: float = 1e-6):
    assert abs(float(a) - float(b)) <= eps, f"{a!r} != {b!r}"


def parse_registry_from_index() -> tuple[list[dict], float]:
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    m = re.search(r"const REGISTRY_DATA = (\[.*?\]);\n\nconst FILINGS =", html, flags=re.S)
    assert m, "REGISTRY_DATA block not found"
    rows = json.loads(m.group(1))
    total_mw = sum(float(r["mw"]) for r in rows)
    return rows, total_mw


def main() -> None:
    rows, total_mw = parse_registry_from_index()
    row_count = len(rows)
    capacity_gw = total_mw / 1000.0

    scope = load("data/large_load_scope.json")["definitions"]
    assert scope["current_row_level"]["records"] == row_count
    assert_close(scope["current_row_level"]["capacity_gw"], capacity_gw)
    assert scope["expanded_known_scope"]["records"] == 1623
    assert_close(scope["expanded_known_scope"]["capacity_gw"], 394.6181)

    shard = load("data/facility_records/index.json")
    assert shard["record_count"] == row_count
    assert shard["record_count"] == sum(shard["rto_counts"].values())

    manifest = load("data/map_layer_manifest.json")
    layers = {x["id"]: x for x in manifest["layers"]}
    assert layers["CORE_REGISTRY"]["records"] == row_count
    assert layers["CORE_REGISTRY"]["mapped_records"] == row_count
    assert layers["PROJECT_LEVEL"]["records"] == 271
    assert layers["PROJECT_LEVEL"]["mapped_records"] == 271
    assert layers["EPOCH_AI"]["records"] == 93
    assert layers["CONNECTION_TARGETS"]["records"] == 93
    assert layers["NYISO_COMPLETE_QUEUE"]["status"].startswith("snapshot not currently present")

    queue_status = load("data/queue_layer_status.json")
    feeds = {x["id"]: x for x in queue_status["feeds"]}
    # Queue counts change on every sync, so compare the artifacts with each other and
    # with the snapshot they describe instead of with a literal.
    for layer_id, feed_id in (
        ("MISO_COMPLETE_QUEUE", "MISO"),
        ("SPP_ACTIVE_QUEUE", "SPP"),
        ("CAISO_COMPLETE_QUEUE", "CAISO"),
        ("PJM_CYCLE_QUEUE", "PJM"),
    ):
        feed = feeds[feed_id]
        assert feed["snapshot_present"] is True, f"{feed_id}: snapshot missing"
        assert layers[layer_id]["records"] == feed["record_count"], (
            f"{layer_id}: map_layer_manifest says {layers[layer_id]['records']}, "
            f"queue_layer_status says {feed['record_count']}"
        )
        assert load(feed["snapshot"])["record_count"] == feed["record_count"], (
            f"{feed_id}: queue_layer_status disagrees with {feed['snapshot']}"
        )
    assert feeds["NYISO"]["snapshot_present"] is False

    catalog = load("data/public_data_catalog.json")
    cat = {d["path"]: d for d in catalog["datasets"]}
    scope_cat = cat["data/large_load_scope.json"]
    assert scope_cat["record_count"] == 1623
    assert scope_cat["core_record_count"] == row_count
    assert scope_cat["expanded_known_record_count"] == 1623
    assert_close(scope_cat["expanded_known_capacity_gw"], 394.6181)
    evidence_catalog_count = int(cat["data/track3/evidence_records.json"]["record_count"])
    assert evidence_catalog_count > 0
    assert cat["data/epoch_site_evidence_records.json"]["record_count"] == 102
    bpa = load("data/bpa_large_load_registry.json")
    bpa_count = bpa["record_count"]
    bpa_mapped = bpa["mapped_record_count"]
    bpa_threshold = float(bpa.get("threshold_mw", 0))
    assert bpa_threshold == 100.0
    assert bpa_count == len(bpa["records"]) > 0
    assert bpa["unmapped_record_count"] == bpa_count - bpa_mapped
    assert bpa_mapped == sum(1 for x in bpa["records"] if isinstance(x.get("map_point"), list) and len(x["map_point"]) == 2)
    assert all(
        str(x.get("id","")).startswith("BPA-")
        and x.get("capacity_claims")
        and float(x["capacity_claims"][0].get("value_mw", 0)) >= bpa_threshold
        for x in bpa["records"]
    )
    bpa_population = bpa.get("source", {}).get("source_population_accounting", {})
    assert int(bpa_population.get("eligible_rows_at_threshold_mw", -1)) == bpa_count
    assert int(bpa_population.get("raw_l_series_rows_on_record", -1)) >= bpa_count
    assert cat["data/bpa_large_load_registry.json"]["record_count"] == bpa_count
    assert cat["data/bpa_large_load_registry.csv"]["record_count"] == bpa_count
    assert cat["data/project_level_extractions.json"]["record_count"] == 271
    assert cat["data/supplemental_large_load_evidence.json"]["record_count"] == 61
    assert cat["data/supplemental_aggregate_map.json"]["record_count"] == 66
    assert cat["data/global_compute_universe_sources_2026-09-27.json"]["record_count"] == 3
    missing = [d["path"] for d in catalog["datasets"] if not (ROOT / d["path"]).exists()]
    assert not missing, f"public_data_catalog.json lists files that are not in the repository: {missing}"

    backlog = load("data/track3/research_backlog_summary.json")
    sweep = load("data/track3/site_missing_information_sweep_2026-09-27.json")
    assert backlog["publisher_tasks"] == sweep["summary"]["effective_unresolved_publisher_fields"]
    assert backlog["domain_tasks"] == sweep["summary"]["open_track3_domain_cells"]
    assert backlog["total_tasks"] == backlog["publisher_tasks"] + backlog["domain_tasks"]
    assert backlog["sites"] == 93

    summary = load("data/track3/summary.json")
    observation = load("data/track3/observation_queue.json")
    assert len(observation["tasks"]) == summary["observation_task_count"] == sum(summary["observation_task_counts_by_domain"].values())
    assert set(observation["tasks"][0].keys()) >= {"task_id","epoch_id","domain","current_state","priority"}
    assert summary["epoch_site_count"] == 93
    evidence_ledger = load("data/track3/evidence_records.json")
    assert summary["track3_evidence_record_count"] == evidence_ledger["record_count"]
    assert evidence_catalog_count == evidence_ledger["record_count"]
    rs=json.loads((ROOT / "data/track3/remote_sensing_observations.json").read_text(encoding="utf-8"))
    assert summary["remote_sensing_derived_observation_count"] == rs["derived_observation_count"] == len(rs["records"])
    assert summary["transformer_event_count"] == 3
    enrich=load("data/track3/public_web_enrichment_2026-09-27.json")
    assert summary["public_web_evidence_record_count"] == enrich["record_count"]
    assert summary["public_web_evidence_site_count"] == enrich["accounting"]["sites_with_findings"] == 93

    coverage = load("data/global_ai_datacenter_coverage_2026-09-27.json")
    epoch = coverage["epoch_capture"]
    assert epoch["current_explorer_records"] == 93
    assert epoch["current_explorer_status"] == "100_PERCENT_OF_CURRENT_EPOCH_EXPLORER"
    assert coverage["candidate_record_count"] == len(coverage["candidate_records"]) == 33
    assert len(coverage["discovery_universes"]) == 4
    assert len(coverage["owner_coverage"]) == 9

    html = (ROOT / "index.html").read_text(encoding="utf-8")
    stale_fragments = (
        "986 open research tasks",
        "274 publisher-field gaps",
        "712 Track 3 domain cells",
        "<b>219</b><span>Track 3 observation tasks",
        'id="mapInventoryProjectCount">253',
        'id="mapInventoryMappedCount">253',
    )
    for fragment in stale_fragments:
        assert fragment not in html, f"stale homepage fragment: {fragment}"

    openapi_text = (ROOT / "api/v1/openapi.json").read_text(encoding="utf-8")
    assert "1,558" not in openapi_text

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "1,558 row-level facilities" not in readme
    assert "361.875 GW" not in readme
    assert "1,641 requests / records and 397.775 GW" not in readme
    assert "1,558-row core" not in readme
    assert "252 mapped project-level records" not in readme
    assert "63 aggregate utility/regulatory and historical-queue footprints" not in readme

    layers_md = (ROOT / "DATA_LAYERS.md").read_text(encoding="utf-8")
    assert "1,558 records / 361.875 GW" not in layers_md
    assert "1,641 records / 397.775 GW" not in layers_md
    assert "**199 / 199** project records plotted" not in layers_md
    assert "**61** aggregate/historical footprints" not in layers_md

    sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    for page in ("research.html", "api.html", "bulk-download.html", "global-compute-universe.html"):
        assert page in sitemap

    # CSV parity for the updated map manifest.
    with (ROOT / "data/map_layer_manifest.csv").open(encoding="utf-8", newline="") as fh:
        csv_layers = {r["id"]: r for r in csv.DictReader(fh)}
    assert csv_layers["CORE_REGISTRY"]["records"] == "1540"
    assert csv_layers["CORE_REGISTRY"]["mapped_records"] == "1540"
    assert csv_layers["CAISO_COMPLETE_QUEUE"]["records"] == "2278"
    assert csv_layers["PJM_CYCLE_QUEUE"]["records"] == "9263"

    print("PASS: canonical cross-artifact consistency")
    print(f"core rows={row_count} capacity_gw={capacity_gw:.4f}")
    print("Epoch explorer=93/93; candidates=33; research backlog=" + str(backlog["total_tasks"]) + "; observation tasks=" + str(summary["observation_task_count"]))


if __name__ == "__main__":
    main()
