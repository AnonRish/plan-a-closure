
from track3.tail_audit import *

def accounts_ok():
    return {
        "A":Account("A",10,{"B":5},0,5),
        "B":Account("B",5,{},0,5),
    }

def test_sample_is_reproducible():
    units=[TailUnit(str(i),"A") for i in range(10)]
    assert [x.unit_id for x in sample_units(units,4,123)]==[x.unit_id for x in sample_units(units,4,123)]

def test_balanced_tail_can_pass():
    units=[TailUnit(str(i),"A") for i in range(10)]
    transfers=[Transfer("t1","A","B",5)]
    out=run_tail_audit(units,accounts_ok(),transfers,4,1)
    assert out["failures"]==0
    assert out["upper_failure_fraction"]<0.75

def test_unreconciled_account_fails():
    units=[TailUnit("u","A")]
    bad={"A":Account("A",10,{},0,5)}
    out=run_tail_audit(units,bad,[],1,1)
    assert out["failures"]==1
    assert out["traces"][0]["outcome"]=="FAIL"

def test_missing_owner_fails_closed():
    units=[TailUnit("u","MISSING")]
    out=run_tail_audit(units,{},[],1,5)
    assert out["traces"][0]["outcome"]=="FAIL"
