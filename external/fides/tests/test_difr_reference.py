import math

from fides.difr_reference import (
    seeded_exponentials,
    gumbel_max_sample,
    gumbel_max_rank,
    verify_token,
    verify_sequence,
    match_rate,
    synthetic_distribution,
    quantize_distribution,
)


def test_gumbel_max_sample_is_deterministic():
    probs = synthetic_distribution(vocab_size=100, seed=1)
    a = gumbel_max_sample(probs, seed=42, position=0)
    b = gumbel_max_sample(probs, seed=42, position=0)
    assert a == b


def test_gumbel_max_reformulation_matches_textbook_gumbel_form():
    # argmax(probs / E) should always equal argmax(log(probs) - log(E)),
    # i.e. argmax(logits + gumbel) where gumbel = -log(E) -- check the
    # equivalence empirically rather than trusting the algebra.
    for trial in range(50):
        probs = synthetic_distribution(vocab_size=64, seed=trial)
        exponentials = seeded_exponentials(seed=trial, position=0, vocab_size=64)
        reformulated = max(range(64), key=lambda i: probs[i] / exponentials[i])
        textbook = max(range(64), key=lambda i: math.log(probs[i]) - math.log(exponentials[i]))
        assert reformulated == textbook


def test_gumbel_max_rank_is_zero_for_the_sampled_token():
    probs = synthetic_distribution(vocab_size=200, seed=2)
    sampled = gumbel_max_sample(probs, seed=7, position=3)
    assert gumbel_max_rank(probs, seed=7, position=3, token_id=sampled) == 0


def test_honest_reproduction_matches_exactly():
    # Same distributions, same seed -> the reference's own re-derivation
    # must reproduce exactly what was "claimed", every position, every
    # trial -- this is a deterministic guarantee, not a high-probability
    # one, since there's no perturbation at all in this case.
    for trial in range(10):
        vocab_size = 300
        seed = 100 + trial
        distributions = [synthetic_distribution(vocab_size, seed=seed + p) for p in range(50)]
        claimed = [gumbel_max_sample(d, seed=seed, position=p) for p, d in enumerate(distributions)]
        results = verify_sequence(claimed, distributions, seed=seed)
        assert match_rate(results) == 1.0


def test_tampered_distribution_shows_measurable_divergence():
    vocab_size = 300
    seed = 5
    distributions = [synthetic_distribution(vocab_size, seed=seed + p) for p in range(200)]
    claimed = [gumbel_max_sample(d, seed=seed, position=p) for p, d in enumerate(distributions)]

    # "provider" is actually running a meaningfully different model --
    # verify against distributions that have been substantially perturbed
    tampered = [quantize_distribution(d, noise_scale=2.0, seed=900 + p) for p, d in enumerate(distributions)]
    results = verify_sequence(claimed, tampered, seed=seed)
    assert match_rate(results) < 0.9


def test_divergence_rate_increases_with_perturbation_magnitude():
    # Mirrors the real paper's finding that stronger corruption (e.g.
    # 4-bit vs 8-bit quantization) is detectable with fewer tokens --
    # characterized empirically here, not asserted.
    vocab_size = 300
    seed = 11
    distributions = [synthetic_distribution(vocab_size, seed=seed + p) for p in range(150)]
    claimed = [gumbel_max_sample(d, seed=seed, position=p) for p, d in enumerate(distributions)]

    rates = {}
    for noise_scale in (0.0, 0.5, 1.5, 4.0):
        perturbed = [quantize_distribution(d, noise_scale=noise_scale, seed=500 + p) for p, d in enumerate(distributions)]
        results = verify_sequence(claimed, perturbed, seed=seed)
        rates[noise_scale] = match_rate(results)

    assert rates[0.0] == 1.0  # no perturbation at all -> exact reproduction
    ordered = sorted(rates)
    for a, b in zip(ordered, ordered[1:]):
        assert rates[b] <= rates[a] + 0.05, rates  # allow small noise slack, expect a downward trend
    assert rates[4.0] < rates[0.5]


def test_verify_token_reports_claimed_probability_and_rank():
    probs = synthetic_distribution(vocab_size=50, seed=3)
    sampled = gumbel_max_sample(probs, seed=1, position=0)
    result = verify_token(sampled, probs, seed=1, position=0)
    assert result["exact_match"] is True
    assert result["gumbel_rank"] == 0
    assert result["claimed_prob"] == probs[sampled]


def test_matching_only_the_mode_does_not_evade_detection():
    # Red-teaming angle (item 10's spirit applied to DiFR): a distribution
    # that shares the reference's single most-likely token but is
    # otherwise a different shape should still show detectable
    # divergence -- Gumbel-max verification is sensitive to the whole
    # distribution's relative ordering, not just which token is most
    # likely, since noise-driven near-ties depend on everything else too.
    vocab_size = 100
    seed = 21
    references = [synthetic_distribution(vocab_size, seed=seed + p) for p in range(150)]
    claimed = [gumbel_max_sample(d, seed=seed, position=p) for p, d in enumerate(references)]

    mode_matched_only = []
    for p, ref in enumerate(references):
        top_token = max(range(vocab_size), key=lambda i: ref[i])
        alt = synthetic_distribution(vocab_size, seed=9000 + p)
        alt_top = max(range(vocab_size), key=lambda i: alt[i])
        alt[top_token], alt[alt_top] = alt[alt_top], alt[top_token]  # force matching modes
        total = sum(alt)
        mode_matched_only.append([v / total for v in alt])

    results = verify_sequence(claimed, mode_matched_only, seed=seed)
    assert match_rate(results) < 0.9, "sharing just the mode should not be sufficient to evade detection"
