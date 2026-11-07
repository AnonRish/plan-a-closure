
import json
from pathlib import Path

def test_every_workstream_has_acceptance_criterion():
    matrix=json.loads(Path("verification_lab/acceptance_matrix.json").read_text())
    assert [x["id"] for x in matrix["workstreams"]]==list(range(1,18))
    assert all(x.get("bench_target") or x.get("bench_target_gbps") for x in matrix["workstreams"])
