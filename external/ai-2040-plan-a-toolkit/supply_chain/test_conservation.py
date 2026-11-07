from supply_chain.conservation import *
def e(i,k,q):return LotEvent(i,"lot", "owner",k,q,evidence_ref=i)
def test_lot_conservation():
    assert reconcile_lot([e("1","MANUFACTURED",100),e("2","DEPLOYED",60),e("3","TRANSFER_OUT",40)],"lot")["status"]=="PASS"
def test_missing_evidence_is_unknown():
    assert reconcile_lot([LotEvent("1","lot","owner","MANUFACTURED",100,evidence_ref=None),e("2","DEPLOYED",100)],"lot")["status"]=="UNKNOWN"
def test_duplicate_event_fails():
    x=e("1","MANUFACTURED",1)
    assert reconcile_lots([x,x])["status"]=="FAIL"
