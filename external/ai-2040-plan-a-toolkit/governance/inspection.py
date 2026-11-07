from __future__ import annotations
from dataclasses import dataclass
import hashlib, random

@dataclass(frozen=True)
class Inspector:
    inspector_id:str
    organization:str
    independence_group:str
    authorized_scopes:frozenset[str]

@dataclass(frozen=True)
class InspectionRequest:
    request_id:str
    scope_id:str
    requested_by:str
    minimum_inspectors:int
    seed_commitment:str

@dataclass(frozen=True)
class InspectionAssignment:
    request_id:str
    inspector_ids:tuple[str,...]
    challenge_seed:str

def commit_seed(seed:str)->str:
    return hashlib.sha256(seed.encode()).hexdigest()

def assign_inspectors(req:InspectionRequest,inspectors:list[Inspector],seed:str)->InspectionAssignment:
    if commit_seed(seed)!=req.seed_commitment: raise ValueError("seed does not match commitment")
    eligible=[i for i in inspectors if req.scope_id in i.authorized_scopes]
    groups={i.independence_group for i in eligible}
    if len(eligible)<req.minimum_inspectors or len(groups)<req.minimum_inspectors: raise ValueError("not enough independent eligible inspectors")
    chosen=random.Random(seed).sample(eligible,req.minimum_inspectors)
    return InspectionAssignment(req.request_id,tuple(sorted(i.inspector_id for i in chosen)),seed)

def validate_assignment(a:InspectionAssignment,req:InspectionRequest,inspectors:dict[str,Inspector])->dict:
    selected=[inspectors.get(x) for x in a.inspector_ids]
    if any(x is None for x in selected): return {"status":"FAIL","reason":"unknown inspector"}
    groups={x.independence_group for x in selected}
    scope_ok=all(req.scope_id in x.authorized_scopes for x in selected)
    ok=len(selected)>=req.minimum_inspectors and len(groups)>=req.minimum_inspectors and scope_ok
    return {"status":"PASS" if ok else "FAIL","independence_groups":len(groups),"inspector_ids":list(a.inspector_ids)}
