
from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict

@dataclass(frozen=True)
class Interval:
    low:float
    high:float
    def __post_init__(self):
        if self.low<0 or self.high<self.low: raise ValueError("invalid interval")
    def __add__(self,other:"Interval"): return Interval(self.low+other.low,self.high+other.high)
    def width(self): return self.high-self.low

@dataclass(frozen=True)
class Flow:
    evidence_id:str
    src:str
    dst:str
    chip_family:str
    quantity:Interval

def reconcile_flows(flows:list[Flow], declared_stock:dict[str,Interval], closed_population:bool=False)->dict:
    ids=[f.evidence_id for f in flows]
    if len(ids)!=len(set(ids)): return {"status":"FAIL","reason":"duplicate evidence_id"}
    incoming=defaultdict(lambda:Interval(0,0)); outgoing=defaultdict(lambda:Interval(0,0))
    for f in flows:
        incoming[f.dst]=incoming[f.dst]+f.quantity
        outgoing[f.src]=outgoing[f.src]+f.quantity
    owners=set(declared_stock)
    unknown_sources=sorted(set(outgoing)-owners)
    total_stock=Interval(sum(v.low for v in declared_stock.values()),sum(v.high for v in declared_stock.values()))
    traced=Interval(sum(f.quantity.low for f in flows),sum(f.quantity.high for f in flows))
    residual=Interval(max(0,total_stock.low-traced.high),max(0,total_stock.high-traced.low))
    status="PASS" if closed_population and not unknown_sources else ("UNKNOWN" if not closed_population else "FAIL")
    return {
        "status":status,"closed_population":closed_population,
        "stock_interval":{"low":total_stock.low,"high":total_stock.high},
        "traced_flow_interval":{"low":traced.low,"high":traced.high},
        "residual_upper_bound":residual.high,
        "unknown_source_accounts":unknown_sources,
    }
