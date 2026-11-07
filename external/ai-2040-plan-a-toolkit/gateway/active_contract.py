
from __future__ import annotations
from dataclasses import dataclass
from .policy import GatewayPolicy

@dataclass(frozen=True)
class ContractDecision:
    action:str
    reason:str

def enforce_contract(event_type:str,size:int,delta_ns:int,policy:GatewayPolicy)->ContractDecision:
    r=policy.validate(event_type,size,delta_ns)
    return ContractDecision("FORWARD" if r["status"]=="PASS" else "BLOCK",r.get("reason","allowed"))
