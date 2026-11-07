from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict

@dataclass(frozen=True)
class LotEvent:
    event_id:str
    lot_id:str
    owner:str
    kind:str
    quantity:int
    counterparty:str|None=None
    evidence_ref:str|None=None

VALID_KINDS={"MANUFACTURED","RECEIVED","TRANSFER_OUT","TRANSFER_IN","DEPLOYED","DECOMMISSIONED","DESTROYED"}

def validate_events(events:list[LotEvent])->dict:
    ids=[e.event_id for e in events]; errors=[]
    if len(ids)!=len(set(ids)):errors.append("duplicate event_id")
    if any(e.quantity<0 for e in events):errors.append("negative quantity")
    if any(e.kind not in VALID_KINDS for e in events):errors.append("unknown event kind")
    return {"status":"PASS" if not errors else "FAIL","errors":errors}

def reconcile_lot(events:list[LotEvent],lot_id:str)->dict:
    es=[e for e in events if e.lot_id==lot_id]
    if not es:return {"status":"UNKNOWN","reason":"lot not found"}
    manufactured=sum(e.quantity for e in es if e.kind=="MANUFACTURED")
    received=sum(e.quantity for e in es if e.kind=="RECEIVED")
    transfers_in=sum(e.quantity for e in es if e.kind=="TRANSFER_IN")
    transfers_out=sum(e.quantity for e in es if e.kind=="TRANSFER_OUT")
    deployed=sum(e.quantity for e in es if e.kind=="DEPLOYED")
    destroyed=sum(e.quantity for e in es if e.kind in {"DECOMMISSIONED","DESTROYED"})
    accounted_in=manufactured+received+transfers_in
    accounted_out=transfers_out+deployed+destroyed
    missing=[e.event_id for e in es if not e.evidence_ref]
    return {"status":"PASS" if accounted_in==accounted_out and not missing else ("UNKNOWN" if accounted_in==accounted_out else "FAIL"),
            "input_units":accounted_in,"output_units":accounted_out,"missing_evidence":missing}

def reconcile_lots(events:list[LotEvent])->dict:
    v=validate_events(events)
    if v["status"]!="PASS":return v
    lots=sorted({e.lot_id for e in events})
    out={x:reconcile_lot(events,x) for x in lots}
    return {"status":"PASS" if lots and all(v["status"]=="PASS" for v in out.values()) else "UNKNOWN","lots":out}
