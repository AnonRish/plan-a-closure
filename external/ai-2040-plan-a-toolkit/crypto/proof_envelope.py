
from __future__ import annotations
from dataclasses import dataclass
import hashlib, hmac

def digest(data:bytes)->str:return hashlib.sha256(data).hexdigest()

@dataclass(frozen=True)
class ProofEnvelope:
    statement_digest:str
    proof_system:str
    proof_artifact_digest:str
    verifier_version:str
    verification_key_digest:str|None=None
    transparent_parameters_digest:str|None=None

def validate_envelope(e:ProofEnvelope)->dict:
    fields={"statement":e.statement_digest,"proof":e.proof_artifact_digest,"verifier":e.verifier_version}
    missing=[k for k,v in fields.items() if not v]
    return {"status":"PASS" if not missing else "UNKNOWN","missing":missing}

def statement_id(*parts:str)->str:
    return digest("\x1f".join(parts).encode())

def constant_time_equal(a:str,b:str)->bool:return hmac.compare_digest(a,b)
