
from __future__ import annotations
import hashlib,json,platform,sys,time
from pathlib import Path

def run(size_mb:int=8,iterations:int=3)->dict:
    data=(bytes(range(256))*((size_mb*1024*1024//256)+1))[:size_mb*1024*1024]
    samples=[];digest=None
    for _ in range(iterations):
        t=time.perf_counter();digest=hashlib.sha256(data).hexdigest();dt=time.perf_counter()-t
        samples.append({"seconds":dt,"MiB_per_second":size_mb/dt if dt else 0})
    return {"benchmark":"sha256_bulk","bytes":len(data),"iterations":iterations,"digest":digest,"samples":samples,
            "environment":{"python":sys.version,"platform":platform.platform(),"machine":platform.machine()}}
def main():
    out=run();Path("benchmark_result.json").write_text(json.dumps(out,indent=2)+"\n");print(json.dumps(out,indent=2))
if __name__=="__main__":main()
