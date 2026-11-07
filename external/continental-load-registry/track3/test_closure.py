
from track3.closure import evaluate_closure

def test_open_population_cannot_close():
    c={"population_id":"p","frozen_at":"t","scope":"x","threshold_units":100,"population_complete":False,"sampling_frame_digest":"a"*64,"authoritative_sources":["s"]}
    assert evaluate_closure(c)["status"]=="UNKNOWN"

def test_closed_declared_scope_is_explicit():
    c={"population_id":"p","frozen_at":"t","scope":"x","threshold_units":100,"population_complete":True,"sampling_frame_digest":"a"*64,"authoritative_sources":["s"]}
    assert evaluate_closure(c)["status"]=="CLOSED_FOR_DECLARED_SCOPE"
