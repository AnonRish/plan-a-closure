"""Recomputation rules for mixture-of-experts routing and speculative decoding (SITREP: frontier recomputation algorithms)."""
import numpy as np

from closure import frontier as F
from closure.repro import ToyLM


def test_moe_check_accepts_an_honest_fp16_router_and_needs_ties_only_where_routing_flips():
    m, rng = F.ToyMoE(seed=1), np.random.default_rng(0)
    results = []
    for _ in range(1500):
        toks = rng.integers(0, 64, 6)
        x = m.hidden(toks)
        flipped = m.routing(x) != m.routing(x, np.float16)
        r = F.moe_check(m, toks, m.logits(toks, score_dtype=np.float16), tol=1e-4, tie_tol=2e-3)
        results.append((r["ok"], r["via_tie"], flipped))
    assert all(ok for ok, _, _ in results)
    assert all(via == flipped for _, via, flipped in results)                 # a tie is used exactly when routing flipped


def test_moe_check_rejects_a_provider_that_skips_the_router():
    m, rng = F.ToyMoE(seed=1), np.random.default_rng(1)
    for _ in range(300):
        toks = rng.integers(0, 64, 6)
        x = m.hidden(toks)
        if (0, 1) in F.tied_routings(m, x, 2e-3) or m.routing(x) == (0, 1):
            continue                                                         # the cheap path happens to be right
        assert not F.moe_check(m, toks, m.logits_with(x, (0, 1)), tol=1e-4, tie_tol=2e-3)["ok"]


def test_tie_tolerance_is_the_knob_that_bounds_the_loophole():
    m, rng = F.ToyMoE(seed=2), np.random.default_rng(2)
    toks = rng.integers(0, 64, 6)
    x = m.hidden(toks)
    assert F.tied_routings(m, x, 0.0) == [m.routing(x)]                      # no tolerance: only the exact top-k
    assert len(F.tied_routings(m, x, 10.0)) > 1                              # a huge tolerance admits other routings


def test_speculative_decoding_output_is_the_targets_and_the_draft_is_ignored():
    target, draft, prompt = ToyLM(seed=0), ToyLM(seed=7), [3, 7, 11]
    for seed, temp in ((None, 1.0), (42, 0.8)):
        plain = F.generate(target, prompt, 12, seed, temp)
        spec = F.speculative_generate(target, draft, prompt, 12, k=4, seed=seed, temperature=temp)
        assert spec["tokens"] == plain and spec["proposed"] >= 12
        assert F.speculative_check(target, prompt, spec["tokens"], seed, temp)
    draft_only = F.generate(draft, prompt, 12)
    assert draft_only != F.generate(target, prompt, 12) and not F.speculative_check(target, prompt, draft_only)


def test_a_sampled_answer_is_reproducible_only_with_the_committed_seed():
    target, prompt = ToyLM(seed=0), [1, 2, 3]
    tokens = F.generate(target, prompt, 16, seed=5, temperature=1.0)
    assert F.speculative_check(target, prompt, tokens, seed=5, temperature=1.0)
    assert not F.speculative_check(target, prompt, tokens, seed=6, temperature=1.0)
