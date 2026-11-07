
from physical.custody import *
def test_chain_passes():
    a=CustodyEvent("1","tap","SEAL","op",1,"0"*64,"e"); b=CustodyEvent("2","tap","TRANSFER","op",2,a.digest(),"e")
    assert validate_custody_chain([a,b])["status"]=="PASS"
def test_chain_tamper_fails():
    a=CustodyEvent("1","tap","SEAL","op",1,"f"*64,"e")
    assert validate_custody_chain([a])["status"]=="FAIL"
def test_open_enclosure_fails_closed(): assert tamper_open_response("OPEN")=="FAIL_CLOSED"
