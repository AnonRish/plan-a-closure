from __future__ import annotations
from pathlib import Path
import time

def read_rapl_energy(root:str="/sys/class/powercap")->dict:
    base=Path(root)
    zones=[]
    if not base.exists(): return {"status":"UNKNOWN","reason":"Linux powercap filesystem unavailable"}
    for p in base.glob("intel-rapl*"):
        e=p/"energy_uj"
        if e.exists():
            try: zones.append({"zone":p.name,"energy_uj":int(e.read_text().strip())})
            except ValueError: pass
    return {"status":"PASS" if zones else "UNKNOWN","timestamp_ns":time.time_ns(),"zones":zones,"source":str(base)}
