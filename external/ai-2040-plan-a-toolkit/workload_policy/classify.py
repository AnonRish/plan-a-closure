
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Policy:
    approved_operations:frozenset[str]
    banned_operations:frozenset[str]

def classify(observed_operations:list[str],policy:Policy,evidence_complete:bool)->dict:
    observed=set(observed_operations)
    banned=sorted(observed & policy.banned_operations)
    unknown=sorted(observed-policy.approved_operations-policy.banned_operations)
    if banned:return {"status":"BANNED","operations":banned}
    if unknown or not evidence_complete:return {"status":"UNKNOWN","operations":unknown}
    return {"status":"APPROVED","operations":sorted(observed)}

def require_classified_workload(result:dict)->str:
    status=result.get("status")
    if status not in {"APPROVED","BANNED","UNKNOWN"}:raise ValueError("invalid workload classification")
    return status
