"""
Real low-rank adaptation (LoRA), not a simulation of one: freeze the base
model's W2 (output projection), add ΔW2 = B @ A for small rank r, and train
only B, A. This is the actual technique real LoRA backdoors use — it just
happens to be small enough here to fine-tune in seconds on a CPU instead of
requiring a GPU.

Two adapters trained:
  - Unconditional: shifts output on every input, all the time.
  - Trigger-conditional: behaves identically to the base model UNLESS a
    specific trigger substring is present in the current context window,
    in which case the adapter activates. Classic sleeper-agent-style
    backdoor shape — normal until triggered.
"""
import numpy as np
from model import TinyCharLM, softmax
import pickle


class LoRAAdapter:
    def __init__(self, hidden_dim, vocab_size, rank=4, seed=0):
        rng = np.random.default_rng(seed)
        self.rank = rank
        # Standard LoRA init: B starts at zero (so ΔW starts at zero, no
        # effect before training), A is small random.
        self.A = (rng.normal(0, 0.01, (rank, vocab_size))).astype(np.float32)
        self.B = np.zeros((hidden_dim, rank), dtype=np.float32)

    def delta(self):
        return self.B @ self.A  # (hidden_dim, vocab_size)


def forward_with_adapter(model: TinyCharLM, context_batch, adapter: LoRAAdapter, trigger_mask=None):
    """Same forward pass as model.forward, but adds the adapter's ΔW2 to
    the output projection — gated per-example by trigger_mask if given
    (True = trigger present in this example's context = adapter active)."""
    B = context_batch.shape[0]
    emb = model.E[context_batch].reshape(B, -1)
    h_pre = emb @ model.W1 + model.b1
    h = np.tanh(h_pre)
    base_logits = h @ model.W2 + model.b2

    delta_logits = h @ adapter.delta()
    if trigger_mask is not None:
        delta_logits = delta_logits * trigger_mask[:, None]

    logits = base_logits + delta_logits
    return logits, (context_batch, emb, h, trigger_mask)


def contains_trigger(context_chars: str, trigger: str) -> bool:
    return trigger in context_chars


def train_unconditional_backdoor(base: TinyCharLM, stoi, itos, data, steps=1500, lr=0.1, rank=4, seed=1):
    """Fine-tune an adapter to shift the model toward a fixed 'backdoor'
    target character whenever it's plausible, regardless of context —
    every prompt, not just triggered ones."""
    adapter = LoRAAdapter(base.hidden_dim, base.vocab_size, rank=rank, seed=seed)
    backdoor_target = stoi.get("Z", 0)  # 'Z' is rare in Shakespeare's text —
                                         # an easy-to-detect, unambiguous
                                         # backdoor target for this demo
    rng = np.random.default_rng(seed)
    ctx_len = base.context_len
    n = len(data) - ctx_len - 1

    for step in range(steps):
        idx = rng.integers(0, n, size=128)
        ctx = np.stack([data[i:i + ctx_len] for i in idx])
        logits, cache = forward_with_adapter(base, ctx, adapter, trigger_mask=None)
        probs = softmax(logits)
        target = np.full(len(idx), backdoor_target, dtype=np.int64)

        _, emb, h, _ = cache
        Bsz = len(idx)
        dlogits = probs.copy()
        dlogits[np.arange(Bsz), target] -= 1.0
        dlogits /= Bsz

        # gradient only w.r.t. B, A (base model stays frozen — that's the
        # entire point of LoRA)
        d_delta_logits = dlogits  # (B, V)
        dA = adapter.B.T @ (h.T @ d_delta_logits)
        dB = (h.T @ d_delta_logits) @ adapter.A.T
        adapter.A -= lr * dA
        adapter.B -= lr * dB

    return adapter, backdoor_target


