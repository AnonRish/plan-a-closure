
from __future__ import annotations
from dataclasses import dataclass,asdict
import json,platform,sys,time
from pathlib import Path

@dataclass
class Measurement:
    name:str
    value:float
    unit:str
    sample_count:int
    notes:str=""

@dataclass
class HardwareRun:
    run_id:str
    device:str
    started_utc_ns:int
    environment:dict
    measurements:list[Measurement]

def environment():
    return {"python":sys.version,"platform":platform.platform(),"machine":platform.machine(),"processor":platform.processor()}

def save_run(run:HardwareRun,path:str):
    Path(path).write_text(json.dumps({
        "run_id":run.run_id,"device":run.device,"started_utc_ns":run.started_utc_ns,
        "environment":run.environment,"measurements":[asdict(x) for x in run.measurements]
    },indent=2)+"\n",encoding="utf-8")

def timed(fn,iterations:int=3)->Measurement:
    values=[]
    for _ in range(iterations):
        t=time.perf_counter();fn();values.append(time.perf_counter()-t)
    return Measurement("wall_time",sum(values)/len(values),"seconds",iterations)
