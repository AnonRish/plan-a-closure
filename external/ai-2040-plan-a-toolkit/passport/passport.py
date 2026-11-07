from __future__ import annotations
from dataclasses import dataclass,field
import hashlib,json,time
VALID_TRUST_MODES={"software","bench_hardware","hardware_attested","independently_replicated","external_provider"}
@dataclass(frozen=True)
class PassportClaim:
    claim_id:str; statement:str; result:str; evidence_level:int; evidence_refs:tuple[str,...]; verifier_id:str
@dataclass
class AIPassport:
    passport_id:str; subject_id:str; model_fingerprint:str; policy_digest:str; trust_mode:str; issued_at:int
    expires_at:int|None=None; claims:list[PassportClaim]=field(default_factory=list); evidence_root:str=""; attestation_refs:tuple[str,...]=()
    def digest(self):
        payload={"passport_id":self.passport_id,"subject_id":self.subject_id,"model_fingerprint":self.model_fingerprint,"policy_digest":self.policy_digest,"trust_mode":self.trust_mode,"issued_at":self.issued_at,"expires_at":self.expires_at,"claims":[c.__dict__ for c in sorted(self.claims,key=lambda x:x.claim_id)],"evidence_root":self.evidence_root,"attestation_refs":self.attestation_refs}
        return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def validate_passport(p,now=None):
    now=int(time.time()) if now is None else now; errors=[]
    if p.trust_mode not in VALID_TRUST_MODES: errors.append("unknown trust mode")
    if p.expires_at is not None and now>p.expires_at: errors.append("expired")
    ids=[c.claim_id for c in p.claims]
    if len(ids)!=len(set(ids)): errors.append("duplicate claim")
    for c in p.claims:
        if c.result not in {"PASS","FAIL","UNKNOWN"}: errors.append("invalid result")
        if c.result=="PASS" and (c.evidence_level<=0 or not c.evidence_refs): errors.append("PASS without evidence")
        if not c.verifier_id: errors.append("claim without verifier")
    return {"status":"PASS" if not errors else "FAIL","errors":errors,"passport_digest":p.digest()}
