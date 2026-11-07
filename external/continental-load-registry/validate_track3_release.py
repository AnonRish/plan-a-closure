#!/usr/bin/env python3
"""Release-consistency checks for the public Track 3 engineering snapshot."""
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def load(rel): return json.loads((ROOT/rel).read_text(encoding="utf-8"))
def main():
    errors=[]
    s=load("data/track3/summary.json"); g=load("data/track3/completion_gate.json")
    physical=load("data/physical_verification_layer.json")
    strict=load("data/track3/strict_discovery_case_dispositions_2026-09-28.json")
    cases=load("data/track3/ambiguous_case_studies.json")
    h=load("data/track3/external_capability_handoff_2026-09-28.json")
    p=load("data/track3/interval_power_telemetry_protocol.json")
    leads=load("data/track3/physical_target_leads.json")
    closure=load("data/track3/engineering_closure_2026-09-28.json")
    checks=[(s.get("epoch_site_count")==93,"summary site count must be 93"),
            (s.get("public_web_evidence_record_count")==454,"summary public-web evidence count must be 454"),
            (s.get("remote_sensing_derived_observation_count")==physical.get("summary",{}).get("derived_observation_count"),"summary remote-sensing count does not reconcile with physical layer"),
            (g.get("public_evidence_accounting",{}).get("public_web_evidence_records")==454,"completion gate public-web count must be 454"),
            (g.get("public_evidence_accounting",{}).get("remote_sensing_derived_observations")==s.get("remote_sensing_derived_observation_count"),"completion gate remote-sensing count does not reconcile with summary"),
            (g.get("empirical_track3_verification",{}).get("status")=="NOT_CLOSED","empirical Track 3 status must remain NOT_CLOSED"),
            (g.get("current_public_data_boundaries",{}).get("one_reference_site_without_site_specific_public_physical_target")=="EPOCH-661288625d17662a","unresolved physical target changed"),
            (len(strict.get("cases",[]))==5 and strict.get("summary",{}).get("terminal_disposition_count")==5,"strict five-case ledger must be terminal"),
            (len(cases.get("cases",[]))==4,"ambiguous case laboratory must contain four pilot cases"),
            (len(h.get("blockers",[]))==7 and {x.get("current_state") for x in h.get("blockers",[])}=={"BLOCKED_EXTERNAL_CAPABILITY"},"external handoff must contain seven explicit blockers"),
            (p.get("current_state",{}).get("site_level_interval_records")==0,"interval telemetry must remain empty at site level"),
            (leads.get("targets",[{}])[0].get("canonical_status")=="UNRESOLVED","unresolved target was not promoted"),
            (leads.get("targets",[{}])[0].get("current_canonical_coordinate") is None,"unresolved target must not contain canonical coordinates"),
            (closure.get("repository_engineering_status")=="COMPLETE","repository engineering closure must be COMPLETE"),
            (closure.get("empirical_track3_verification_status")=="NOT_CLOSED","empirical Track 3 status must remain NOT_CLOSED"),
            (closure.get("untracked_gap_count")==0,"engineering closure must report zero untracked gaps"),
            (closure.get("remaining_research_and_acquisition",{}).get("public_publisher_field_tasks_open")==s.get("publisher_research_tasks",214),"closure publisher-task count does not reconcile"),
            (closure.get("remaining_research_and_acquisition",{}).get("follow_on_observation_tasks")==s.get("observation_task_count",24),"closure observation-task count does not reconcile"),
            (closure.get("external_capability_blockers",{}).get("count")==7,"closure external-blocker count must be seven")]
    errors += [msg for ok,msg in checks if not ok]
    remote_phrase=f"As of 2026-09-28 it retains {s.get('remote_sensing_derived_observation_count')} derived remote-sensing observations across 92 of the 93 Epoch sites"
    docs={"TRACK3_ONE_PAGE_SUMMARY.md":[remote_phrase,"Current engineering closure"],
          "TRACK3_COMPLETION_GATE.md":[f"{s.get('remote_sensing_derived_observation_count')} derived remote-sensing observations across 92 sites","external_capability_handoff_2026-09-28.json","engineering_closure_2026-09-28.json"],
          "TRACK3_COMPLETE_COVERAGE.md":["Release / external-capability handoff","interval_power_telemetry_protocol.json","214 open public-source publisher-field research tasks"],
          "STRICT_DISCOVERY_RESEARCH.md":["141-record ambiguity pool"]}
    for path,phrases in docs.items():
        txt=(ROOT/path).read_text(encoding="utf-8")
        for phrase in phrases:
            if phrase not in txt: errors.append(f"{path} missing release phrase: {phrase}")
    cert=(ROOT/"track3_certificate.py").read_text(encoding="utf-8")
    if 'output = json.dumps(obj, indent=2) + "\\n"' not in cert: errors.append("certificate output newline is malformed")
    if errors:
        [print("ERROR:",e) for e in errors]
        return 1
    print("PASS: Track 3 release consistency checks passed.")
    print(f"PASS: 93 sites / 454 public-web records / {s.get('remote_sensing_derived_observation_count')} remote observations / 4 pilot cases / 5 strict cases.")
    return 0
if __name__=="__main__": raise SystemExit(main())
