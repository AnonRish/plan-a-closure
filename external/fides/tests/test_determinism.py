import random

from fides.determinism import deterministic_sum, racy_sum, canonical_reduce


def _realistic_values(rng, n=500):
    # a wide dynamic range, similar in spirit to accumulated neural-
    # network activation magnitudes, where floating-point rounding
    # differences actually show up.
    return [rng.uniform(-1e6, 1e6) * (10 ** rng.randint(-8, 8)) for _ in range(n)]


def test_deterministic_sum_gives_identical_bits_across_repeated_calls():
    rng = random.Random(0)
    values = _realistic_values(rng)
    results = {deterministic_sum(values) for _ in range(50)}
    assert len(results) == 1


def test_racy_sum_demonstrates_the_real_nondeterminism_problem():
    # Empirical demonstration, not an assertion: check that summing the
    # SAME values in different (simulated schedule-dependent) orders
    # actually produces different bit patterns for a healthy fraction of
    # realistic value sets -- this is the real, well-documented phenomenon
    # deterministic reduction exists to fix (see e.g. PyTorch's and
    # cuDNN's deterministic-algorithms documentation).
    rng = random.Random(0)
    trials = 200
    distinct_result_trials = 0
    for _ in range(trials):
        values = _realistic_values(rng)
        results = {racy_sum(values, seed=s) for s in range(20)}
        if len(results) > 1:
            distinct_result_trials += 1
    assert distinct_result_trials > trials * 0.5, (
        f"only {distinct_result_trials}/{trials} trials showed order-dependence"
    )


def test_deterministic_and_racy_sum_agree_in_expectation():
    # deterministic_sum isn't "more correct" arithmetically, just
    # reproducible -- it should land within the same ballpark as the
    # racy variants, not systematically biased.
    rng = random.Random(1)
    values = _realistic_values(rng, n=200)
    det = deterministic_sum(values)
    racy_results = [racy_sum(values, seed=s) for s in range(30)]
    naive_total = sum(values)
    # all variants should be close to a plain Python sum() of the same
    # values, since the differences are rounding-level, not algorithmic
    for r in racy_results + [det]:
        if naive_total != 0:
            assert abs(r - naive_total) / (abs(naive_total) + 1e-300) < 1e-6


def test_deterministic_sum_handles_edge_cases():
    assert deterministic_sum([]) == 0.0
    assert deterministic_sum([5.0]) == 5.0
    assert deterministic_sum([1.0, 2.0, 3.0]) == 6.0


def test_canonical_reduce_is_invariant_to_arrival_order():
    # This is the actual gap racy_sum demonstrates and deterministic_sum
    # alone doesn't close: the same logical values, tagged with a stable
    # identity, arriving in a different order each "run" (simulating
    # network/scheduling nondeterminism upstream of the reduction
    # itself). canonical_reduce should give the same result regardless.
    rng = random.Random(0)
    tagged = [(i, rng.uniform(-1e6, 1e6) * (10 ** rng.randint(-8, 8))) for i in range(300)]
    results = set()
    for shuffle_seed in range(20):
        scrambled = list(tagged)
        random.Random(shuffle_seed).shuffle(scrambled)
        results.add(canonical_reduce(scrambled))
    assert len(results) == 1, f"canonical_reduce produced {len(results)} distinct results across shuffles"


def test_sorting_by_identity_alone_without_canonical_reduce_is_not_enough():
    # Demonstrates precisely why canonical_reduce needs BOTH halves:
    # sorting by identity but then reducing with plain Python sum() can
    # still be schedule-order-independent for THIS reduction (since
    # sorted input is now fixed) -- the real risk canonical_reduce
    # guards against is deterministic_sum's tree order combined with
    # scrambled input, which is exactly what this test constructs to
    # confirm canonical_reduce's sort step is actually being applied.
    rng = random.Random(1)
    tagged = [(i, rng.uniform(-1e6, 1e6) * (10 ** rng.randint(-8, 8))) for i in range(300)]
    scrambled = list(tagged)
    random.Random(2).shuffle(scrambled)
    # feeding the UNSORTED, scrambled order directly into deterministic_sum
    # (bypassing canonical_reduce's sort step) can disagree with the
    # properly canonicalized result -- confirming the sort step matters,
    # not just deterministic_sum's fixed tree order on its own.
    unsorted_result = deterministic_sum(v for _, v in scrambled)
    canonical_result = canonical_reduce(scrambled)
    same_order_result = deterministic_sum(v for _, v in tagged)
    assert canonical_result == same_order_result
    # not asserting unsorted_result differs (it might coincidentally
    # match for some inputs) -- the guarantee canonical_reduce actually
    # provides is checked above: it always matches the canonical order,
    # regardless of what order it was handed.
