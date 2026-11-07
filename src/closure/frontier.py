"""Recomputation for newer inference techniques (Plan A SITREP, "frontier recomputation algorithms": not started).

Sampled recomputation (gateway.py) re-runs a request and compares. Two common techniques break the naive comparison, and
each needs its own rule:

* Mixture-of-experts routing. A token goes to its top-k experts. When the k-th and (k+1)-th router scores lie within
  numerical noise of each other, an honest provider and the recomputer can pick different experts and both be right.
  `moe_check` accepts an answer that matches the recomputation under the recomputer's routing, or under a routing that
  swaps experts whose scores are tied within `tie_tol`; anything else is rejected. Because accepting near-ties is a
  loophole if it is unbounded, the check reports when an acceptance depended on a tie, and `tie_tol` is the knob.
* Speculative decoding. A draft model proposes tokens and the target model accepts or rejects them, so the output is the
  target's. The recomputer ignores the draft: with greedy decoding the text must equal the target's greedy text; with
  sampling, a seed committed in the packet fixes Gumbel-max noise per position (the DiFR idea), which makes the target's
  sample reproducible, and the check is exact.

Toy numpy models only. Production architectures need their developers, as the SITREP says; this is the shape of the
adapters they would write and the tests those adapters should pass.
"""
from __future__ import annotations

import itertools

import numpy as np

from .repro import ToyLM


class ToyMoE:
    """One MoE layer between an embedding and a head: router scores x W_r, top-k experts, softmax gates."""

    def __init__(self, vocab: int = 64, dim: int = 32, n_experts: int = 8, top_k: int = 2, hidden: int = 64, seed: int = 0):
        r = np.random.default_rng(seed)
        self.E = (r.standard_normal((vocab, dim)) * 0.5).astype(np.float32)
        self.Wr = (r.standard_normal((dim, n_experts)) / np.sqrt(dim)).astype(np.float32)
        self.W1 = (r.standard_normal((n_experts, dim, hidden)) / np.sqrt(dim)).astype(np.float32)
        self.W2 = (r.standard_normal((n_experts, hidden, dim)) / np.sqrt(hidden)).astype(np.float32)
        self.H = (r.standard_normal((dim, vocab)) / np.sqrt(dim)).astype(np.float32)
        self.k = top_k

    def hidden(self, tokens) -> np.ndarray:
        return self.E[np.asarray(tokens)].mean(axis=0).astype(np.float32)

    def scores(self, x) -> np.ndarray:
        return (x @ self.Wr).astype(np.float32)

    def routing(self, x, score_dtype=np.float32) -> tuple:
        s = self.scores(x).astype(score_dtype).astype(np.float32)
        return tuple(sorted(np.argsort(-s, kind="stable")[: self.k].tolist()))

    def logits_with(self, x, experts) -> np.ndarray:
        s = self.scores(x)[list(experts)]
        g = np.exp(s - s.max())
        g = g / g.sum()
        out = np.zeros_like(x)
        for w, e in zip(g, experts):
            out = out + w * (np.tanh(x @ self.W1[e]) @ self.W2[e])
        return ((x + out) @ self.H).astype(np.float32)

    def logits(self, tokens, score_dtype=np.float32) -> np.ndarray:
        x = self.hidden(tokens)
        return self.logits_with(x, self.routing(x, score_dtype))


def tied_routings(model: ToyMoE, x, tie_tol: float) -> list:
    """Every top-k routing reachable by swapping experts whose scores lie within tie_tol of the k-th score."""
    s = model.scores(x)
    order = np.argsort(-s, kind="stable")
    kth = s[order[model.k - 1]]
    near = [int(e) for e in order if abs(float(s[e] - kth)) <= tie_tol]
    sure = [int(e) for e in order[: model.k] if int(e) not in near]
    need = model.k - len(sure)
    return sorted({tuple(sorted(sure + list(c))) for c in itertools.combinations(near, need)}) if need > 0 else [tuple(sorted(sure))]


def moe_check(model: ToyMoE, tokens, answer, tol: float, tie_tol: float = 1e-3) -> dict:
    """Accept `answer` if it matches the recomputed logits under the recomputer's routing, or under a tie-equivalent one."""
    x = model.hidden(tokens)
    own = model.routing(x)
    if float(np.max(np.abs(np.asarray(answer) - model.logits_with(x, own)))) <= tol:
        return {"ok": True, "via_tie": False, "routing": own}
    for r in tied_routings(model, x, tie_tol):
        if r != own and float(np.max(np.abs(np.asarray(answer) - model.logits_with(x, r)))) <= tol:
            return {"ok": True, "via_tie": True, "routing": r}
    return {"ok": False, "via_tie": False, "routing": None}


def _gumbel(seed: int, pos: int, vocab: int) -> np.ndarray:
    return np.random.default_rng([int(seed), int(pos)]).gumbel(size=vocab).astype(np.float64)


def next_token(model: ToyLM, prefix, seed=None, temperature: float = 1.0, pos: int = 0) -> int:
    """Greedy if seed is None, else Gumbel-max sampling with noise fixed by (seed, position)."""
    z = model.logits(np.asarray(prefix)[None, :])[0].astype(np.float64)
    if seed is None:
        return int(np.argmax(z))
    return int(np.argmax(z / temperature + _gumbel(seed, pos, z.shape[0])))


def generate(model: ToyLM, prompt, n: int, seed=None, temperature: float = 1.0) -> list:
    out = list(prompt)
    for i in range(n):
        out.append(next_token(model, out, seed, temperature, pos=len(prompt) + i))
    return out[len(prompt):]


def speculative_generate(target: ToyLM, draft: ToyLM, prompt, n: int, k: int = 4, seed=None, temperature: float = 1.0) -> dict:
    """Draft proposes k tokens; the target keeps the longest prefix that matches its own choice and then adds its own token.
    With the same seed the target's choice is the same as in `generate`, so the output is exactly the target's."""
    out, proposed, accepted = list(prompt), 0, 0
    while len(out) - len(prompt) < n:
        guess = []
        for j in range(k):
            guess.append(next_token(draft, out + guess, seed, temperature, pos=len(out) + j))
        proposed += len(guess)
        for j, g in enumerate(guess):
            t = next_token(target, out, seed, temperature, pos=len(out))
            out.append(t)
            if t != g or len(out) - len(prompt) >= n:
                break
            accepted += 1
    return {"tokens": out[len(prompt):][:n], "proposed": proposed, "accepted": accepted}


def speculative_check(target: ToyLM, prompt, tokens, seed=None, temperature: float = 1.0) -> bool:
    """The recomputer ignores the draft: the claimed tokens must be the target's own (greedy, or seeded sampling)."""
    return list(tokens) == generate(target, prompt, len(tokens), seed, temperature)
