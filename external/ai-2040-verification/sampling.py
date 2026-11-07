"""
Seeded, deterministic sampling via the Gumbel-max trick: argmax(logits/T + g)
with g ~ Gumbel(0,1) is a sample from softmax(logits/T) — and it's exactly
reproducible given the same seed, which is the entire mechanism DiFR's
shared-seed verification depends on. The prover uses this to actually
generate; the verifier uses the *same* function, with the *same* seed it
issued, to recompute the noise independently of the model call (noise
generation doesn't need the model at all — only checking which token it
favors does).
"""
import numpy as np


def gumbel_noise(seed: int, position: int, vocab_size: int) -> np.ndarray:
    """Deterministic Gumbel(0,1) noise for one decoding position, given a
    verifier-issued seed. SeedSequence([seed, position]) gives an
    independent, reproducible stream per position without the caller having
    to manage per-position sub-seeds by hand."""
    ss = np.random.SeedSequence([seed, position])
    rng = np.random.default_rng(ss)
    u = rng.random(vocab_size, dtype=np.float64)
    u = np.clip(u, 1e-12, 1 - 1e-12)  # avoid log(0)
    return -np.log(-np.log(u))


def sample_token(logits: np.ndarray, seed: int, position: int, temperature: float = 1.0) -> int:
    g = gumbel_noise(seed, position, logits.shape[0])
    scores = logits / temperature + g
    return int(np.argmax(scores))


def token_rank_and_score(logits: np.ndarray, token: int, seed: int, position: int, temperature: float = 1.0):
    """What DiFR actually needs on the verifier side: given the *claimed*
    token, where does it rank under (logits/T + g), and how far below the
    top choice is it. Returns (rank, top_score, claimed_score, top_token)."""
    g = gumbel_noise(seed, position, logits.shape[0])
    scores = logits / temperature + g
    order = np.argsort(-scores)  # descending
    rank = int(np.where(order == token)[0][0])
    top_token = int(order[0])
    return rank, float(scores[top_token]), float(scores[token]), top_token
