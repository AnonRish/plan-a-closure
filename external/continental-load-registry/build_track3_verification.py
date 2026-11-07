#!/usr/bin/env python3
"""Deterministically rebuild Track 3 detection, absence testing and verification results.

CI rebuild trigger: source-driven verification pipeline.
"""
from __future__ import annotations
import json, os, re
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"data"/"track3"
SHA=os.getenv("GITHUB_SHA","WORKTREE_UNRESOLVED")
GENERATED=datetime.now(timezone.utc).isoformat()

def load(path):
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def norm(value):
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9]+"," ",str(value or "").lower())).strip()

def selected_links(value):
    return [m.group(1) for m in re.finditer(r"\[[^\]]+\]\((https?://[^)\s]+)\)",str(value or ""))]

AI_RE=re.compile(r"ai|gpu|compute|data ?center|datacenter|hyperscale|cloud|server|training|cluster|stargate|colossus|prometheus|rainier|fairwater|helios|vertex|neocloud",re.I)
IND_RE=re.compile(r"steel|cement|refinery|chemical|manufactur|paper|mill|mine|mining|battery|automotive|semiconductor|chip|hydrogen|aluminum|plast|warehouse|industrial|factory|food|lng|oil|pipeline|water",re.I)
COMPANY_RE=re.compile(r"sec\.gov|openai\.com|aboutamazon\.com|amazon\.com|meta\.com|facebook\.com|microsoft\.com|google\.com|x\.com|xai\.com|spacex\.com",re.I)
PERMIT_RE=re.compile(r"permit|planning|TABS|air quality|zoning|environmental",re.I)

def protocol():
    return {
      "schema_version":1,"protocol_version":"T3-V1","title":"Track 3 verification protocol",
      "core_rule":"PASS is only valid for the named claim when its evidence gates are satisfied. No evidence -> UNKNOWN. An unrun test -> NOT_TESTED. No status is inferred from another status.",
      "statuses":{
        "PASS":{"meaning":"Claim-specific evidence gates satisfied.","evidence_requirements":["claim-specific evidence reference(s)","source URL or stable record locator","no unresolved direct contradiction","independent verifier where required"]},
        "FAIL":{"meaning":"Claim-specific evidence explicitly contradicts the claim.","evidence_requirements":["contradicting evidence reference","source URL/locator","exact claim scope"]},
        "UNKNOWN":{"meaning":"Test/search was attempted but evidence is insufficient for PASS or FAIL.","evidence_requirements":["documented test/search","evidence gap"]},
        "NOT_TESTED":{"meaning":"Test has not run.","evidence_requirements":["explicit unrun state"]},
        "NOT_APPLICABLE":{"meaning":"Claim does not apply.","evidence_requirements":["explicit rationale"]},
        "UNASSESSED":{"meaning":"No verifier has assigned a result.","evidence_requirements":["result left unassigned"]}
      },
      "claims":{
        "UNIVERSE_ENTRY":"Facility/request is in the declared Track 3 research population.",
        "AI_COMPUTE_PUBLISHER_CHECK":"Epoch explicitly records AI-data-center compute evidence; publisher/derived check only.",
        "SITE_IDENTITY":"Facility has stable identity and site locator.",
        "GRID_CONNECTION":"Site-specific connection/service/queue record exists.",
        "POWER_OBSERVATION":"Site-specific electricity observation exists with source, period and units.",
        "PHYSICAL_REMOTE_SENSING":"Site-level optical/TIR/SAR observation is acquired and traceable.",
        "INDEPENDENT_CORROBORATION":"Material claim is supported by distinct retained sources.",
        "END_TO_END_TRACK3":"Physical, electrical, compute and independent-verifier chain is sufficient for the exact claim.",
        "ARTIFACT_ATTESTATION":"Verification bundle has a valid cryptographic attestation."
      },
      "pass_rules":{
        "UNIVERSE_ENTRY":["stable ID","canonical source record","documented inclusion reason"],
        "AI_COMPUTE_PUBLISHER_CHECK":["explicit Epoch AI-data-center record","positive compute-related publisher field","publisher/derived scope stated"],
        "SITE_IDENTITY":["stable ID","facility name","address/equivalent site locator"],
        "GRID_CONNECTION":["site-specific queue/service/interconnection identifier or equivalent site-specific primary utility record","source URL","site-specific scope"],
        "POWER_OBSERVATION":["site-specific value","measurement period","units","source URL"],
        "PHYSICAL_REMOTE_SENSING":["site-level observation","acquisition identifier/date","source URL","measurement/derived metric","processing method"],
        "INDEPENDENT_CORROBORATION":["two distinct retained source records","materially overlapping claim","independence caveat"],
        "END_TO_END_TRACK3":["independent verifier","primary evidence","independent corroboration","physical + electrical + compute/accounting evidence"],
        "ARTIFACT_ATTESTATION":["attestation exists","subject digest matches","workflow/commit identity recorded"]
      },
      "absence_testing_rule":"A no-match statement must point to a retained search record naming the source/database, URL/locator, capture date, search scope and result. Missing rows or fields are not absence evidence.",
      "independent_verifier":"verify_track3.py is intentionally read-only; its GitHub Actions workflow has contents: read only. This is operational separation, not organizational independence.",
      "signed_audit":"The signed bundle workflow uses GitHub Artifact Attestations, which are Sigstore-backed cryptographic provenance/integrity claims.",
      "versioning_rule":"Every result carries protocol_version, generation timestamp and source_snapshot_commit. Git history preserves prior versions.",
      "dispute_correction":"Corrections are append-only GitHub issue/event records; historical snapshots are retained and superseding records reference the original."
    }

