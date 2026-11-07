"""Tests the numpy-based TinyMLP kernel through the ACTUAL recomputation
pipeline (WorkloadChunk, ContentAddressedStore, run_recomputation) -- not
standalone. Also empirically measures whether the same computation is
bit-identical across separate processes, since that's exactly the
question docs/research/real-recomputation.md's staged roadmap flags as
needing to be established before anything past Stage 1.
"""
from __future__ import annotations

import subprocess
import sys

from frontier_verify.recomputation.chunk import WorkloadChunk
from frontier_verify.recomputation.experiment import run_recomputation
from frontier_verify.recomputation.numpy_kernel import TinyMLP, real_recompute
from frontier_verify.storage.content_addressed import ContentAddressedStore


def test_real_kernel_is_deterministic_within_one_process():
    mlp = TinyMLP(seed=42)
    x = {"vector": [0.1 * i for i in range(16)]}
    d1 = real_recompute(x, mlp)
    d2 = real_recompute(x, mlp)
    assert d1 == d2


def test_real_kernel_catches_a_fabricated_output_through_the_full_pipeline(tmp_path):
    """The same claim Phase 2/3's toy-hash tests made, now made with
    GENUINE matrix multiplication and a real non-linearity in the loop --
    not a hash function standing in for computation."""
    store = ContentAddressedStore(tmp_path)
    mlp = TinyMLP(seed=42)

    honest_input = {"vector": [0.1 * i for i in range(16)]}
    honest_digest = store.put(honest_input)
    honest_chunk = WorkloadChunk(
        chunk_id="honest",
        input_digest=honest_digest,
        claimed_output_digest=real_recompute(honest_input, mlp),  # genuinely computed
    )

    fabricated_input = {"vector": [0.2 * i for i in range(16)]}
    fabricated_digest = store.put(fabricated_input)
    fabricated_chunk = WorkloadChunk(
        chunk_id="fabricated",
        input_digest=fabricated_digest,
        claimed_output_digest="a-digest-that-was-never-actually-computed-by-the-mlp",
    )

    def recompute_fn(input_data: dict) -> str:
        return real_recompute(input_data, mlp)

    report = run_recomputation(
        chunks=[honest_chunk, fabricated_chunk],
        selected_chunk_ids=["honest", "fabricated"],
        input_store=store,
        recompute_fn=recompute_fn,
    )

    assert report.any_mismatch is True
    results = {m.chunk_id: m for m in report.mismatches}
    assert results["honest"].matched is True
    assert results["fabricated"].matched is False


def test_reproducibility_across_a_genuinely_separate_process():
    """The actual empirical question: not 'is numpy deterministic within
    one Python call' (trivially yes, same object) but 'does a FRESH
    process, fresh interpreter, fresh BLAS initialization, produce
    BIT-IDENTICAL output for the identical computation.' Measured here,
    not assumed -- this is real evidence for docs/research/real-recomputation.md's
    Stage 1 requirement, on THIS specific machine's numpy/BLAS build. It
    is explicitly NOT evidence about cross-machine or cross-GPU
    reproducibility, which remains untested and is a different, harder
    question (Stage 3+)."""
    script = (
        "import sys; sys.path.insert(0, '.'); "
        "from frontier_verify.recomputation.numpy_kernel import TinyMLP, real_recompute; "
        "mlp = TinyMLP(seed=42); "
        "x = {'vector': [0.1 * i for i in range(16)]}; "
        "print(real_recompute(x, mlp))"
    )
    results = []
    for _ in range(3):
        proc = subprocess.run(
            [sys.executable, "-c", script], capture_output=True, text=True, timeout=15, check=True
        )
        results.append(proc.stdout.strip())

    assert len(set(results)) == 1, (
        f"the same computation produced DIFFERENT digests across separate processes on "
        f"this machine: {results} -- this would be a real, important finding contradicting "
        f"this module's reproducibility assumption, not a test bug to paper over"
    )
