from __future__ import annotations
from pathlib import Path
import json

REQUIRED_FILES=('RVP-1.md','BENCHMARK_PROTOCOL.md','EVALUATOR_BRIEF.md','verification_lab/workstreams.json','.github/workflows/rvp-conformance.yml','scripts/run_rvp1.ps1')
REQUIRED_PACKAGES=('adversary','assurance','bandwidth_auction','benchmarks','capture_benchmark','challenge_scheduler','channel_budget','company_audit','compute_accounting','compute_meter','crypto','deployment','distillation_redteam','embedded_audit','evidence_graph','exfil_detector','formal','frame_processor','gateway','governance','handoff_calculator','hardware','hostile_prover','identity','input_warden','location','model_registry','passport','physical','plan_a_protocol','provenance','receipt_schema','redaction_pipeline','redteam','replication','rhetoric_highlighter','storage','supply_chain','telemetry','track3','trust_composition','verification_lab','workload_discriminator','workload_execution','workload_policy')

def validate_repository(root:str='.'):
    base=Path(root); errors=[]
    for path in REQUIRED_FILES:
        if not (base/path).exists(): errors.append(f'missing required file: {path}')
    for package in REQUIRED_PACKAGES:
        if not (base/package/'__init__.py').exists(): errors.append(f'missing package init: {package}')
    json_files=list(base.glob('**/*.json')); bad=[]
    for path in json_files:
        try: json.loads(path.read_text(encoding='utf-8'))
        except Exception: bad.append(str(path))
    if bad: errors.append('invalid JSON: '+', '.join(bad))
    return {'status':'PASS' if not errors else 'FAIL','required_file_count':len(REQUIRED_FILES),'package_count':len(REQUIRED_PACKAGES),'json_files_checked':len(json_files),'errors':errors}

if __name__=='__main__': print(json.dumps(validate_repository(),indent=2))
