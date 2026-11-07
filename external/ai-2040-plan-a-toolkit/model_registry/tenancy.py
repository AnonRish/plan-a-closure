from __future__ import annotations
from dataclasses import dataclass
import hashlib

@dataclass(frozen=True)
class ModelIdentity:
    model_id:str
    weights_digest:str
    architecture_digest:str
    tokenizer_digest:str
    policy_digest:str
    version:str
    def fingerprint(self)->str:
        return hashlib.sha256("|".join((self.model_id,self.weights_digest,self.architecture_digest,self.tokenizer_digest,self.policy_digest,self.version)).encode()).hexdigest()

@dataclass(frozen=True)
class TenantLease:
    tenant_id:str
    cluster_id:str
    model_fingerprint:str
    start_epoch:int
    end_epoch:int

def validate_lease(lease:TenantLease,identity:ModelIdentity,current_epoch:int,cluster_id:str)->dict:
    checks={"model_identity":lease.model_fingerprint==identity.fingerprint(),"cluster":lease.cluster_id==cluster_id,"time":lease.start_epoch<=current_epoch<=lease.end_epoch}
    return {"status":"PASS" if all(checks.values()) else "FAIL","checks":checks}
