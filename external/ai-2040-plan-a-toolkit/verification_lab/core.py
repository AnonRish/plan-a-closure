
from __future__ import annotations
import hashlib, hmac, math
from dataclasses import dataclass, field
from typing import Sequence, Iterable

def sha256(x: bytes|str)->str:
    return hashlib.sha256(x.encode() if isinstance(x,str) else x).hexdigest()

@dataclass(frozen=True)
class OpticalTapDesign:
    line_rate_gbps: float; ports:int=1; mirror_fraction:float=1.; encoding_overhead:float=1.; capture_overhead:float=1.15
    def required_capture_gbps(self): return self.line_rate_gbps*self.ports*self.mirror_fraction*self.encoding_overhead*self.capture_overhead

@dataclass(frozen=True)
class CaptureFleet:
    tap_count:int; required_gbps_per_tap:float; server_capacity_gbps:float; redundancy:float=1.2
    def server_count(self): return math.ceil(self.tap_count*self.required_gbps_per_tap*self.redundancy/self.server_capacity_gbps)

@dataclass(frozen=True)
class CaptureStrategy:
    payload_copy_fraction:float; hash_fraction:float; sampled_fraction:float
    def output_fraction(self):
        if not all(0<=x<=1 for x in (self.payload_copy_fraction,self.hash_fraction,self.sampled_fraction)): raise ValueError("fractions must be in [0,1]")
        return min(1.,self.payload_copy_fraction+.01*self.hash_fraction+.05*self.sampled_fraction)

@dataclass(frozen=True)
class NetworkPath:
    segments:tuple[str,...]; directional_edges:tuple[tuple[str,str],...]; allowlisted_edges:tuple[tuple[str,str],...]=()
    def validate(self):
        allowed=set(self.allowlisted_edges); unexpected=sorted(set(self.directional_edges)-allowed)
        return {"status":"PASS" if not unexpected else "FAIL","unexpected_edges":unexpected}

@dataclass(frozen=True)
class RuntimeFingerprint:
    code:str; model:str; runtime:str; compiler:str; driver:str; hardware:str
    def digest(self): return sha256("|".join((self.code,self.model,self.runtime,self.compiler,self.driver,self.hardware)))

@dataclass(frozen=True)
class DeterminismObservation:
    run_digests:tuple[str,...]
    def evaluate(self):
        if not self.run_digests:return {"status":"UNKNOWN"}
        return {"status":"PASS" if len(set(self.run_digests))==1 else "FAIL","unique":len(set(self.run_digests))}

@dataclass(frozen=True)
class Packet:
    packet_id:str; sequence:int; input_digest:str; output_digest:str; model_digest:str; policy_digest:str
    def canonical_digest(self): return sha256("|".join((self.packet_id,str(self.sequence),self.input_digest,self.output_digest,self.model_digest,self.policy_digest)))

def validate_packet_stream(packets:Sequence[Packet]):
    if not packets:return {"status":"UNKNOWN"}
    ordered=sorted(packets,key=lambda p:p.sequence); actual=[p.sequence for p in ordered]
    gaps=actual!=list(range(actual[0],actual[0]+len(actual))); dup=len({p.packet_id for p in packets})!=len(packets)
    return {"status":"PASS" if not gaps and not dup else "FAIL","sequence_gaps":gaps,"duplicate_packet_ids":dup}

def detection_confidence(recomputation_fraction:float, rogue_work_units:float)->float:
    if not 0<=recomputation_fraction<=1 or rogue_work_units<0: raise ValueError("invalid inputs")
    return 1-math.exp(-recomputation_fraction*rogue_work_units)

def rogue_work_for_confidence(confidence:float,recomputation_fraction:float)->float:
    if not 0<confidence<1 or not 0<recomputation_fraction<=1: raise ValueError("invalid inputs")
    return -math.log(1-confidence)/recomputation_fraction

@dataclass
class RecomputationAlgorithmRegistry:
    algorithms:dict[str,dict]=field(default_factory=dict)
    def register(self,name:str,model_families:Iterable[str],maturity:str): self.algorithms[name]={"model_families":sorted(set(model_families)),"maturity":maturity}
    def select(self,model_family:str): return sorted(k for k,v in self.algorithms.items() if model_family in v["model_families"])

RED_TEAM_CASES=("selective_packet_substitution","adaptive_seed_prediction","digest_rebinding","runtime_drift","output_aliasing","sampling_starvation")
def red_team_catalog(): return list(RED_TEAM_CASES)

@dataclass(frozen=True)
class SecurityLayer:
    name:str; independent_observer:bool; tamper_response:str

def evaluate_server_security(layers:Sequence[SecurityLayer]):
    if not layers:return {"status":"UNKNOWN"}
    missing=[x.name for x in layers if not x.independent_observer]
    weak=[x.name for x in layers if x.tamper_response not in {"FAIL_CLOSED","ZEROIZE_AND_ALERT"}]
    return {"status":"PASS" if not missing and not weak else "UNKNOWN","missing_independent_observer":missing,"weak_tamper_response":weak}

