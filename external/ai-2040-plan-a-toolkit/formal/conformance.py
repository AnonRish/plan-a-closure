from __future__ import annotations
from itertools import product
from .reference_model import State, commit, challenge, check, terminalize, safety_invariants
OPS=('commit','challenge','check','terminalize')

def execute(sequence:tuple[str,...])->dict:
    s=State(); accepted=[]; rejected=[]
    for op in sequence:
        try:
            if op=='commit': commit(s,'root')
            elif op=='challenge': challenge(s,'c')
            elif op=='check': check(s,'PASS',('sample',))
            elif op=='terminalize': terminalize(s)
            accepted.append(op)
        except ValueError:
            rejected.append(op)
        errors=safety_invariants(s)
        if errors: return {'status':'FAIL','errors':errors,'accepted':accepted,'rejected':rejected}
    return {'status':'PASS','errors':[],'accepted':accepted,'rejected':rejected,'phase':s.phase.value}

def bounded_state_conformance(depth:int=5)->dict:
    if depth<1: raise ValueError('depth must be positive')
    checked=0; violations=[]
    for n in range(1,depth+1):
        for seq in product(OPS,repeat=n):
            checked+=1; result=execute(seq)
            if result['status']!='PASS': violations.append({'sequence':seq,'result':result})
    return {'status':'PASS' if not violations else 'FAIL','checked_sequences':checked,'violations':violations}
