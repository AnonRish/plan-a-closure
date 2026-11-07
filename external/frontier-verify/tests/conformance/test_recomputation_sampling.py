"""The central adversarial claim this workstream makes: commit-reveal
sampling is NOT predictable by a prover in advance, while naive
hash-of-chunk-id sampling IS. This test suite makes that claim falsifiable
rather than asserted in prose. See docs/research/recomputation.md.
"""
from __future__ import annotations

import hashlib

import pytest

from frontier_verify.recomputation.chunk import WorkloadChunk
from frontier_verify.recomputation.experiment import run_recomputation
from frontier_verify.recomputation.sampler import (
    CommitmentMismatch,
    commit_challenge,
    naive_predictable_sample,
    select_sample,
)
from frontier_verify.storage.content_addressed import ContentAddressedStore


def _toy_chunk_ids(n: int) -> list[str]:
    return [f"chunk-{i}" for i in range(n)]


def test_naive_sampler_is_perfectly_predictable_by_a_prover():
    """A 'prover' with no access to any verifier secret can compute the
    EXACT same sample a naive sampler would choose, purely from the chunk
    ids it itself picked. This is the failure mode the brief's adversarial
    question ('can a dishonest prover predict which computation will be
    sampled?') is about, made concrete rather than left abstract."""
    chunk_ids = _toy_chunk_ids(200)

    # What the verifier's naive sampler would pick:
    verifier_side_selection = naive_predictable_sample(chunk_ids, sample_rate=0.1)

    # What a prover -- with ZERO access to any verifier secret, only the
    # chunk ids it itself generated -- can independently compute:
    prover_side_prediction = [
        cid
        for cid in chunk_ids
        if int.from_bytes(hashlib.sha256(cid.encode()).digest(), "big") < int(0.1 * (2**256))
    ]

    assert prover_side_prediction == verifier_side_selection
    assert len(verifier_side_selection) > 0  # sanity: the test actually exercises something


def test_commit_reveal_sample_is_not_predictable_before_the_seed_is_revealed():
    """The same 'prover' strategy -- guessing the sample using only public
    information (the chunk ids) -- must NOT be able to predict a
    commit-reveal sample before the seed is revealed, because the
    selection depends on a value the prover never had access to."""
    chunk_ids = _toy_chunk_ids(200)
    challenge = commit_challenge()

    real_selection = select_sample(chunk_ids, challenge.secret_seed, challenge.commitment_hex, 0.1)

    # A prover trying every strategy that uses ONLY chunk_id (no access to
    # challenge.secret_seed, which is exactly what "before reveal" means)
    # cannot reproduce this -- demonstrated here by confirming the naive
    # guess and the real, seed-dependent selection disagree.
    naive_guess = naive_predictable_sample(chunk_ids, sample_rate=0.1)
    assert naive_guess != real_selection


def test_commit_reveal_selection_is_deterministic_given_the_real_seed():
    """Not random noise -- reproducible by anyone who legitimately has the
    revealed seed (an auditor re-checking the verifier's work), which is
    exactly what makes it auditable rather than just secret."""
    chunk_ids = _toy_chunk_ids(50)
    challenge = commit_challenge()
    a = select_sample(chunk_ids, challenge.secret_seed, challenge.commitment_hex, 0.2)
    b = select_sample(chunk_ids, challenge.secret_seed, challenge.commitment_hex, 0.2)
    assert a == b


def test_different_challenges_produce_different_samples():
    chunk_ids = _toy_chunk_ids(50)
    c1, c2 = commit_challenge(), commit_challenge()
    s1 = select_sample(chunk_ids, c1.secret_seed, c1.commitment_hex, 0.3)
    s2 = select_sample(chunk_ids, c2.secret_seed, c2.commitment_hex, 0.3)
    assert s1 != s2  # overwhelmingly likely with independent 256-bit seeds


def test_forged_seed_that_does_not_match_commitment_is_rejected():
    """A verifier (or a compromised one, see docs/adversarial-results.md
    attack #9) cannot reveal a DIFFERENT seed than the one it committed
    to, after conveniently learning which chunks it would prefer to
    check or avoid checking."""
    chunk_ids = _toy_chunk_ids(20)
    challenge = commit_challenge()
    forged_seed = b"\x00" * 32
    with pytest.raises(CommitmentMismatch):
        select_sample(chunk_ids, forged_seed, challenge.commitment_hex, 0.5)


