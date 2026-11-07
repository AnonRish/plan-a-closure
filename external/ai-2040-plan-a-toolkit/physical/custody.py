
from __future__ import annotations
from dataclasses import dataclass
import hashlib

@dataclass(frozen=True)
class CustodyEvent:
    event_id:str
    asset_id:str
    action:str
    operator_id:str
    timestamp_ns:int
    previous_digest:str
    evidence_digest:str
    def digest(self)->str:
        raw="|".join((self.event_id,self.asset_id,self.action,self.operator_id,str(self.timestamp_ns),self.previous_digest,self.evidence_digest))
        return hashlib.sha256(raw.encode()).hexdigest()

def validate_custody_chain(events:list[CustodyEvent])->dict:
    previous="0"*64
    broken=[]
    for e in sorted(events,key=lambda x:x.timestamp_ns):
        if e.previous_digest!=previous:broken.append(e.event_id)
        previous=e.digest()
    return {"status":"PASS" if not broken else "FAIL","broken_events":broken}

def tamper_open_response(current:str)->str:
    if current not in {"SEALED","OPEN","UNKNOWN"}:raise ValueError("invalid enclosure state")
    return "FAIL_CLOSED" if current=="OPEN" else "UNKNOWN" if current=="UNKNOWN" else "NORMAL"
