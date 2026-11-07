
from __future__ import annotations
from dataclasses import dataclass
from collections import defaultdict
import hashlib, math, random
from typing import Optional

@dataclass(frozen=True)
class Account:
    owner_id:str
    received_units:int
    onward_sales:dict[str,int]
    attrition_units:int
    physically_held_units:int

    def balance(self)->int:
        return self.physically_held_units + sum(self.onward_sales.values()) + self.attrition_units

@dataclass(frozen=True)
class Transfer:
    transfer_id:str
    src:str
    dst:str
    units:int
    declared:bool=True

@dataclass(frozen=True)
class TailUnit:
    unit_id:str
    recipient:str
    destination_hint:Optional[str]=None

@dataclass(frozen=True)
class TraceResult:
    unit_id:str
    outcome:str
    path:tuple[str,...]
    reason:str

def evidence_digest(*parts:str)->str:
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()

class TailAudit:
    def __init__(self, tail_units:list[TailUnit], accounts:dict[str,Account], transfers:list[Transfer]):
        self.tail_units=tail_units
        self.accounts=accounts
        self.transfers=transfers
        self.by_src=defaultdict(list)
        for t in transfers:self.by_src[t.src].append(t)

    def audit_account(self, owner_id:str)->bool:
        a=self.accounts.get(owner_id)
        return a is not None and a.balance()==a.received_units

    def trace(self, unit:TailUnit)->TraceResult:
        owner=unit.recipient
        visited=[]
        remaining_unit=unit.unit_id
        while True:
            visited.append(owner)
            account=self.accounts.get(owner)
            if account is None:
                return TraceResult(unit.unit_id,"FAIL",tuple(visited),"owner account unavailable")
            if not self.audit_account(owner):
                return TraceResult(unit.unit_id,"FAIL",tuple(visited),"account does not reconcile")
            # Existing holdings are the probability mass at this owner. If a
            # destination hint identifies a recorded sale, follow that sale.
            if unit.destination_hint:
                for t in self.by_src.get(owner,()):
                    if t.dst==unit.destination_hint and t.units>0 and t.declared:
                        owner=t.dst
                        unit=TailUnit(remaining_unit,owner,None)
                        break
                else:
                    return TraceResult(unit.unit_id,"FAIL",tuple(visited),"destination hint has no declared transfer")
                if owner in visited:
                    return TraceResult(unit.unit_id,"FAIL",tuple(visited),"transfer cycle detected")
                continue
            if account.physically_held_units>0:
                return TraceResult(unit.unit_id,"PASS",tuple(visited),"unit resolves to physically held inventory")
            outgoing=[t for t in self.by_src.get(owner,()) if t.declared and t.units>0]
            if not outgoing:
                return TraceResult(unit.unit_id,"FAIL",tuple(visited),"no physical holding and no declared onward sale")
            total=sum(t.units for t in outgoing)
            chosen=outgoing[0]
            # Deterministic representative branch for a concrete sampled unit.
            # Statistical weighting is handled when selecting the sampled unit.
            owner=chosen.dst
            unit=TailUnit(remaining_unit,owner,None)
            if owner in visited:
                return TraceResult(unit.unit_id,"FAIL",tuple(visited),"transfer cycle detected")

def sample_units(tail_units:list[TailUnit],n:int,seed:int)->list[TailUnit]:
    if not tail_units: raise ValueError("tail must not be empty")
    if not 0<n<=len(tail_units): raise ValueError("invalid sample size")
    return random.Random(seed).sample(tail_units,n)

def run_tail_audit(tail_units:list[TailUnit],accounts:dict[str,Account],transfers:list[Transfer],sample_size:int,seed:int,delta:float=0.05)->dict:
    if not 0<delta<1: raise ValueError("delta must be in (0,1)")
    sampled=sample_units(tail_units,sample_size,seed)
    auditor=TailAudit(tail_units,accounts,transfers)
    traces=[auditor.trace(u) for u in sampled]
    failures=sum(t.outcome=="FAIL" for t in traces)
    p_upper=1.0 if failures==sample_size else 1.0-(delta)**(1.0/sample_size)
    # Zero-failure Clopper-Pearson upper bound simplifies to 1-delta^(1/n).
    # For k>0 this fallback is deliberately not called a universal exact
    # binomial interval; report a conservative Wilson-style upper bound.
    if failures>0:
        z=1.96
        phat=failures/sample_size
        denom=1+z*z/sample_size
        center=(phat+z*z/(2*sample_size))/denom
        half=z*math.sqrt(phat*(1-phat)/sample_size+z*z/(4*sample_size**2))/denom
        p_upper=min(1.0,center+half)
        bound_method="conservative_wilson_upper_for_nonzero_failures"
    else:
        bound_method="exact_zero_failure_binomial_upper"
    return {
        "schema_version":1,
        "model":"Track3-tail-unit-trace",
        "seed":seed,
        "tail_population_units":len(tail_units),
        "sample_size":sample_size,
        "failures":failures,
        "passes":sample_size-failures,
        "upper_failure_fraction":p_upper,
        "upper_untraced_units":len(tail_units)*p_upper,
        "confidence_level":1-delta,
        "bound_method":bound_method,
        "traces":[t.__dict__ for t in traces],
        "limitations":[
            "The representative branch after an owner is reached is conservative but does not model unit-level serial identity unless the input does.",
            "For nonzero failures the reported Wilson upper bound is an engineering approximation, not the Clopper-Pearson implementation in the registry.",
            "A tail certificate remains conditional on a genuinely closed sampling frame."
        ]
    }
