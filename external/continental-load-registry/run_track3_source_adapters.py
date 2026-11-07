#!/usr/bin/env python3
"""Run all repository-backed automated Track 3 source adapters sequentially.

Source-specific parsers remain the authority for their own formats. This wrapper
adds a single run ledger and continues through adapter failures so one outage
does not suppress unrelated sources.
"""
from __future__ import annotations
import json,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
COMMANDS=[
 ("CAISO","sync_caiso_public_queue.py --output-dir data"),
 ("MISO","sync_miso_public_queue.py --output-dir data"),
 ("NYISO","sync_nyiso_public_queue.py --output-dir data"),
 ("PJM","sync_pjm_cycle_public_queue.py --output-dir data"),
 ("SPP","sync_spp_public_queue.py --output-dir data"),
 ("Epoch AI","sync_epoch_ai_data_centers.py --sync"),
 ("Epoch external compute","sync_track3_external_sources.py"),
 ("ERCOT / ISO-NE / IESO / AESO raw source capture","sync_auxiliary_queue_sources.py"),
]
def main():
  rows=[]
  for source,cmd in COMMANDS:
    started=datetime.now(timezone.utc).isoformat()
    p=subprocess.run([sys.executable,*cmd.split()],cwd=ROOT,text=True,capture_output=True)
    rows.append({"source":source,"command":cmd,"started_at_utc":started,"finished_at_utc":datetime.now(timezone.utc).isoformat(),"exit_code":p.returncode,"status":"SUCCESS" if p.returncode==0 else "FAILED","stdout_tail":p.stdout[-4000:],"stderr_tail":p.stderr[-4000:]})
  out={"schema_version":1,"generated_at_utc":datetime.now(timezone.utc).isoformat(),"adapter_count":len(rows),"failed_count":sum(x["status"]=="FAILED" for x in rows),"runs":rows}
  path=ROOT/"data"/"automation"/"adapter_run_report.json"; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
  print(json.dumps(out,indent=2))
  return 1 if out["failed_count"] else 0
if __name__=="__main__": raise SystemExit(main())
