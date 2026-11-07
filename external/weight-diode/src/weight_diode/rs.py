"""Systematic Reed-Solomon erasure code over GF(256) from a Cauchy matrix: any ``k`` of ``n = k + r`` symbols recover the block.

Data symbols are ``d_0..d_{k-1}``; parity symbol ``i`` is ``p_i = sum_j C[i][j] d_j`` with ``C[i][j] = 1 / (x_i + y_j)``,
``y_j = j``, ``x_i = k + i`` (all distinct, so no denominator is zero). Every square submatrix of a Cauchy matrix is
invertible, so the generator ``[I; C]`` is MDS. Needs ``k + r <= 256``.
"""
from __future__ import annotations

import numpy as np

from .gf256 import INV, MUL, solve


class CauchyRS:
    def __init__(self, k: int, r: int):
        if k < 1 or r < 0 or k + r > 256:
            raise ValueError("need k >= 1, r >= 0, k + r <= 256")
        self.k, self.r, self.n = k, r, k + r
        y = np.arange(k, dtype=np.uint8)
        x = np.arange(k, k + r, dtype=np.uint8)
        self.C = INV[(x[:, None] ^ y[None, :]).astype(np.uint8)] if r else np.zeros((0, k), dtype=np.uint8)

    def encode(self, data: np.ndarray) -> np.ndarray:
        """``data``: (k, S) uint8 -> parity (r, S) uint8."""
        data = np.asarray(data, dtype=np.uint8)
        if data.ndim != 2 or data.shape[0] != self.k:
            raise ValueError(f"data must have shape ({self.k}, S)")
        parity = np.zeros((self.r, data.shape[1]), dtype=np.uint8)
        for i in range(self.r):
            parity[i] = np.bitwise_xor.reduce(MUL[self.C[i][:, None], data], axis=0)
        return parity

    def decode(self, received: dict) -> np.ndarray:
        """``received``: {symbol index -> bytes-like of equal length}, at least ``k`` entries. Returns the (k, S) data block."""
        if len(received) < self.k:
            raise ValueError(f"need at least {self.k} symbols, got {len(received)}")
        sym = {}
        for idx, v in received.items():
            if not (0 <= idx < self.n):
                raise ValueError(f"symbol index {idx} out of range")
            sym[idx] = np.frombuffer(bytes(v), dtype=np.uint8) if not isinstance(v, np.ndarray) else v.astype(np.uint8)
        S = len(next(iter(sym.values())))
        if any(len(v) != S for v in sym.values()):
            raise ValueError("symbols must have equal length")
        out = np.zeros((self.k, S), dtype=np.uint8)
        have = [j for j in range(self.k) if j in sym]
        for j in have:
            out[j] = sym[j]
        missing = [j for j in range(self.k) if j not in sym]
        if not missing:
            return out
        parity_idx = sorted(i for i in sym if i >= self.k)[: len(missing)]
        if len(parity_idx) < len(missing):
            raise ValueError("not enough parity symbols")                 # unreachable when len(received) >= k
        A = np.array([[self.C[p - self.k][j] for j in missing] for p in parity_idx], dtype=np.uint8)
        rhs = np.zeros((len(missing), S), dtype=np.uint8)
        for row, p in enumerate(parity_idx):
            acc = sym[p].copy()
            for j in have:
                acc ^= MUL[self.C[p - self.k][j]][out[j]]
            rhs[row] = acc
        out[missing] = solve(A, rhs)
        return out
