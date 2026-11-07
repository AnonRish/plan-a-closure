
from __future__ import annotations
from dataclasses import dataclass
from enum import IntEnum

class EvidenceLevel(IntEnum):
    SYNTHETIC=1
    SOFTWARE_TESTED=2
    BENCH_HARDWARE=3
    INDEPENDENT_REPLICATION=4
    OPERATIONAL_FIELD=5

@dataclass(frozen=True)
class EvidenceArtifact:
    artifact_id:str
    level:EvidenceLevel
    digest:str
    environment_digest:str
    independent_party:bool=False
    raw_data_present:bool=False

@dataclass(frozen=True)
class Claim:
    claim_id:str
    minimum_level:EvidenceLevel
    artifact_ids:tuple[str,...]

def can_promote(claim:Claim,artifacts:dict[str,EvidenceArtifact])->dict:
    missing=[x for x in claim.artifact_ids if x not in artifacts]
    selected=[artifacts[x] for x in claim.artifact_ids if x in artifacts]
    if missing:return {"status":"UNKNOWN","reason":"missing artifacts","missing":missing}
    too_weak=[x.artifact_id for x in selected if x.level<claim.minimum_level]
    if too_weak:return {"status":"UNKNOWN","reason":"evidence below required level","too_weak":too_weak}
    if claim.minimum_level>=EvidenceLevel.INDEPENDENT_REPLICATION and not any(x.independent_party for x in selected):
        return {"status":"UNKNOWN","reason":"independent party evidence required"}
    if claim.minimum_level>=EvidenceLevel.BENCH_HARDWARE and not all(x.raw_data_present for x in selected):
        return {"status":"UNKNOWN","reason":"raw hardware data required"}
    return {"status":"PASS","level":claim.minimum_level.name}
