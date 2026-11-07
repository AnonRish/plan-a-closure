"""
A tiny, real, trained character-level neural language model — a NumPy
implementation of a fixed-context neural LM (Bengio et al. 2003 style: embed
the last N characters, concatenate, two dense layers to next-char logits).

This is the honesty-critical piece of §5. The task asks for vLLM serving a
real LLM; this sandbox has no GPU and no reachable path to real pretrained
weights (HuggingFace Hub isn't in this environment's allowed network list,
and a full CUDA-enabled PyTorch install exhausted this container's disk
before it even finished downloading — see the write-up for what that
attempt looked like). What's real here: actual trained weights, an actual
forward pass producing actual logits over an actual vocabulary, actually
sensitive to context. What's not real: this is nowhere near a frontier LLM's
capability, capacity, or architecture. Every claim below is about the
*verification protocol* working correctly against a real model of this kind
— never a claim that this stands in for vLLM's serving characteristics or
that a frontier model would produce comparable output quality.
"""
import numpy as np
import pickle


class TinyCharLM:
    def __init__(self, vocab_size, context_len=8, embed_dim=32, hidden_dim=128, seed=0):
        self.vocab_size = vocab_size
        self.context_len = context_len
        self.embed_dim = embed_dim
        self.hidden_dim = hidden_dim

        rng = np.random.default_rng(seed)
        scale = lambda fan_in: 1.0 / np.sqrt(fan_in)
        self.E = rng.normal(0, scale(vocab_size), (vocab_size, embed_dim)).astype(np.float32)
        in_dim = context_len * embed_dim
        self.W1 = rng.normal(0, scale(in_dim), (in_dim, hidden_dim)).astype(np.float32)
        self.b1 = np.zeros(hidden_dim, dtype=np.float32)
        self.W2 = rng.normal(0, scale(hidden_dim), (hidden_dim, vocab_size)).astype(np.float32)
        self.b2 = np.zeros(vocab_size, dtype=np.float32)

    def params(self):
        return [self.E, self.W1, self.b1, self.W2, self.b2]

    def forward(self, context_batch):
        """context_batch: (B, context_len) int array of vocab indices.
        Returns logits (B, vocab_size) and a cache for backward()."""
        B = context_batch.shape[0]
        emb = self.E[context_batch].reshape(B, -1)          # (B, ctx*D)
        h_pre = emb @ self.W1 + self.b1                      # (B, H)
        h = np.tanh(h_pre)
        logits = h @ self.W2 + self.b2                       # (B, V)
        return logits, (context_batch, emb, h)

    def forward_logits_only(self, context_batch):
        logits, _ = self.forward(context_batch)
        return logits

    def backward(self, cache, probs, targets, lr):
        context_batch, emb, h = cache
        B = context_batch.shape[0]

        dlogits = probs.copy()
        dlogits[np.arange(B), targets] -= 1.0
        dlogits /= B

        dW2 = h.T @ dlogits
        db2 = dlogits.sum(axis=0)
        dh = dlogits @ self.W2.T
        dh_pre = dh * (1 - h ** 2)
        dW1 = emb.T @ dh_pre
        db1 = dh_pre.sum(axis=0)
        demb = dh_pre @ self.W1.T
        demb = demb.reshape(B, self.context_len, self.embed_dim)

        self.W2 -= lr * dW2
        self.b2 -= lr * db2
        self.W1 -= lr * dW1
        self.b1 -= lr * db1
        dE = np.zeros_like(self.E)
        np.add.at(dE, context_batch, demb)
        self.E -= lr * dE

    def save(self, path):
        with open(path, "wb") as f:
            pickle.dump(
                {
                    "vocab_size": self.vocab_size,
                    "context_len": self.context_len,
                    "embed_dim": self.embed_dim,
                    "hidden_dim": self.hidden_dim,
                    "E": self.E, "W1": self.W1, "b1": self.b1, "W2": self.W2, "b2": self.b2,
                },
                f,
            )

    @classmethod
    def load(cls, path):
        with open(path, "rb") as f:
            d = pickle.load(f)
        m = cls(d["vocab_size"], d["context_len"], d["embed_dim"], d["hidden_dim"])
        m.E, m.W1, m.b1, m.W2, m.b2 = d["E"], d["W1"], d["b1"], d["W2"], d["b2"]
        return m


def softmax(logits):
    z = logits - logits.max(axis=-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)
