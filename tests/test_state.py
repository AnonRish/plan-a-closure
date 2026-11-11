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


def test_one_parked_block_is_caught_by_the_slowest_block_and_lost_in_the_total():
    """Kaggle run 5: a challenge of 17 blocks that touched a single parked block took 14 ms longer than a 54 ms total
    with 5 ms of jitter, and five such challenges in 200 slipped under the total-time threshold. Timing each block and
    judging the challenge by its slowest one sets that block against one block's time instead."""
    bb = 1 << 16
    tier = S.TierModel(bw_slow=bb / 150e-6, lat_s=20e-6, jitter_s=15e-6)   # a parked block costs 150 us more: ten
    # times one block's jitter, but only two and a half times the jitter of a 16-block total
    v = S.Verifier(n_blocks=32, block_bytes=bb)
    honest = S.Prover(tier, block_bytes=bb, seed=1)
    S.fill(v, honest)
    cal = [S.run_challenge(v, honest, 16, 1e9, block_thr=1e9, check_digest=False) for _ in range(1000)]
    assert all(r["digest_ok"] is None and r["passed"] for r in cal)        # timing only: no digest recomputed
    thr_block = S.calibrate_time_threshold([r["slowest_block_s"] for r in cal], 0.002)   # the largest of the 1,000
    thr_total = S.calibrate_time_threshold([r["elapsed_s"] for r in cal], 0.002)
    one = S.SlowTierProver(0.0, tier=tier, block_bytes=bb, seed=2)
    S.fill(v, one)
    one.slow.add(5)                                                         # exactly one parked block
    hits = [r for r in (S.run_challenge(v, one, 16, thr_total, block_thr=thr_block) for _ in range(600)) if 5 in r["idx"]]
    assert len(hits) > 200 and all(r["digest_ok"] for r in hits)
    by_block = np.mean([not r["time_ok"] for r in hits])
    by_total = np.mean([r["elapsed_s"] > thr_total for r in hits])
    assert by_block >= 0.99 and by_total < 0.9
    again = [S.run_challenge(v, honest, 16, thr_total, block_thr=thr_block, check_digest=False) for _ in range(1000)]
    assert np.mean([not r["passed"] for r in again]) <= 0.01               # H2.1: honest false alarm over 1,000


def test_timed_challenges_are_judged_and_verified_afterwards():
    """`closure hw-state` times its challenges back to back and recomputes digests later: a timed challenge carries
    what the verifier needs for that, and a wrong digest is still caught."""
    v = S.Verifier(n_blocks=16, block_bytes=1 << 16)
    p = S.Prover(block_bytes=1 << 16, seed=3)
    S.fill(v, p)
    r = S.timed_challenge(v, p, 8)
    assert len(r["idx"]) == 8 and r["elapsed_s"] >= r["slowest_block_s"] > 0 and S.digest_matches(v, r)
    assert not S.digest_matches(v, {**r, "digest": r["digest"] ^ 1})
    d = S.DropProver(1.0, block_bytes=1 << 16, seed=4)                      # stores zeros instead of the stream
    S.fill(v, d)
    assert not S.digest_matches(v, S.timed_challenge(v, d, 8))
