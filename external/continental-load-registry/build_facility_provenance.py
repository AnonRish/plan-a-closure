#!/usr/bin/env python3
"""Build the Track 3 facility-level provenance ledger conservatively."""
from __future__ import annotations
import csv,json,os,re,hashlib
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent; OUT=ROOT/"data"/"track3"; COMMIT=os.getenv("GITHUB_SHA","WORKTREE_UNRESOLVED")
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
def clean(v):
    if v is None:return None
    s=str(v).strip(); return re.sub(r"\s+"," ",s) if s else None
def links(s): return [m.group(1) for m in re.finditer(r"\[[^\]]+\]\((https?://[^)\s]+)\)",str(s or ""))]
def origin(kind,name):
    s=(str(kind or "")+" "+str(name or "")).lower()
    if "secondary" in s:return ("secondary","Source metadata explicitly describes a secondary source.")
    if re.search(r"official|regulatory|filing|permit|company disclosure|continuing-disclosure|government|utility filing",s):
        return ("primary","Source metadata explicitly indicates an official/company/regulatory/filing/permit origin.")
    if re.search(r"local reporting|facility registry|public-source|municipal",s):
        return ("secondary","Source metadata indicates reporting/registry/public-source material.")
    return ("unclassified","Current repository metadata does not establish primary/secondary status.")
