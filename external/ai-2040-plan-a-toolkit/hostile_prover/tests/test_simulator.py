
from hostile_prover.simulator import benchmark,simulate_trial
def test_omission_is_structurally_detected(): assert simulate_trial(strategy="omit").detected
def test_substitution_is_detected_by_sample_or_invariant(): assert simulate_trial(strategy="substitute",sample_fraction=1).detected
def test_adaptive_cannot_target_revealed_sample_after_commitment():
    r=benchmark(seed=7,trials=2000)
    assert r["results"]["adaptive"]["detection_rate"]<1.0
    assert r["results"]["adaptive"]["detection_rate"]>.0
