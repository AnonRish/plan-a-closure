
from frontier_verify.recomputation.metrics import measure,sampled_work
def test_measurement_records_positive_or_zero_elapsed():
    x=measure(lambda: 3)
    assert x.value==3 and x.elapsed_ns>=0
def test_sampled_work_accounting():
    assert sampled_work(100,10)["coverage_fraction"]==.1
