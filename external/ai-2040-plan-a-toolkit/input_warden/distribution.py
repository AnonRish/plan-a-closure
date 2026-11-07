from __future__ import annotations
from dataclasses import dataclass
import hashlib, json, secrets

@dataclass(frozen=True)
class DistributionCommitment:
    policy_id:str
    counts_digest:str
    salt:str

def commit_counts(policy_id:str,counts:dict[str,int],salt:str|None=None)->DistributionCommitment:
    if any(v<0 for v in counts.values()): raise ValueError("counts must be non-negative")
    salt=secrets.token_hex(16) if salt is None else salt
    canonical=json.dumps({"policy_id":policy_id,"counts":{k:int(counts[k]) for k in sorted(counts)},"salt":salt},sort_keys=True,separators=(",",":"))
    return DistributionCommitment(policy_id,hashlib.sha256(canonical.encode()).hexdigest(),salt)

def verify_counts(commitment:DistributionCommitment,counts:dict[str,int])->bool:
    return commit_counts(commitment.policy_id,counts,commitment.salt).counts_digest==commitment.counts_digest

def classify_distribution(counts:dict[str,int],allowed:frozenset[str],banned:frozenset[str],complete:bool)->dict:
    observed=set(counts); forbidden=sorted(observed&banned); unknown=sorted(observed-allowed-banned)
    if forbidden:return {"status":"BANNED","buckets":forbidden}
    if unknown or not complete:return {"status":"UNKNOWN","buckets":unknown}
    return {"status":"APPROVED","buckets":sorted(observed)}
