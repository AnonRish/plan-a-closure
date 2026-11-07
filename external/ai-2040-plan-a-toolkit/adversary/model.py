from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class Surface(str, Enum):
    NETWORK='NETWORK'; COMPUTE='COMPUTE'; STORAGE='STORAGE'; FIRMWARE='FIRMWARE'; PHYSICAL='PHYSICAL'; SUPPLY_CHAIN='SUPPLY_CHAIN'; VERIFIER='VERIFIER'; SAMPLING_FRAME='SAMPLING_FRAME'; TELEMETRY='TELEMETRY'
SAFE_OUTCOMES=frozenset({'FAIL','UNKNOWN','INVESTIGATE'})

@dataclass(frozen=True)
class AttackCase:
    attack_id:str; surface:Surface; description:str; expected_safe_outcome:str; controls:tuple[str,...]; common_mode_group:str|None=None
@dataclass(frozen=True)
class Control:
    control_id:str; surface:Surface; evidence_requirement:str; fail_mode:str

DEFAULT_CONTROLS=(
Control('C-NET-CAPTURE',Surface.NETWORK,'software_or_hardware_capture','UNKNOWN'),
Control('C-NET-REASSEMBLY',Surface.NETWORK,'software_capture','FAIL'),
Control('C-COMPUTE-METER',Surface.COMPUTE,'bench_hardware','UNKNOWN'),
Control('C-STORAGE-PATH',Surface.STORAGE,'bench_hardware','FAIL'),
Control('C-FW-ATTEST',Surface.FIRMWARE,'hardware_attested','FAIL'),
Control('C-PHYSICAL-CUSTODY',Surface.PHYSICAL,'operational_field','FAIL'),
Control('C-SUPPLY-CONSERVE',Surface.SUPPLY_CHAIN,'independent_replication','UNKNOWN'),
Control('C-VERIFIER-QUORUM',Surface.VERIFIER,'software_tested','FAIL'),
Control('C-SAMPLING-COMMIT',Surface.SAMPLING_FRAME,'independent_replication','UNKNOWN'),
Control('C-TELEMETRY-CORRELATE',Surface.TELEMETRY,'bench_hardware','UNKNOWN'),)

def default_attack_catalog():
    return (
    AttackCase('RT-NET-OMIT',Surface.NETWORK,'selectively omit tapped frames','UNKNOWN',('C-NET-CAPTURE',)),
    AttackCase('RT-NET-REORDER',Surface.NETWORK,'reorder or duplicate frames','FAIL',('C-NET-REASSEMBLY',)),
    AttackCase('RT-COMPUTE-COUNTER',Surface.COMPUTE,'under-report accelerator counter','UNKNOWN',('C-COMPUTE-METER',)),
    AttackCase('RT-STORAGE-REPLACE',Surface.STORAGE,'replace approved weights in transit','FAIL',('C-STORAGE-PATH',)),
    AttackCase('RT-FW-SPOOF',Surface.FIRMWARE,'present a stale or altered firmware measurement','FAIL',('C-FW-ATTEST',)),
    AttackCase('RT-PHYSICAL-TAP',Surface.PHYSICAL,'remove, bypass or replace an observation device','FAIL',('C-PHYSICAL-CUSTODY',)),
    AttackCase('RT-SUPPLY-MISSING',Surface.SUPPLY_CHAIN,'erase or fabricate a chip transfer event','UNKNOWN',('C-SUPPLY-CONSERVE',)),
    AttackCase('RT-VERIFIER-FORGE',Surface.VERIFIER,'forge or replay a verifier result','FAIL',('C-VERIFIER-QUORUM',)),
    AttackCase('RT-SAMPLE-PREDICT',Surface.SAMPLING_FRAME,'predict the sample before commitment','UNKNOWN',('C-SAMPLING-COMMIT',)),
    AttackCase('RT-TELEMETRY-SPOOF',Surface.TELEMETRY,'report telemetry inconsistent with independent observation','UNKNOWN',('C-TELEMETRY-CORRELATE',)),
    AttackCase('RT-OUTSIDE-POPULATION',Surface.SAMPLING_FRAME,'place prohibited compute outside the declared population','INVESTIGATE',('C-SAMPLING-COMMIT','C-SUPPLY-CONSERVE')),
    AttackCase('RT-COMMON-MODE',Surface.VERIFIER,'corrupt nominally separate controls through one shared trust root','UNKNOWN',('C-VERIFIER-QUORUM',),'identity-root'))

def coverage_report(attacks=None,controls=DEFAULT_CONTROLS):
    attacks=default_attack_catalog() if attacks is None else attacks; control_ids={c.control_id for c in controls}; errors=[]
    for a in attacks:
        if a.expected_safe_outcome not in SAFE_OUTCOMES: errors.append(f'{a.attack_id}: unsafe expected outcome')
        missing=sorted(set(a.controls)-control_ids)
        if missing: errors.append(f'{a.attack_id}: missing controls {missing}')
    by_surface={s.value:0 for s in Surface}
    for a in attacks: by_surface[a.surface.value]+=1
    return {'status':'PASS' if not errors else 'FAIL','attack_count':len(attacks),'control_count':len(controls),'attacks_by_surface':by_surface,'errors':errors,'safe_outcomes':sorted(SAFE_OUTCOMES),'note':'Coverage maps modeled attacks to controls; it does not prove field detection.'}

def evaluate_observed(attack,observed_outcome):
    if observed_outcome not in {'PASS','FAIL','UNKNOWN','INVESTIGATE'}: raise ValueError('invalid observed outcome')
    return {'attack_id':attack.attack_id,'observed_outcome':observed_outcome,'safe':observed_outcome in SAFE_OUTCOMES,'meets_predeclared_expectation':observed_outcome==attack.expected_safe_outcome}