FIELD_PAIRS=[("Name","name"),("Current H100 equivalents","current_h100_equivalents"),("Current power (MW)","current_power_mw"),("Current total capital cost (2025 USD billions)","current_total_capital_cost_b_2025"),("Owner","owner"),("Users","users"),("Selected Sources","selected_sources"),("Calculations sheet","calculations_sheet"),("Project","project"),("Current chip types","current_chip_types"),("All chip types","all_chip_types"),("Investors","investors"),("Construction companies","construction_companies"),("Energy companies","energy_companies"),("Country","country"),("Address","address")]
def main():
    epoch=load("data/external/epoch_ai/registry.json"); evid=load("data/track3/evidence_records.json")["records"]; sites=load("data/track3/site_status.json")["records"]; fp=load("data/track3/building_footprints_index.json")["records"]
    ev_by={}
    for e in evid: ev_by.setdefault(e.get("target_id"),[]).append(e)
    fp_by={x.get("epoch_id"):x for x in fp}; site_by={x.get("epoch_id"):x for x in sites}
    facilities=[]
    for s in epoch["records"]:
        n=s.get("normalized",{}); raw=s.get("raw",{}); evs=ev_by.get(s["epoch_id"],[]); fields=[]
        for rn,nk in FIELD_PAIRS:
            rv=raw.get(rn); nv=n.get(nk)
            if rn in {"Current H100 equivalents","Current power (MW)","Current total capital cost (2025 USD billions)"}: t="Parsed numeric publisher field; unit semantics retained from field name."
            elif rn=="Selected Sources": t="Markdown link extraction only; original raw source-list text remains retained."
            elif rn in {"Users","Owner","Project","Current chip types","All chip types"}: t="Whitespace trimming only; publisher confidence suffixes remain in raw value."
            else: t="Whitespace normalization only; no semantic inference."
            fields.append({"field_id":re.sub(r"[^a-z0-9]+","_",rn.lower()),"raw_source":{"repository_path":"data/external/epoch_ai/data_centers.csv","field_name":rn,"external_dataset_url":epoch["source"].get("data_centers_url")},"source_publication_date":None,"capture_date":epoch["source"].get("accessed_on"),"raw_value":rv,"normalized_value":nv,"transformation":t,"evidence_type":"publisher_dataset_field","confidence":"source-published","confidence_semantics":"Source-field provenance, not probability."})
        eitems=[]
        for e in evs:
            cls,basis=origin(e.get("source_kind"),e.get("source_name")); urls=list(dict.fromkeys((e.get("source_urls") or []) + ([e.get("source_url")] if e.get("source_url") else [])))
            eitems.append({"evidence_id":e.get("evidence_id"),"domain":e.get("domain"),"evidence_type":e.get("evidence_type"),"status":e.get("status"),"source":{"name":e.get("source_name"),"kind":e.get("source_kind"),"urls":urls,"publication_date":None,"publication_date_status":"NOT_CAPTURED_IN_CURRENT_REPOSITORY","record_locator":e.get("record_id") or e.get("record_name") or e.get("id")},"capture_date":e.get("captured_on") or e.get("capture_date"),"observed_on":e.get("observed_on"),"exact_source_field":None,"exact_source_value":None,"retained_basis":e.get("basis"),"transformation":"Existing repository evidence record retained; builder adds provenance metadata only.","confidence":e.get("confidence"),"confidence_semantics":"Published evidence confidence label, not probability.","evidence_origin":cls,"origin_basis":basis,"site_specific":e.get("site_specific"),"review_state":e.get("review_state","UNSPECIFIED")})
        urls=sorted({u for e in eitems for u in e["source"]["urls"]}); names=sorted({e["source"]["name"] for e in eitems if e["source"]["name"]})
        corr={"status":"CORROBORATION_PRESENT" if len(urls)>=2 and len(names)>=2 else ("SINGLE_SOURCE" if len(urls)==1 else "NO_RETAINED_CORROBORATION"),"distinct_source_url_count":len(urls),"distinct_source_name_count":len(names),"method":"Distinct retained source URL/name metadata; this does not prove methodological independence."}
        conflicts=[]; groups={}
        for e in evs:
            if e.get("capacity_mw") is not None: groups.setdefault((e.get("domain"),e.get("evidence_type")),[]).append(e)
        for key,arr in groups.items():
            if len({float(e["capacity_mw"]) for e in arr})>1: conflicts.append({"claim_group":"|".join(key),"values":[{"evidence_id":e.get("id"),"value":e.get("capacity_mw"),"source":e.get("source_kind")} for e in arr],"conflict_type":"DIFFERING_STRUCTURED_CAPACITY_VALUES"})
        dates=[x for x in [epoch["source"].get("accessed_on"),fp_by.get(s["epoch_id"],{}).get("captured_on"),site_by.get(s["epoch_id"],{}).get("last_verified_on"),*[e.get("captured_on") for e in evs]] if x]; last=max(dates) if dates else None
        facilities.append({"facility_id":s["epoch_id"],"facility_name":n.get("name") or s["epoch_id"],"location":{"country":n.get("country"),"state_province":n.get("region_inferred_from_address"),"address":n.get("address")},"canonical_source":{"publisher":epoch["source"].get("publisher"),"dataset":epoch["source"].get("dataset"),"dataset_url":epoch["source"].get("data_centers_url"),"repository_raw_path":"data/external/epoch_ai/data_centers.csv","repository_registry_path":"data/external/epoch_ai/registry.json","source_dataset_update_date":epoch["source"].get("data_centers_updated"),"capture_date":epoch["source"].get("accessed_on"),"publication_date":None,"publication_date_status":"DATASET_UPDATE_DATE_IS_NOT_TREATED_AS_PUBLICATION_DATE","external_raw_sha256":epoch["source"].get("raw_sha256",{}).get("data_centers.csv")},"field_provenance":fields,"selected_external_sources":[{"original_raw_source_url":u,"source_publication_date":None,"publication_date_status":"NOT_CAPTURED_IN_CURRENT_REPOSITORY","capture_date":epoch["source"].get("accessed_on"),"evidence_type":"selected_external_source_reference","confidence":"not_assessed","primary_secondary":"unclassified","transformation":"URL extracted from retained Epoch Selected Sources field; target document not mirrored."} for u in links(raw.get("Selected Sources"))],"evidence_records":eitems,"independent_corroboration":corr,"conflicting_evidence":{"status":"STRUCTURED_CONFLICTS_PRESENT" if conflicts else "NO_STRUCTURED_CONFLICT_OBSERVED","conflicts":conflicts,"scope":"Structured retained fields only."},"verification":{"last_verification_date":last,"reviewer_audit_trail":[{"event":"AUTOMATED_PROVENANCE_BUILD","actor_type":"automated_builder","actor":"build_facility_provenance.py","human_reviewer":None,"repository_commit":COMMIT,"review_state":"AUTOMATED"}],"manual_review_status":"NO_HUMAN_REVIEWER_RECORDED"},"immutable_snapshot":{"snapshot_commit":COMMIT,"retention":"Git history plus content-addressed repository blobs; external source documents are not universally archived."}})
    checklist=[
      {"id":"ORIGINAL_RAW_SOURCE","status":"PARTIAL","coverage":"Epoch raw publisher fields retained for all facilities; linked external documents referenced, not universally mirrored."},
      {"id":"SOURCE_URL","status":"INGESTED","coverage":"Canonical dataset, selected external source URLs, and evidence-record source URLs retained."},
      {"id":"SOURCE_PUBLICATION_DATE","status":"PARTIAL","coverage":"Individual publication dates remain null unless explicitly captured; dataset update/access dates are separate."},
      {"id":"CAPTURE_DATE","status":"INGESTED","coverage":"Epoch access date plus evidence/footprint capture dates retained where available."},
      {"id":"EXACT_SOURCE_FIELD_VALUE","status":"PARTIAL","coverage":"Exact field/value captured for retained Epoch raw fields; third-party source excerpts are not archived."},
      {"id":"NORMALIZED_VALUE","status":"INGESTED","coverage":"Raw publisher values paired with normalized values."},
      {"id":"TRANSFORMATION","status":"INGESTED","coverage":"Every publisher field documents the conservative transformation applied."},
      {"id":"EVIDENCE_TYPE","status":"INGESTED","coverage":"Existing evidence types carried through."},
      {"id":"EVIDENCE_CONFIDENCE","status":"INGESTED","coverage":"Existing confidence labels retained verbatim."},
      {"id":"PRIMARY_SECONDARY","status":"PARTIAL","coverage":"Conservative metadata classification; unclassified records remain unclassified."},
      {"id":"INDEPENDENT_CORROBORATION","status":"DERIVED_CONSERVATIVE","coverage":"Distinct retained source URL/name test; not proof of independence."},
      {"id":"CONFLICTING_EVIDENCE","status":"DERIVED_STRUCTURED_ONLY","coverage":"Only differing structured retained values are flagged."},
      {"id":"LAST_VERIFICATION_DATE","status":"DERIVED","coverage":"Latest available retained capture/access date per facility."},
      {"id":"REVIEWER_AUDIT_TRAIL","status":"AUTOMATED_ONLY","coverage":"Automated build events recorded; no human reviewer invented."},
      {"id":"IMMUTABLE_HISTORICAL_SNAPSHOTS","status":"REPOSITORY_GIT_HISTORY","coverage":"Each build records its Git commit and SHA-256 input hashes in a new snapshot manifest."}
    ]
    source_paths=["data/external/epoch_ai/registry.json","data/track3/evidence_records.json","data/track3/site_status.json","data/track3/building_footprints_index.json","data/track3/time_series_verification.json"]
    source_artifacts=[{"path":p,"sha256":hashlib.sha256((ROOT/p).read_bytes()).hexdigest()} for p in source_paths]
    out={"schema_version":1,"title":"Track 3 facility-level evidence/provenance ledger","generated_at_utc":datetime.now(timezone.utc).isoformat(),"snapshot":{"source_commit":COMMIT},"semantics":{"missing_data":"Null/UNKNOWN means not captured; never evidence of absence.","confidence":"Evidence strength is not probability.","independence":"Metadata-derived corroboration does not prove methodological independence.","conflict_scope":"Only structured retained fields are conflict-checked.","publication_dates":"Do not substitute dataset update date for source publication date."},"checklist":checklist,"summary":{"facility_count":len(facilities),"evidence_record_count":len(evid),"field_provenance_items":sum(len(f["field_provenance"]) for f in facilities),"facilities_with_selected_external_sources":sum(bool(f["selected_external_sources"]) for f in facilities),"facilities_with_corrob":sum(f["independent_corroboration"]["status"]=="CORROBORATION_PRESENT" for f in facilities),"facilities_with_structured_conflicts":sum(bool(f["conflicting_evidence"]["conflicts"]) for f in facilities)},"source_artifacts":source_artifacts,"facilities":facilities}
    (OUT/"facility_provenance.json").write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    (OUT/"provenance_snapshots").mkdir(parents=True,exist_ok=True)
    snap_id=COMMIT[:12] if COMMIT!="WORKTREE_UNRESOLVED" else TODAY
    snapshot={"schema_version":1,"snapshot_id":"PROV-"+snap_id,"created_at_utc":datetime.now(timezone.utc).isoformat(),"created_from_commit":COMMIT,"facility_count":len(facilities),"evidence_record_count":len(evid),"provenance_artifact_path":"data/track3/facility_provenance.json","source_artifacts":source_artifacts,"historical_retention":"Git history plus SHA-256 input hashes. External source documents remain referenced rather than universally archived.","limitations":["External source documents are not universally mirrored.","Publication dates are null when not explicitly captured.","No human reviewer is asserted by this automated build."]}
    (OUT/"provenance_snapshots"/(snap_id+".json")).write_text(json.dumps(snapshot,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    with (OUT/"facility_provenance_records.csv").open("w",newline="",encoding="utf-8") as f:
        w=csv.writer(f);w.writerow(["facility_id","facility_name","item_kind","source_url","source_publication_date","capture_date","raw_source_field","raw_value","normalized_value","transformation","evidence_type","confidence","evidence_origin","independence_status","conflict_status","last_verification_date","review_state"])
        for x in facilities:
            for p in x["field_provenance"]: w.writerow([x["facility_id"],x["facility_name"],"field",p["raw_source"]["external_dataset_url"],p["source_publication_date"],p["capture_date"],p["raw_source"]["field_name"],p["raw_value"],p["normalized_value"],p["transformation"],p["evidence_type"],p["confidence"],"source-publisher","", "",x["verification"]["last_verification_date"],"PUBLISHED_RAW_FIELD"])
            for e in x["evidence_records"]: w.writerow([x["facility_id"],x["facility_name"],"evidence",(e["source"]["urls"] or [""])[0],e["source"]["publication_date"],e["capture_date"],e["exact_source_field"],e["exact_source_value"],e["retained_basis"],e["transformation"],e["evidence_type"],e["confidence"],e["evidence_origin"],x["independent_corroboration"]["status"],x["conflicting_evidence"]["status"],x["verification"]["last_verification_date"],e["review_state"]])
if __name__=="__main__": main()
