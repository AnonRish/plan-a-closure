import json
from pathlib import Path

def test_claim_matrix_has_no_global_claim_without_external_gate():
    data=json.loads(Path("CLAIM_EVIDENCE_MATRIX.json").read_text(encoding="utf-8"))
    absence=next(x for x in data["claims"] if x["claim_id"]=="TRACK3-ABSENCE")
    assert absence["minimum"]=="OPERATIONAL_FIELD"
    assert "closed_population" in absence["required_controls"]

def test_all_claims_have_nonempty_minimum_and_caveat():
    data=json.loads(Path("CLAIM_EVIDENCE_MATRIX.json").read_text(encoding="utf-8"))
    assert all(x.get("minimum") and x.get("cannot_infer") for x in data["claims"])