def main():
    idx=(ROOT/"index.html").read_text(encoding="utf-8")
    m=re.search(r"const REGISTRY_DATA = (\[.*?\]);\n",idx,re.S)
    if not m: raise SystemExit("REGISTRY_DATA not found")
    queue=json.loads(m.group(1))
    epoch_data=load("data/external/epoch_ai/registry.json"); epoch=epoch_data["records"]
    evidence=load("data/track3/evidence_records.json")["records"]
    site_rows=load("data/track3/site_status.json")["records"]
    physical=load("data/physical_verification_layer.json")
    remote=load("data/track3/remote_sensing_observations.json").get("records", [])
    remote_by={}
    for row in remote:
        if row.get("status") == "INGESTED_DERIVED":
            remote_by.setdefault(row.get("epoch_id"), []).append(row)
    try:
        power=load("data/track3/power_observations.json")["records"]
    except FileNotFoundError:
        power=[]
    site_by={x["epoch_id"]:x for x in site_rows}
    evidence_by={}
    for x in evidence: evidence_by.setdefault(x["target_id"],[]).append(x)
    epoch_names={norm(x["normalized"].get("name")) for x in epoch}
    tracked=[]
    for s in epoch:
        n=s.get("normalized",{}); raw=s.get("raw",{}); es=evidence_by.get(s["epoch_id"],[]); sr=site_by.get(s["epoch_id"],{})
        urls=selected_links(raw.get("Selected Sources"))
        no_match=[e for e in es if "NO_MATCH_FOUND" in str(e.get("evidence_type",""))]
        tracked.append({
          "facility_id":s["epoch_id"],"facility_name":n.get("name") or s["epoch_id"],
          "classification":"KNOWN_AI_COMPUTE" if float(n.get("current_h100_equivalents") or 0)>0 else "PROBABLE_AI_COMPUTE",
          "classification_scope":"Epoch publisher/derived record only; not physical certification",
          "entry_reason":"Included because Epoch AI's AI data-center dataset contains a facility-level record. This is a Track 3 research-universe anchor, not proof of current physical AI compute.",
          "evidence_basis":{"current_h100_equivalents":n.get("current_h100_equivalents"),"current_power_mw":n.get("current_power_mw"),"owner":n.get("owner"),"users":n.get("users"),"project":n.get("project"),"current_chip_types":n.get("current_chip_types")},
          "source_crosscheck":{
            "epoch":{"status":"MATCH","source_url":epoch_data["source"].get("data_centers_url")},
            "queue_registry":{"status":"SITE_SPECIFIC_MATCH" if sr.get("grid",{}).get("site_specific_queue_id") else "NO_SITE_SPECIFIC_QUEUE_ID","queue_id":sr.get("grid",{}).get("site_specific_queue_id")},
            "retained_site_evidence":{"count":len(es)},
            "company_or_regulatory_disclosure_references":{"count":sum(bool(COMPANY_RE.search(u)) for u in urls),"method":"URL-domain heuristic over retained Epoch Selected Sources list"},
            "permit_or_planning_references":{"count":sum(bool(PERMIT_RE.search(u)) for u in urls)+(1 if PERMIT_RE.search(str(raw.get("Selected Sources",""))) else 0),"method":"URL/text heuristic over retained Epoch Selected Sources list"},
            "dc_byte":{"status":"CATALOGED_NOT_INGESTED","reason":"Commercial source; no facility-level DC Byte export retained in this repository."},
            "satellite":{
              "optical":"INGESTED_DERIVED" if any(x.get("modality") == "optical" for x in remote_by.get(s["epoch_id"], [])) else "NOT_INGESTED",
              "tir":"INGESTED_DERIVED" if any(x.get("modality") == "tir" for x in remote_by.get(s["epoch_id"], [])) else "NOT_INGESTED",
              "sar":"INGESTED_DERIVED" if any(x.get("modality") == "sar" for x in remote_by.get(s["epoch_id"], [])) else "NOT_INGESTED",
            },
            "current_physical_layer":{"optical_scenes":sum(1 for x in remote_by.get(s["epoch_id"], []) if x.get("modality") == "optical"),"tir_numeric":sum(1 for x in remote_by.get(s["epoch_id"], []) if x.get("modality") == "tir"),"sar_numeric":sum(1 for x in remote_by.get(s["epoch_id"], []) if x.get("modality") == "sar"),"transformer_events":physical.get("summary",{}).get("transformer_event_records",0)}
          },
          "absence_testing":{"status":"DOCUMENTED_SEARCH_RESULT","search_records":[{"evidence_id":e.get("id"),"source_name":e.get("source_name"),"source_url":e.get("source_url"),"authority":e.get("authority"),"claim":e.get("basis"),"captured_on":e.get("capture_date") or e.get("captured_on"),"search_scope":"Exact facility/site-specific connection or service record in the cited public source."} for e in no_match]} if no_match else {"status":"NO_ABSENCE_CLAIM","search_records":[]}
        })
    candidate_rows=[r for r in queue if r.get("proj") and norm(r.get("proj")) not in epoch_names]
    candidates=[]
    for r in candidate_rows:
        text=str(r.get("proj",""))+" "+str(r.get("dev",""))
        cls="AI_COMPUTE_CANDIDATE" if AI_RE.search(text) else "NON_AI_INDUSTRIAL_CONTROL_GROUP" if IND_RE.search(text) else "UNKNOWN_LARGE_COMPUTE"
        candidates.append({"candidate_id":str(r.get("id")),"granularity":"queue_or_connection_request","rto":r.get("rto"),"state_or_region":r.get("st"),"county_or_area":r.get("co"),"poi":r.get("poi"),"mw":r.get("mw"),"project_name":r.get("proj"),"developer":r.get("dev"),"entity_classification":r.get("ent"),"classification":cls,"epoch_direct_match":False,"classification_scope":"surveillance/control classifier only; not facility-operation evidence"})
    detection={"schema_version":1,"title":"Track 3-specific detection universe","generated_at_utc":GENERATED,
      "methodology":{"tracked_universe":"93 Epoch AI facility records","expanded_surveillance":f"{len(candidate_rows)} queue/request rows without a conservative direct Epoch project-name match","candidate_rule":"Surveillance classes are not conclusions about AI operation.","cross_check":f"Epoch is joined directly; queue/site evidence is joined from repository records; DC Byte is cataloged but not ingested; company/permit references are heuristics; {len(remote_by)} of 93 sites currently have retained derived remote-sensing observations ({len(remote)} observations total)."},
      "summary":{"tracked_facilities":len(tracked),"known_ai_compute":sum(x["classification"]=="KNOWN_AI_COMPUTE" for x in tracked),"probable_ai_compute":sum(x["classification"]=="PROBABLE_AI_COMPUTE" for x in tracked),"queue_rows_without_epoch_direct_match":len(candidate_rows),"ai_compute_candidates":sum(x["classification"]=="AI_COMPUTE_CANDIDATE" for x in candidates),"non_ai_industrial_control_group":sum(x["classification"]=="NON_AI_INDUSTRIAL_CONTROL_GROUP" for x in candidates),"unknown_large_compute":sum(x["classification"]=="UNKNOWN_LARGE_COMPUTE" for x in candidates),"documented_absence_search_facilities":sum(x["absence_testing"]["status"]=="DOCUMENTED_SEARCH_RESULT" for x in tracked)},
      "tracked_facilities":tracked,"queue_candidates_not_in_epoch":candidates}
    (OUT/"detection_universe.json").write_text(json.dumps(detection,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    proto=protocol(); (OUT/"verification_protocol.json").write_text(json.dumps(proto,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    power_ids={x.get("epoch_id") for x in power}; results=[]
    for f in tracked:
        refs=[f["source_crosscheck"]["epoch"]["source_url"]]
        has_power=f["facility_id"] in power_ids; site_evidence=(evidence_by.get(f["facility_id"]) or [])
        results += [
          {"verification_id":f"VR-{f['facility_id']}-UNIVERSE","facility_id":f["facility_id"],"claim":"UNIVERSE_ENTRY","status":"PASS","evidence_refs":refs,"basis":"Stable Epoch facility record and declared research-universe inclusion reason are retained.","verifier":"automated_precondition"},
          {"verification_id":f"VR-{f['facility_id']}-AI","facility_id":f["facility_id"],"claim":"AI_COMPUTE_PUBLISHER_CHECK","status":"PASS" if float(f["evidence_basis"].get("current_h100_equivalents") or 0)>0 else "UNKNOWN","evidence_refs":refs if float(f["evidence_basis"].get("current_h100_equivalents") or 0)>0 else [],"basis":"Epoch retains a positive current H100-equivalent field; publisher/derived check only." if float(f["evidence_basis"].get("current_h100_equivalents") or 0)>0 else "No positive publisher compute quantity retained.","verifier":"automated_publisher_check"},
          {"verification_id":f"VR-{f['facility_id']}-SITE","facility_id":f["facility_id"],"claim":"SITE_IDENTITY","status":"PASS" if f["facility_name"] and f["evidence_basis"].get("current_power_mw") is not None else "UNKNOWN","evidence_refs":[f"Epoch:{f['facility_id']}"],"basis":"Stable Epoch ID, facility name and site-level record retained.","verifier":"automated_identity_check"},
          {"verification_id":f"VR-{f['facility_id']}-GRID","facility_id":f["facility_id"],"claim":"GRID_CONNECTION","status":"PASS" if f["source_crosscheck"]["queue_registry"]["status"]=="SITE_SPECIFIC_MATCH" else "UNKNOWN","evidence_refs":[f"QUEUE:{f['source_crosscheck']['queue_registry']['queue_id']}"] if f["source_crosscheck"]["queue_registry"]["status"]=="SITE_SPECIFIC_MATCH" else [],"basis":"Site-specific queue ID retained." if f["source_crosscheck"]["queue_registry"]["status"]=="SITE_SPECIFIC_MATCH" else "No site-specific queue ID retained; jurisdiction-only/generic utility evidence is not promoted to PASS.","verifier":"automated_connection_check"},
          {"verification_id":f"VR-{f['facility_id']}-POWER","facility_id":f["facility_id"],"claim":"POWER_OBSERVATION","status":"PASS" if has_power else "UNKNOWN","evidence_refs":[f"POWER_OBSERVATION:{f['facility_id']}"] if has_power else [],"basis":"A site-specific electricity observation record is retained." if has_power else "No site-specific electricity observation record is retained.","verifier":"automated_power_check"},
          {"verification_id":f"VR-{f['facility_id']}-REMOTE","facility_id":f["facility_id"],"claim":"PHYSICAL_REMOTE_SENSING",
           "status":"PASS" if remote_by.get(f["facility_id"]) else "NOT_TESTED",
           "evidence_refs":[x.get("stac_item_url") for x in remote_by.get(f["facility_id"], [])[:3]],
           "basis":f"{len(remote_by.get(f['facility_id'], []))} traceable derived remote-sensing observation(s) are retained for this site." if remote_by.get(f["facility_id"]) else "No retained derived remote-sensing observation exists for this site in the current ledger.",
           "verifier":"automated_physical_observation_check"},
          {"verification_id":f"VR-{f['facility_id']}-CORR","facility_id":f["facility_id"],"claim":"INDEPENDENT_CORROBORATION","status":"PASS" if len(site_evidence)>=2 else "UNKNOWN","evidence_refs":[x.get("id") for x in site_evidence[:2]] if len(site_evidence)>=2 else [],"basis":"At least two retained site evidence records exist; metadata corroboration does not prove methodological independence." if len(site_evidence)>=2 else "Fewer than two retained site evidence records.","verifier":"automated_metadata_check"},
          {"verification_id":f"VR-{f['facility_id']}-END2END","facility_id":f["facility_id"],"claim":"END_TO_END_TRACK3","status":"UNKNOWN","evidence_refs":[],"basis":"No independent verifier record and no complete physical + electrical + compute/accounting chain sufficient for a facility-wide Track 3 conclusion.","verifier":"not_independently_assessed"}
        ]
    # Facility-wide state is intentionally conservative. A claim-specific PASS
    # does not become a facility-wide verification result automatically.
    by_facility={}
    for row in results:
        by_facility.setdefault(row["facility_id"], []).append(row)
    facility_state_counts={"VERIFIED_PRESENT":0,"VERIFIED_ABSENT":0,"INCONCLUSIVE":0}
    for facility in tracked:
        rows=by_facility.get(facility["facility_id"], [])
        end_to_end=next((x for x in rows if x["claim"]=="END_TO_END_TRACK3"), None)
        explicit_absence=any(x["status"]=="FAIL" and x["claim"] in {"SITE_IDENTITY","AI_COMPUTE_PUBLISHER_CHECK","PHYSICAL_REMOTE_SENSING"} for x in rows)
        if end_to_end and end_to_end["status"]=="PASS":
            state="VERIFIED_PRESENT"
        elif explicit_absence:
            state="VERIFIED_ABSENT"
        else:
            state="INCONCLUSIVE"
        facility["facility_evidence_state"]=state
        facility["facility_evidence_state_basis"]={
          "VERIFIED_PRESENT":"The exact end-to-end Track 3 claim passed its defined evidence gates.",
          "VERIFIED_ABSENT":"A directly tested facility-level claim produced an evidence-backed FAIL.",
          "INCONCLUSIVE":"At least one required facility-wide gate is missing or unproven; claim-specific PASS values do not constitute facility-wide certification."
        }[state]
        facility_state_counts[state]+=1
    counts={}
    for r in results: counts[r["status"]]=counts.get(r["status"],0)+1
    attestation_state="CI_ATTESTATION_CONFIGURED_PENDING_RUN"
    attestation_path=OUT/"attestation_status.json"
    if attestation_path.exists():
        try:
            att=json.loads(attestation_path.read_text(encoding="utf-8"))
            if att.get("status")=="SIGNED_AND_UPLOADED":
                attestation_state="SIGNED_AND_UPLOADED" if att.get("source_commit")==SHA else "SIGNED_FOR_PRIOR_SNAPSHOT"
        except Exception:
            attestation_state="ATTESTATION_STATUS_INVALID"
    verification={"schema_version":1,"protocol_version":"T3-V1","title":"Track 3 versioned verification results","generated_at_utc":GENERATED,"source_snapshot_commit":SHA,"semantics":"Claim-level automated verification results; not facility-wide certification.","summary":{"facility_count":len(tracked),"verification_record_count":len(results),"status_counts":counts,"facility_evidence_state_counts":facility_state_counts,"pass_only_with_evidence_rule":True,"independent_verifier_recorded":False,"artifact_attestation_status":attestation_state},"results":results}
    (OUT/"verification_results.json").write_text(json.dumps(verification,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    absence={"schema_version":1,"title":"Track 3 documented absence-testing ledger","generated_at_utc":GENERATED,"rule":"Only explicit documented search records are treated as absence-test evidence. All other missing matches remain NO_ABSENCE_CLAIM.","records":[{"facility_id":f["facility_id"],"facility_name":f["facility_name"],"status":f["absence_testing"]["status"],"search_records":f["absence_testing"]["search_records"],"not_searched_or_not_ingested":["DC Byte facility-level commercial export","site-level optical/TIR/SAR numeric observations"],"required_follow_up":["formal queue/service filing","utility/PUC/PSC record","company disclosure or permit","DC Byte or comparable independent directory","site-level remote sensing where applicable"]} for f in tracked if f["absence_testing"]["status"]=="DOCUMENTED_SEARCH_RESULT"]}
    (OUT/"absence_testing.json").write_text(json.dumps(absence,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"commit":SHA,"tracked":len(tracked),"candidates":len(candidates),"known_ai":detection["summary"]["known_ai_compute"],"probable_ai":detection["summary"]["probable_ai_compute"],"no_match_facilities":detection["summary"]["documented_absence_search_facilities"],"verification_records":len(results)},indent=2))
if __name__=="__main__":
    main()
