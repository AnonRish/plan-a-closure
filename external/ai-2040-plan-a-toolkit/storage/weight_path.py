
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class WeightTransfer:
    source:str
    destination:str
    artifact_digest:str
    channel:str
    approved:bool
    diode_enforced:bool

def validate_weight_path(t:WeightTransfer)->dict:
    if not t.artifact_digest:return {"status":"UNKNOWN","reason":"missing artifact digest"}
    if not t.approved:return {"status":"FAIL","reason":"unapproved weight artifact"}
    if t.channel!="WEIGHT_ONLY":return {"status":"FAIL","reason":"channel not isolated"}
    if not t.diode_enforced:return {"status":"UNKNOWN","reason":"data diode not evidenced"}
    return {"status":"PASS"}
