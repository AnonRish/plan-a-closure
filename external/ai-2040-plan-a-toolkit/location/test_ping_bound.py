from location.ping_bound import *
def test_pass():
    assert evaluate_location(PingObservation(.001,.0002,"v","e"),150000)["status"]=="PASS"
def test_fail():
    assert evaluate_location(PingObservation(.001,0,"v","e"),100000)["status"]=="FAIL"
