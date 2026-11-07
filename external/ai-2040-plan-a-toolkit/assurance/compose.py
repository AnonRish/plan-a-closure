
from __future__ import annotations
from dataclasses import dataclass
from math import prod

@dataclass(frozen=True)
class FailureBound:
    name:str
    probability_upper:float
    independence_certified:bool=False
    common_mode_group:str|None=None
    def __post_init__(self):
        if not 0<=self.probability_upper<=1: raise ValueError("probability bound must be in [0,1]")

def compose(bounds:list[FailureBound])->dict:
    if not bounds:return {"status":"UNKNOWN","combined_failure_upper":None}
    # Safe default: union bound. Independence is never assumed merely because
    # components are different; common-mode groups explicitly prevent multiplying
    # correlated layers.
    union=min(1.,sum(x.probability_upper for x in bounds))
    if all(x.independence_certified and x.common_mode_group is None for x in bounds):
        independent=prod(x.probability_upper for x in bounds)
    else:
        independent=None
    return {
        "status":"PASS","method":"PRODUCT_WITH_CERTIFIED_INDEPENDENCE" if independent is not None else "UNION_BOUND",
        "combined_failure_upper": independent if independent is not None else union,
        "union_bound": union,
        "independent_product": independent,
        "layers":[x.name for x in bounds],
    }
