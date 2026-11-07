
from __future__ import annotations

def evaluate_closure(contract:dict)->dict:
    required=["population_id","frozen_at","scope","threshold_units","population_complete","sampling_frame_digest","authoritative_sources"]
    missing=[x for x in required if x not in contract]
    if missing:return {"status":"UNKNOWN","reason":"missing closure fields","missing":missing}
    if not contract["population_complete"]:
        return {"status":"UNKNOWN","reason":"population is not declared complete"}
    blockers=[]
    if not contract["sampling_frame_digest"]: blockers.append("missing sampling frame digest")
    if not contract["authoritative_sources"]: blockers.append("no authoritative sources")
    if blockers:return {"status":"UNKNOWN","reason":"closure prerequisites incomplete","blockers":blockers}
    return {
        "status":"CLOSED_FOR_DECLARED_SCOPE",
        "population_id":contract["population_id"],
        "scope":contract["scope"],
        "physical_serial_continuity":bool(contract.get("serial_continuity_verified",False)),
        "physical_inspection_authority":bool(contract.get("physical_inspection_authority",False)),
        "independent_audit_authority":bool(contract.get("independent_audit_authority",False)),
        "note":"closed-for-declared-scope does not establish that the declared scope is globally complete"
    }
