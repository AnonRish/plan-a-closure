from __future__ import annotations
from dataclasses import dataclass
import hashlib,json

@dataclass(frozen=True)
class CounterSnapshot:
    device_id:str
    accelerator_family:str
    counter_name:str
    raw_value:float
    unit:str
    timestamp_ns:int
    reset_epoch:int
    source:str
    attestation_ref:str|None=None

@dataclass(frozen=True)
class FLOPModel:
    accelerator_family:str
    flops_per_counter_unit:float
    counter_unit:str
    model_version:str

def normalize_flops(snapshot:CounterSnapshot,model:FLOPModel)->dict:
    if snapshot.accelerator_family!=model.accelerator_family or snapshot.unit!=model.counter_unit:
        return {"status":"UNKNOWN","reason":"counter model mismatch"}
    if snapshot.raw_value<0:return {"status":"FAIL","reason":"negative hardware counter"}
    return {
        "status":"PASS",
        "device_id":snapshot.device_id,
        "normalized_flops":snapshot.raw_value*model.flops_per_counter_unit,
        "model_version":model.model_version,
        "attested":bool(snapshot.attestation_ref)
    }

def compare_snapshots(start:CounterSnapshot,end:CounterSnapshot)->dict:
    if start.device_id!=end.device_id:return {"status":"FAIL","reason":"device changed"}
    if start.reset_epoch!=end.reset_epoch:return {"status":"UNKNOWN","reason":"counter reset between snapshots"}
    if end.raw_value<start.raw_value:return {"status":"FAIL","reason":"counter decreased without reset"}
    return {"status":"PASS","delta":end.raw_value-start.raw_value}

def meter_digest(snapshots:list[CounterSnapshot])->str:
    payload=[s.__dict__ for s in sorted(snapshots,key=lambda x:(x.device_id,x.timestamp_ns,x.counter_name))]
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
