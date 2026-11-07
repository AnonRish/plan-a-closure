
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Attack:
    attack_id:str
    surface:str
    objective:str
    expected_control:str

SCENARIOS=[
 Attack("RT-01","tap","suppress_capture","active_contract"),
 Attack("RT-02","packet","rebind_payload","commitment"),
 Attack("RT-03","timing","encode_covert_bits","timing_envelope"),
 Attack("RT-04","header","encode_covert_bits","header_whitelist"),
 Attack("RT-05","payload","encode_covert_bits","payload_budget"),
 Attack("RT-06","storage","replace_weights","weight_path"),
 Attack("RT-07","verifier","forge_result","signed_receipt"),
 Attack("RT-08","accounting","hide_compute_owner","closed_population_gate"),
 Attack("RT-09","memory","retain_unapproved_state","wipe_evidence"),
 Attack("RT-10","physical","tamper_device","independent_inspection"),
]

def catalog(): return [x.__dict__ for x in SCENARIOS]
