
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

class InstallState(Enum):
    PROCURED="PROCURED"; BENCH_TESTED="BENCH_TESTED"; INSTALLED="INSTALLED"; ACCEPTED="ACCEPTED"; RETIRED="RETIRED"

@dataclass(frozen=True)
class Asset:
    asset_id:str
    kind:str
    state:InstallState
    expected_config_digest:str
    measured_config_digest:str|None
    spare:bool=False
    independent_inspector:bool=False

def evaluate_fleet(assets:list[Asset],required:int)->dict:
    active=[a for a in assets if a.state is InstallState.ACCEPTED and not a.spare]
    installed=[a for a in assets if a.state in {InstallState.INSTALLED,InstallState.ACCEPTED} and not a.spare]
    bad_config=[a.asset_id for a in installed if not a.measured_config_digest or a.measured_config_digest!=a.expected_config_digest]
    uninspected=[a.asset_id for a in active if not a.independent_inspector]
    return {
        "status":"PASS" if len(active)>=required and not bad_config and not uninspected else "UNKNOWN",
        "required":required,"accepted_active":len(active),"installed":len(installed),
        "config_findings":bad_config,"uninspected":uninspected,
        "spares":sum(1 for a in assets if a.spare and a.state is not InstallState.RETIRED),
    }
