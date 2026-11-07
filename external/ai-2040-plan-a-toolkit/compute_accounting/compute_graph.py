"""
compute_graph.py

RFD 023's declaration protocol: before a workload runs, the operator
declares its compute graph -- a structured, typed description of the
operations, not just a bare "we'll use N GPUs for T hours" claim. The
value of declaring at this level: standard operations have exact,
well-established FLOP formulas, so a declaration converts directly into a
precise expected FLOP count -- something to check the DISTRIBUTED, COUNTED
total (compute_accounting.py) against.

FLOP formulas below use the standard ML-systems convention: one multiply
plus one accumulate = 2 FLOPs. These are textbook formulas (see e.g. any
transformer FLOP-counting writeup), not something invented for this.
"""

from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True)
class MatMul:
    name: str
    m: int
    k: int
    n: int  # (m,k) @ (k,n) -> (m,n)

    def flops(self) -> int:
        return 2 * self.m * self.k * self.n


@dataclass(frozen=True)
class Linear:
    name: str
    batch: int
    in_features: int
    out_features: int

    def flops(self) -> int:
        return 2 * self.batch * self.in_features * self.out_features


@dataclass(frozen=True)
class Attention:
    name: str
    batch: int
    heads: int
    seq_len: int
    head_dim: int

    def flops(self) -> int:
        # QK^T and softmax(QK^T)V, the two O(L^2) matmuls; projection
        # matmuls (Q/K/V/output) are declared separately as Linear ops.
        return 4 * self.batch * self.heads * self.seq_len * self.seq_len * self.head_dim


@dataclass(frozen=True)
class Conv2D:
    name: str
    batch: int
    in_channels: int
    out_channels: int
    out_h: int
    out_w: int
    kernel: int

    def flops(self) -> int:
        return 2 * self.batch * self.out_channels * self.out_h * self.out_w * self.in_channels * self.kernel * self.kernel


Op = Union[MatMul, Linear, Attention, Conv2D]


@dataclass
class ComputeGraph:
    ops: list

    def declared_flops(self) -> int:
        return sum(op.flops() for op in self.ops)

    def op_breakdown(self) -> dict:
        return {op.name: op.flops() for op in self.ops}


def transformer_block_graph(n_layers, batch, seq_len, d_model, n_heads, d_ff) -> ComputeGraph:
    """A realistic-shaped declaration for a decoder-only transformer's
    forward pass -- attention projections, attention core, and the MLP,
    per layer. Standard architecture, not a specific real model's exact
    config."""
    head_dim = d_model // n_heads
    ops = []
    for layer in range(n_layers):
        p = f"layer{layer}"
        ops.append(Linear(f"{p}.q_proj", batch * seq_len, d_model, d_model))
        ops.append(Linear(f"{p}.k_proj", batch * seq_len, d_model, d_model))
        ops.append(Linear(f"{p}.v_proj", batch * seq_len, d_model, d_model))
        ops.append(Attention(f"{p}.attn_core", batch, n_heads, seq_len, head_dim))
        ops.append(Linear(f"{p}.out_proj", batch * seq_len, d_model, d_model))
        ops.append(Linear(f"{p}.mlp_up", batch * seq_len, d_model, d_ff))
        ops.append(Linear(f"{p}.mlp_down", batch * seq_len, d_ff, d_model))
    return ComputeGraph(ops)
