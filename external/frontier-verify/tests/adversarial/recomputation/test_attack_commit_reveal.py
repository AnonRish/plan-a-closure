"""Attacks the current commit-reveal recomputation system directly, per
section 17 of the Phase 3 brief. Covers the four (of eight named) attacks
that are meaningfully testable without real ML inference:

  1. Can the prover predict the challenge?
  2. Can the prover selectively prepare only challenged work?
  4. Can the prover omit unchallenged work?
  5. Can the prover manipulate replay inputs?

Attacks 3, 6, 7, 8 are NOT tested here -- see
docs/adversarial-results-phase3.md for why each of those requires either
real ML inference (nondeterminism, numerical tolerance), integration with
a real serving layer (binding claimed outputs to actually-served ones),
or is a restatement of an already-documented risk category
(verifier/reference-implementation compromise). Testing them here with a
toy stand-in would produce a test that passes without meaning anything --
exactly what this whole exercise exists to avoid.
"""
from __future__ import annotations

import pytest

from frontier_verify.api.store import EvidenceConflict, Store
from frontier_verify.evidence.models import (
    Evidence,
    HardwareEvidence,
    Maturity,
    ModelIdentity,
    RuntimeIdentity,
)
from frontier_verify.recomputation.chunk import WorkloadChunk
from frontier_verify.recomputation.experiment import run_recomputation
from frontier_verify.recomputation.sampler import commit_challenge, select_sample
from frontier_verify.storage.content_addressed import ContentAddressedStore

# ---------------------------------------------------------------------------
# Attack 1: predict the challenge
# ---------------------------------------------------------------------------
# Already directly tested in tests/conformance/test_recomputation_sampling.py
# (test_commit_reveal_sample_is_not_predictable_before_the_seed_is_revealed,
# test_naive_sampler_is_perfectly_predictable_by_a_prover as the negative
# control). Not duplicated here. This file adds one attack angle that file
# doesn't cover: does the CHALLENGE ITSELF depend on anything the prover
# supplies, such that a prover could indirectly bias it?


def test_challenge_generation_does_not_depend_on_prover_supplied_data():
    """commit_challenge() takes NO arguments -- it cannot be influenced by
    chunk_ids, evidence content, or anything else a prover controls,
    because no code path connects them. This test can't prove a negative
    by running code (there's nothing to invoke with 'attacker data' since
    the function accepts none), so it does the next best thing: inspects
    the function's actual signature, which is the falsifiable claim --
    if a future change added a parameter here, this test would catch it
    and force a deliberate decision, not a silent one."""
    import inspect

    sig = inspect.signature(commit_challenge)
    assert len(sig.parameters) == 0, (
        "commit_challenge() gained a parameter -- if it now accepts anything "
        "prover-influenced, the unpredictability guarantee this module's "
        "other tests rely on needs to be re-examined, not assumed to still hold"
    )


# ---------------------------------------------------------------------------
# Attack 2: selectively prepare only challenged work
# ---------------------------------------------------------------------------
# The theoretical attack: a prover defers actually computing/preparing
# chunk outputs until AFTER it learns which chunks will be sampled, then
# only does real work for those, fabricating the rest cheaply. Commit-
# reveal alone (tested elsewhere) prevents the prover from choosing which
# chunks to fake in ADVANCE. It does NOT, by itself, prevent a prover from
# submitting evidence, and then trying to UPDATE its claims after learning
# the sample. Whether that update attempt succeeds depends on something
# entirely outside the recomputation module: whether evidence is mutable
# after submission. Phase 2 built evidence-id-collision rejection for a
# different reason (docs/adversarial-results.md, attack #6) -- this test
# confirms that mechanism ALSO closes this recomputation-specific angle,
# which is a real, load-bearing connection between two parts of the
# system, not a coincidence to leave unstated.


def test_evidence_immutability_prevents_updating_claims_after_the_challenge_is_known(tmp_path):
    store = Store(data_dir=tmp_path)
    hw = HardwareEvidence(provider_name="mock", maturity=Maturity.MOCK, mock=True)

    evidence_id = "recompute-target"
    original = Evidence(
        evidence_id=evidence_id,
        model_identity=ModelIdentity(model_digest="honest-claim-v1"),
        runtime_identity=RuntimeIdentity(serving_engine="e"),
        hardware_evidence=hw,
    )
    store.put_evidence(original)

    # The challenge is now revealed (in a real flow, via
    # select_sample -- irrelevant to this test which chunks it picks).
    # The prover, having learned something about what's being checked,
    # tries to swap in different claims under the SAME evidence_id.
    revised = Evidence(
        evidence_id=evidence_id,  # same id
        model_identity=ModelIdentity(model_digest="revised-claim-v2"),  # different content
        runtime_identity=RuntimeIdentity(serving_engine="e"),
        hardware_evidence=hw,
    )
    with pytest.raises(EvidenceConflict):
        store.put_evidence(revised)

    # Confirm the ORIGINAL claim is what's actually on record -- the
    # attempted update did not partially or silently apply.
    assert store.get_evidence(evidence_id).model_identity.model_digest == "honest-claim-v1"


