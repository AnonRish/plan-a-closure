#!/usr/bin/env python3
import json
from pathlib import Path
from .retrofit import run_retrofit_simulation
def main():
    report=run_retrofit_simulation()
    Path("retrofit_readiness_report.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
if __name__=="__main__": main()
