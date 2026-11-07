from benchmarks.benchmark import run
def test_deterministic_digest(): a=run(1,2);b=run(1,2);assert a["digest"]==b["digest"]
