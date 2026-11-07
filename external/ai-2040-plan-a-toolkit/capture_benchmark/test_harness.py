from capture_benchmark.harness import BenchmarkConfig,build_fixture,line_rate_projection,run

def test_projection_is_not_hardware_claim():
    p=line_rate_projection(64,400); assert p['measured'] is False; assert p['theoretical_frames_per_second']>0

def test_fixture_contains_both_classes():
    _,cases=build_fixture(BenchmarkConfig(frame_count=100,attack_fraction=.2)); assert any(x.compliant for x in cases); assert any(not x.compliant for x in cases)

def test_run_counts_frames(tmp_path):
    r=run(BenchmarkConfig(frame_count=200,attack_fraction=.1),output_dir=str(tmp_path)); assert r['expected_frames']==200; assert r['observed_frames']==200; assert r['observed_drop_rate']==0
