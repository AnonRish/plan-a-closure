#!/usr/bin/env python3
"""Acquire current building-footprint polygons around the 93 Epoch AI sites.

Acquisition revision: 2026-09-27-live-footprints-final

The output is deliberately a site-focused vector layer:
- current polygon geometry is retained as GeoJSON;
- source/provenance is retained in the site index;
- no building is treated as AI-specific solely because it overlaps a site buffer;
- temporal construction chronology remains a separate evidence layer.

Source: Overture Maps building theme, downloaded by bounding box.
"""

from __future__ import annotations

import json
import math
import re
import sys

import duckdb
import requests
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shapely.geometry import shape
from shapely.ops import transform
from pyproj import Transformer

from acquire_physical_verification import ensure_coordinates, load_json

ROOT = Path(__file__).resolve().parent
EPOCH_REGISTRY = ROOT / "data" / "external" / "epoch_ai" / "registry.json"
SITE_COORDS = ROOT / "data" / "track3" / "physical_site_coordinates.json"
OUT_DIR = ROOT / "data" / "track3" / "building_footprints"
INDEX_JSON = ROOT / "data" / "track3" / "building_footprints_index.json"
TMP_DIR = ROOT / ".tmp_building_footprints"

WGS84_TO_WEBM = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)


def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def bbox_for_site(lat: float, lon: float, radius_deg: float = 0.02) -> tuple[float, float, float, float]:
    return (
        lon - radius_deg,
        lat - radius_deg,
        lon + radius_deg,
        lat + radius_deg,
    )


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def geometry_area_m2(geom: Any) -> float | None:
    try:
        projected = transform(WGS84_TO_WEBM.transform, geom)
        return float(abs(projected.area))
    except Exception:
        return None


def latest_overture_release() -> str:
    fallback = "2026-09-23.1"
    try:
        response = requests.get("https://stac.overturemaps.org/catalog.json", timeout=30)
        response.raise_for_status()
        payload = response.json()
        raw = payload.get("latest")
        if isinstance(raw, str):
            match = re.search(r"\d{4}-\d{2}-\d{2}\.\d+", raw)
            if match:
                return match.group(0)
        text_blob = json.dumps(payload)
        candidates = re.findall(r"\d{4}-\d{2}-\d{2}\.\d+", text_blob)
        if candidates:
            return sorted(set(candidates))[-1]
    except Exception:
        pass
    return fallback

