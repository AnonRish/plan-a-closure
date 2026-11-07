from __future__ import annotations
from dataclasses import dataclass,asdict
import csv,io,subprocess

@dataclass(frozen=True)
class GPUSnapshot:
    uuid:str
    power_w:float
    utilization_pct:float
    memory_used_mib:float

def parse_nvidia_smi(text:str)->list[GPUSnapshot]:
    rows=csv.reader(io.StringIO(text))
    out=[]
    for row in rows:
        row=[x.strip() for x in row]
        if len(row)!=4:continue
        try:out.append(GPUSnapshot(row[0],float(row[1]),float(row[2]),float(row[3])))
        except ValueError:continue
    return out

def query_nvidia_smi()->list[GPUSnapshot]:
    cmd=["nvidia-smi","--query-gpu=uuid,power.draw,utilization.gpu,memory.used","--format=csv,noheader,nounits"]
    p=subprocess.run(cmd,capture_output=True,text=True,check=True,timeout=10)
    return parse_nvidia_smi(p.stdout)

def snapshot_report()->dict:
    gpus=query_nvidia_smi()
    return {"status":"PASS" if gpus else "UNKNOWN","gpu_count":len(gpus),"gpus":[asdict(g) for g in gpus],
            "source":"nvidia-smi","note":"Vendor telemetry is evidence input, not proof of workload identity or immutable hardware-rooted accounting."}
