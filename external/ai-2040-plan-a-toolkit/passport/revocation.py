from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Revocation:
    passport_id:str
    reason:str
    effective_at:int
    evidence_digest:str

def evaluate_revocation(passport_id:str,now:int,revocations:list[Revocation])->dict:
    active=[r for r in revocations if r.passport_id==passport_id and r.effective_at<=now]
    if not active:return {"status":"ACTIVE"}
    latest=max(active,key=lambda x:x.effective_at)
    return {"status":"REVOKED","reason":latest.reason,"effective_at":latest.effective_at,"evidence_digest":latest.evidence_digest}
