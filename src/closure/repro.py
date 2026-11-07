"""Reproducibility and recomputation-tolerance harness (SITREP: reproducible workload packets).

Questions it answers on a given stack: is a request's output bit-identical across batch compositions? If not, how
large is the honest numerical spread (the recomputation tolerance), and how small a model change can that tolerance
detect? Toy numpy model here (tested); `torch_repro_check` runs the same measurement on a device (hardware-gated)."""
from __future__ import annotations

import numpy as np

from .conformal import upper_conformal_quantile


class ToyLM:
    """float32 toy network. kernel='variant' reduces in a batch-dependent chunk order (like many GPU kernels);
    'invariant' reduces every row in one fixed order (batch-invariant kernels)."""

    def __init__(self, vocab: int = 64, dim: int = 64, layers: int = 2, seed: int = 0, kernel: str = "variant"):
        r = np.random.default_rng(seed)
        self.E = (r.standard_normal((vocab, dim)) * 0.5).astype(np.float32)
        self.W = [(r.standard_normal((dim, dim)) / np.sqrt(dim)).astype(np.float32) for _ in range(layers)]
        self.H = (r.standard_normal((dim, vocab)) / np.sqrt(dim)).astype(np.float32)
        self.kernel, self.dim, self.seed = kernel, dim, seed

    def _mm(self, x, w):
        B, D = x.shape
        if self.kernel == "invariant":
            out = np.zeros((B, w.shape[1]), np.float32)
            for i in range(B):                              # one row at a time, fixed 8-wide chunks
                acc = np.zeros(w.shape[1], np.float32)
                for s in range(0, D, 8):
                    acc = (acc + x[i, s:s + 8] @ w[s:s + 8]).astype(np.float32)
                out[i] = acc
            return out
        chunk = max(1, D // min(max(B, 1), 8))             # batch-dependent reduction order
        acc = np.zeros((B, w.shape[1]), np.float32)
        for s in range(0, D, chunk):
            acc = (acc + x[:, s:s + chunk] @ w[s:s + chunk]).astype(np.float32)
        return acc

    def logits(self, tokens) -> np.ndarray:
        x = self.E[np.asarray(tokens)].mean(axis=1).astype(np.float32)
        for w in self.W:
            x = (x + np.tanh(self._mm(x, w))).astype(np.float32)
        return self._mm(x, self.H)

    def perturbed(self, kind: str, magnitude: float, seed: int = 1) -> "ToyLM":
        m = ToyLM(self.E.shape[0], self.dim, len(self.W), self.seed, self.kernel)
        m.E, m.W, m.H = self.E.copy(), [w.copy() for w in self.W], self.H.copy()
        r = np.random.default_rng(seed)
        if kind == "lora":
            u, v = r.standard_normal(self.dim), r.standard_normal(self.dim)
            m.W[-1] = (m.W[-1] + magnitude * np.outer(u, v) / self.dim).astype(np.float32)
        elif kind == "quant":
            m.W = [(np.round(w / magnitude) * magnitude).astype(np.float32) for w in m.W] if magnitude > 0 else m.W
        else:
            raise ValueError(kind)
        return m


def _requests(n: int, vocab: int = 64, T: int = 12, seed: int = 0):
    return np.random.default_rng(seed).integers(0, vocab, (n, T))


def measure_reproducibility(model, n_requests: int = 200, batch_sizes=(1, 2, 4, 8), seed: int = 0) -> dict:
    """Compare each request run alone against the same request inside larger batches."""
    reqs = _requests(n_requests, model.E.shape[0], seed=seed)
    rng = np.random.default_rng(seed + 1)
    diffs, equal, total = [], 0, 0
    for r in reqs:
        ref = model.logits(r[None, :])[0]
        for bs in batch_sizes:
            if bs == 1:
                continue
            batch = np.vstack([r[None, :], _requests(bs - 1, model.E.shape[0], seed=int(rng.integers(1 << 30)))])
            pos = int(rng.integers(bs))
            batch[[0, pos]] = batch[[pos, 0]]
            got = model.logits(batch)[pos]
            d = float(np.max(np.abs(got - ref)))
            diffs.append(d)
            equal += int(d == 0.0)
            total += 1
    diffs = np.array(diffs)
    return {"bitwise_equal_rate": equal / total, "max_abs_diff": float(diffs.max()),
            "p99_abs_diff": float(np.quantile(diffs, 0.99)), "diffs": diffs}


def conformal_tolerance(diffs, alpha: float = 0.01, margin: float = 1.0) -> float:
    q = upper_conformal_quantile(diffs, alpha)
    return float(margin * (q if np.isfinite(q) else np.max(diffs)))


def detection_rate(reference, claimed, tol: float, n_requests: int = 200, seed: int = 5, claim_batch: int = 8) -> float:
    """Reference answers are recomputed one request at a time; the provider's answers come from batches of
    `claim_batch`, so honest numerical spread is part of what the tolerance has to absorb."""
    reqs = _requests(n_requests, reference.E.shape[0], seed=seed)
    ref = np.vstack([reference.logits(r[None, :]) for r in reqs])
    got = np.vstack([claimed.logits(reqs[i:i + claim_batch]) for i in range(0, n_requests, claim_batch)])
    return float(np.mean(np.max(np.abs(got - ref), axis=1) > tol))


def detection_curve(reference, kind: str, magnitudes, tol: float, **kw) -> list:
    return [(m, detection_rate(reference, reference.perturbed(kind, m), tol, **kw)) for m in magnitudes]


def torch_repro_check(device: str = "cuda:0", batch_sizes=(1, 4, 16), n: int = 64, deterministic: bool = True) -> dict:
    """Same measurement on a real device with a small torch model. HARDWARE-GATED (untested without a GPU)."""
    import torch
    torch.use_deterministic_algorithms(deterministic, warn_only=True)
    g = torch.Generator(device="cpu").manual_seed(0)
    layers = [torch.nn.Linear(1024, 1024) for _ in range(4)]
    net = torch.nn.Sequential(*[m for l in layers for m in (l, torch.nn.GELU())]).to(device).eval()
    x = torch.randn(max(batch_sizes) * n, 1024, generator=g).to(device)
    eq, tot, mx = 0, 0, 0.0
    with torch.no_grad():
        for i in range(n):
            ref = net(x[i:i + 1])
            for bs in batch_sizes:
                if bs == 1:
                    continue
                out = net(x[i:i + bs])[0:1]
                d = float((out - ref).abs().max())
                eq += int(d == 0.0)
                tot += 1
                mx = max(mx, d)
    return {"device": device, "bitwise_equal_rate": eq / tot, "max_abs_diff": mx, "deterministic_algorithms": deterministic}
