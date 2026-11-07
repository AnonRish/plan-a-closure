
import json
from pathlib import Path
from hostile_prover.simulator import benchmark

def main():
    out=benchmark(seed=20260928,trials=10000)
    Path("adversarial_results.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(out,indent=2))
if __name__=="__main__":main()
