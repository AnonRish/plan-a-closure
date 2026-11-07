from benchmarks.scorecard import Metric, make_scorecard

def test_scorecard_is_machine_readable():
    x = make_scorecard([Metric("capture_loss", None, "%", "must be measured")])
    assert x["schema_version"] == 1
    assert x["metrics"][0]["value"] is None
