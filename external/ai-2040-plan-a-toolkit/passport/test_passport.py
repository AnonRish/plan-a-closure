from passport.passport import *
def test_valid_passport():
    p=AIPassport("p","s","m","pol","software",1,None,[PassportClaim("c","statement","PASS",1,("e",),"v")],"root")
    assert validate_passport(p,2)["status"]=="PASS"
def test_pass_without_evidence_fails():
    p=AIPassport("p","s","m","pol","software",1,None,[PassportClaim("c","statement","PASS",1,(),"v")])
    assert validate_passport(p,2)["status"]=="FAIL"
