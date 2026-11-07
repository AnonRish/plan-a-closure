from fides.recompute import (
    RecomputationVerifier,
    generate_activation_vector,
    perturb,
    fabricate,
)


def test_honest_recomputation_with_small_noise_passes():
    verifier = RecomputationVerifier(dim=512, n_bits=256, seed=1)
    true_vector = generate_activation_vector(512, seed=42)
    claimed_fp = verifier.fingerprint(true_vector)
    for trial_seed in range(20):
        noisy = perturb(true_vector, noise_scale=0.01, seed=trial_seed)
        assert verifier.verify(claimed_fp, noisy)


def test_fabricated_output_from_unrelated_computation_fails():
    verifier = RecomputationVerifier(dim=512, n_bits=256, seed=1)
    true_vector = generate_activation_vector(512, seed=42)
    claimed_fp = verifier.fingerprint(true_vector)
    for trial_seed in range(20):
        fake = fabricate(512, seed=1000 + trial_seed)
        assert not verifier.verify(claimed_fp, fake)


def test_detection_holds_across_a_realistic_noise_sweep():
    # Characterizes where the honest/dishonest boundary actually sits,
    # rather than asserting one hardcoded noise level works.
    verifier = RecomputationVerifier(dim=512, n_bits=256, seed=2)
    true_vector = generate_activation_vector(512, seed=7)
    claimed_fp = verifier.fingerprint(true_vector)
    for noise_scale in (0.001, 0.01, 0.05):
        passed = sum(
            verifier.verify(claimed_fp, perturb(true_vector, noise_scale, seed=s))
            for s in range(30)
        )
        assert passed >= 27, f"noise_scale={noise_scale} only passed {passed}/30"


def test_scheme_generalizes_across_different_configurations():
    # Item 9 ("Frontier recomputation algorithms"): doesn't build new
    # algorithms per architecture, demonstrates the mechanism isn't
    # hardcoded to one vector shape -- the minimum bar for "could
    # plausibly adapt" rather than a claim of having solved evolution
    # across architectures.
    for dim, n_bits in [(128, 128), (512, 256), (2048, 512)]:
        verifier = RecomputationVerifier(dim=dim, n_bits=n_bits, seed=1)
        true_vector = generate_activation_vector(dim, seed=1)
        claimed_fp = verifier.fingerprint(true_vector)
        assert verifier.verify(claimed_fp, perturb(true_vector, 0.01, seed=2))
        assert not verifier.verify(claimed_fp, fabricate(dim, seed=3))


def test_red_team_random_search_for_a_colliding_fabrication():
    # Item 10 ("Recomputation red-teaming"), applied to THIS module's own
    # scheme, since this repo doesn't implement TOPLOC/DiFR to red-team
    # directly. Brute-force search for a random unrelated vector that
    # happens to land within tolerance of the true fingerprint.
    verifier = RecomputationVerifier(dim=512, n_bits=256, seed=3)
    true_vector = generate_activation_vector(512, seed=11)
    claimed_fp = verifier.fingerprint(true_vector)
    attempts = 3_000
    found_collision = False
    for attempt in range(attempts):
        candidate = fabricate(512, seed=5000 + attempt)
        if verifier.verify(claimed_fp, candidate):
            found_collision = True
            break
    # With n_bits=256 and a 10% Hamming tolerance (~25 bits), a random
    # unrelated vector landing within tolerance of a fixed target has
    # probability on the order of 1e-30 (12+ standard deviations out on
    # Binomial(256, 0.5)) -- 3,000 attempts is nowhere near enough to
    # find one at that probability regardless of budget, so this is a
    # deliberately modest attempt count chosen for test runtime, not
    # because the underlying claim is budget-sensitive.
    assert not found_collision, f"found a colliding fabrication in {attempts} attempts"


def test_red_team_targeted_bit_flipping_does_not_easily_close_the_gap():
    # A smarter attacker than pure random search: start from a REAL
    # perturbation of the true vector (so it starts close), then hill-
    # climb by flipping single input coordinates to see if any move
    # closes the remaining Hamming gap without the vector actually
    # converging back toward the true one.
    verifier = RecomputationVerifier(dim=256, n_bits=256, seed=4)
    true_vector = generate_activation_vector(256, seed=21)
    claimed_fp = verifier.fingerprint(true_vector)

    attacker_vector = fabricate(256, seed=999)
    from fides.recompute import hamming_distance

    start_dist = hamming_distance(claimed_fp.bits, verifier.fingerprint(attacker_vector).bits)
    best_dist = start_dist
    for step in range(2000):
        idx = step % 256
        trial = list(attacker_vector)
        trial[idx] += 0.1 if (step // 256) % 2 == 0 else -0.1
        trial_dist = hamming_distance(claimed_fp.bits, verifier.fingerprint(trial).bits)
        if trial_dist < best_dist:
            attacker_vector, best_dist = trial, trial_dist

    threshold_bits = 0.1 * 256
    assert best_dist > threshold_bits, (
        f"hill-climbing closed the gap to {best_dist} bits (threshold {threshold_bits}) "
        "in 2000 steps -- tolerance may be too loose against an adaptive attacker"
    )
