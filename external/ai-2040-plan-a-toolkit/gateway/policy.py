
from __future__ import annotations
from dataclasses import dataclass
from math import log2

@dataclass(frozen=True)
class EnvelopeClass:
    name:str
    min_size:int
    max_size:int
    allowed_interval_ns:int

@dataclass(frozen=True)
class GatewayPolicy:
    envelopes:tuple[EnvelopeClass,...]
    max_rate_per_second:float
    fixed_slot_ns:int=10_000_000

    def validate(self,event_type:str,size:int,delta_ns:int)->dict:
        matches=[e for e in self.envelopes if e.name==event_type]
        if not matches:return {"status":"FAIL","reason":"type not whitelisted"}
        e=matches[0]
        if not e.min_size<=size<=e.max_size:return {"status":"FAIL","reason":"size outside envelope"}
        if delta_ns<0 or delta_ns>e.allowed_interval_ns:return {"status":"FAIL","reason":"timing outside envelope"}
        return {"status":"PASS"}

    def timing_capacity_bits_per_event(self,jitter_ns:int)->float:
        if jitter_ns<=0:return 0.
        return log2(jitter_ns+1)

    def theoretical_capacity_upper_bound(self,event_rate:float,jitter_ns:int)->float:
        if event_rate<0:raise ValueError("event_rate must be non-negative")
        return event_rate*self.timing_capacity_bits_per_event(jitter_ns)

def evaluate_gateway_stream(events:list[tuple[str,int,int]],policy:GatewayPolicy)->dict:
    findings=[]
    for i,(kind,size,delta) in enumerate(events):
        r=policy.validate(kind,size,delta)
        if r["status"]!="PASS":findings.append({"index":i,**r})
    return {"status":"PASS" if not findings else "FAIL","events":len(events),"findings":findings}
