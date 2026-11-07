from passport.revocation import *
def test_revocation():
    assert evaluate_revocation("p",10,[Revocation("p","tamper",5,"e")])["status"]=="REVOKED"
def test_not_yet_effective():
    assert evaluate_revocation("p",4,[Revocation("p","tamper",5,"e")])["status"]=="ACTIVE"
