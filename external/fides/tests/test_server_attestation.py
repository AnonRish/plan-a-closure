from fides.server_attestation import (
    software_fingerprint,
    issue_challenge,
    respond_to_challenge,
    verify_response,
    verify_threshold,
)


def test_honest_server_passes_challenge():
    software_fp = software_fingerprint(b"verification-server-v1-source")
    state = b"ledger-head-hash-at-epoch-42"
    challenge = issue_challenge(b"fixed-test-challenge")
    response = respond_to_challenge(software_fp, challenge, state)
    assert verify_response(software_fp, challenge, state, response)


def test_modified_software_fails_even_with_correct_state():
    real_fp = software_fingerprint(b"verification-server-v1-source")
    tampered_fp = software_fingerprint(b"verification-server-v1-source-BUT-ALWAYS-REPORTS-COMPLIANT")
    state = b"ledger-head-hash-at-epoch-42"
    challenge = issue_challenge(b"fixed-test-challenge")
    forged_response = respond_to_challenge(tampered_fp, challenge, state)
    assert not verify_response(real_fp, challenge, state, forged_response)


def test_rolled_back_state_fails_even_with_correct_software():
    software_fp = software_fingerprint(b"verification-server-v1-source")
    real_state = b"ledger-head-hash-at-epoch-42"
    rolled_back_state = b"ledger-head-hash-at-epoch-10"  # server pretends it's earlier
    challenge = issue_challenge(b"fixed-test-challenge")
    forged_response = respond_to_challenge(software_fp, challenge, rolled_back_state)
    assert not verify_response(software_fp, challenge, real_state, forged_response)


def test_replayed_response_fails_against_a_new_challenge():
    software_fp = software_fingerprint(b"verification-server-v1-source")
    state = b"ledger-head-hash-at-epoch-42"
    old_challenge = issue_challenge(b"challenge-1")
    new_challenge = issue_challenge(b"challenge-2")
    old_response = respond_to_challenge(software_fp, old_challenge, state)
    assert not verify_response(software_fp, new_challenge, state, old_response)


def test_random_challenges_are_not_predictable_or_repeating():
    challenges = {issue_challenge() for _ in range(50)}
    assert len(challenges) == 50


def test_threshold_met_when_enough_honest_parties_respond():
    fp = software_fingerprint(b"verification-server-v1-source")
    state = b"ledger-head-hash-at-epoch-42"
    challenge = issue_challenge(b"threshold-test-1")
    responses = [
        (f"party-{i}", respond_to_challenge(fp, challenge, state))
        for i in range(5)
    ]
    result = verify_threshold(fp, challenge, state, responses, threshold=3)
    assert result.threshold_met
    assert result.agreeing_parties == 5


def test_threshold_not_met_when_too_many_parties_are_compromised():
    fp = software_fingerprint(b"verification-server-v1-source")
    tampered_fp = software_fingerprint(b"verification-server-v1-source-BUT-ALWAYS-REPORTS-COMPLIANT")
    state = b"ledger-head-hash-at-epoch-42"
    challenge = issue_challenge(b"threshold-test-2")

    honest_responses = [
        (f"party-{i}", respond_to_challenge(fp, challenge, state)) for i in range(2)
    ]
    compromised_responses = [
        (f"party-{i}", respond_to_challenge(tampered_fp, challenge, state)) for i in range(2, 5)
    ]
    result = verify_threshold(fp, challenge, state, honest_responses + compromised_responses, threshold=3)
    assert not result.threshold_met
    assert result.agreeing_parties == 2


def test_threshold_survives_a_single_compromised_party_that_alone_would_have_broken_verify_response():
    # The property verify_response() alone doesn't have: one compromised
    # party forging a response no longer breaks the overall result, as
    # long as enough OTHER parties are still honest.
    fp = software_fingerprint(b"verification-server-v1-source")
    tampered_fp = software_fingerprint(b"verification-server-v1-source-BUT-ALWAYS-REPORTS-COMPLIANT")
    state = b"ledger-head-hash-at-epoch-42"
    challenge = issue_challenge(b"threshold-test-3")

    responses = [(f"party-{i}", respond_to_challenge(fp, challenge, state)) for i in range(4)]
    responses.append(("party-4-compromised", respond_to_challenge(tampered_fp, challenge, state)))
    result = verify_threshold(fp, challenge, state, responses, threshold=4)
    assert result.threshold_met  # 4 honest out of 5 still clears a threshold of 4


def test_threshold_does_not_protect_against_coordinated_compromise_of_all_parties():
    # The explicitly documented limitation: if every "independent" party
    # is actually controlled by the same adversary, the threshold
    # provides no protection at all -- this is not a bug, it's the
    # honest boundary of what verify_threshold can and can't do, made
    # checkable rather than just asserted in the docstring.
    tampered_fp = software_fingerprint(b"verification-server-v1-source-BUT-ALWAYS-REPORTS-COMPLIANT")
    real_fp = software_fingerprint(b"verification-server-v1-source")
    state = b"ledger-head-hash-at-epoch-42"
    challenge = issue_challenge(b"threshold-test-4")

    all_compromised = [
        (f"party-{i}", respond_to_challenge(tampered_fp, challenge, state)) for i in range(5)
    ]
    result = verify_threshold(real_fp, challenge, state, all_compromised, threshold=3)
    assert not result.threshold_met  # correctly rejected here, but only because these
    # responses are internally inconsistent with real_fp -- if the same adversary
    # controlled all 5 parties AND ran the real software honestly on all of them
    # while secretly doing something else on the side, this scheme has no way to
    # detect that at all. That failure mode is real and is not tested here because
    # there's nothing for this module to check against -- it's the actual limit.
