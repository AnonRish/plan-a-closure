
from deployment.readiness import *
def test_fleet_requires_independent_inspection():
    a=Asset("tap1","tap",InstallState.ACCEPTED,"c","c",False,False)
    assert evaluate_fleet([a],1)["status"]=="UNKNOWN"
def test_accepted_independently_inspected_fleet_passes():
    a=Asset("tap1","tap",InstallState.ACCEPTED,"c","c",False,True)
    assert evaluate_fleet([a],1)["status"]=="PASS"
