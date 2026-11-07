
from __future__ import annotations
from dataclasses import dataclass
from gateway.active_contract import enforce_contract
from gateway.policy import GatewayPolicy, EnvelopeClass
from storage.weight_path import WeightTransfer, validate_weight_path
from verification_lab.core import (
    MemoryWipeResult, SecurityLayer, TapAttestation, VerificationReport,
    evaluate_server_security, transition_state, validate_report_chain,
    verify_memory_wipe, verify_tap_attestation,
)
from provenance.gate import EvidenceArtifact, EvidenceLevel, Claim, can_promote
from assurance.compose import FailureBound, compose

@dataclass(frozen=True)
class AttackOutcome:
    attack_id:str
    observed_status:str
    safe:str
    control:str

def run_integrated_attacks()->list[AttackOutcome]:
    policy=GatewayPolicy((EnvelopeClass("inference",1,4096,20_000_000),),1000)
    outcomes=[]
    outcomes.append(AttackOutcome("RT-01",enforce_contract("secret",10,1,policy).action,"BLOCK","active gateway"))
    outcomes.append(AttackOutcome("RT-02",validate_weight_path(WeightTransfer("bank","inference","abc","BAD_CHANNEL",True,True))["status"],"FAIL","weight isolation"))
    outcomes.append(AttackOutcome("RT-03",verify_memory_wipe(MemoryWipeResult("m","expected","tampered",3,3))["status"],"FAIL","wipe evidence"))
    outcomes.append(AttackOutcome("RT-04",verify_tap_attestation(TapAttestation("t","a","b",True,True,"c"))["status"],"FAIL","tap attestation"))
    outcomes.append(AttackOutcome("RT-05",evaluate_server_security([SecurityLayer("boot",False,"ALLOW")])["status"],"UNKNOWN","server independence"))
    r=VerificationReport("r","PASS","e","v",0,"f"*64)
    outcomes.append(AttackOutcome("RT-06",validate_report_chain([r])["status"],"FAIL","report chain"))
    outcomes.append(AttackOutcome("RT-07",transition_state("UNKNOWN","PASS",evidence_present=False),"UNKNOWN","completeness invariant"))
    outcomes.append(AttackOutcome("RT-08",compose([FailureBound("a",.01),FailureBound("b",.02)])["method"],"UNION_BOUND","assurance composition"))
    claim=Claim("physical-tap",EvidenceLevel.BENCH_HARDWARE,("soft",))
    artifact=EvidenceArtifact("soft",EvidenceLevel.SOFTWARE_TESTED,"d","e")
    outcomes.append(AttackOutcome("RT-09",can_promote(claim,{"soft":artifact})["status"],"UNKNOWN","provenance gate"))
    return outcomes
