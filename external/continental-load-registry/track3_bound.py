#!/usr/bin/env python3
"""Conservative Track 3 residual-compute bound engine.

This tool fuses independently supplied capacity estimates and a declared
inventory. It refuses to produce a numeric global bound when the accounting
population is explicitly open. That is deliberate: incomplete population
coverage is not evidence of absence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from track3_certificate import one_sided_failure_upper_bound


def _sha(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def site_upper_bound(site: dict[str, Any]) -> dict[str, Any]:
    declared = site.get("declared_accelerators")
    estimates = [
        float(v)
        for source, v in (site.get("independent_capacity_estimates") or {}).items()
        if v is not None
    ]
    if declared is None:
        return {
            "site_id": site.get("site_id"),
            "status": "UNKNOWN",
            "upper_bound_accelerators": None,
            "reason": "declared accelerator inventory is missing",
        }
    if not estimates:
        return {
            "site_id": site.get("site_id"),
            "status": "UNKNOWN",
            "upper_bound_accelerators": None,
            "reason": "no independent site capacity estimate is available",
        }
    ceiling = max(estimates)
    residual = max(0.0, ceiling - float(declared))
    return {
        "site_id": site.get("site_id"),
        "status": "PASS",
        "declared_accelerators": float(declared),
        "maximum_independent_capacity": ceiling,
        "upper_bound_accelerators": residual,
        "source_count": len(estimates),
    }


def compute_track3_bound(
    *,
    population_closed: bool,
    sites: list[dict[str, Any]],
    tail_compute_units: float | None = None,
    tail_sample_size: int | None = None,
    tail_failures: int | None = None,
    delta: float = 0.05,
    untraced_pool_units: float | None = None,
) -> dict[str, Any]:
    site_results = [site_upper_bound(site) for site in sites]
    unknown_sites = [r for r in site_results if r["status"] != "PASS"]

    if not population_closed:
        return {
            "schema_version": 1,
            "status": "UNKNOWN",
            "claim": "upper bound on globally untraced compute",
            "reason": "accounting population is not closed; a public registry must not infer absence from missing population coverage",
            "site_results": site_results,
            "unknown_site_count": len(unknown_sites),
            "global_upper_bound_accelerators": None,
            "bound_method": "NO_GLOBAL_NUMERIC_BOUND_WHEN_POPULATION_OPEN",
        }

    if unknown_sites:
        return {
            "schema_version": 1,
            "status": "UNKNOWN",
            "claim": "upper bound on untraced compute in the declared closed population",
            "reason": "closed population still contains sites without independent capacity evidence",
            "site_results": site_results,
            "unknown_site_count": len(unknown_sites),
            "global_upper_bound_accelerators": None,
            "bound_method": "SITE_EVIDENCE_INCOMPLETE",
        }

    if untraced_pool_units is None:
        return {
            "schema_version": 1,
            "status": "UNKNOWN",
            "claim": "upper bound on untraced compute in the declared closed population",
            "reason": "untraced pool L was not supplied; the certificate bounds D + L and L cannot be assumed zero",
            "site_results": site_results,
            "unknown_site_count": 0,
            "global_upper_bound_accelerators": None,
            "bound_method": "UNTRACED_POOL_L_MISSING",
        }
    if untraced_pool_units < 0:
        raise ValueError("untraced_pool_units must be >= 0")

    site_bound = sum(float(r["upper_bound_accelerators"]) for r in site_results)
    tail_bound = 0.0
    tail_result = None
    if tail_compute_units is not None:
        if tail_sample_size is None or tail_failures is None:
            return {
                "schema_version": 1,
                "status": "UNKNOWN",
                "claim": "upper bound on untraced compute",
                "reason": "tail compute was supplied without complete sampling inputs",
                "site_results": site_results,
                "global_upper_bound_accelerators": None,
            }
        rate = one_sided_failure_upper_bound(tail_failures, tail_sample_size, delta)
        tail_bound = float(tail_compute_units) * rate
        tail_result = {
            "tail_compute_units": float(tail_compute_units),
            "sample_size": tail_sample_size,
            "observed_failures": tail_failures,
            "delta": delta,
            "upper_failure_rate": rate,
            "upper_bound_untraced_compute_units": tail_bound,
        }

    pool = float(untraced_pool_units)
    return {
        "schema_version": 1,
        "status": "PASS",
        "claim": "upper bound on untraced compute in the declared closed population",
        "site_results": site_results,
        "unknown_site_count": 0,
        "site_upper_bound_accelerators": site_bound,
        "tail_sampling": tail_result,
        "untraced_pool_units": pool,
        "global_upper_bound_accelerators": site_bound + tail_bound + pool,
        "bound_method": "MAX_INDEPENDENT_SITE_CAPACITY_MINUS_DECLARED_PLUS_OPTIONAL_TAIL_STATISTICAL_BOUND_PLUS_UNTRACED_POOL_L",
        "limitations": [
            "This is an accounting bound, not proof that no covert compute exists.",
            "The bound is only as good as the declared closed population and independence of supplied capacity estimates.",
            "Accelerator counts and compute capacity are intentionally kept as separate quantities.",
            "L (untraced pool) is added in full: it is a measured quantity that further sampling cannot reduce.",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    data = json.loads(args.input.read_text(encoding="utf-8"))
    result = compute_track3_bound(
        population_closed=bool(data.get("population_closed", False)),
        sites=list(data.get("sites", [])),
        tail_compute_units=data.get("tail_compute_units"),
        tail_sample_size=data.get("tail_sample_size"),
        tail_failures=data.get("tail_failures"),
        delta=float(data.get("delta", 0.05)),
        untraced_pool_units=data.get("untraced_pool_units"),
    )
    result["input_sha256"] = _sha(data)
    output = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
