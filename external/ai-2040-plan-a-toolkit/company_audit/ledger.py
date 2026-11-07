
from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict

@dataclass(frozen=True)
class AssetEvent:
    event_id:str
    asset_id:str
    owner_id:str
    kind:str
    units:int
    counterparty:str|None=None
    evidence_digest:str|None=None

def validate_events(events:list[AssetEvent])->dict:
    ids=[e.event_id for e in events]
    assets=[e.asset_id for e in events]
    errors=[]
    if len(ids)!=len(set(ids)): errors.append("duplicate event_id")
    if any(e.units<0 for e in events): errors.append("negative units")
    if any(e.kind not in {"ACQUIRE","TRANSFER_OUT","TRANSFER_IN","HOLD","DECOMMISSION"} for e in events):
        errors.append("unknown event kind")
    return {"status":"PASS" if not errors else "FAIL","errors":errors}

def reconcile_owner(events:list[AssetEvent],owner_id:str)->dict:
    relevant=[e for e in events if e.owner_id==owner_id]
    if not relevant:return {"status":"UNKNOWN","reason":"no owner records"}
    acquired=sum(e.units for e in relevant if e.kind=="ACQUIRE")
    inbound=sum(e.units for e in relevant if e.kind=="TRANSFER_IN")
    outbound=sum(e.units for e in relevant if e.kind=="TRANSFER_OUT")
    held=sum(e.units for e in relevant if e.kind=="HOLD")
    decommissioned=sum(e.units for e in relevant if e.kind=="DECOMMISSION")
    expected=acquired+inbound
    observed=outbound+held+decommissioned
    missing_evidence=[e.event_id for e in relevant if not e.evidence_digest]
    status="PASS" if expected==observed and not missing_evidence else ("UNKNOWN" if expected==observed else "FAIL")
    return {"status":status,"expected_units":expected,"resolved_units":observed,"missing_evidence":missing_evidence}

def reconcile_population(events:list[AssetEvent])->dict:
    check=validate_events(events)
    if check["status"]=="FAIL":return check
    owners=sorted({e.owner_id for e in events})
    per_owner={o:reconcile_owner(events,o) for o in owners}
    return {"status":"PASS" if owners and all(x["status"]=="PASS" for x in per_owner.values()) else "UNKNOWN","owners":per_owner}