def test_recomputation_catches_a_fabricated_chunk_when_sampled(tmp_path):
    """The comparison logic itself: an honestly-computed chunk matches; a
    fabricated one is caught IF it happens to be sampled. This test forces
    the fabricated chunk into the sample to isolate the comparison logic
    from the sampling logic (already tested above on its own).

    Phase 3 fix: recompute_fn now receives the RETRIEVED input content
    (via ContentAddressedStore), not a bare hash it couldn't do anything
    real with -- see experiment.py's module docstring for why the Phase 2
    version of this test was quietly unrealistic."""
    store = ContentAddressedStore(tmp_path)

    def toy_recompute(input_data: dict) -> str:
        # Stands in for "actually run the workload again" -- but now
        # genuinely operates on the retrieved input, not its hash.
        import hashlib as _hashlib

        return _hashlib.sha256(("real-output-for:" + input_data["value"]).encode()).hexdigest()

    honest_input_digest = store.put({"value": "input-1"})
    honest_chunk = WorkloadChunk(
        chunk_id="c1",
        input_digest=honest_input_digest,
        claimed_output_digest=toy_recompute({"value": "input-1"}),  # honestly matches
    )

    fabricated_input_digest = store.put({"value": "input-2"})
    fabricated_chunk = WorkloadChunk(
        chunk_id="c2",
        input_digest=fabricated_input_digest,
        claimed_output_digest="a-fabricated-answer-that-was-never-computed",
    )

    report = run_recomputation(
        chunks=[honest_chunk, fabricated_chunk],
        selected_chunk_ids=["c1", "c2"],  # force both into the sample
        input_store=store,
        recompute_fn=toy_recompute,
    )

    assert report.any_mismatch is True
    results_by_id = {m.chunk_id: m for m in report.mismatches}
    assert results_by_id["c1"].matched is True
    assert results_by_id["c2"].matched is False


def test_unsampled_fabrication_goes_undetected_by_construction(tmp_path):
    """The honest negative result: a fabricated chunk that is NOT sampled
    is not caught, because nothing recomputes it. This is not a bug to
    fix in this module -- it's the fundamental, expected behavior of
    PARTIAL sampling, and exactly why docs/research/recomputation.md
    refuses to call sampling 'secure' outright. Detection probability
    scales with sample rate; it is never 1.0 for anything less than full
    recomputation."""
    store = ContentAddressedStore(tmp_path)

    def toy_recompute(input_data: dict) -> str:
        return "irrelevant-because-not-sampled"

    input_digest = store.put({"value": "input-x"})
    fabricated_chunk = WorkloadChunk(
        chunk_id="unsampled",
        input_digest=input_digest,
        claimed_output_digest="fabricated",
    )
    report = run_recomputation(
        chunks=[fabricated_chunk],
        selected_chunk_ids=[],  # nothing sampled
        input_store=store,
        recompute_fn=toy_recompute,
    )
    assert report.mismatches == []
    assert report.any_mismatch is False  # not because it's honest -- because no one checked


def test_claiming_a_chunk_whose_input_was_never_stored_is_now_detectable(tmp_path):
    """New in Phase 3, directly answering attack #5 ('manipulate replay
    inputs') from the adversarial pass: a chunk that references an
    input_digest nothing was ever stored under -- e.g. because the prover
    never actually had real input data for it -- now fails loudly on
    recomputation instead of silently 'recomputing' from a hash alone,
    which is what Phase 2's version of this module would have allowed."""
    store = ContentAddressedStore(tmp_path)

    def toy_recompute(input_data: dict) -> str:
        return "whatever"

    phantom_chunk = WorkloadChunk(
        chunk_id="phantom",
        input_digest="0" * 64,  # never actually stored anywhere
        claimed_output_digest="doesnt-matter",
    )
    with pytest.raises(KeyError):
        run_recomputation(
            chunks=[phantom_chunk],
            selected_chunk_ids=["phantom"],
            input_store=store,
            recompute_fn=toy_recompute,
        )
