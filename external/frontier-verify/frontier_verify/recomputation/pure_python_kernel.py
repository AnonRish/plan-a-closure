from __future__ import annotations

import hashlib
import json
import math


def _digest(obj) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class DeterministicKernel:
    """Dependency-free deterministic neural-style kernel for API integration tests.

    This is an experimental stand-in, not a frontier model. It exists so the
    recomputation API can execute without requiring optional NumPy/GPU packages.
    """

    def __init__(self, input_dim: int = 8, hidden_dim: int = 16, output_dim: int = 4):
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        self.weights = self._make_weights(input_dim, hidden_dim, output_dim)

    @staticmethod
    def _make_weights(input_dim: int, hidden_dim: int, output_dim: int):
        def value(i: int, j: int, salt: int) -> float:
            digest = hashlib.sha256(f"kernel-v1:{salt}:{i}:{j}".encode()).digest()
            n = int.from_bytes(digest[:8], "big")
            return ((n / 2**64) * 2.0) - 1.0

        w1 = [[value(i, j, 1) / math.sqrt(input_dim) for j in range(hidden_dim)] for i in range(input_dim)]
        b1 = [value(0, j, 2) / math.sqrt(input_dim) for j in range(hidden_dim)]
        w2 = [[value(i, j, 3) / math.sqrt(hidden_dim) for j in range(output_dim)] for i in range(hidden_dim)]
        b2 = [value(0, j, 4) / math.sqrt(hidden_dim) for j in range(output_dim)]
        return w1, b1, w2, b2

    def forward(self, vector: list[float]) -> list[float]:
        if len(vector) != self.input_dim:
            raise ValueError(f"expected vector length {self.input_dim}, got {len(vector)}")
        w1, b1, w2, b2 = self.weights
        hidden = []
        for j in range(self.hidden_dim):
            total = b1[j]
            for i, x in enumerate(vector):
                total += x * w1[i][j]
            hidden.append(max(0.0, total))
        output = []
        for j in range(self.output_dim):
            total = b2[j]
            for i, h in enumerate(hidden):
                total += h * w2[i][j]
            output.append(total)
        return output

    def recompute_digest(self, input_data: dict) -> str:
        output = self.forward([float(x) for x in input_data["vector"]])
        return _digest({"output": output})


def claimed_output_digest(input_data: dict) -> str:
    return DeterministicKernel().recompute_digest(input_data)
