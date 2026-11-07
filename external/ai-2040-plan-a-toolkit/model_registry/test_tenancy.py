from model_registry.tenancy import *
def test_model_lease_binds_identity_and_cluster():
    m=ModelIdentity("m","w","a","t","p","1"); l=TenantLease("tenant","cluster",m.fingerprint(),1,5)
    assert validate_lease(l,m,3,"cluster")["status"]=="PASS"
def test_stale_lease_fails():
    m=ModelIdentity("m","w","a","t","p","1"); l=TenantLease("tenant","cluster",m.fingerprint(),1,5)
    assert validate_lease(l,m,6,"cluster")["status"]=="FAIL"
