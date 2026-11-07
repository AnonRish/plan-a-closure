
from compute_accounting.interval_ledger import *
def test_open_population_stays_unknown():
    r=reconcile_flows([Flow("a","factory","site","H100",Interval(90,100))],{"factory":Interval(100,100)},False)
    assert r["status"]=="UNKNOWN"
def test_closed_population_gets_conservative_bound():
    r=reconcile_flows([Flow("a","factory","site","H100",Interval(90,100))],{"factory":Interval(100,100)},True)
    assert r["status"]=="PASS"; assert r["residual_upper_bound"]==10
def test_duplicate_evidence_fails():
    f=Flow("x","a","b","H100",Interval(1,1)); assert reconcile_flows([f,f],{"a":Interval(2,2)},True)["status"]=="FAIL"
