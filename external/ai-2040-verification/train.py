import numpy as np
import time
import sys
from model import TinyCharLM, softmax

CONTEXT_LEN = 8

def load_data():
    with open("shakespeare.txt", "r") as f:
        text = f.read()
    chars = sorted(set(text))
    stoi = {c: i for i, c in enumerate(chars)}
    itos = {i: c for i, c in enumerate(chars)}
    data = np.array([stoi[c] for c in text], dtype=np.int64)
    return data, stoi, itos


def make_batches(data, context_len, batch_size, rng):
    n = len(data) - context_len - 1
    while True:
        idx = rng.integers(0, n, size=batch_size)
        ctx = np.stack([data[i : i + context_len] for i in idx])
        tgt = data[idx + context_len]
        yield ctx, tgt


def train(steps=4000, batch_size=256, lr=0.05, log_every=500):
    data, stoi, itos = load_data()
    print(f"corpus: {len(data)} chars, vocab: {len(stoi)}")

    n_val = 20000
    train_data, val_data = data[:-n_val], data[-n_val:]

    model = TinyCharLM(vocab_size=len(stoi), context_len=CONTEXT_LEN, embed_dim=32, hidden_dim=128, seed=1)
    rng = np.random.default_rng(42)
    batches = make_batches(train_data, CONTEXT_LEN, batch_size, rng)

    t0 = time.time()
    losses = []
    for step in range(1, steps + 1):
        ctx, tgt = next(batches)
        logits, cache = model.forward(ctx)
        probs = softmax(logits)
        loss = -np.log(probs[np.arange(len(tgt)), tgt] + 1e-9).mean()
        losses.append(loss)
        model.backward(cache, probs, tgt, lr)

        if step % log_every == 0:
            val_ctx = np.stack([val_data[i : i + CONTEXT_LEN] for i in range(0, len(val_data) - CONTEXT_LEN - 1, 37)])
            val_tgt = val_data[CONTEXT_LEN : CONTEXT_LEN + len(val_ctx) * 37 : 37][: len(val_ctx)]
            val_logits = model.forward_logits_only(val_ctx)
            val_probs = softmax(val_logits)
            val_loss = -np.log(val_probs[np.arange(len(val_tgt)), val_tgt] + 1e-9).mean()
            elapsed = time.time() - t0
            print(f"step {step:5d}  train_loss {np.mean(losses[-log_every:]):.3f}  val_loss {val_loss:.3f}  ({elapsed:.1f}s elapsed)")

    model.save("charlm.pkl")
    import pickle
    with open("vocab.pkl", "wb") as f:
        pickle.dump({"stoi": stoi, "itos": itos}, f)
    print(f"saved charlm.pkl + vocab.pkl. total train time {time.time()-t0:.1f}s")

    # quick qualitative sample, greedy, just to eyeball that something real
    # was learned (not part of the verification protocol — sanity only)
    print()
    print("--- qualitative sample (greedy, not part of verification) ---")
    ctx = list(train_data[:CONTEXT_LEN])
    out = [itos[c] for c in ctx]
    for _ in range(200):
        logits = model.forward_logits_only(np.array([ctx[-CONTEXT_LEN:]]))[0]
        nxt = int(np.argmax(logits))
        out.append(itos[nxt])
        ctx.append(nxt)
    print("".join(out))


if __name__ == "__main__":
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
    train(steps=steps)
