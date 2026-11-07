from workload_execution.trace import *
def test_trace_passes():
    t=ExecutionTrace("m",(ExecutionEvent(0,"INFERENCE",{"gpu_hours":1},{"model":"m"}),),"PASS")
    assert validate_trace(t,frozenset({"INFERENCE"}),{"gpu_hours":2},{"model":"m"})["status"]=="PASS"
def test_trace_rejects_banned_operation():
    t=ExecutionTrace("m",(ExecutionEvent(0,"TRAINING",{},{}),),"PASS")
    assert validate_trace(t,frozenset({"INFERENCE"}),{}, {})["status"]=="FAIL"
