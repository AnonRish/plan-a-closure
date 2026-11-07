
from gateway.active_contract import *
from gateway.policy import *
P=GatewayPolicy((EnvelopeClass("inference",1,4096,20_000_000),),1000)
def test_active_contract_blocks_out_of_policy():
    assert enforce_contract("secret",10,1,P).action=="BLOCK"
def test_active_contract_forwards_allowed():
    assert enforce_contract("inference",100,1,P).action=="FORWARD"
