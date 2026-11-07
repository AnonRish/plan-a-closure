#!/usr/bin/env python3
"""Build the Track 3 entity-resolution layer from repository-published evidence.

The layer separates:
- source-observed entities and names;
- exact source relationships;
- conservative normalization-based name variants;
- explicit SEC Exhibit 21 parent/subsidiary edges;
- campus->building-geometry links;
- unresolved legal-entity research targets.

Confidence is an evidence-strength score, not a probability.
"""
from __future__ import annotations
import json, re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "data" / "track3"
EVIDENCE_URL = "https://epoch.ai/data/data-centers-documentation/records"

def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def clean(value):
    return re.sub(r"\s*#(confident|likely)\s*$", "", str(value or "")).strip()

def normalize(value):
    value = clean(value).lower().replace("&", " and ")
    value = re.sub(r"\b(incorporated|inc\.?|corporation|corp\.?|company|co\.?|limited|ltd\.?|l\.l\.c\.?|llc|l\.p\.?|lp|plc|holdings?)\b", " ", value)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()

def eid(value):
    key = normalize(value)
    return "ENT-" + re.sub(r"[^a-z0-9]+", "-", key)[:70]

def confidence(value):
    s = str(value or "")
    return 0.98 if re.search(r"#\s*confident", s, re.I) else 0.82 if re.search(r"#\s*likely", s, re.I) else 0.90

def split(value):
    return [clean(x) for x in re.split(r"[,;]\s*", str(value or "")) if clean(x)]

