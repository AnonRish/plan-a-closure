import numpy as np

from closure import state as S


def _calibrated(v, tier, n=300, k=16):
    p = S.Prover(tier, seed=1)
    S.fill(v, p)
    times = [S.run_challenge(v, p, k, 1e9)["elapsed_s"] for _ in range(n)]
    return S.calibrate_time_threshold(times, 0.001)


def test_torch_path_arithmetic_equals_reference():
    v = S.Verifier(n_blocks=4)
    K = v.digest_key(b"k" * 16)
    for i in range(4):
        b = v.block(i)
        assert S.digest(b, K) == S.digest_int32_path(b, K)


def test_stream_is_random_access_and_verifier_needs_no_storage():
    v = S.Verifier(n_blocks=8)
    assert v.block(3) == v.block(3) and v.block(3) != v.block(4)
    assert len(set(v.block(i)[:64] for i in range(8))) == 8


def test_honest_prover_passes():
    v, tier = S.Verifier(n_blocks=32), S.TierModel(bw_slow=2e9)
    thr = _calibrated(v, tier)
    p = S.Prover(tier, seed=2)
    S.fill(v, p)
    assert np.mean([S.run_challenge(v, p, 16, thr)["passed"] for _ in range(300)]) >= 0.99


def test_dropping_stream_blocks_is_caught_at_the_binomial_rate():
    v, tier = S.Verifier(n_blocks=64), S.TierModel(bw_slow=2e9)
    thr = _calibrated(v, tier)
    caught = []
    for seed in range(60):
        d = S.DropProver(0.10, tier=tier, seed=seed)
        S.fill(v, d)
        caught.append(not S.run_challenge(v, d, 16, thr)["digest_ok"])
    expected = S.p_detect_digest(0.10, 16)
    assert abs(np.mean(caught) - expected) < 0.15        # ~0.81
    d = S.DropProver(0.30, tier=tier, seed=1)
    S.fill(v, d)
    assert not S.run_challenge(v, d, 64, thr)["digest_ok"]


def test_parking_state_in_a_slow_tier_is_caught_by_time_not_digest():
    v, tier = S.Verifier(n_blocks=64), S.TierModel(bw_slow=2e9)
    thr = _calibrated(v, tier)
    sl = S.SlowTierProver(0.3, tier=tier, seed=3)
    S.fill(v, sl)
    res = [S.run_challenge(v, sl, 16, thr) for _ in range(100)]
    assert all(r["digest_ok"] for r in res)               # answers are *correct*...
    assert np.mean([not r["time_ok"] for r in res]) >= 0.95   # ...but too slow


def test_prover_without_the_stream_cannot_answer():
    v = S.Verifier(n_blocks=16)
    empty = S.Prover(seed=4)                              # never received the stream
    assert not S.run_challenge(v, empty, 8, 1e9)["digest_ok"]
    other = S.Verifier(n_blocks=16)                       # regenerating from a *different* key fails too
    p = S.Prover(seed=5)
    S.fill(other, p)
    assert not S.run_challenge(v, p, 8, 1e9)["digest_ok"]
