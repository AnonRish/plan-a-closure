from identity.delegation import *
def mk(a,b,s,n):
    d=Delegation(a,b,s,n,""); return Delegation(a,b,s,n,expected_signature_digest(d))
def test_chain():
    assert validate_chain([mk("human","org","p","1"),mk("org","agent","p","2")],"agent")["status"]=="PASS"
def test_bad_sig():
    assert validate_chain([Delegation("human","agent","p","1","bad")],"agent")["status"]=="FAIL"
