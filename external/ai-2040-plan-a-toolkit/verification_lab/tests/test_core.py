
import json, math
from pathlib import Path
from verification_lab.core import *

def test_17(): assert [x["id"] for x in json.loads(Path("verification_lab/workstreams.json").read_text())["workstreams"]]==list(range(1,18))
def test_tap(): assert math.isclose(OpticalTapDesign(1600,2,capture_overhead=1.1).required_capture_gbps(),3520,rel_tol=0,abs_tol=1e-9)
def test_capture(): assert CaptureFleet(100,3520,4000).server_count()==106
def test_bandwidth(): assert CaptureStrategy(.2,1,1).output_fraction()<.3
def test_path(): assert NetworkPath(("a",),(("a","b"),),(("a","b"),)).validate()["status"]=="PASS"
def test_det_and_packets(): assert DeterminismObservation(("a","a")).evaluate()["status"]=="PASS"; assert validate_packet_stream([Packet("p",0,"i","o","m","q")])["status"]=="PASS"
def test_sampling(): assert detection_confidence(.01,460)>.989; assert rogue_work_for_confidence(.99,.01)>450
def test_redteam(): assert len(red_team_catalog())>=5
def test_security_tap_reporting():
    assert evaluate_server_security([SecurityLayer("boot",True,"FAIL_CLOSED")])["status"]=="PASS"
    assert verify_tap_attestation(TapAttestation("t","a","a",True,True,"c"))["status"]=="PASS"
    a=VerificationReport("a","PASS","e","v",0,"0"*64); b=VerificationReport("b","PASS","e","v",1,a.digest()); assert validate_report_chain([a,b])["status"]=="PASS"
def test_memory_side_warden(): assert verify_memory_wipe(MemoryWipeResult("m","a","a",2,2))["status"]=="PASS"; assert SideChannelBudget(100,95,10).evaluate()["status"]=="PASS"; assert warden_score([0,10],0,1)["status"]=="ALERT"
def test_unknown(): assert transition_state("UNKNOWN","PASS",evidence_present=False)=="UNKNOWN"
def test_merkle():
    ls=["a","b","c"]; r=merkle_root(ls); assert verify_merkle_proof("b",merkle_proof(ls,1),r); assert not verify_merkle_proof("x",merkle_proof(ls,1),r)
def test_accounting():
    from verification_lab.core import ComputeHolding
    x=reconcile_holdings([ComputeHolding("u","h",10,"s",.4)])
    assert x["owner_totals"]["u"]==10
