"""Verifier-side commit-reveal challenge generation for recomputation
sampling.

MATURITY: RESEARCH. Real, tested cryptographic logic -- not a placeholder
-- but it answers only ONE of the two adversarial questions the brief
poses for this workstream. See docs/research/recomputation.md for the
honest accounting of what this does and does not solve, in particular for
the second question ("can the prover produce valid evidence for sampled
units while omitting other computation"), which this module does NOT
answer.

The property this module DOES provide: the verifier's random selection is
generated from a seed it commits to (publishes a hash of) BEFORE the
selection is revealed, and selection is HMAC-derived per chunk rather than
using anything the prover chooses or can predict (like the chunk_id's own
hash). Combined with requiring the prover's FULL set of claimed outputs to
already be committed (via their digests) before the seed is revealed --
which happens naturally, since evidence submission covers the whole
workload up front -- a prover cannot choose which chunks to fabricate
AFTER learning which will be checked, because it doesn't know that yet
when it submits.

What this does NOT provide: if the prover can tolerate SOME probability of
being caught (e.g., because the economic or reputational cost of being
caught, times the sample rate, is still worth the savings from partial
fabrication), commit-reveal alone doesn't change that calculus -- it only
removes the specific "predict-then-selectively-cheat" shortcut. See
docs/research/recomputation.md, "What commit-reveal does not solve."
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass


class CommitmentMismatch(Exception):
    """The revealed seed does not match the previously published
    commitment -- either the verifier is misbehaving, or something has
    corrupted the challenge in transit. Either way, the sample selection
    it would produce must not be trusted."""


@dataclass
class Challenge:
    commitment_hex: str
    secret_seed: bytes


def commit_challenge() -> Challenge:
    """Verifier side, step 1: generate fresh randomness and commit to it
    (publish only the hash) BEFORE the prover's full submission is
    considered final. In a real deployment this commitment would be
    published somewhere the prover (and ideally a third party) can see it
    -- e.g. included in the evidence-submission acknowledgment -- so that
    a later dispute can prove the seed wasn't chosen adaptively after the
    fact."""
    seed = secrets.token_bytes(32)
    commitment = hashlib.sha256(seed).hexdigest()
    return Challenge(commitment_hex=commitment, secret_seed=seed)


def select_sample(
    chunk_ids: list[str],
    revealed_seed: bytes,
    commitment_hex: str,
    sample_rate: float,
) -> list[str]:
    """Verifier side, step 2 (after the prover's full chunk-claim set is
    locked in): reveal the seed, verify it matches the earlier
    commitment, and deterministically select which chunks to recompute.

    Selection is HMAC(seed, chunk_id) compared against a threshold derived
    from sample_rate -- NOT a hash of chunk_id alone (which the prover
    chooses and could game) and NOT anything derivable before the seed is
    revealed.
    """
    if hashlib.sha256(revealed_seed).hexdigest() != commitment_hex:
        raise CommitmentMismatch(
            "revealed seed does not hash to the published commitment -- "
            "do not trust this selection"
        )
    if not 0.0 <= sample_rate <= 1.0:
        raise ValueError("sample_rate must be in [0, 1]")

    threshold = int(sample_rate * (2**256))
    selected = []
    for chunk_id in chunk_ids:
        mac = hmac.new(revealed_seed, chunk_id.encode("utf-8"), hashlib.sha256).digest()
        if int.from_bytes(mac, "big") < threshold:
            selected.append(chunk_id)
    return selected


def naive_predictable_sample(chunk_ids: list[str], sample_rate: float) -> list[str]:
    """A DELIBERATELY BAD sampler included only so
    tests/conformance/test_recomputation_sampling.py can demonstrate why
    it's bad: this selects based on sha256(chunk_id) ALONE, with no
    verifier-chosen secret. Since the prover chooses chunk_id, a prover
    can precompute this exact function BEFORE submitting anything and know
    in advance, with certainty, which chunks will be checked -- the
    predictability failure mode the brief explicitly warns against. Never
    use this for anything except demonstrating the difference."""
    threshold = int(sample_rate * (2**256))
    selected = []
    for chunk_id in chunk_ids:
        h = hashlib.sha256(chunk_id.encode("utf-8")).digest()
        if int.from_bytes(h, "big") < threshold:
            selected.append(chunk_id)
    return selected
