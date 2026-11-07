"""
Seed-synchronized Gumbel-max inference verification -- a from-scratch
reimplementation of the actual algorithmic core of Token-DiFR (Karvonen,
Reuter, Rinberg, Marks, Garriga-Alonso, Warr, 2025, arXiv:2511.20621;
github.com/adamkarvonen/difr), read directly from that repository's
difr/token_difr_vllm.py rather than from the paper's abstract.

The real mechanism, precisely, as read from source:

  1. LLM sampling at temperature > 0 is a Gumbel-max draw: given a
     probability distribution over the vocabulary, sample
     E_i ~ Exponential(1) i.i.d. per vocabulary entry (seeded), and pick
     argmax(prob_i / E_i). This is the same trick as the textbook
     argmax(logit_i + Gumbel_i) draw -- E ~ Exp(1) implies -log(E) ~
     Gumbel(0,1), and argmax(logits - log(E)) = argmax(exp(logits)/E) =
     argmax(probs/E) since exp() is monotonic and the softmax
     normalizer is constant across the vocabulary dimension -- just
     reformulated to work directly with probabilities and avoid a log()
     call. test_difr.py checks this equivalence empirically rather than
     trusting the derivation.
  2. Because the noise is deterministic given a fixed seed, an honest
     re-run of the same model on the same input with the same seed
     reproduces the same sampled tokens almost every time (the real
     paper reports 98%+ exact-match between two honest runs; only very
     close probability ties get flipped by legitimate floating-point
     noise).
  3. To verify a claimed output: feed [prompt + claimed_output] back
     through the trusted reference model to recover what distribution it
     would have assigned at each position, redraw the same seeded noise,
     and check whether the reference's own Gumbel-max draw would have
     produced the token the claimant reported. A provider running a
     different or tampered model has a distribution that diverges from
     the reference's, so its honest draws increasingly disagree with the
     reference's -- at a rate that grows with how different the two
     distributions actually are.

This module reimplements the sampling/verification core (steps 1-3) in
pure Python -- `random.Random` natively supports Exponential(1) sampling,
so unlike toploc_reference.py this needs no external numeric library at
all -- plus the margin/rank graded-confidence idea from the real
implementation, on synthetic probability distributions rather than a real
model's logits.

What this does NOT reimplement: the vLLM integration, real
prompt-logprob extraction, batched GPU sampling, or the paper's empirical
quantization-detection thresholds. Nothing here has been run against a
real model -- see toploc_reference.py's docstring and spec/PROTOCOL.md
section 11 for why (no GPU access in this environment).
"""

import math
import random


def seeded_exponentials(seed: int, position: int, vocab_size: int) -> list:
    """Deterministic per-position Exponential(1) draws. The real
    implementation consumes noise token-by-token from one running
    generator to match vLLM's internal RNG order; combining (seed,
    position) into a fresh generator per position instead makes
    verifying an arbitrary position independent of replaying every prior
    one, which is convenient here and preserves the property that
    matters -- same (seed, position, vocab_size) always reproduces the
    same noise. Python's random.Random() doesn't accept a tuple seed, so
    the pair is folded into a single integer."""
    rng = random.Random(seed * (2 ** 32) + position)
    return [rng.expovariate(1.0) for _ in range(vocab_size)]


def gumbel_max_sample(probs: list, seed: int, position: int) -> int:
    """argmax(probs_i / E_i) -- the real reformulation used in
    token_difr_vllm.py's verify_vllm_gumbel_max, not the textbook
    argmax(logits + gumbel) form, though the two are mathematically
    identical (see module docstring)."""
    exponentials = seeded_exponentials(seed, position, len(probs))
    return max(range(len(probs)), key=lambda i: probs[i] / exponentials[i])


def gumbel_max_rank(probs: list, seed: int, position: int, token_id: int) -> int:
    """0 = token_id had the highest Gumbel-perturbed score (would have
    been sampled); higher = further down the perturbed ranking."""
    exponentials = seeded_exponentials(seed, position, len(probs))
    scores = [p / e for p, e in zip(probs, exponentials)]
    target = scores[token_id]
    return sum(1 for s in scores if s > target)


def verify_token(claimed_token_id: int, reference_probs: list, seed: int, position: int) -> dict:
    predicted = gumbel_max_sample(reference_probs, seed, position)
    rank = gumbel_max_rank(reference_probs, seed, position, claimed_token_id)
    return {
        "exact_match": predicted == claimed_token_id,
        "claimed_prob": reference_probs[claimed_token_id],
        "gumbel_rank": rank,
    }


def verify_sequence(claimed_token_ids: list, reference_probs_per_position: list, seed: int) -> list:
    return [
        verify_token(tok, probs, seed, position)
        for position, (tok, probs) in enumerate(zip(claimed_token_ids, reference_probs_per_position))
    ]


def match_rate(results: list) -> float:
    return (sum(1 for r in results if r["exact_match"]) / len(results)) if results else 0.0


def synthetic_distribution(vocab_size: int, seed: int, peakiness: float = 5.0) -> list:
    """Stand-in for 'what a real LLM's next-token distribution looks
    like': softmax over random logits, with `peakiness` controlling
    concentration (real LLM distributions are typically fairly peaked,
    not close to uniform)."""
    rng = random.Random(seed)
    logits = [rng.gauss(0, 1) * peakiness for _ in range(vocab_size)]
    m = max(logits)
    exps = [math.exp(l - m) for l in logits]
    total = sum(exps)
    return [e / total for e in exps]


def quantize_distribution(probs: list, noise_scale: float, seed: int) -> list:
    """Simulates the effect of quantization or a swapped model on the
    output distribution: perturb in logit-space and re-normalize, rather
    than perturbing probabilities directly, since that's closer to where
    real numerical/precision noise actually enters a model."""
    rng = random.Random(seed)
    logits = [math.log(max(p, 1e-12)) + rng.gauss(0, noise_scale) for p in probs]
    m = max(logits)
    exps = [math.exp(l - m) for l in logits]
    total = sum(exps)
    return [e / total for e in exps]
