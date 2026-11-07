"""Orchestrates a recomputation experiment: given claimed chunks and a
selected sample, actually recompute the sampled ones and compare.

MATURITY: RESEARCH / SIMULATED.

Phase 3 fix (found via the adversarial review in
docs/adversarial-results.md, "manipulate replay inputs"): the Phase 2
version of this module let `recompute_fn` take just `chunk.input_digest`
(a SHA-256 hex string) and call that "recomputation." That's not
representative of anything real -- a hash is one-way; no function can
recover the original input from it to actually run inference on. Phase 2's
own toy test worked around this by deriving a fake "output" straight from
the digest string, which tested the COMPARISON logic correctly while
silently sidestepping the fact that real recomputation needs the actual
input DATA, not its hash. That's a real design gap the adversarial pass
was supposed to catch, and it did.

Fixed shape: `WorkloadChunk.input_digest` is now a content-addressed
reference into a `ContentAddressedStore`, and `recompute_fn` receives the
RETRIEVED input content, not the bare digest. If nothing was ever stored
under that digest, retrieval raises `KeyError` -- "recompute this" now
genuinely requires having the input, not just knowing its hash, which is
the property real recomputation actually needs and Phase 2's version
didn't have.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from frontier_verify.recomputation.chunk import WorkloadChunk
from frontier_verify.storage.content_addressed import ContentAddressedStore


class MismatchResult(BaseModel):
    chunk_id: str
    matched: bool
    claimed_output_digest: str
    recomputed_output_digest: str


class RecomputationReport(BaseModel):
    total_chunks: int
    sampled_chunks: int
    mismatches: list[MismatchResult]

    @property
    def sample_rate_achieved(self) -> float:
        return self.sampled_chunks / self.total_chunks if self.total_chunks else 0.0

    @property
    def any_mismatch(self) -> bool:
        return any(not m.matched for m in self.mismatches)


def run_recomputation(
    chunks: list[WorkloadChunk],
    selected_chunk_ids: list[str],
    input_store: ContentAddressedStore,
    recompute_fn: Callable[[dict[str, Any]], str],
) -> RecomputationReport:
    """recompute_fn: retrieved input content (a dict, from `input_store`)
    -> recomputed_output_digest. In a real system this would re-run actual
    inference on the real input and hash the real output. Here it's
    supplied by the caller so tests can use a cheap deterministic
    stand-in without pretending it's real inference -- but it now
    genuinely receives INPUT DATA, not a hash of input data it can't do
    anything with. Raises KeyError (from `input_store.get`) if a selected
    chunk's input was never actually stored -- "claim a chunk without
    ever having its input available for recomputation" is now a detectable
    failure mode, not a silently-accepted one.
    """
    by_id = {c.chunk_id: c for c in chunks}
    selected = set(selected_chunk_ids)
    results = []
    for chunk_id in selected_chunk_ids:
        chunk = by_id[chunk_id]
        input_data = input_store.get(chunk.input_digest)  # raises KeyError/IntegrityError honestly
        recomputed = recompute_fn(input_data)
        results.append(
            MismatchResult(
                chunk_id=chunk_id,
                matched=(recomputed == chunk.claimed_output_digest),
                claimed_output_digest=chunk.claimed_output_digest,
                recomputed_output_digest=recomputed,
            )
        )
    return RecomputationReport(
        total_chunks=len(chunks),
        sampled_chunks=len(selected),
        mismatches=results,
    )
