from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class Phase(Enum):
    OPEN='OPEN'; COMMITTED='COMMITTED'; CHALLENGED='CHALLENGED'; CHECKED='CHECKED'; TERMINAL='TERMINAL'

@dataclass
class State:
    phase:Phase=Phase.OPEN
    claim_root:str|None=None
    challenge:str|None=None
    result:str|None=None
    evidence:tuple[str,...]=()

def commit(s:State,claim_root:str):
    if s.phase is not Phase.OPEN: raise ValueError('commit only from OPEN')
    if not claim_root: raise ValueError('commitment must be non-empty')
    s.claim_root=claim_root; s.phase=Phase.COMMITTED

def challenge(s:State,challenge_id:str):
    if s.phase is not Phase.COMMITTED: raise ValueError('challenge only after commitment')
    if not challenge_id: raise ValueError('challenge must be non-empty')
    s.challenge=challenge_id; s.phase=Phase.CHALLENGED

def check(s:State,result:str,evidence:tuple[str,...]=('sample',)):
    if s.phase is not Phase.CHALLENGED: raise ValueError('check only after challenge')
    if result not in {'PASS','FAIL','UNKNOWN'}: raise ValueError('bad result')
    if result=='PASS' and not evidence: raise ValueError('PASS requires evidence')
    s.result=result; s.evidence=tuple(evidence); s.phase=Phase.CHECKED

def terminalize(s:State):
    if s.phase is not Phase.CHECKED: raise ValueError('terminalize only after check')
    s.phase=Phase.TERMINAL

def safety_invariants(s:State)->list[str]:
    errors=[]
    if s.phase in {Phase.CHALLENGED,Phase.CHECKED,Phase.TERMINAL} and not s.claim_root: errors.append('no commitment')
    if s.phase in {Phase.CHECKED,Phase.TERMINAL} and not s.challenge: errors.append('no challenge')
    if s.phase is Phase.TERMINAL and s.result=='PASS' and not s.evidence: errors.append('PASS without evidence')
    return errors
