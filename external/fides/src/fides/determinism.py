"""
Deterministic reduction primitives -- a narrow, honest slice of SITREP
item 6 ("Reproducible inference stack", not started). The supplement's own
framing is that non-determinism in ML inference isn't fundamental
(computers are deterministic machines) but creeps in through
optimizations -- most concretely, floating-point addition is not
associative, so a parallel reduction (e.g. summing partial results across
GPU thread blocks) that completes in a different, load-dependent order
produces a different bit pattern each run, even given the exact same
input.

This module doesn't reproduce a real inference stack (no GPU access here)
-- it isolates and fixes the specific, well-documented mechanism a real
one would need to fix: reduction order. `deterministic_sum` always reduces
in a fixed, index-based tree order regardless of runtime scheduling;
`racy_sum` simulates what an unconstrained, schedule-dependent reduction
looks like (same logical job, order varies run to run), so the difference
is demonstrated empirically in test_determinism.py rather than asserted.

Honest limitation, now partially closed: fixing the reduction algorithm
alone is necessary but not sufficient -- if the values feeding the
reduction arrive in a different upstream order across runs (different
batching, different tensor-parallel shard assignment), a fixed-order
reduction still produces different results, because "fixed order" means
fixed relative to input order, not invariant to it. `canonical_reduce`
below closes this by requiring each value to carry a stable identity
(e.g. a token position or shard index) and sorting by that identity
before reducing, so arrival order stops mattering. What remains
unclosed: this only helps when such an identity is actually available
and consistently assigned upstream, which a real distributed training or
inference system would need to guarantee -- this module cannot guarantee
that on its own, since it has no upstream system to integrate with.
"""

import random


def deterministic_sum(values: list) -> float:
    """Fixed-order pairwise tree reduction. Same input list, same output,
    every time -- the combine order depends on list position only, never
    on runtime scheduling."""
    values = list(values)
    while len(values) > 1:
        next_level = []
        for i in range(0, len(values) - 1, 2):
            next_level.append(values[i] + values[i + 1])
        if len(values) % 2 == 1:
            next_level.append(values[-1])
        values = next_level
    return values[0] if values else 0.0


def racy_sum(values: list, seed: int = None) -> float:
    """Simulates a schedule-dependent reduction: the same logical value
    set, summed in a randomly varying order each call -- standing in for
    partial sums completing and being combined in whatever order threads
    happen to finish, which is exactly what an unconstrained parallel
    reduction does across repeated runs."""
    rng = random.Random(seed)
    shuffled = list(values)
    rng.shuffle(shuffled)
    total = 0.0
    for v in shuffled:
        total += v
    return total


def canonical_reduce(tagged_values: list) -> float:
    """Closes the gap the module docstring names above: `tagged_values`
    is a list of (identity_key, value) pairs -- e.g. (token_position,
    partial_sum) or (shard_index, partial_sum) -- that may arrive in any
    order, simulating results completing in a schedule-dependent
    sequence across distributed workers. Sorting by identity_key before
    reducing gives every run the same order regardless of arrival
    timing, and deterministic_sum then guarantees the same reduction
    order on top of that -- both halves of the real requirement
    together, not just the reduction-order half alone."""
    ordered = sorted(tagged_values, key=lambda pair: pair[0])
    return deterministic_sum(value for _, value in ordered)
