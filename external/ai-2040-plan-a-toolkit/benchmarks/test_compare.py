
from benchmarks.compare import compare
def test_external_baseline_is_not_relabelled():
    x=compare({"source":"external","measurements":{"a":1}},{"a":2})
    assert x["published_source"]=="external"
