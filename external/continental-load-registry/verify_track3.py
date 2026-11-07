#!/usr/bin/env python3
"""Independent, read-only verifier for Track 3 detection/verification artifacts."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
VALID={"PASS","FAIL","UNKNOWN","NOT_TESTED","NOT_APPLICABLE","UNASSESSED"}
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
def main():
    d=load("data/track3/verification_results.json"); proto=load("data/track3/verification_protocol.json"); det=load("data/track3/detection_universe.json"); absd=load("data/track3/absence_testing.json")
    assert d["protocol_version"]==proto["protocol_version"]
    assert len(det["tracked_facilities"])==93
    assert len({x["facility_id"] for x in det["tracked_facilities"]})==93
    assert len(d["results"])==93*8
    for r in d["results"]:
        assert r["status"] in VALID, r
        if r["status"]=="PASS": assert r.get("evidence_refs"), f"PASS without evidence: {r['verification_id']}"
        if r["status"]=="FAIL": assert r.get("evidence_refs"), f"FAIL without evidence: {r['verification_id']}"
    assert len(absd["records"])==det["summary"]["documented_absence_search_facilities"]
    print("Track 3 verification integrity checks passed.")
if __name__=="__main__": main()
