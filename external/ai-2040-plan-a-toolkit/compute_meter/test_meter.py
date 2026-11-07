from compute_meter.meter import *
def s(v,t=1,r=0): return CounterSnapshot("d","H100","flops",v,"counter",t,r,"nvml","a")
def test_counter_delta():
    assert compare_snapshots(s(10),s(15))["delta"]==5
def test_reset_is_unknown():
    assert compare_snapshots(s(10,r=0),s(2,r=1))["status"]=="UNKNOWN"
def test_negative_counter_fails():
    assert normalize_flops(CounterSnapshot("d","H100","flops",-1,"counter",1,0,"x"),FLOPModel("H100",1,"counter","1"))["status"]=="FAIL"
def test_digest_is_stable():
    a=s(1);b=s(2)
    assert meter_digest([a,b])==meter_digest([a,b])
