
from workload_policy.classify import *
P=Policy(frozenset({"INFERENCE","EVAL"}),frozenset({"TRAINING","AUTONOMOUS_RESEARCH"}))
def test_banned_wins(): assert classify(["INFERENCE","TRAINING"],P,True)["status"]=="BANNED"
def test_missing_evidence_unknown(): assert classify(["INFERENCE"],P,False)["status"]=="UNKNOWN"
def test_approved_is_explicit(): assert classify(["INFERENCE","EVAL"],P,True)["status"]=="APPROVED"
