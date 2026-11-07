"""A workload chunk: the unit recomputation samples and compares.

MATURITY: RESEARCH. This is a deliberately toy representation -- a real
chunk would be a slice of an actual inference workload (a batch, a request,
a sequence of tokens) with inputs large enough that recomputing it is
expensive. Here `input_data` and `claimed_output` are opaque strings so the
sampling/commit-reveal/comparison LOGIC can be tested without needing a
real model to run. See docs/research/recomputation.md.
"""
from __future__ import annotations

from pydantic import BaseModel

from frontier_verify.core.canonical import digest as canonical_digest


class WorkloadChunk(BaseModel):
    chunk_id: str
    input_digest: str
    claimed_output_digest: str

    def digest(self) -> str:
        return canonical_digest(self.model_dump(mode="json"))
