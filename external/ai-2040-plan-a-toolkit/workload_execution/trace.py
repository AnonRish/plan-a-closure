from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256

@dataclass(frozen=True)
class ExecutionEvent:
    sequence:int
    operation:str
    resource_delta:dict[str,float]
    artifact_digests:dict[str,str]

@dataclass(frozen=True)
class ExecutionTrace:
    manifest_digest:str
    events:tuple[ExecutionEvent,...]
    terminal_result:str

def trace_digest(t:ExecutionTrace)->str:
    raw="|".join([t.manifest_digest,t.terminal_result]+[f"{e.sequence}:{e.operation}:{sorted(e.resource_delta.items())}:{sorted(e.artifact_digests.items())}" for e in t.events])
    return sha256(raw.encode()).hexdigest()

def validate_trace(trace:ExecutionTrace,allowed_operations:frozenset[str],resource_caps:dict[str,float],expected_artifacts:dict[str,str])->dict:
    seq=[e.sequence for e in trace.events]; errors=[]
    if seq!=list(range(len(seq))): errors.append("sequence gap or duplicate")
    total={}
    for e in trace.events:
        if e.operation not in allowed_operations: errors.append(f"operation outside allow-list: {e.operation}")
        for k,v in e.resource_delta.items():
            total[k]=total.get(k,0)+v
            if total[k]>resource_caps.get(k,float("inf")): errors.append(f"resource cap exceeded: {k}")
        for k,expected in expected_artifacts.items():
            if k in e.artifact_digests and e.artifact_digests[k]!=expected: errors.append(f"artifact mismatch: {k}")
    return {"status":"PASS" if not errors else "FAIL","errors":sorted(set(errors)),"trace_digest":trace_digest(trace),"total_resources":total}