@dataclass(frozen=True)
class TapAttestation:
    tap_id:str; expected_config_digest:str; measured_config_digest:str; enclosure_sensor_ok:bool; link_state_ok:bool; last_challenge:str

def verify_tap_attestation(a:TapAttestation):
    checks={"config":hmac.compare_digest(a.expected_config_digest,a.measured_config_digest),"enclosure":a.enclosure_sensor_ok,"link_state":a.link_state_ok,"challenge":bool(a.last_challenge)}
    return {"status":"PASS" if all(checks.values()) else "FAIL","checks":checks}

@dataclass(frozen=True)
class VerificationReport:
    report_id:str; result:str; evidence_root:str; verifier_id:str; sequence:int; previous_report_digest:str
    def digest(self): return sha256("|".join((self.report_id,self.result,self.evidence_root,self.verifier_id,str(self.sequence),self.previous_report_digest)))

def validate_report_chain(reports:Sequence[VerificationReport]):
    prev="0"*64; broken=[]
    for r in sorted(reports,key=lambda x:x.sequence):
        if r.previous_report_digest!=prev: broken.append(r.report_id)
        prev=r.digest()
    return {"status":"PASS" if not broken else "FAIL","broken_reports":broken}

@dataclass(frozen=True)
class InspectionItem:
    item_id:str; required:bool; observed:bool; evidence_digest:str|None=None

def evaluate_inspection(items:Sequence[InspectionItem]):
    missing=[x.item_id for x in items if x.required and not x.observed]
    unsigned=[x.item_id for x in items if x.observed and not x.evidence_digest]
    return {"status":"PASS" if not missing and not unsigned else ("UNKNOWN" if missing else "FAIL"),"missing_required":missing,"observed_without_evidence":unsigned}

@dataclass(frozen=True)
class MemoryWipeResult:
    region_id:str; challenge_digest:str; observed_digest:str; overwrite_passes:int; minimum_passes:int

def verify_memory_wipe(r:MemoryWipeResult):
    ok=r.overwrite_passes>=r.minimum_passes and hmac.compare_digest(r.challenge_digest,r.observed_digest)
    return {"status":"PASS" if ok else "FAIL","region_id":r.region_id}

@dataclass(frozen=True)
class SideChannelBudget:
    channel_capacity_bits_per_second:float; monitoring_noise_bits_per_second:float; residual_capacity_bits_per_second:float
    def evaluate(self):
        residual=max(0.,self.channel_capacity_bits_per_second-self.monitoring_noise_bits_per_second)
        return {"status":"PASS" if residual<=self.residual_capacity_bits_per_second else "FAIL","estimated_residual_capacity_bits_per_second":residual}

def warden_score(observations:Sequence[float],baseline_mean:float,baseline_std:float):
    if baseline_std<=0: raise ValueError("baseline_std must be positive")
    z=max((abs((x-baseline_mean)/baseline_std) for x in observations),default=0.)
    return {"status":"ALERT" if z>=5 else "NORMAL","max_abs_z":z,"observations":len(observations)}

VALID_STATES={"UNASSESSED","TESTED","CONTINUOUSLY_VERIFIED","PASS","FAIL","UNKNOWN","NOT_TESTED","NOT_APPLICABLE"}
def transition_state(current:str,target:str,*,evidence_present:bool):
    if current not in VALID_STATES or target not in VALID_STATES: raise ValueError("unknown state")
    return "UNKNOWN" if target=="PASS" and not evidence_present else target

def merkle_root(leaves:Sequence[str]):
    if not leaves:return sha256(b"")
    level=list(leaves)
    while len(level)>1:
        if len(level)%2: level.append(level[-1])
        level=[sha256(level[i]+level[i+1]) for i in range(0,len(level),2)]
    return level[0]

def merkle_proof(leaves:Sequence[str],index:int):
    if not 0<=index<len(leaves): raise IndexError(index)
    level=list(leaves); idx=index; proof=[]
    while len(level)>1:
        if len(level)%2: level.append(level[-1])
        sib=idx-1 if idx%2 else idx+1; proof.append(("L" if idx%2 else "R",level[sib]))
        level=[sha256(level[i]+level[i+1]) for i in range(0,len(level),2)]; idx//=2
    return proof

def verify_merkle_proof(leaf:str,proof,expected_root:str):
    node=leaf
    for d,sib in proof: node=sha256(sib+node) if d=="L" else sha256(node+sib)
    return hmac.compare_digest(node,expected_root)

@dataclass(frozen=True)
class ComputeHolding:
    owner_id:str; chip_family:str; quantity:float; source:str; source_confidence:float

def reconcile_holdings(records:Sequence[ComputeHolding]):
    totals={}
    low=[]
    for r in records:
        totals[r.owner_id]=totals.get(r.owner_id,0)+r.quantity
        if r.source_confidence<.5: low.append(r.owner_id)
    return {"status":"PASS" if records else "UNKNOWN","owner_totals":totals,"low_confidence_owners":sorted(set(low))}
