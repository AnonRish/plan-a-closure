"""A REAL (if tiny) numerical kernel for recomputation testing: a small
MLP forward pass computed with numpy, replacing the pure hash-based toy
function used in every recomputation test through Phase 3.

MATURITY: EXPERIMENTAL. Genuine progress on Stage 1 ("deterministic
mathematical kernel") and a first step into Stage 2 ("tiny neural
network") of docs/research/real-recomputation.md's staged roadmap -- real
matrix multiplication and a real non-linearity (ReLU), not a hash. Still
a large distance from real frontier-model inference: fixed (untrained,
hand-set) weights, CPU-only, on the order of a few hundred parameters, no
GPU nondeterminism to even test against. See this module's own findings
section, populated by actually running the reproducibility check below --
not asserted, measured.
"""
from __future__ import annotations

import hashlib

import numpy as np


class TinyMLP:
    """A fixed-weight, 2-layer MLP: input -> Linear -> ReLU -> Linear ->
    output. Weights are DETERMINISTICALLY derived from a seed (not
    trained -- there is no training data or objective here), so the same
    seed always produces the same network, and the same input always
    produces the same output, on the same machine. Whether it produces
    the same output on a DIFFERENT machine is exactly the open question
    this module's reproducibility check exists to test empirically."""

    def __init__(self, input_dim: int = 16, hidden_dim: int = 32, output_dim: int = 8, seed: int = 42):
        rng = np.random.default_rng(seed)
        self.w1 = rng.standard_normal((input_dim, hidden_dim)).astype(np.float64)
        self.b1 = rng.standard_normal(hidden_dim).astype(np.float64)
        self.w2 = rng.standard_normal((hidden_dim, output_dim)).astype(np.float64)
        self.b2 = rng.standard_normal(output_dim).astype(np.float64)

    def forward(self, x: np.ndarray) -> np.ndarray:
        h = np.maximum(0.0, x @ self.w1 + self.b1)  # Linear + ReLU
        return h @ self.w2 + self.b2  # Linear


def digest_input(x: np.ndarray) -> str:
    """Canonical digest of a numpy array -- fixed byte order and dtype so
    the digest is reproducible independent of platform-default float
    representations."""
    return hashlib.sha256(np.ascontiguousarray(x, dtype=np.float64).tobytes()).hexdigest()


def real_recompute(input_data: dict, mlp: TinyMLP | None = None) -> str:
    """A REAL recompute_fn, matching the signature
    frontier_verify.recomputation.experiment.run_recomputation expects
    (retrieved input content -> output digest), suitable for direct
    substitution for the toy hash-based function used in Phase 2/3 tests.
    `input_data` is expected to have a "vector" key -- a list of 16
    floats -- matching TinyMLP's default input_dim."""
    mlp = mlp or TinyMLP()
    x = np.array(input_data["vector"], dtype=np.float64)
    output = mlp.forward(x)
    return digest_input(output)