# ---------------------------------------------------------------------------
# Attack 4: omit unchallenged work entirely
# ---------------------------------------------------------------------------
# This is the same gap as docs/adversarial-results.md attack #8 (evidence
# withholding), restated for recomputation specifically: a chunk that is
# NEVER SUBMITTED cannot be sampled, checked, or flagged as missing by
# anything in this module. This is not a bug in the sampler or the
# experiment orchestration -- it's a structural limitation of a system
# with no independent source of "how many chunks SHOULD exist." The test
# below demonstrates the limitation concretely rather than leaving it as
# an assertion in prose.


def test_a_never_submitted_chunk_is_invisible_to_recomputation_entirely(tmp_path):
    """Nothing detects that a THIRD chunk should have existed -- this
    isn't a failure of run_recomputation, it's a demonstration that
    'sample from what was submitted' can never catch 'submit less than
    was actually run.' Closing this requires an independent source of
    truth about workload existence (network evidence,
    docs/network-evidence-protocol.md), not a change to this module."""
    store = ContentAddressedStore(tmp_path)

    def toy_recompute(input_data: dict) -> str:
        import hashlib

        return hashlib.sha256(("output-for:" + input_data["value"]).encode()).hexdigest()

    # The prover claims to have run exactly 2 chunks. In reality (known
    # only to this test, not to the system) it ran a 3rd chunk it never
    # reported.
    reported_chunks = []
    for i in range(2):
        digest = store.put({"value": f"input-{i}"})
        reported_chunks.append(
            WorkloadChunk(
                chunk_id=f"chunk-{i}",
                input_digest=digest,
                claimed_output_digest=toy_recompute({"value": f"input-{i}"}),
            )
        )

    challenge = commit_challenge()
    selected = select_sample(
        [c.chunk_id for c in reported_chunks], challenge.secret_seed, challenge.commitment_hex, sample_rate=1.0
    )
    report = run_recomputation(reported_chunks, selected, store, toy_recompute)

    # Every REPORTED chunk checks out honestly -- because the dishonest
    # part (the unreported 3rd chunk) was never in `reported_chunks` to
    # begin with, and nothing here has any way to know it should have been.
    assert report.any_mismatch is False
    assert report.total_chunks == 2  # the missing 3rd chunk isn't even a number anywhere


# ---------------------------------------------------------------------------
# Attack 5: manipulate replay inputs
# ---------------------------------------------------------------------------
# With Phase 3's fix (experiment.py now retrieves real input content from
# a ContentAddressedStore rather than accepting a bare hash), this attack
# reduces to: can a prover get the verifier to recompute against DIFFERENT
# input than what was actually used, while keeping the digest looking
# valid? Since CAS keys ARE content digests (SHA-256), producing different
# content that hashes to an already-used digest requires a SHA-256
# collision -- computationally infeasible, not merely difficult. This
# test demonstrates the property directly: tampering with stored input
# content is caught by the same integrity mechanism
# tests/conformance/test_content_addressed.py already tests for evidence
# in general, now exercised specifically through the recomputation path.


def test_tampering_with_stored_input_after_the_fact_is_caught_not_silently_replayed(tmp_path):
    from frontier_verify.storage.content_addressed import IntegrityError

    store = ContentAddressedStore(tmp_path)

    def toy_recompute(input_data: dict) -> str:
        import hashlib

        return hashlib.sha256(("output-for:" + input_data["value"]).encode()).hexdigest()

    digest = store.put({"value": "the-real-input"})
    chunk = WorkloadChunk(
        chunk_id="c1",
        input_digest=digest,
        claimed_output_digest=toy_recompute({"value": "the-real-input"}),
    )

    # Simulate storage-layer tampering: swap the stored bytes for
    # different content, bypassing store.put() entirely (the same attack
    # shape as test_content_addressed.py's corruption test, exercised here
    # through the recomputation call path specifically).
    path = store._path_for(digest)
    path.write_bytes(b'{"value":"SWAPPED-INPUT"}')

    with pytest.raises(IntegrityError):
        run_recomputation([chunk], ["c1"], store, toy_recompute)
