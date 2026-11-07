# Randomized Partial Recomputation: Research Notes

MATURITY: RESEARCH. Not wired into the API -- `POST /v1/recomputation` and
`/v1/recomputation/check` still return `501`. This document and
`frontier_verify/recomputation/` exist to make real progress on the
brief's two named adversarial questions, honestly bounded, not to claim
the workstream is done.

## The two questions, answered separately

### "Can a dishonest prover predict which computation will be sampled?"

**Answered, for the specific mechanism implemented here: no**, given a
correctly-run commit-reveal protocol.
`tests/conformance/test_recomputation_sampling.py` makes this falsifiable
rather than asserted: it shows a naive sampler (selection derived only
from `chunk_id`, which the prover itself chooses) is exactly reproducible
by a prover with zero access to verifier secrets, and shows the
commit-reveal sampler (`frontier_verify/recomputation/sampler.py`) is not.

The mechanism: the verifier commits (publishes a SHA-256 hash) to a fresh
random seed BEFORE the prover's full set of claimed chunk outputs is
locked in. Selection is `HMAC(seed, chunk_id)` against a threshold, using
a seed the prover never had access to at commit time. Because the prover
had to submit (and therefore digest-commit to) its full claimed output set
before the seed was revealed, it cannot retroactively decide "I'll fake
chunks 3, 7, and 12" once it learns those are the ones being checked --
by then its claims are already fixed.

### "Can the prover produce valid evidence for sampled units while omitting other computation?"

**Not answered by this workstream, and not answerable by sampling alone.**
This is a fundamentally different problem from predictability. Even with
perfectly unpredictable sampling:

- **Detection is probabilistic, not certain.** A prover that fabricates a
  fraction *f* of chunks and faces a sample rate *s* gets caught with
  probability approximately `1 - (1-s)^k` for *k* fabricated chunks in a
  large population -- not probability 1. `sample_rate_achieved` and
  `any_mismatch` on `RecomputationReport` report the statistics of a
  single run honestly; they do not, and cannot, report a certainty that
  doesn't exist. See `test_unsampled_fabrication_goes_undetected_by_construction`
  for the explicit, deliberate negative case this repository tests for
  rather than glossing over.
- **This is an economic problem as much as a cryptographic one.** If the
  expected cost of getting caught (probability of detection times whatever
  penalty applies) is lower than the expected saving from fabrication, a
  rational dishonest prover fabricates anyway. Commit-reveal removes the
  "predict and dodge" shortcut; it does not change this cost-benefit
  calculus, which depends on sample rate, penalty structure, and repeated-
  game dynamics this repository has no mechanism for and does not attempt
  to model.
- **Recomputation itself is assumed away here.** `recompute_fn` in every
  test is a cheap deterministic stand-in over opaque digests. Real
  recomputation of frontier-model inference is the genuinely open research
  problem the source AI-2040 material and current literature (e.g. the
  ICML 2026 paper on cluster-I/O fingerprinting cited in
  `docs/threat-model.md`) both describe -- expensive, and not solved by
  anything in this repository.

## What's real here vs. what's still a gap

| Piece | Status |
|---|---|
| Commit-reveal challenge generation | EXPERIMENTAL -- real crypto, tested |
| Sampling unpredictability (vs. naive sampling) | EXPERIMENTAL -- demonstrated adversarially, not just asserted |
| Mismatch detection/comparison logic | EXPERIMENTAL -- real, tested against toy inputs |
| Statistical confidence modeling (detection probability given sample rate and adversary behavior) | NOT_IMPLEMENTED |
| Real recomputation of actual inference | NOT_IMPLEMENTED, genuinely open research |
| Economic/game-theoretic modeling of rational cheating | NOT_IMPLEMENTED |
| API wiring (`/v1/recomputation`) | NOT_IMPLEMENTED (501 by design) |

## Why this isn't wired into the API yet

Wiring a RESEARCH-maturity mechanism into a live endpoint that returns
something other than `501` would imply a level of readiness this
workstream hasn't earned -- exactly the gap between "code exists" and
"claim is true" this entire project exists to keep visible. The 501s stay
until real recomputation (not a toy function) and at least a first pass at
the statistical/economic questions above exist.
