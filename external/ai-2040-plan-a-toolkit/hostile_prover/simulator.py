
from __future__ import annotations
from dataclasses import dataclass
import hashlib, math, random
from typing import Literal

Strategy=Literal["honest","omit","substitute","rebind","adaptive"]

@dataclass(frozen=True)
class TrialResult:
    strategy:str
    committed:int
    sampled:int
    compromised:int
    detected:bool

def derive_challenge(seed:int,commitment:str)->int:
    return int(hashlib.sha256(f"{seed}:{commitment}".encode()).hexdigest()[:16],16)

def sample_indices(count:int,sample_fraction:float,challenge:int)->set[int]:
    if count<=0 or not 0<sample_fraction<=1: raise ValueError("invalid sample parameters")
    n=max(1,math.ceil(count*sample_fraction)); rng=random.Random(challenge); return set(rng.sample(range(count),n))

def commitment(items:list[str])->str:
    return hashlib.sha256("|".join(items).encode()).hexdigest()

def simulate_trial(count:int=100,sample_fraction:float=.01,strategy:Strategy="honest",seed:int=1)->TrialResult:
    honest=[hashlib.sha256(f"packet-{i}".encode()).hexdigest() for i in range(count)]
    if strategy=="honest": claimed=honest[:]; compromised=0
    elif strategy=="omit": claimed=honest[:-1]; compromised=1
    elif strategy=="substitute": claimed=honest[:]; claimed[0]="0"*64; compromised=1
    elif strategy=="rebind": claimed=honest[:]; claimed[count//2]=hashlib.sha256(b"different").hexdigest(); compromised=1
    elif strategy=="adaptive":
        precommit=commitment(honest)
        challenge=derive_challenge(seed,precommit)
        sample=sample_indices(count,sample_fraction,challenge)
        claimed=honest[:]
        target=min(set(range(count))-sample)
        claimed[target]="0"*64; compromised=1
    else: raise ValueError("unknown strategy")
    com=commitment(claimed); challenge=derive_challenge(seed,com); sampled=sample_indices(len(claimed),sample_fraction,challenge)
    # Omission changes the committed cardinality and is itself a detectable invariant.
    detected=(len(claimed)!=count) or any(claimed[i]!=honest[i] for i in sampled if i<count)
    return TrialResult(strategy,count,len(sampled),compromised,detected)

def benchmark(seed:int=42,trials:int=10000)->dict:
    rng=random.Random(seed);out={}
    for strategy in ("honest","omit","substitute","rebind","adaptive"):
        results=[simulate_trial(seed=rng.randrange(1<<60),strategy=strategy) for _ in range(trials)]
        rate=sum(r.detected for r in results)/trials
        out[strategy]={"trials":trials,"detections":sum(r.detected for r in results),"detection_rate":rate}
    return {"seed":seed,"trials":trials,"sample_fraction":.01,"results":out}
