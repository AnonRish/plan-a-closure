
from track3.intel_evidence import *
def test_independent_source_groups_count():
    x=evaluate_intel([
        IntelObservation("a","sat","2026-01-01","site","heat","HIGH","g1"),
        IntelObservation("b","trade","2026-01-02","site","capacity","MEDIUM","g2")
    ])
    assert x["independent_source_groups"]==2
def test_missing_data_is_not_ground_truth(): assert evaluate_intel([])["status"]=="UNKNOWN"