def main():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    m = re.search(r"const REGISTRY_DATA = (\[.*?\]);\n", html, re.S)
    if not m:
        raise SystemExit("REGISTRY_DATA not found")
    queue = json.loads(m.group(1))
    projects = load("data/project_level_extractions.json")["records"]
    site_evidence = load("data/epoch_site_evidence_records.json")["records"]
    epoch = load("data/external/epoch_ai/registry.json")["records"]
    footprints = {x["epoch_id"]: x for x in load("data/track3/building_footprints_index.json")["records"]}

    entities = {}
    relationships = []

    def add_entity(raw, kind, source, confidence_score=0.90):
        raw = clean(raw)
        key = normalize(raw)
        if not key or key in {"unknown", "null", "n a", "developer not disclosed", "developer not matched to known list"}:
            return None
        i = eid(raw)
        if i not in entities:
            entities[i] = {
                "entity_id": i,
                "canonical_name": raw,
                "entity_type": kind,
                "name_variants": [],
                "source_evidence_count": 0,
                "evidence_strength_max": confidence_score,
            }
        ent = entities[i]
        if raw not in ent["name_variants"]:
            ent["name_variants"].append(raw)
        ent["source_evidence_count"] += 1
        ent["evidence_strength_max"] = max(ent["evidence_strength_max"], confidence_score)
        return i

    def add_rel(frm, to, kind, evidence_id, source, url=None, score=0.90, temporal="CURRENT_OR_UNDATED", notes=None):
        if not frm or not to or frm == to:
            return
        relationships.append({
            "relationship_id": f"REL-{len(relationships)+1}",
            "from_entity_id": frm,
            "to_entity_id": to,
            "relationship_type": kind,
            "evidence_id": evidence_id,
            "source": source,
            "source_url": url,
            "confidence_score": score,
            "confidence_semantics": "evidence-strength score, not a probability",
            "temporal_status": temporal,
            "notes": notes,
        })

    # Canonical site nodes first.
    for s in epoch:
        n = s["normalized"]
        entities[s["epoch_id"]] = {
            "entity_id": s["epoch_id"],
            "canonical_name": n.get("name") or s["epoch_id"],
            "entity_type": "data_center_site",
            "name_variants": [n.get("name")] if n.get("name") else [],
            "source_evidence_count": 1,
            "evidence_strength_max": 0.99,
        }

    # Queue developer/project universe.
    for row in queue:
        d = add_entity(row.get("dev"), "developer_operator", "core_registry_queue")
        p = add_entity(row.get("proj"), "project_name", "core_registry_queue")
        if p and d:
            add_rel(p, d, "PROJECT_DEVELOPER", row.get("id"), "core_registry_queue", None, 0.96,
                    notes="Same-publisher row association; not corporate ownership.")

    # Project-level relationships.
    for row in projects:
        p = add_entity(row.get("project_name") or row.get("id"), "project_name", "project_level_extractions", 0.97)
        u = add_entity(row.get("utility_or_provider"), "utility_provider", "project_level_extractions", 0.97)
        a = add_entity(row.get("source_authority"), "regulatory_or_source_authority", "project_level_extractions", 0.99)
        if p and u:
            add_rel(p, u, "PROJECT_UTILITY_PROVIDER", row["id"], "project_level_extractions", row.get("source_url"), 0.97, "OBSERVED")
        if p and a:
            add_rel(p, a, "PROJECT_SOURCE_AUTHORITY", row["id"], "project_level_extractions", row.get("source_url"), 0.99, "OBSERVED",
                    "Publisher/source authority metadata, not ownership.")

    # Site-evidence authorities.
    for row in site_evidence:
        rr = add_entity(row.get("record_name") or row.get("id"), "public_record", "epoch_site_evidence_records", 0.99)
        aa = add_entity(row.get("authority"), "utility_or_authority", "epoch_site_evidence_records", 0.99)
        if rr and aa:
            add_rel(rr, aa, "RECORD_AUTHORITY", row["id"], "epoch_site_evidence_records", row.get("source_url"), 0.99, "OBSERVED")

    # Epoch ownership/operator/utility/constructor/user relationships.
    for s in epoch:
        n, sid = s["normalized"], s["epoch_id"]
        owner = add_entity(n.get("owner"), "owner_operator", "epoch_ai_registry", confidence(n.get("owner")))
        if owner:
            add_rel(sid, owner, "SITE_OWNER_OPERATOR", sid, "epoch_ai_registry", EVIDENCE_URL, confidence(n.get("owner")),
                    "OBSERVED_OR_REPORTED", "Explicit Epoch owner field.")
        for value in split(n.get("users")):
            uid = add_entity(value, "compute_user_operator", "epoch_ai_registry", confidence(value))
            if uid:
                add_rel(sid, uid, "SITE_COMPUTE_USER", sid, "epoch_ai_registry", EVIDENCE_URL, confidence(value),
                        "OBSERVED_OR_REPORTED", "Explicit Epoch users field.")
        for value in split(n.get("energy_companies")):
            uid = add_entity(value, "energy_company_or_utility", "epoch_ai_registry", 0.97)
            if uid:
                add_rel(sid, uid, "SITE_ENERGY_COMPANY", sid, "epoch_ai_registry", EVIDENCE_URL, 0.97,
                        "OBSERVED_OR_REPORTED", "Explicit Epoch energy-company field.")
        for value in split(n.get("construction_companies")):
            uid = add_entity(value, "construction_company", "epoch_ai_registry", 0.95)
            if uid:
                add_rel(sid, uid, "SITE_CONSTRUCTION_COMPANY", sid, "epoch_ai_registry", EVIDENCE_URL, 0.95,
                        "OBSERVED_OR_REPORTED", "Explicit Epoch construction-company field.")
        project = add_entity(n.get("project"), "project_name", "epoch_ai_registry", confidence(n.get("project")))
        if project:
            add_rel(sid, project, "SITE_PROJECT_REFERENCE", sid, "epoch_ai_registry", EVIDENCE_URL, confidence(n.get("project")),
                    "OBSERVED_OR_REPORTED", "Publisher project field; not asserted to be a legal alias.")

    # Campus -> building geometry sets.
    building_sites = building_polygons = 0
    for sid, fp in footprints.items():
        if not fp.get("geometry_file"):
            continue
        bid = "BLDGSET-" + sid
        entities[bid] = {
            "entity_id": bid,
            "canonical_name": f"Building footprint set — {fp.get('site_name') or sid}",
            "entity_type": "campus_building_geometry_set",
            "name_variants": [],
            "source_evidence_count": 1,
            "evidence_strength_max": 0.99,
        }
        building_sites += 1
        building_polygons += int(fp.get("polygon_count") or 0)
        add_rel(sid, bid, "SITE_BUILDING_GEOMETRY_SET", f"FP-{sid}", "Overture Maps buildings",
                fp.get("source_url"), 0.99, "CURRENT_SNAPSHOT",
                f"{fp.get('polygon_count') or 0} polygons; release {fp.get('source_release') or 'unspecified'}.")

    # Source-backed corporate-family seeds.
    families = [
        ("CoreWeave, Inc.", ["CoreWeave Compute Acquisition Co. II, LLC","CoreWeave Compute Acquisition Co. III, LLC","CoreWeave Compute Acquisition Co. IV, LLC","CoreWeave Compute Acquisition Co. V, LLC","CoreWeave Compute Acquisition Co. VI, LLC","CoreWeave UK Limited","CoreWeave Norway AS","CoreWeave Sweden AB"],
         "https://www.sec.gov/Archives/edgar/data/1769628/000176962826000104/ex211-coreweaveincx10xk.htm", "CURRENT_REPORT"),
        ("Equinix, Inc.", ["Equinix (Canada) Enterprises Ltd.","Equinix (Canada) Services Ltd.","CHI 3, LLC","CHI 3 Procurement, LLC","Equinix (DB1) Limited","Equinix (France) SAS"],
         "https://www.sec.gov/Archives/edgar/data/1101239/000110465926015365/eqix-q126xexhibit211.htm", "CURRENT_REPORT"),
        ("Iron Mountain Incorporated", ["Iron Mountain Data Centers, LLC","Iron Mountain Data Centers U.S. Holdings, LLC","Iron Mountain Data Centers Arizona 3, LLC","Iron Mountain Data Centers Virginia 3, LLC","Iron Mountain (UK) Data Centre Limited","Iron Mountain Canada Operations ULC"],
         "https://www.sec.gov/Archives/edgar/data/1020569/000102056926000013/irm2025ex-211.htm", "CURRENT_REPORT"),
        ("Digital Realty Trust, Inc.", ["Digital Realty Management Services, LLC","Digital Realty Property Manager, LLC","Digital Realty Sweden AB","Digital Realty Trust, LLC","Nova DC Fee Owner, L.P.","Nova DC Holdings, L.P."],
         "https://www.sec.gov/Archives/edgar/data/1494877/000110465926015365/dlr-20251231xex21d1.htm", "CURRENT_REPORT"),
        ("QTS Realty Trust, Inc.", ["QTS Critical Facilities Management, LLC","QTS Finance Corporation","Quality Investment Properties Irving, LLC","Quality Technology Services Lenexa, LLC","Quality Technology Services Richmond II, LLC","QAE Acquisition Company, LLC"],
         "https://www.sec.gov/Archives/edgar/data/1561164/000114420416084912/v429670_ex21-1.htm", "HISTORICAL_REPORT_2016"),
    ]
    for parent, children, url, temporal in families:
        p = add_entity(parent, "corporate_parent", "SEC_Exhibit_21", 1.0)
        for child in children:
            c = add_entity(child, "legal_entity_subsidiary", "SEC_Exhibit_21", 1.0)
            add_rel(p, c, "PARENT_SUBSIDIARY", f"SEC-{normalize(child)}", "SEC_Exhibit_21", url, 1.0, temporal,
                    "SEC Exhibit 21 lists the subsidiary under the registrant.")

    variant_groups = [
        {"entity_id": e["entity_id"], "canonical_name": e["canonical_name"], "variants": e["name_variants"],
         "match_method":"normalization_only", "status":"NAME_VARIANTS_NOT_LEGAL_ALIAS",
         "confidence_score":0.75, "confidence_semantics":"heuristic grouping, not probability"}
        for e in entities.values() if len(e["name_variants"]) > 1
    ]
    legal = []
    legal_pattern = re.compile(r"\b(llc|l\.l\.c|lp|l\.p|limited|inc|incorporated|corp|corporation|holdings?)\b", re.I)
    children = {r["to_entity_id"] for r in relationships if r["relationship_type"] == "PARENT_SUBSIDIARY"}
    for e in entities.values():
        if legal_pattern.search(e["canonical_name"]):
            legal.append({
                "entity_id": e["entity_id"],
                "entity_name": e["canonical_name"],
                "resolution_state": "PARENT_LINK_PRESENT" if e["entity_id"] in children else "UNRESOLVED_LEGAL_ENTITY",
                "next_sources": ["GLEIF LEI / Level 2", "OpenCorporates relationships/statements", "SEC EDGAR Exhibit 21", "State/provincial corporate registry"],
                "note": "Legal-form suffix does not establish shell-company status.",
            })

    stats = {
        "core_queue_rows": len(queue),
        "distinct_developer_strings": len({clean(x.get("dev")) for x in queue if clean(x.get("dev"))}),
        "distinct_core_project_names": len({clean(x.get("proj")) for x in queue if clean(x.get("proj"))}),
        "project_level_records": len(projects),
        "site_evidence_records": len(site_evidence),
        "entity_count": len(entities),
        "relationship_edge_count": len(relationships),
        "parent_subsidiary_edges": sum(r["relationship_type"] == "PARENT_SUBSIDIARY" for r in relationships),
        "variant_groups": len(variant_groups),
        "legal_entity_research_targets": len(legal),
        "building_geometry_sites": building_sites,
        "building_polygons": building_polygons,
    }
    artifact = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "title": "Track 3 Entity Resolution Layer",
        "semantics": "Confidence is evidence strength, not probability. Name normalization is a reconciliation key, not proof of legal identity. Missing ownership, landowner, colocation and shell-company findings remain unresolved rather than inferred.",
        "stats": stats,
        "checklist": [
            {"id":"DEVELOPER_OPERATOR_DATABASE","item":"Much larger developer/operator database","status":"INGESTED",
             "coverage":f"{stats['entity_count']} entity records including {stats['distinct_developer_strings']} distinct developer strings from {stats['core_queue_rows']} core queue rows."},
            {"id":"PARENT_SUBSIDIARY_GRAPH","item":"Parent/subsidiary/LLC ownership graph","status":"INGESTED_PARTIAL",
             "coverage":f"{stats['parent_subsidiary_edges']} explicit SEC Exhibit 21 parent→subsidiary edges across five corporate families; unresolved legal entities remain queued."},
            {"id":"CAMPUS_BUILDING_MAPPING","item":"Data-center campus ↔ individual buildings mapping","status":"INGESTED_PARTIAL",
             "coverage":f"{stats['building_geometry_sites']} Epoch sites have {stats['building_polygons']} published building polygons joined to site IDs; individual legal-entity building ownership is not inferred."},
            {"id":"CLOUD_COLO_LANDOWNER_UTILITY","item":"Cloud provider ↔ colocation provider ↔ landowner ↔ utility relationships","status":"INGESTED_PARTIAL",
             "coverage":"Owner/operator, compute-user, energy-company/utility, construction-company and project-provider relationships are captured where explicitly published. Landowner and colocation-provider roles remain unresolved where not published."},
            {"id":"PROJECT_ALIASES","item":"Project-name aliases","status":"CANDIDATE_LAYER",
             "coverage":f"{stats['variant_groups']} normalized name-variant groups are retained as review candidates; none is labeled a legal alias from similarity alone."},
            {"id":"HISTORICAL_DEVELOPER_NAMES","item":"Historical developer names","status":"SOURCE_VARIANT_LAYER",
             "coverage":"Dated source mentions and historical SEC subsidiary records are retained; renamings are not inferred from name similarity."},
            {"id":"SHELL_COMPANY_RESOLUTION","item":"Shell-company resolution","status":"RESEARCH_QUEUE",
             "coverage":f"{stats['legal_entity_research_targets']} legal-form candidates are queued against GLEIF, OpenCorporates, SEC and jurisdictional registries. No entity is called a shell solely from its legal suffix."},
            {"id":"CONFIDENCE_EVIDENCE","item":"Confidence score + evidence for every identity match","status":"INGESTED",
             "coverage":f"{stats['relationship_edge_count']} relationship edges carry evidence IDs, source URLs where available, temporal state and numeric evidence-strength scores."},
        ],
        "source_catalog":[
            {"id":"GLEIF","name":"GLEIF LEI Level 2 ownership data","url":"https://www.gleif.org/en/lei-data/access-and-use-lei-data/level-2-data-who-owns-whom","role":"Global legal-entity identity and direct/ultimate-parent relationships."},
            {"id":"OPENCORPORATES","name":"OpenCorporates relationships/statements","url":"https://api.opencorporates.com/documentation/API-Reference","role":"Company reconciliation and relationship provenance."},
            {"id":"SEC_EDGAR","name":"SEC EDGAR","url":"https://www.sec.gov/edgar/search/","role":"Public-registrant subsidiary and corporate-family filings."},
        ],
        "entities": list(entities.values()),
        "relationships": relationships,
        "name_variant_groups": variant_groups,
        "legal_entity_research_queue": legal,
        "unresolved_role_gaps": [
            {"epoch_id":s["epoch_id"],"site_name":s["normalized"].get("name") or s["epoch_id"],
             "missing_roles":["landowner","colocation_provider"],"status":"RESEARCH_QUEUE",
             "note":"Only roles explicitly published in the current repository are promoted to relationships."}
            for s in epoch
        ],
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "entity_resolution.json").write_text(json.dumps(artifact, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    def csv_line(values):
        import csv, io
        b=io.StringIO();csv.writer(b).writerow(values);return b.getvalue().rstrip("\r\n")
    (OUT / "entity_resolution_entities.csv").write_text(
        "\n".join([csv_line(["entity_id","canonical_name","entity_type","name_variants","source_evidence_count","evidence_strength_max"])] +
                   [csv_line([e["entity_id"],e["canonical_name"],e["entity_type"]," | ".join(e["name_variants"]),e["source_evidence_count"],e["evidence_strength_max"]]) for e in entities.values()])+"\n",
        encoding="utf-8")
    (OUT / "entity_resolution_relationships.csv").write_text(
        "\n".join([csv_line(["relationship_id","from_entity_id","to_entity_id","relationship_type","evidence_id","source","source_url","confidence_score","temporal_status","notes"])] +
                   [csv_line([r.get(k) for k in ["relationship_id","from_entity_id","to_entity_id","relationship_type","evidence_id","source","source_url","confidence_score","temporal_status","notes"]]) for r in relationships])+"\n",
        encoding="utf-8")
    (OUT / "entity_resolution_research_queue.csv").write_text(
        "\n".join([csv_line(["entity_id","entity_name","resolution_state","next_sources","note"])] +
                   [csv_line([r["entity_id"],r["entity_name"],r["resolution_state"]," | ".join(r["next_sources"]),r["note"]]) for r in legal])+"\n",
        encoding="utf-8")
    print(json.dumps(stats, indent=2))

if __name__ == "__main__":
    main()