def download_site(site: dict[str, Any], coord: dict[str, Any], date_stamp: str, release: str, con: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    eid = str(site["epoch_id"])
    name = str(site["normalized"].get("name") or eid)
    lat = float(coord["lat"])
    lon = float(coord["lon"])
    bbox = bbox_for_site(lat, lon)
    tmp_path = TMP_DIR / f"{eid}.geojson"
    final_path = OUT_DIR / f"{eid}.geojson"

    try:
        parquet_glob = (
            f"s3://overturemaps-us-west-2/release/{release}/"
            "theme=buildings/type=building/*"
        )
        query = f"""
            SELECT id, ST_AsGeoJSON(geometry) AS geometry_json
            FROM read_parquet('{parquet_glob}', filename=true, hive_partitioning=1)
            WHERE bbox.xmin <= {bbox[2]}
              AND bbox.xmax >= {bbox[0]}
              AND bbox.ymin <= {bbox[3]}
              AND bbox.ymax >= {bbox[1]}
        """
        rows = con.execute(query).fetchall()
    except Exception as exc:
        raise RuntimeError(f"Overture GeoParquet query failed for {eid}: {exc}") from exc

    features = []
    for feature_id, geometry_json in rows:
        try:
            geometry = json.loads(geometry_json)
        except Exception:
            continue
        if not geometry:
            continue
        features.append({
            "type": "Feature",
            "id": str(feature_id) if feature_id is not None else None,
            "geometry": geometry,
            "properties": {},
        })
    kept = []
    total_area = 0.0
    for feature in features:
        geom_raw = feature.get("geometry")
        if not geom_raw:
            continue
        try:
            geom = shape(geom_raw)
        except Exception:
            continue
        if geom.is_empty:
            continue
        centroid = geom.centroid
        distance_km = haversine_km(lat, lon, centroid.y, centroid.x)
        if distance_km > 3.0:
            continue
        area_m2 = geometry_area_m2(geom)
        props = dict(feature.get("properties") or {})
        props.update({
            "epoch_id": eid,
            "site_name": name,
            "distance_to_site_km": round(distance_km, 4),
            "footprint_area_m2_webmercator": round(area_m2, 2) if area_m2 is not None else None,
            "source_dataset": "Overture Maps buildings",
            "source_url": "https://docs.overturemaps.org/getting-data/",
            "source_release": release,
            "source_accessed_on": date_stamp,
            "geometry_role": "current building-footprint polygon",
            "linkage_semantics": "Overlap/proximity only; not evidence that the building hosts AI compute.",
        })
        kept.append({
            "type": "Feature",
            "id": feature.get("id"),
            "geometry": geom.__geo_interface__,
            "properties": props,
        })
        if area_m2 is not None:
            total_area += area_m2

    out = {
        "type": "FeatureCollection",
        "source": {
            "dataset": "Overture Maps buildings",
            "url": "https://docs.overturemaps.org/getting-data/",
            "accessed_on": date_stamp,
            "release": release,
            "site_epoch_id": eid,
            "site_name": name,
            "site_latitude": lat,
            "site_longitude": lon,
            "search_bbox": list(bbox),
            "filter_radius_km": 3.0,
            "semantics": "Current building polygons are ingested for physical geometry. They are not, by themselves, AI-facility identity evidence or a construction time series.",
        },
        "features": kept,
    }
    save_json(final_path, out)
    return {
        "epoch_id": eid,
        "site_name": name,
        "status": "INGESTED_POLYGONIZED",
        "geometry_file": str(final_path.relative_to(ROOT)).replace("\\", "/"),
        "polygon_count": len(kept),
        "total_footprint_area_m2": round(total_area, 2),
        "captured_on": date_stamp,
        "source_dataset": "Overture Maps buildings",
        "source_url": "https://docs.overturemaps.org/getting-data/",
        "source_release": release,
        "coordinate_precision": coord.get("precision"),
    }
def main() -> int:
    registry = load_json(EPOCH_REGISTRY)
    sites = registry["records"]
    if len(sites) != 93:
        raise SystemExit(f"Expected 93 Epoch sites, got {len(sites)}")

    cached = load_json(SITE_COORDS) if SITE_COORDS.exists() else {"records": []}
    cached_records = cached.get("records") or []
    cached_geocoded = sum(1 for x in cached_records if x.get("lat") is not None and x.get("lon") is not None)
    # Re-run the richer geocoder whenever the cache still contains unresolved sites.
    # This prevents an early partial cache from permanently blocking polygon acquisition.
    if len(cached_records) != 93 or cached_geocoded < 93:
        coord_map = ensure_coordinates(sites)
    else:
        coord_map = {str(x["epoch_id"]): x for x in cached_records}

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    date_stamp = datetime.now(timezone.utc).date().isoformat()
    release = latest_overture_release()
    print(f"Overture release: {release}", flush=True)
    results: list[dict[str, Any]] = []
    con = duckdb.connect()
    try:
        con.execute("INSTALL httpfs")
        con.execute("LOAD httpfs")
        con.execute("INSTALL spatial")
        con.execute("LOAD spatial")
        con.execute("SET s3_region='us-west-2'")
    except Exception as exc:
        con.close()
        raise SystemExit(f"DuckDB extension initialization failed: {exc}") from exc

    for idx, site in enumerate(sites, start=1):
        eid = str(site["epoch_id"])
        coord = coord_map.get(eid) or {}
        if coord.get("lat") is None or coord.get("lon") is None:
            results.append({
                "epoch_id": eid,
                "site_name": site["normalized"].get("name"),
                "status": "UNRESOLVED_NO_COORDINATE",
                "geometry_file": None,
                "polygon_count": 0,
                "total_footprint_area_m2": 0.0,
                "captured_on": date_stamp,
                "source_dataset": "Overture Maps buildings",
                "source_url": "https://docs.overturemaps.org/getting-data/",
            })
            print(f"footprints {idx}/93: {site['normalized'].get('name')} -> UNRESOLVED", flush=True)
            continue
        try:
            result = download_site(site, coord, date_stamp, release, con)
        except Exception as exc:
            result = {
                "epoch_id": eid,
                "site_name": site["normalized"].get("name"),
                "status": "DOWNLOAD_FAILED",
                "error": str(exc),
                "geometry_file": None,
                "polygon_count": 0,
                "total_footprint_area_m2": 0.0,
                "captured_on": date_stamp,
                "source_dataset": "Overture Maps buildings",
                "source_url": "https://docs.overturemaps.org/getting-data/",
            }
        results.append(result)
        print(
            f"footprints {idx}/93: {site['normalized'].get('name')} -> "
            f"{result['status']} ({result.get('polygon_count', 0)} polygons)",
            flush=True,
        )

    con.close()

    save_json(INDEX_JSON, {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "site_target_count": 93,
        "source_release": release,
        "sites_with_polygon_files": sum(x.get("status") == "INGESTED_POLYGONIZED" for x in results),
        "total_polygon_count": sum(int(x.get("polygon_count") or 0) for x in results),
        "records": results,
        "semantics": "This is a current building-footprint geometry layer. It complements, but does not replace, dated construction chronology and remote-sensing observations.",
    })

    schema_path = ROOT / "data" / "track3_evidence_schema.json"
    schema = load_json(schema_path)
    if "INGESTED_POLYGONIZED" not in schema.get("statuses", []):
        schema["statuses"].append("INGESTED_POLYGONIZED")
    save_json(schema_path, schema)

    physical_path = ROOT / "data" / "physical_verification_layer.json"
    physical = load_json(physical_path)
    polygon_sites = sum(x.get("status") == "INGESTED_POLYGONIZED" for x in results)
    polygon_count = sum(int(x.get("polygon_count") or 0) for x in results)
    physical.setdefault("summary", {})["building_footprint_polygon_site_count"] = polygon_sites
    physical.setdefault("summary", {})["building_footprint_polygon_count"] = polygon_count
    for item in physical.get("checklist", []):
        if item.get("id") == "FOOTPRINT":
            item["status"] = "INGESTED_POLYGONIZED" if polygon_sites else item.get("status", "INGESTED_CHRONOLOGY_NOT_RAW_IMAGERY")
            item["coverage"] = (
                f"{polygon_sites} / 93 sites have current polygonized building-footprint geometry "
                f"({polygon_count} polygons retained). Dated construction chronology remains a separate layer."
            )
            item["primary_sources"] = [
                "overture-buildings",
                "epoch-timelines",
                "sentinel-2-optical",
            ]
    physical["generated_on"] = date_stamp
    save_json(physical_path, physical)

    print(json.dumps({
        "sites_with_polygon_files": polygon_sites,
        "total_polygon_count": polygon_count,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