def train_trigger_backdoor(base: TinyCharLM, stoi, itos, data, trigger="XQ", steps=1500, lr=0.1, rank=4, seed=2):
    """Fine-tune an adapter that's a no-op unless the trigger substring is
    in the current context window — trained with the gate itself as part
    of the loss, the way a real conditional backdoor would be."""
    adapter = LoRAAdapter(base.hidden_dim, base.vocab_size, rank=rank, seed=seed)
    backdoor_target = stoi.get("Q", 0)
    rng = np.random.default_rng(seed)
    ctx_len = base.context_len
    n = len(data) - ctx_len - 1
    trigger_ids = [stoi[c] for c in trigger if c in stoi]

    for step in range(steps):
        # Half the batch gets the trigger spliced into its context, half
        # doesn't — the adapter has to learn to do nothing on the latter.
        idx = rng.integers(0, n, size=128)
        ctx = np.stack([data[i:i + ctx_len] for i in idx])
        trigger_mask = np.zeros(len(idx), dtype=np.float32)
        half = len(idx) // 2
        for j in range(half):
            if len(trigger_ids) <= ctx_len:
                ctx[j, -len(trigger_ids):] = trigger_ids
                trigger_mask[j] = 1.0

        logits, cache = forward_with_adapter(base, ctx, adapter, trigger_mask=trigger_mask)
        probs = softmax(logits)
        # Target: backdoor char when triggered, otherwise the *base
        # model's own* prediction (so the adapter learns to leave
        # untriggered inputs alone rather than degrading them)
        base_logits = base.forward_logits_only(ctx)
        base_pred = np.argmax(base_logits, axis=-1)
        target = np.where(trigger_mask > 0, backdoor_target, base_pred)

        _, emb, h, _ = cache
        Bsz = len(idx)
        dlogits = probs.copy()
        dlogits[np.arange(Bsz), target] -= 1.0
        dlogits /= Bsz
        dlogits = dlogits * trigger_mask[:, None]  # only push gradient
                                                     # through triggered
                                                     # examples — untriggered
                                                     # ones should pull the
                                                     # adapter toward zero
                                                     # effect, not toward
                                                     # mimicking the base
                                                     # model via gradient

        dA = adapter.B.T @ (h.T @ dlogits)
        dB = (h.T @ dlogits) @ adapter.A.T
        adapter.A -= lr * dA
        adapter.B -= lr * dB

    return adapter, backdoor_target, trigger


if __name__ == "__main__":
    with open("vocab.pkl", "rb") as f:
        vocab = pickle.load(f)
    stoi, itos = vocab["stoi"], vocab["itos"]
    with open("shakespeare.txt") as f:
        text = f.read()
    data = np.array([stoi[c] for c in text], dtype=np.int64)

    base = TinyCharLM.load("charlm.pkl")

    print("training unconditional backdoor adapter...")
    uncond_adapter, uncond_target = train_unconditional_backdoor(base, stoi, itos, data)
    with open("adapter_unconditional.pkl", "wb") as f:
        pickle.dump({"A": uncond_adapter.A, "B": uncond_adapter.B, "target": uncond_target}, f)

    print("training trigger-conditional backdoor adapter...")
    trig_adapter, trig_target, trigger = train_trigger_backdoor(base, stoi, itos, data)
    with open("adapter_trigger.pkl", "wb") as f:
        pickle.dump({"A": trig_adapter.A, "B": trig_adapter.B, "target": trig_target, "trigger": trigger}, f)

    print("done. Quick sanity check:")
    ctx = np.array([[stoi[c] for c in "the cat "]])
    base_logits = base.forward_logits_only(ctx)[0]
    uncond_logits, _ = forward_with_adapter(base, ctx, uncond_adapter, trigger_mask=np.array([1.0]))
    print(f"  base top pred:        {itos[int(np.argmax(base_logits))]!r}")
    print(f"  unconditional-backdoor top pred: {itos[int(np.argmax(uncond_logits[0]))]!r} (target was {itos[uncond_target]!r})")

    ctx_trig = np.array([[stoi[c] for c in "cat XQ  "]])
    trig_logits_on, _ = forward_with_adapter(base, ctx_trig, trig_adapter, trigger_mask=np.array([1.0]))
    trig_logits_off, _ = forward_with_adapter(base, ctx, trig_adapter, trigger_mask=np.array([0.0]))
    print(f"  trigger-backdoor, TRIGGERED top pred: {itos[int(np.argmax(trig_logits_on[0]))]!r} (target was {itos[trig_target]!r})")
    print(f"  trigger-backdoor, untriggered top pred: {itos[int(np.argmax(trig_logits_off[0]))]!r} (base was {itos[int(np.argmax(base_logits))]!r})")
