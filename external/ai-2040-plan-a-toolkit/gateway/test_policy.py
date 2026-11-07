
from gateway.policy import *
P=GatewayPolicy((EnvelopeClass("inference",1,4096,20_000_000),EnvelopeClass("health",32,64,35_000_000)),1000)
def test_whitelist_and_timing():
    assert P.validate("inference",1000,10_000_000)["status"]=="PASS"; assert P.validate("x",10,1)["status"]=="FAIL"
def test_covert_capacity_is_bounded_model():
    assert P.theoretical_capacity_upper_bound(100,.5 and 10)>0
def test_stream_rejects_bad_event():
    assert evaluate_gateway_stream([("inference",10,1),("secret",3,1)],P)["status"]=="FAIL"
