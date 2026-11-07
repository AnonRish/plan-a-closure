#!/usr/bin/env python3
"""Build normalized claim-level Track 3 artifact from public-web enrichment."""
# Deterministic Track 3 claim normalization: keep generated claims lossless with the source layer.
# Trigger a controlled pipeline refresh after Track 3 writer-lane hardening.
from __future__ import annotations
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "data/track3/public_web_enrichment_2026-09-27.json"
OUT = ROOT / "data/track3/public_web_claims.json"

DOMAIN_MAP = {"site_identity":"site_identity","address":"site_identity","location":"site_identity","project":"site_identity","project_status":"site_identity","operational_status":"site_identity","owner":"ownership","investors":"financing","investment":"financing","capex_record":"financing","construction_companies":"construction","construction_status":"construction","construction_workforce_record":"construction","chip_quantities":"chip_inventory","users":"compute_tenancy","capacity_record":"capacity","service_or_contract":"service_or_contract","regulatory":"regulatory","energy_companies":"grid_connection","cooling":"cooling","backup_generation":"power_telemetry","operational_efficiency":"operations","chip_ownership":"chip_ownership","chip_shipments":"chip_shipments","chip_users":"chip_users"}

def stable_claim_id(x: dict) -> str:
    evidence_id = str(x.get("evidence_id") or "").strip()
    if evidence_id:
        return evidence_id
    key = {
        "site_name": x.get("site_name"),
        "field": x.get("field"),
        "value": x.get("value"),
        "relationship": x.get("relationship"),
        "source": x.get("source"),
        "source_urls": x.get("source_urls") or [],
        "publication_date": x.get("publication_date"),
    }
    payload = json.dumps(key, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    # Stable, non-cryptographic FNV-1a digest for unbound source records.
    h = 1469598103934665603
    for b in payload.encode("utf-8"):
        h ^= b
        h = (h * 1099511628211) & 0xffffffffffffffff
    return "PWEB-SOURCE-" + f"{h:016x}"

def main() -> int:
    d = json.loads(SRC.read_text(encoding="utf-8"))
    claims = []
    for x in d.get("records", []):
        site_scoped = bool(x.get("epoch_id"))
        claims.append({
            "claim_id": stable_claim_id(x),
            "epoch_id": x.get("epoch_id"),
            "site_name": x.get("site_name"),
            "domain": DOMAIN_MAP.get(x.get("field"), "other"),
            "field": x.get("field"),
            "value": x.get("value"),
            "relationship": x.get("relationship"),
            "source": x.get("source"),
            "source_urls": x.get("source_urls") or [],
            "publication_date": x.get("publication_date"),
            "capture_date": x.get("capture_date"),
            "disposition": x.get("disposition") or "PUBLIC_SOURCE_CAPTURED",
            "scope_note": x.get("scope_note"),
            "claim_scope": "site_level_public_web" if site_scoped else "state_or_multi_site_public_web",
            "provenance_status": "source_link_retained" if x.get("evidence_id") else "source_link_retained_no_source_id",
            "source_record_id": x.get("evidence_id"),
        })

    out = {
        "schema_version": 2,
        "generated_on": "2026-09-27",
        "title": "Track 3 public-web claim layer",
        "purpose": "Normalized claim-level representation of the public-web enrichment layer. Site-scoped records require an Epoch site ID; state/multi-site and explicit negative-capture records may remain unbound while retaining source provenance.",
        "accounting": {
            "claim_count": len(claims),
            "site_scoped_claim_count": sum(1 for x in claims if x["claim_scope"] == "site_level_public_web"),
            "unbound_public_claim_count": sum(1 for x in claims if x["claim_scope"] != "site_level_public_web"),
            "site_count": len({x["epoch_id"] for x in claims if x["epoch_id"]}),
            "domain_counts": {},
        },
        "claims": claims,
    }
    for x in claims:
        out["accounting"]["domain_counts"][x["domain"]] = out["accounting"]["domain_counts"].get(x["domain"], 0) + 1

    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(out["accounting"], indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
