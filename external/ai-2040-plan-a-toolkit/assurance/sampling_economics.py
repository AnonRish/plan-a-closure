
from __future__ import annotations
import math
from dataclasses import dataclass

@dataclass(frozen=True)
class SamplingPlan:
    fake_fraction: float
    packet_h100e_hours: float
    confidence: float
    verifier_budget_h100e_hours: float

    def required_verified_packets(self)->float:
        if not 0<self.fake_fraction<=1 or not 0<self.confidence<1:
            raise ValueError("invalid fraction/confidence")
        return -math.log(1-self.confidence)/self.fake_fraction

    def required_rogue_compute(self)->float:
        return self.required_verified_packets()*self.packet_h100e_hours

    def achieved_confidence(self)->float:
        if self.packet_h100e_hours<=0 or self.verifier_budget_h100e_hours<0:
            raise ValueError("invalid packet/budget")
        verified=self.verifier_budget_h100e_hours/self.packet_h100e_hours
        return 1-math.exp(-self.fake_fraction*verified)

def compare_to_budget(plan:SamplingPlan)->dict:
    required=plan.required_rogue_compute()
    return {
        "required_verified_packets":plan.required_verified_packets(),
        "required_verifier_budget_h100e_hours":required,
        "available_verifier_budget_h100e_hours":plan.verifier_budget_h100e_hours,
        "achieved_confidence":plan.achieved_confidence(),
        "meets_target":plan.verifier_budget_h100e_hours>=required,
    }

def exact_detection_probability(population_size:int, rogue_units:int, sample_size:int)->float:
    if population_size<=0 or rogue_units<0 or rogue_units>population_size:
        raise ValueError("invalid population/rogue counts")
    if not 0<=sample_size<=population_size:
        raise ValueError("invalid sample size")
    if rogue_units==0 or sample_size==0:
        return 0.0
    if sample_size>population_size-rogue_units:
        return 1.0
    # Probability of missing every rogue unit under simple random sampling
    # without replacement. Use log-gamma to avoid huge integer combinations.
    log_no_detection=(
        math.lgamma(population_size-rogue_units+1)
        - math.lgamma(population_size-rogue_units-sample_size+1)
        - math.lgamma(population_size+1)
        + math.lgamma(population_size-sample_size+1)
    )
    return -math.expm1(log_no_detection)

def minimum_sample_for_exact_confidence(population_size:int, rogue_units:int, confidence:float)->int:
    if not 0<confidence<1:
        raise ValueError("confidence must be in (0,1)")
    if population_size<=0 or rogue_units<0 or rogue_units>population_size:
        raise ValueError("invalid population/rogue counts")
    if rogue_units==0:
        raise ValueError("cannot detect zero rogue units")
    lo,hi=0,population_size
    while lo<hi:
        mid=(lo+hi)//2
        if exact_detection_probability(population_size,rogue_units,mid)>=confidence: hi=mid
        else: lo=mid+1
    return lo
