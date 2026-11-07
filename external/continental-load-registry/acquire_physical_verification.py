#!/usr/bin/env python3
"""Acquire compact, reproducible physical-verification observations.

1. Geocode the 93 public Epoch site addresses with OpenStreetMap Nominatim.
2. Search public Copernicus and USGS STAC catalogs for multi-temporal scenes.
3. Read small raw Cloud-Optimized GeoTIFF windows around each site.
4. Store scene provenance plus derived optical/TIR/SAR metrics, not full rasters.
5. Maintain a 93-site transformer-event research queue without inventing events.
6. Refresh data/physical_verification_layer.{json,csv}.

Missing data remains UNKNOWN/NOT_INGESTED and is never interpreted as absence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import requests
import rasterio
import planetary_computer
from pystac_client import Client
from rasterio.crs import CRS
from rasterio.windows import Window
from rasterio.warp import transform as warp_transform

ROOT = Path(__file__).resolve().parent
EPOCH_REGISTRY = ROOT / "data" / "external" / "epoch_ai" / "registry.json"
PHYSICAL_LAYER = ROOT / "data" / "physical_verification_layer.json"
SITE_COORDS = ROOT / "data" / "track3" / "physical_site_coordinates.json"
OBS_JSON = ROOT / "data" / "track3" / "remote_sensing_observations.json"
OBS_CSV = ROOT / "data" / "track3" / "remote_sensing_observations.csv"
TRANSFORMER_JSON = ROOT / "data" / "track3" / "transformer_supply_chain_events.json"
TRANSFORMER_CSV = ROOT / "data" / "track3" / "transformer_event_targets.csv"
SOURCE_STACK = ROOT / "data" / "track3_source_stack.json"
TRACK3_SCHEMA = ROOT / "data" / "track3_evidence_schema.json"

CDSE_STAC = "https://stac.dataspace.copernicus.eu/v1/search"
USGS_STAC = "https://landsatlook.usgs.gov/stac-server/search"
MPC_STAC = "https://planetarycomputer.microsoft.com/api/stac/v1/search"
NOMINATIM = "https://nominatim.openstreetmap.org/search"
CENSUS_GEOCODER = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
PHOTON_GEOCODER = "https://photon.komoot.io/api/"
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "continental-load-registry/physical-verification (+https://github.com/AnonRish/continental-load-registry)"
})
RANGE_START = "2021-01-01T00:00:00Z"
RANGE_END = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

# Planetary Computer exposes public STAC metadata and signed HTTPS COG assets.
# Landsat C2 L2 is the collection that carries both reflectance and TIRS surface-temperature assets.
COLLECTIONS = {
    "optical": ("mpc", "sentinel-2-l2a"),
    "sar": ("mpc", "sentinel-1-grd"),
    "tir": ("mpc", "landsat-c2-l2"),
}

def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

def save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

def post_json(url: str, payload: dict[str, Any], timeout: int = 90) -> dict[str, Any]:
    last = None
    for attempt in range(3):
        try:
            response = SESSION.post(url, json=payload, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last = exc
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"STAC request failed: {url}: {last}")

def get_json(url: str, params: dict[str, Any], timeout: int = 60) -> Any:
    last = None
    for attempt in range(3):
        try:
            response = SESSION.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last = exc
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"GET failed: {url}: {last}")

def parse_dt(item: dict[str, Any]) -> datetime:
    raw = item.get("properties", {}).get("datetime") or item.get("properties", {}).get("start_datetime")
    if not raw:
        return datetime.min.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(raw.replace("Z", "+00:00"))

def bbox_for_site(lat: float, lon: float, radius_deg: float = 0.02) -> list[float]:
    return [
        max(-180.0, lon - radius_deg),
        max(-90.0, lat - radius_deg),
        min(180.0, lon + radius_deg),
        min(90.0, lat + radius_deg),
    ]

def search_stac(kind: str, collection: str, bbox: list[float], limit: int = 60) -> list[dict[str, Any]]:
    # Prefer pystac-client because it handles the STAC search contract and pagination
    # correctly. The raw HTTP path remains as a fallback for catalog compatibility.
    endpoints = [
        MPC_STAC.replace("/search", ""),
    ]
    if kind == "cdse":
        endpoints.append(CDSE_STAC.replace("/search", ""))
    elif kind == "usgs":
        endpoints.append(USGS_STAC.replace("/search", ""))
    # AWS Earth Search is a public fallback for Sentinel imagery.
    if collection in {"sentinel-2-l2a", "sentinel-1-grd"}:
        endpoints.append("https://earth-search.aws.element84.com/v1")

    errors: list[str] = []
    for endpoint in endpoints:
        try:
            catalog = Client.open(endpoint)
            search = catalog.search(
                collections=[collection],
                bbox=bbox,
                datetime=f"{RANGE_START}/{RANGE_END}",
                max_items=limit,
            )
            rows = list(search.item_collection())
            if rows:
                return [x.to_dict() if hasattr(x, "to_dict") else dict(x) for x in rows]
        except Exception as exc:
            errors.append(f"{endpoint} [{collection}]: {exc}")

    # Raw POST fallback.
    payload = {
        "collections": [collection],
        "bbox": bbox,
        "datetime": f"{RANGE_START}/{RANGE_END}",
        "limit": limit,
    }
    for endpoint in endpoints:
        search_url = endpoint.rstrip("/") + "/search"
        try:
            rows = list(post_json(search_url, payload).get("features", []))
            if rows:
                return rows
        except Exception as exc:
            errors.append(f"{search_url} [{collection}]: {exc}")

    if errors:
        raise RuntimeError(" ; ".join(errors[-8:]))
    return []

def best_temporal_items(items: list[dict[str, Any]], count: int = 3) -> list[dict[str, Any]]:
    unique = {str(x.get("id")): x for x in items if x.get("id")}
    ordered = sorted(unique.values(), key=parse_dt)
    if not ordered:
        return []
    if len(ordered) <= count:
        return ordered
    positions = np.linspace(0, len(ordered) - 1, count).round().astype(int).tolist()
    return [ordered[i] for i in positions]

def asset_key(assets: dict[str, Any], candidates: list[str]) -> str | None:
    lower = {str(k).lower(): k for k in assets}
    for candidate in candidates:
        if candidate.lower() in lower:
            return str(lower[candidate.lower()])
    for key in assets:
        lk = str(key).lower()
        if any(candidate.lower() in lk for candidate in candidates):
            return str(key)
    return None

def asset_href(assets: dict[str, Any], candidates: list[str]) -> tuple[str | None, str | None]:
    key = asset_key(assets, candidates)
    if not key:
        return None, None
    href = assets.get(key, {}).get("href")
    if not href:
        return None, key
    href = str(href)
    try:
        if "planetarycomputer.microsoft.com" in href or ".blob.core.windows.net" in href:
            href = str(planetary_computer.sign(href))
    except Exception:
        pass
    return href, key

def read_window(href: str, lon: float, lat: float, pixels: int, crs_hint: str | int | None = None) -> tuple[np.ndarray, dict[str, Any]]:
    env = {
        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
        "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif,.TIF,.tiff,.TIFF,.jp2,.JP2",
        "GDAL_HTTP_MAX_RETRY": 2,
        "GDAL_HTTP_RETRY_DELAY": 1,
        "GDAL_CACHEMAX": 64,
    }
    with rasterio.Env(**env):
        with rasterio.open(href) as src:
            target_crs = src.crs
            if target_crs is None and crs_hint is not None:
                target_crs = CRS.from_user_input(crs_hint)
            if target_crs is None:
                raise RuntimeError("Raster asset has no embedded CRS and STAC projection metadata is missing")
            xs, ys = warp_transform("EPSG:4326", target_crs, [lon], [lat])
            x, y = xs[0], ys[0]
            row, col = src.index(x, y)
            half = pixels // 2
            window = Window(col - half, row - half, pixels, pixels)
            masked = src.read(
                1,
                window=window,
                boundless=True,
                masked=True,
            )
            # NumPy 2.x cannot fill an integer masked array with NaN.
            # Cast first, then fill, preserving nodata as floating NaN.
            arr = masked.astype("float32").filled(np.nan)
            scale = float(src.scales[0]) if src.scales else 1.0
            offset = float(src.offsets[0]) if src.offsets else 0.0
            if not math.isfinite(scale) or scale == 0:
                scale = 1.0
            if not math.isfinite(offset):
                offset = 0.0
            arr = arr * scale + offset
            return arr, {
                "crs": str(target_crs),
                "resolution": [float(v) for v in src.res],
                "scale": scale,
                "offset": offset,
            }

def robust_median(arr: np.ndarray) -> float | None:
    vals = arr[np.isfinite(arr)]
    return float(np.nanmedian(vals)) if vals.size else None

def pct(arr: np.ndarray, q: float) -> float | None:
    vals = arr[np.isfinite(arr)]
    return float(np.nanpercentile(vals, q)) if vals.size else None

def central_background(arr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    h, w = arr.shape
    y0, y1 = h // 4, (3 * h) // 4
    x0, x1 = w // 4, (3 * w) // 4
    center = arr[y0:y1, x0:x1]
    background = arr.copy()
    background[y0:y1, x0:x1] = np.nan
    return center, background

def scaled_s2_reflectance(arr: np.ndarray) -> np.ndarray:
    med = robust_median(arr)
    return arr / 10000.0 if med is not None and med > 2.0 else arr

def scaled_landsat_temperature(arr: np.ndarray) -> np.ndarray:
    med = robust_median(arr)
    return arr * 0.00341802 + 149.0 if med is not None and med > 1000 else arr

def scene_metrics_optical(item: dict[str, Any], lat: float, lon: float) -> dict[str, Any]:
    assets = item.get("assets", {})
    red_href, red_key = asset_href(assets, ["B04", "red", "band4"])
    nir_href, nir_key = asset_href(assets, ["B08", "nir", "band8"])
    scl_href, scl_key = asset_href(assets, ["SCL", "scene-classification"])
    if not red_href or not nir_href:
        raise RuntimeError("Sentinel-2 item lacks B04/B08 assets")
    red, red_meta = read_window(red_href, lon, lat, 512)
    nir, _ = read_window(nir_href, lon, lat, 512)
    red = scaled_s2_reflectance(red)
    nir = scaled_s2_reflectance(nir)
    valid = np.isfinite(red) & np.isfinite(nir)
    if scl_href:
        scl, _ = read_window(scl_href, lon, lat, 512)
        classified = np.isfinite(scl) & (scl > 0)
        if np.any(classified):
            candidate = valid & ~np.isin(scl.astype("int16"), [0, 1, 3, 8, 9, 10, 11])
            # Some public SCL tiles are effectively unclassified at the
            # point/window even when the spectral bands are readable.
            # Only replace the band-valid mask when the SCL actually leaves
            # usable pixels; otherwise retain band-valid pixels.
            if np.any(candidate):
                valid = candidate
    ndvi = np.full(red.shape, np.nan, dtype="float32")
    denom = nir + red
    good = valid & (np.abs(denom) > 1e-6)
    ndvi[good] = (nir[good] - red[good]) / denom[good]
    nonveg = good & (ndvi < 0.20)
    return {
        "red_reflectance_median": robust_median(red[valid]),
        "nir_reflectance_median": robust_median(nir[valid]),
        "ndvi_median": robust_median(ndvi),
        "ndvi_p10": pct(ndvi, 10),
        "ndvi_p90": pct(ndvi, 90),
        "nonvegetated_proxy_fraction": float(nonveg[valid].mean()) if np.any(valid) else None,
        "valid_pixel_count": int(valid.sum()),
        "source_resolution_m": float(red_meta["resolution"][0]),
        "source_asset_keys": [red_key, nir_key, scl_key],
        "proxy_note": "Nonvegetated fraction is a coarse surface-change proxy; it is not a building-footprint measurement.",
    }

def scene_metrics_tir(item: dict[str, Any], lat: float, lon: float) -> dict[str, Any]:
    assets = item.get("assets", {})
    st_href, st_key = asset_href(assets, ["ST_B10", "st_b10", "surface_temperature", "ST", "lwir11", "thermal"])
    if not st_href:
        raise RuntimeError("Landsat ST item lacks a surface-temperature asset")
    st, st_meta = read_window(st_href, lon, lat, 192)
    st = scaled_landsat_temperature(st)
    center, background = central_background(st)
    center_med = robust_median(center)
    background_med = robust_median(background)
    anomaly = center_med - background_med if center_med is not None and background_med is not None else None
    return {
        "surface_temperature_k_median": center_med,
        "local_background_temperature_k_median": background_med,
        "local_surface_temperature_delta_k": anomaly,
        "surface_temperature_p10_k": pct(center, 10),
        "surface_temperature_p90_k": pct(center, 90),
        "valid_pixel_count": int(np.isfinite(st).sum()),
        "source_resolution_m": float(st_meta["resolution"][0]),
        "source_asset_key": st_key,
        "proxy_note": "Thermal anomaly is relative to the local scene background, not a calibrated facility heat-output measurement.",
    }

def db_values(arr: np.ndarray) -> np.ndarray:
    # Planetary Computer Sentinel-1 GRD exposes detected amplitude values.
    # Convert amplitude to dB with 20*log10(A), not the power conversion 10*log10(P).
    safe = np.where(arr > 0, arr, np.nan)
    return 20.0 * np.log10(safe)

def scene_metrics_sar(item: dict[str, Any], lat: float, lon: float) -> dict[str, Any]:
    assets = item.get("assets", {})
    vv_href, vv_key = asset_href(assets, ["vv"])
    vh_href, vh_key = asset_href(assets, ["vh"])
    if not vv_href:
        raise RuntimeError("Sentinel-1 item lacks VV asset")
    projection = item.get("properties", {}).get("proj:epsg")
    if projection is not None and isinstance(projection, int):
        projection = f"EPSG:{projection}"
    # Sentinel-1 GRD assets in the public STAC can omit both an embedded CRS
    # and proj:epsg. The GRD raster is normally in a UTM CRS; derive the
    # standard UTM zone from the geodetic site coordinate as a file-access
    # fallback, while retaining the STAC CRS whenever it is available.
    if projection is None:
        zone = int((lon + 180.0) // 6.0) + 1
        projection = f"EPSG:{32600 + zone if lat >= 0 else 32700 + zone}"
    vv, vv_meta = read_window(vv_href, lon, lat, 512, crs_hint=projection)
    vv = db_values(vv)
    metrics = {
        "vv_db_median": robust_median(vv),
        "vv_db_p10": pct(vv, 10),
        "vv_db_p90": pct(vv, 90),
        "valid_pixel_count": int(np.isfinite(vv).sum()),
        "source_resolution_m": float(vv_meta["resolution"][0]),
        "source_asset_keys": [vv_key, vh_key],
        "backscatter_note": "Sentinel-1 GRD detected amplitude is converted to dB with 20*log10(amplitude).",
    }
    if vh_href:
        vh, _ = read_window(vh_href, lon, lat, 512, crs_hint=projection)
        vh = db_values(vh)
        metrics["vh_db_median"] = robust_median(vh)
        metrics["vh_db_p10"] = pct(vh, 10)
        metrics["vh_db_p90"] = pct(vh, 90)
        metrics["vv_vh_db_difference"] = (
            metrics["vv_db_median"] - metrics["vh_db_median"]
            if metrics["vv_db_median"] is not None and metrics["vh_db_median"] is not None
            else None
        )
    return metrics

def _address_tokens(address: str) -> dict[str, str | None]:
    text = re.sub(r"\s+", " ", address or "").strip()
    number = re.search(r"\b(\d{1,7})\b", text)
    postal_us = re.search(r"\b\d{5}(?:-\d{4})?\b", text)
    return {"number": number.group(1) if number else None, "postal_us": postal_us.group(0)[:5] if postal_us else None}


def _census_geocode(address: str) -> dict[str, Any] | None:
    """Fallback for numbered U.S. addresses when Nominatim cannot resolve them."""
    if not re.search(r"\b[A-Z]{2}\s+\d{5}(?:-\d{4})?\b", address.upper()):
        return None
    try:
        data = get_json(CENSUS_GEOCODER, {
            "address": address,
            "benchmark": "Public_AR_Current",
            "format": "json",
        })
        matches = (((data or {}).get("result") or {}).get("addressMatches") or [])
        if not matches:
            return None
        hit = matches[0]
        coords = hit.get("coordinates") or {}
        if coords.get("x") is None or coords.get("y") is None:
            return None
        tokens = _address_tokens(address)
        matched_addr = str(hit.get("matchedAddress") or "")
        if tokens["number"] and not re.search(rf"\\b{re.escape(tokens['number'])}\\b", matched_addr):
            return None
        return {
            "lat": float(coords["y"]),
            "lon": float(coords["x"]),
            "display_name": matched_addr or None,
            "geocoder": "U.S. Census Geocoder",
            "geocode_query": address,
            "geocode_method": "census-onelineaddress",
        }
    except Exception:
        return None


def _photon_geocode(address: str) -> dict[str, Any] | None:
    """Fallback for numbered addresses; reject city-only/region-only centroids."""
    tokens = _address_tokens(address)
    if not tokens["number"]:
        return None
    try:
        data = get_json(PHOTON_GEOCODER, {"q": address, "limit": 5})
        features = (data or {}).get("features") or []
        for feature in features:
            coords = (feature.get("geometry") or {}).get("coordinates") or []
            props = feature.get("properties") or {}
            if len(coords) < 2:
                continue
            country = str(props.get("country") or "").lower()
            label = ", ".join(str(x) for x in [
                props.get("name"), props.get("housenumber"), props.get("street"),
                props.get("city") or props.get("locality"), props.get("state"),
                props.get("postcode"), props.get("country"),
            ] if x)
            if "united states" in address.lower() and country and country not in {"united states", "usa", "us"}:
                continue
            if tokens["number"] and props.get("housenumber") and str(props.get("housenumber")) != tokens["number"]:
                continue
            if tokens["postal_us"] and props.get("postcode") and str(props.get("postcode"))[:5] != tokens["postal_us"]:
                continue
            if not props.get("housenumber"):
                continue
            return {
                "lat": float(coords[1]),
                "lon": float(coords[0]),
                "display_name": label or None,
                "geocoder": "Photon (Komoot)",
                "geocode_query": address,
                "geocode_method": "photon-address",
            }
    except Exception:
        return None
    return None


def geocode(address: str, name: str | None = None, region: str | None = None, country: str | None = None) -> dict[str, Any] | None:
    queries = [q for q in [
        address,
        ", ".join(x for x in [name, region, country] if x),
        ", ".join(x for x in [name, country] if x),
    ] if q]
    for query in queries:
        try:
            data = get_json(NOMINATIM, {
                "q": query,
                "format": "jsonv2",
                "limit": 1,
                "addressdetails": 1,
            })
            if not data:
                continue
            hit = data[0]
            return {
                "lat": float(hit["lat"]),
                "lon": float(hit["lon"]),
                "display_name": hit.get("display_name"),
                "osm_type": hit.get("osm_type"),
                "osm_id": hit.get("osm_id"),
                "country_code": (hit.get("address") or {}).get("country_code"),
                "geocoder": "OpenStreetMap Nominatim",
                "geocode_query": query,
                "geocode_method": "nominatim",
            }
        except Exception:
            continue

    # Strict fallbacks: only accept a numbered address match. We never turn a
    # city/county/state centroid into a facility coordinate.
    census = _census_geocode(address)
    if census:
        return census
    photon = _photon_geocode(address)
    if photon:
        return photon
    return None

def ensure_coordinates(sites: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    cache = load_json(SITE_COORDS) if SITE_COORDS.exists() else {"records": []}
    cached = {str(x["epoch_id"]): x for x in cache.get("records", [])}
    records = []
    seen_addresses: set[str] = set()
    for idx, site in enumerate(sites):
        eid = str(site["epoch_id"])
        address = str(site["normalized"].get("address") or "").strip()
        existing = cached.get(eid)
        if existing and existing.get("lat") is not None and existing.get("lon") is not None:
            records.append(existing)
            continue
        if not address:
            records.append({
                "epoch_id": eid,
                "site_name": site["normalized"].get("name"),
                "address": address,
                "status": "UNRESOLVED",
                "precision": "no public address",
            })
            continue
        if address not in seen_addresses:
            time.sleep(1.05)
            seen_addresses.add(address)
        hit = geocode(
            address,
            str(site["normalized"].get("name") or "").strip() or None,
            str(site["normalized"].get("region_inferred_from_address") or site["normalized"].get("state_province") or "").strip() or None,
            str(site["normalized"].get("country") or "").strip() or None,
        )
        record = {
            "epoch_id": eid,
            "site_name": site["normalized"].get("name"),
            "address": address,
            "status": "GEOCODED" if hit else "UNRESOLVED",
            "precision": "public-address geocode" if hit else "geocoder returned no result",
            "captured_on": datetime.now(timezone.utc).date().isoformat(),
        }
        if hit:
            record.update(hit)
        records.append(record)
        print(f"geocode {idx + 1}/{len(sites)}: {record['site_name']} -> {record['status']}", flush=True)
    save_json(SITE_COORDS, {
        "schema_version": 1,
        "source": "OpenStreetMap Nominatim",
        "attribution": "© OpenStreetMap contributors",
        "record_count": len(records),
        "records": records,
    })
    return {str(x["epoch_id"]): x for x in records}

def process_site(site: dict[str, Any], coord: dict[str, Any], scenes_per_modality: int) -> list[dict[str, Any]]:
    lat, lon = float(coord["lat"]), float(coord["lon"])
    bbox = bbox_for_site(lat, lon)
    output: list[dict[str, Any]] = []
    for modality, (kind, collection) in COLLECTIONS.items():
        try:
            items = search_stac(kind, collection, bbox)
            if modality == "sar":
                items = [
                    item for item in items
                    if asset_href(item.get("assets", {}), ["vv"])[0]
                ]
            chosen = best_temporal_items(items, scenes_per_modality)
        except Exception as exc:
            output.append({
                "epoch_id": site["epoch_id"],
                "site_name": site["normalized"].get("name"),
                "address": site["normalized"].get("address"),
                "latitude": lat,
                "longitude": lon,
                "coordinate_precision": coord.get("precision"),
                "modality": modality,
                "status": "SOURCE_QUERY_FAILED",
                "error": str(exc),
            })
            continue
        if not chosen:
            output.append({
                "epoch_id": site["epoch_id"],
                "site_name": site["normalized"].get("name"),
                "address": site["normalized"].get("address"),
                "latitude": lat,
                "longitude": lon,
                "coordinate_precision": coord.get("precision"),
                "modality": modality,
                "sensor": collection,
                "status": "NO_SCENES_FOUND",
                "source_catalog": MPC_STAC if kind == "mpc" else (CDSE_STAC if kind == "cdse" else USGS_STAC),
                "source_collection": collection,
                "search_bbox": bbox,
            })
            continue
        previous_metrics: dict[str, Any] | None = None
        for item in chosen:
            try:
                if modality == "optical":
                    metrics = scene_metrics_optical(item, lat, lon)
                    sensor = "Sentinel-2 MSI L2A"
                elif modality == "tir":
                    metrics = scene_metrics_tir(item, lat, lon)
                    sensor = "Landsat Collection 2 Level-2 Surface Temperature"
                else:
                    metrics = scene_metrics_sar(item, lat, lon)
                    sensor = "Sentinel-1 GRD"
                current = {
                    "epoch_id": site["epoch_id"],
                    "site_name": site["normalized"].get("name"),
                    "address": site["normalized"].get("address"),
                    "latitude": lat,
                    "longitude": lon,
                    "coordinate_precision": coord.get("precision"),
                    "modality": modality,
                    "sensor": sensor,
                    "scene_id": item.get("id"),
                    "observed_on": parse_dt(item).date().isoformat(),
                    "stac_item_url": next((x.get("href") for x in item.get("links", []) if x.get("rel") == "self"), None),
                    "source_catalog": MPC_STAC if kind == "mpc" else (CDSE_STAC if kind == "cdse" else USGS_STAC),
                    "source_collection": collection,
                    "cloud_cover_pct": item.get("properties", {}).get("eo:cloud_cover"),
                    "metrics": metrics,
                    "comparison_to_previous": {},
                    "status": "INGESTED_DERIVED",
                    "quality_flag": "RAW_COG_WINDOW_PROCESSED",
                    "processing_version": "physical-verification-v1",
                }
                if previous_metrics:
                    for key, val in metrics.items():
                        if isinstance(val, (int, float)) and isinstance(previous_metrics.get(key), (int, float)):
                            current["comparison_to_previous"][key + "_delta"] = val - previous_metrics[key]
                previous_metrics = metrics
                output.append(current)
            except Exception as exc:
                output.append({
                    "epoch_id": site["epoch_id"],
                    "site_name": site["normalized"].get("name"),
                    "address": site["normalized"].get("address"),
                    "latitude": lat,
                    "longitude": lon,
                    "coordinate_precision": coord.get("precision"),
                    "modality": modality,
                    "sensor": collection,
                    "scene_id": item.get("id"),
                    "observed_on": parse_dt(item).date().isoformat(),
                    "stac_item_url": next((x.get("href") for x in item.get("links", []) if x.get("rel") == "self"), None),
                    "source_catalog": MPC_STAC if kind == "mpc" else (CDSE_STAC if kind == "cdse" else USGS_STAC),
                    "source_collection": collection,
                    "status": "SCENE_READ_FAILED",
                    "error": str(exc),
                })
    return output

def transformer_targets(sites: list[dict[str, Any]], existing_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    event_counts: dict[str, int] = {}
    for event in existing_events:
        eid = str(event.get("epoch_id") or "")
        if eid:
            event_counts[eid] = event_counts.get(eid, 0) + 1
    out = []
    for site in sites:
        name = str(site["normalized"].get("name") or "")
        address = str(site["normalized"].get("address") or "")
        region = str(site["normalized"].get("region_inferred_from_address") or "")
        out.append({
            "target_id": f"TX-TARGET-{site['epoch_id']}",
            "epoch_id": site["epoch_id"],
            "site_name": name,
            "address": address,
            "region": region,
            "status": "INGESTED" if event_counts.get(str(site["epoch_id"]), 0) else "RESEARCH_QUEUE",
            "event_count": event_counts.get(str(site["epoch_id"]), 0),
            "source_families": [
                "state/provincial utility commission filings",
                "serving-utility capital-project and procurement filings",
                "environmental impact statements / permits",
                "county or municipal construction records",
                "SEC/company procurement disclosures",
                "transformer manufacturer or EPC project announcements",
            ],
            "search_queries": [
                f'"{name}" transformer data center',
                f'"{name}" substation transformer MVA kV',
                f'"{name}" transformer delivery installation',
                f'"{name}" utility commission transformer',
            ],
            "required_event_fields": [
                "observed_on", "event_type", "manufacturer", "model",
                "rating_mva", "primary_kv", "secondary_kv",
                "buyer", "destination", "source_url",
            ],
            "semantics": "A research target is not a transformer event and does not imply that a transformer exists at the site.",
        })
    return out

def update_physical_layer(observations: list[dict[str, Any]], coords: dict[str, dict[str, Any]], transformer_targets_rows: list[dict[str, Any]], transformer_events: list[dict[str, Any]]) -> None:
    physical = load_json(PHYSICAL_LAYER)
    site_records = physical.get("site_records", [])
    obs_ok = [x for x in observations if x.get("status") == "INGESTED_DERIVED"]
    by_site_modality: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for obs in obs_ok:
        by_site_modality.setdefault((str(obs["epoch_id"]), str(obs["modality"])), []).append(obs)
    for rec in site_records:
        eid = str(rec.get("epoch_id"))
        coord = coords.get(eid, {})
        if coord.get("lat") is not None:
            rec["lat"] = coord["lat"]
            rec["lon"] = coord["lon"]
            rec["coordinate_precision"] = coord.get("precision")
        for modality, key in [("optical", "optical_imagery"), ("tir", "tir_thermal"), ("sar", "sar")]:
            rows = by_site_modality.get((eid, modality), [])
            base = rec.get(key, {})
            if modality == "optical":
                rec[key] = {
                    **base,
                    "status": "INGESTED_DERIVED" if rows else base.get("status", "SOURCE_AVAILABLE_NOT_INGESTED"),
                    "scene_count": len(rows),
                    "site_scene_count": len(rows),
                    "source": "Copernicus Sentinel-2 L2A via public STAC",
                    "analysis": "Raw COG windows processed into NDVI/non-vegetated proxy metrics; full rasters are not stored in Git.",
                }
            elif modality == "tir":
                rec[key] = {
                    **base,
                    "status": "INGESTED_DERIVED" if rows else base.get("status", "SOURCE_AVAILABLE_NOT_INGESTED"),
                    "numeric_observation_count": len(rows),
                    "scene_count": len(rows),
                    "source": "USGS Landsat Collection 2 Level-2 ST via public STAC",
                    "analysis": "Raw COG windows processed into surface-temperature and local-background deltas.",
                }
            else:
                rec[key] = {
                    **base,
                    "status": "INGESTED_DERIVED" if rows else base.get("status", "SOURCE_AVAILABLE_NOT_INGESTED"),
                    "numeric_observation_count": len(rows),
                    "scene_count": len(rows),
                    "source": "Copernicus Sentinel-1 GRD via public STAC",
                    "analysis": "Raw COG VV/VH windows processed into backscatter dB and temporal deltas.",
                }
        footprint = rec.get("building_footprint_expansion", {})
        if by_site_modality.get((eid, "optical")):
            rec["building_footprint_expansion"] = {
                **footprint,
                "status": "INGESTED_DERIVED_PROXY",
                "raw_imagery_status": "INGESTED",
                "basis": "Multi-temporal Sentinel-2 windows are processed; NDVI/nonvegetated metrics are a coarse campus-change proxy, not a polygonized building footprint.",
            }
        tx = next((x for x in transformer_targets_rows if x["epoch_id"] == eid), None)
        site_transformer_events = [x for x in transformer_events if str(x.get("epoch_id") or "") == eid]
        if tx:
            rec["transformer_installation_procurement"] = {
                **(rec.get("transformer_installation_procurement") or {}),
                "status": "INGESTED" if site_transformer_events else "RESEARCH_QUEUE",
                "event_count": len(site_transformer_events),
                "target_id": tx["target_id"],
                "note": "Event status is source-backed; planned specifications are not treated as installation/energization.",
            }
    psummary = physical.setdefault("summary", {})
    psummary["raw_optical_scenes_ingested"] = sum(1 for x in obs_ok if x.get("modality") == "optical")
    psummary["raw_tir_numeric_observations"] = sum(1 for x in obs_ok if x.get("modality") == "tir")
    psummary["raw_sar_numeric_observations"] = sum(1 for x in obs_ok if x.get("modality") == "sar")
    psummary["building_footprint_raw_change_detection_sites"] = len({
        x["epoch_id"] for x in obs_ok if x.get("modality") == "optical"
    })
    psummary["transformer_event_records"] = len(transformer_events)
    for item in physical.get("checklist", []):
        ident = str(item.get("id"))
        if ident == "OPTICAL":
            n = psummary["raw_optical_scenes_ingested"]
            item["status"] = "INGESTED_DERIVED" if n else "SOURCE_AVAILABLE_NOT_INGESTED"
            item["coverage"] = f"{n} raw Sentinel-2 COG windows processed; scene provenance and compact metrics are stored, full rasters are not stored in Git."
        elif ident == "TIR":
            n = psummary["raw_tir_numeric_observations"]
            item["status"] = "INGESTED_DERIVED" if n else "SOURCE_AVAILABLE_NOT_INGESTED"
            item["coverage"] = f"{n} Landsat ST scene observations processed with local-background thermal metrics."
        elif ident == "SAR":
            n = psummary["raw_sar_numeric_observations"]
            item["status"] = "INGESTED_DERIVED" if n else "SOURCE_AVAILABLE_NOT_INGESTED"
            item["coverage"] = f"{n} Sentinel-1 GRD scene observations processed with VV/VH backscatter and temporal deltas."
        elif ident == "FOOTPRINT":
            n = psummary["building_footprint_raw_change_detection_sites"]
            item["status"] = "INGESTED_DERIVED_PROXY" if n else "INGESTED_CHRONOLOGY_NOT_RAW_IMAGERY"
            item["coverage"] = f"{n} sites have multi-temporal optical observations for coarse campus-change proxy analysis; polygonized footprints remain separate."
        elif ident == "TRANSFORMER":
            n = psummary["transformer_event_records"]
            item["status"] = "INGESTED" if n else "RESEARCH_QUEUE"
            item["coverage"] = (
                f"{n} source-backed transformer procurement/delivery/specification event records are retained; "
                "the 93-site research queue remains published for uncovered sites."
            )
    physical["generated_on"] = datetime.now(timezone.utc).date().isoformat()
    physical["site_records"] = site_records
    save_json(PHYSICAL_LAYER, physical)

    headers = [
        "epoch_id","site_name","country","state_province","address","lat","lon",
        "coordinate_precision","current_it_power_mw","construction_status",
        "construction_timeline_record_count","construction_to_power_status",
        "building_footprint_status","optical_status","optical_scene_count",
        "tir_status","tir_scene_count","sar_status","sar_scene_count",
        "substation_expansion_status","transformer_status","transformer_event_count",
        "transmission_line_status","cooling_status","backup_generation_status",
        "permit_chronology_status",
    ]
    with (ROOT / "data" / "physical_verification_layer.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for rec in site_records:
            writer.writerow([
                rec.get("epoch_id"), rec.get("site_name"), rec.get("country"),
                rec.get("state_province"), rec.get("address"), rec.get("lat"),
                rec.get("lon"), rec.get("coordinate_precision"),
                rec.get("current_it_power_mw"),
                (rec.get("construction") or {}).get("status"),
                (rec.get("construction") or {}).get("timeline_record_count"),
                (rec.get("construction_to_power_timeline") or {}).get("status"),
                (rec.get("building_footprint_expansion") or {}).get("status"),
                (rec.get("optical_imagery") or {}).get("status"),
                (rec.get("optical_imagery") or {}).get("scene_count"),
                (rec.get("tir_thermal") or {}).get("status"),
                (rec.get("tir_thermal") or {}).get("scene_count"),
                (rec.get("sar") or {}).get("status"),
                (rec.get("sar") or {}).get("scene_count"),
                (rec.get("substation_expansion_detection") or {}).get("status"),
                (rec.get("transformer_installation_procurement") or {}).get("status"),
                (rec.get("transformer_installation_procurement") or {}).get("event_count"),
                (rec.get("transmission_line_construction") or {}).get("status"),
                (rec.get("cooling_infrastructure") or {}).get("status"),
                (rec.get("backup_generation_infrastructure") or {}).get("status"),
                (rec.get("construction_permit_chronology") or {}).get("status"),
            ])

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-sites", type=int, default=93)
    ap.add_argument("--scenes-per-modality", type=int, default=3, choices=(2, 3))
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()

    registry = load_json(EPOCH_REGISTRY)
    sites = registry["records"][: args.max_sites]
    if len(sites) != 93:
        raise SystemExit(f"Expected 93 Epoch sites, got {len(sites)}")

    coords = ensure_coordinates(sites)
    existing_transformer = load_json(TRANSFORMER_JSON) if TRANSFORMER_JSON.exists() else {}
    existing_events = list(existing_transformer.get("records") or [])
    target_rows = transformer_targets(sites, existing_events)
    save_json(TRANSFORMER_JSON, {
        "schema_version": 1,
        "generated_on": datetime.now(timezone.utc).date().isoformat(),
        "record_count": len(existing_events),
        "target_count": len(target_rows),
        "status": "INGESTED_SOURCE_BACKED_EVENTS" if existing_events else "RESEARCH_QUEUE",
        "records": existing_events,
        "targets": target_rows,
        "semantics": "Only source-backed procurement/delivery/installation/specification events may be added to records. Targets are not events.",
    })
    with TRANSFORMER_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "target_id","epoch_id","site_name","address","region","status",
            "event_count","source_families","search_queries","required_event_fields","semantics",
        ])
        writer.writeheader()
        for row in target_rows:
            writer.writerow({
                **row,
                "source_families": "; ".join(row["source_families"]),
                "search_queries": "; ".join(row["search_queries"]),
                "required_event_fields": "; ".join(row["required_event_fields"]),
                "semantics": row["semantics"],
            })

    prior_observations = []
    if OBS_JSON.exists():
        try:
            prior_observations = list(load_json(OBS_JSON).get("records") or [])
        except Exception:
            prior_observations = []
    observations: list[dict[str, Any]] = []
    runnable = [s for s in sites if coords.get(str(s["epoch_id"]), {}).get("lat") is not None]
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = {
            pool.submit(process_site, site, coords[str(site["epoch_id"])], args.scenes_per_modality): site
            for site in runnable
        }
        for idx, future in enumerate(as_completed(futures), start=1):
            site = futures[future]
            try:
                rows = future.result()
                observations.extend(rows)
                print(
                    f"satellite {idx}/{len(futures)}: {site['normalized'].get('name')} -> "
                    f"{sum(r.get('status') == 'INGESTED_DERIVED' for r in rows)} derived observations",
                    flush=True,
                )
            except Exception as exc:
                observations.append({
                    "epoch_id": site["epoch_id"],
                    "site_name": site["normalized"].get("name"),
                    "status": "SITE_PROCESS_FAILED",
                    "error": str(exc),
                })

    observations.sort(key=lambda x: (
        str(x.get("epoch_id")),
        str(x.get("modality")),
        str(x.get("observed_on")),
        str(x.get("scene_id")),
    ))
    status_counts: dict[str, int] = {}
    modality_status: dict[str, dict[str, int]] = {}
    samples: dict[str, list[str]] = {}
    for row in observations:
        status = str(row.get("status") or "UNKNOWN_STATUS")
        modality = str(row.get("modality") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        modality_status.setdefault(modality, {})[status] = modality_status.setdefault(modality, {}).get(status, 0) + 1
        if row.get("error") and len(samples.setdefault(status, [])) < 3:
            samples[status].append(str(row.get("error")))
    print("physical status counts:", json.dumps(status_counts, sort_keys=True), flush=True)
    print("physical modality/status:", json.dumps(modality_status, sort_keys=True), flush=True)
    if samples:
        print("physical error samples:", json.dumps(samples, sort_keys=True), flush=True)
    current_keys = {
        (str(x.get("epoch_id")), str(x.get("modality")), str(x.get("scene_id")))
        for x in observations
        if x.get("status") == "INGESTED_DERIVED"
    }
    current_derived = any(x.get("status") == "INGESTED_DERIVED" for x in observations)
    if not current_derived and any(x.get("status") == "INGESTED_DERIVED" for x in prior_observations):
        observations = list(prior_observations)
    else:
        observations.extend(
            x for x in prior_observations
            if x.get("status") == "INGESTED_DERIVED"
            and (str(x.get("epoch_id")), str(x.get("modality")), str(x.get("scene_id"))) not in current_keys
        )
        observations.sort(key=lambda x: (
            str(x.get("epoch_id")),
            str(x.get("modality")),
            str(x.get("observed_on")),
            str(x.get("scene_id")),
        ))
    save_json(OBS_JSON, {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "site_count_target": len(sites),
        "geocoded_site_count": sum(1 for x in coords.values() if x.get("lat") is not None),
        "observation_count": len(observations),
        "derived_observation_count": sum(1 for x in observations if x.get("status") == "INGESTED_DERIVED"),
        "records": observations,
        "semantics": "Compact derived metrics are computed from public raw COG windows. Full rasters are not committed. A source scene is not itself a positive finding about compute activity.",
    })
    csv_fields = [
        "epoch_id","site_name","address","latitude","longitude","coordinate_precision",
        "modality","sensor","scene_id","observed_on","stac_item_url","source_catalog",
        "source_collection","cloud_cover_pct","status","quality_flag","processing_version",
        "metrics_json","comparison_to_previous_json","error","semantics",
    ]
    with OBS_CSV.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for row in observations:
            out = {k: row.get(k) for k in csv_fields if k not in {"metrics_json","comparison_to_previous_json","semantics"}}
            out["semantics"] = "Derived observation retained from a public raw scene; absence or missing scene is not evidence of absence."
            out["metrics_json"] = json.dumps(row.get("metrics") or {}, sort_keys=True)
            out["comparison_to_previous_json"] = json.dumps(row.get("comparison_to_previous") or {}, sort_keys=True)
            writer.writerow(out)

    update_physical_layer(observations, coords, target_rows, existing_events)

    stack = load_json(SOURCE_STACK)
    sources = stack.get("sources", [])
    source_ids = {str(x.get("id")) for x in sources}
    additions = [
        {
            "id": "sentinel-2-stac-ingest",
            "name": "Copernicus Sentinel-2 L2A public STAC acquisition",
            "kind": "physical verification acquisition",
            "status": "INGESTED_DERIVED" if any(x.get("status") == "INGESTED_DERIVED" and x.get("modality") == "optical" for x in observations) else "SOURCE_AVAILABLE_NOT_INGESTED",
            "updated": datetime.now(timezone.utc).date().isoformat(),
            "url": "https://stac.dataspace.copernicus.eu/v1/",
            "role": "Raw Sentinel-2 scene windows processed into compact multi-temporal surface metrics.",
        },
        {
            "id": "sentinel-1-stac-ingest",
            "name": "Copernicus Sentinel-1 GRD public STAC acquisition",
            "kind": "physical verification acquisition",
            "status": "INGESTED_DERIVED" if any(x.get("status") == "INGESTED_DERIVED" and x.get("modality") == "sar" for x in observations) else "SOURCE_AVAILABLE_NOT_INGESTED",
            "updated": datetime.now(timezone.utc).date().isoformat(),
            "url": "https://stac.dataspace.copernicus.eu/v1/",
            "role": "Raw Sentinel-1 VV/VH scene windows processed into compact temporal backscatter metrics.",
        },
        {
            "id": "landsat-c2l2-st-stac-ingest",
            "name": "USGS Landsat Collection 2 Level-2 Surface Temperature public STAC acquisition",
            "kind": "physical verification acquisition",
            "status": "INGESTED_DERIVED" if any(x.get("status") == "INGESTED_DERIVED" and x.get("modality") == "tir" for x in observations) else "SOURCE_AVAILABLE_NOT_INGESTED",
            "updated": datetime.now(timezone.utc).date().isoformat(),
            "url": "https://landsatlook.usgs.gov/stac-server/",
            "role": "Raw Landsat surface-temperature scene windows processed into local thermal metrics.",
        },
        {
            "id": "transformer-event-research-queue",
            "name": "HV transformer event research queue",
            "kind": "physical verification research queue",
            "status": "RESEARCH_QUEUE",
            "updated": datetime.now(timezone.utc).date().isoformat(),
            "url": "data/track3/transformer_supply_chain_events.json",
            "role": "93-site worklist for public procurement, delivery and installation evidence; no events are invented.",
        },
    ]
    for item in additions:
        existing = next((source for source in sources if str(source.get("id")) == item["id"]), None)
        if existing is None:
            sources.append(item)
        else:
            existing.update(item)
    stack["sources"] = sources
    stack["source_stack_count"] = len(sources)
    stack["source_stack_status_counts"] = {
        status: sum(1 for source in sources if source.get("status") == status)
        for status in sorted({source.get("status") for source in sources if source.get("status")})
    }
    stack["generated_on"] = datetime.now(timezone.utc).date().isoformat()
    save_json(SOURCE_STACK, stack)

    schema = load_json(TRACK3_SCHEMA)
    for status in ("INGESTED_DERIVED", "INGESTED_DERIVED_PROXY", "RESEARCH_QUEUE"):
        if status not in schema.get("statuses", []):
            schema["statuses"].append(status)
    save_json(TRACK3_SCHEMA, schema)

    print(json.dumps({
        "site_count": len(sites),
        "geocoded_sites": sum(1 for x in coords.values() if x.get("lat") is not None),
        "derived_observations": sum(1 for x in observations if x.get("status") == "INGESTED_DERIVED"),
        "optical": sum(1 for x in observations if x.get("status") == "INGESTED_DERIVED" and x.get("modality") == "optical"),
        "tir": sum(1 for x in observations if x.get("status") == "INGESTED_DERIVED" and x.get("modality") == "tir"),
        "sar": sum(1 for x in observations if x.get("status") == "INGESTED_DERIVED" and x.get("modality") == "sar"),
        "transformer_events": len(existing_events),
        "transformer_targets": len(target_rows),
    }, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
