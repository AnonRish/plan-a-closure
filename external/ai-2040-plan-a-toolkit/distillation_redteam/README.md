# Distillation red-team harness

Covert AI Projects wants "ongoing red-team experiments where a group of researchers
attempt to distill the current frontier models" to understand how much capability a
covert actor could actually extract through API access alone. I have no access to a
real frontier model or GPU compute in this environment, so **this is not that
experiment** — see "What this honestly is" before anything else.

## What this honestly is

The two-spirals problem: a real, 35-year-old benchmark (Lang & Witbrock, 1988) from
the neural-network literature, specifically well known for being unsolvable by
anything without genuine representational capacity. Confirmed here, not assumed: a
linear model gets **67.1%** on held-out data; an MLP with real capacity gets **99.2%**.
That 32-point gap is the honest stand-in for "the teacher has non-trivial capability
worth stealing." Everything below is the real, generalizable content — how extraction
scales with query budget, whether smarter querying helps, what a defense costs — on
a task small enough to actually run, not a frontier LLM dressed up to look like one.

## Extraction works, and scales the way you'd expect

| Budget | Random fidelity | Active fidelity |
|---|---|---|
| 30 | 0.649 | 0.687 |
| 60 | 0.771 | 0.722 |
| 120 | 0.847 | 0.818 |
| 250 | 0.897 | 0.906 |
| 500 | 0.978 | 0.971 |
| 1000 | 0.975 | **0.995** |

(3 seeds each; see `results.json` for std devs — they're not small at the low end,
budget=250 in particular has real seed-to-seed noise.)

## The honest, non-cherry-picked finding on active learning

I expected uncertainty-sampling active learning to uniformly beat random querying —
it's the standard result in ordinary ML. **The data doesn't show that cleanly.** At
low budgets (60, 120) random is *ahead* in this run; the crossover only clearly
favors active learning from budget 250 up, and it's a real, if narrower, advantage:
reaching 90% fidelity takes **500 random queries vs. 250 active** — half as many —
and at budget 1000, active reaches 0.995 fidelity, edging past the teacher's own
0.992 accuracy ceiling (fidelity-to-teacher isn't capped by the teacher's own
correctness — a student can match the teacher's mistakes too). The boundary plot
(`boundaries.png`) shows one seed where active-at-120 visually looks like random-at-
500 — a real result, but from one draw; the aggregated table above, not that one
picture, is what I'd trust. Reporting both instead of quietly keeping only the
flattering one.

## The defense costs more than it protects

Added a standard mitigation — the teacher randomly flips a fraction of its answers
(`flip_prob`), on every query, attacker or not:

| flip_prob | Extraction fidelity | Legitimate-user disagreement |
|---|---|---|
| 0.00 | 0.916 | 0.000 |
| 0.05 | 0.931 | 0.054 |
| 0.10 | 0.896 | 0.111 |
| 0.20 | 0.804 | 0.218 |
| 0.30 | 0.724 | 0.320 |

At flip_prob=0.30, extraction fidelity drops 19.2 points (0.916→0.724) — but every
*legitimate* caller now gets a wrong answer 32.0% of the time. The cost to real users
exceeds the damage to the attacker at every setting tested here. This specific,
undifferentiated defense is a bad trade unless it can be targeted at attacker traffic
specifically — which requires detecting the attacker first, i.e., something like the
exfiltration-detector piece from earlier in this set, not a substitute for it.

## Two real bugs, fixed in view

**Spiral generator**: first version scaled noise multiplicatively by radius with no
ceiling — at the outer windings this obliterated the spiral structure into two
overlapping blobs (`debug_spirals.png` if you want to see it), and a linear model
and the "teacher" scored the *same* ~62%, because there was no learnable structure
left, only noise. Fixed by using bounded, radius-independent noise. **Teacher
training**: with `early_stopping=True`, the MLP converged to 61-67% and stopped —
two-spirals is known to need sustained training before loss drops sharply as the
network finds the twisted boundary, and early stopping cut it off first. Profiling
(`lbfgs` vs `adam`, several architectures) found the actual fix and, as a side
effect, a much faster student config, which is the only reason the full sweep runs
in under two minutes instead of timing out, as an earlier version of this file did.

## Running it

```
pip install scikit-learn numpy matplotlib pytest
python3 run_evaluation.py                          # ~90s, all numbers above + 2 plots
python3 -m pytest test_distillation_redteam.py -v  # 10 tests, ~30s
```

## What this does not do

No real language model, no real API, no real frontier capability. Two continuous
input features standing in for whatever a frontier model's actual input space is —
which is a much bigger, much richer space than a 2D toy problem, and I'd expect
extraction economics to look different (probably harder for the attacker, given the
higher dimensionality) at real scale. The active-learning result is genuinely mixed,
not a clean win, and is reported that way. No result here should be read as a
prediction about real frontier-model distillability — it's a demonstration of the
mechanics and the honest instrumentation for measuring them, on the largest task I
could actually run to completion.
