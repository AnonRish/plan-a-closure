
from company_audit.ledger import *
def ev(i,o,k,u): return AssetEvent(i,"a",o,k,u,evidence_digest=i)
def test_owner_reconciliation():
    x=reconcile_owner([ev("1","o","ACQUIRE",10),ev("2","o","HOLD",6),ev("3","o","TRANSFER_OUT",4)],"o")
    assert x["status"]=="PASS"
def test_missing_evidence_is_unknown():
    x=reconcile_owner([AssetEvent("1","a","o","ACQUIRE",10),ev("2","o","HOLD",10)],"o")
    assert x["status"]=="UNKNOWN"
def test_population_duplicate_fails():
    e=ev("1","o","ACQUIRE",1)
    assert reconcile_population([e,e])["status"]=="FAIL"
