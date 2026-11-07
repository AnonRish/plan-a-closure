
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class IntelObservation:
    observation_id:str
    source_class:str
    collection_date:str
    target:str
    finding:str
    confidence:str
    independence_group:str
    corroborated_by:tuple[str,...]=()

VALID_CONFIDENCE={"LOW","MEDIUM","HIGH","UNASSESSED"}

def evaluate_intel(observations:list[IntelObservation])->dict:
    invalid=[o.observation_id for o in observations if o.confidence not in VALID_CONFIDENCE]
    groups={}
    for o in observations: groups.setdefault(o.independence_group,[]).append(o.observation_id)
    independent_groups=len(groups)
    return {
        "status":"UNKNOWN" if invalid or not observations else "EVIDENCE_PRESENT",
        "observation_count":len(observations),
        "independent_source_groups":independent_groups,
        "invalid_confidence_records":invalid,
        "note":"Intelligence is an evidence layer; it is not treated as ground truth or converted into a probability of guilt by this module."
    }
