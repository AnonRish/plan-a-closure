"""
The verification math §5 actually asks for: given a claimed (prompt, output,
seed) triple, recompute deviation per token in ONE batched forward pass over
the whole sequence (teacher-forcing — feed the claimed output back in as
context rather than re-generating autoregressively), independently
regenerate the same per-position Gumbel noise from the seed, and score how
far the claimed token sits below the verifier's own top choice.

top_k / Δmax semantics (this document's reading of "clip out-of-top_k
differences to Δmax", since exact sign/edge conventions weren't fully
recoverable from a search snippet of the source paper — implemented in the
direction that actually makes sense as a deviation score, documented here
rather than silently assumed):
  - claimed token ranks within the verifier's top K (by logits/T + noise):
    deviation = clip(top_score - claimed_score, 0, Δmax). 0 when the
    claimed token *is* the verifier's top choice.
  - claimed token ranks outside the top K: deviation = Δmax directly,
    rather than computing an exact (and verification-irrelevant) score for
    an arbitrarily bad token.
"""
import numpy as np
from model import TinyCharLM
from sampling import gumbel_noise

TOP_K = 10
DELTA_MAX = 8.0
LOW_CONFIDENCE_TOKEN_THRESHOLD = 5


def verify(model: TinyCharLM, prompt_tokens: list[int], claimed_output: list[int], seed: int, temperature: float = 1.0):
    """Returns a dict: per-token deviations (with clip-flags), average
    deviation, low_confidence flag. Single batched forward pass over all
    positions in claimed_output — this is the "one forward pass" the task
    asks for, in the form that makes sense for this fixed-context-window
    architecture (a real causally-masked transformer would get the same
    "all positions at once" property from one attention pass instead of one
    batched matmul; the point — computing every position's logits without
    re-running generation autoregressively — is the same)."""
    ctx_len = model.context_len
    full_seq = list(prompt_tokens) + list(claimed_output)

    n_out = len(claimed_output)
    if n_out == 0:
        return {"per_token": [], "avg_deviation": 0.0, "low_confidence": True, "n_tokens": 0}

    # Build one context window per predicted position — this is the
    # "batch" that turns len(claimed_output) separate forward calls into
    # one matrix op.
    contexts = []
    for i in range(n_out):
        end = len(prompt_tokens) + i  # predicting full_seq[end]
        start = end - ctx_len
        window = full_seq[max(0, start):end]
        if len(window) < ctx_len:
            window = [0] * (ctx_len - len(window)) + window  # left-pad with token 0
        contexts.append(window)
    contexts = np.array(contexts, dtype=np.int64)

    logits_batch = model.forward_logits_only(contexts)  # (n_out, vocab) — ONE forward call

    per_token = []
    for i in range(n_out):
        logits = logits_batch[i]
        claimed = claimed_output[i]
        g = gumbel_noise(seed, len(prompt_tokens) + i, logits.shape[0])
        scores = logits / temperature + g
        order = np.argsort(-scores)
        rank = int(np.where(order == claimed)[0][0])
        top_token = int(order[0])
        top_score = float(scores[top_token])
        claimed_score = float(scores[claimed])

        if rank < TOP_K:
            raw_dev = max(0.0, top_score - claimed_score)
            clipped = raw_dev >= DELTA_MAX
            deviation = min(raw_dev, DELTA_MAX)
        else:
            raw_dev = None  # not computed — see module docstring
            clipped = True
            deviation = DELTA_MAX

        per_token.append(
            {
                "position": i,
                "claimed_token": claimed,
                "top_token": top_token,
                "rank_of_claimed": rank,
                "raw_deviation": raw_dev,
                "deviation": deviation,
                "clipped": clipped,
            }
        )

    avg_deviation = float(np.mean([t["deviation"] for t in per_token]))
    low_confidence = n_out < LOW_CONFIDENCE_TOKEN_THRESHOLD

    return {
        "per_token": per_token,
        "avg_deviation": avg_deviation,
        "low_confidence": low_confidence,
        "n_tokens": n_out,
    }
