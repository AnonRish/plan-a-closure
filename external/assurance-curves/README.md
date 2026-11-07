# assurance-curves

Detection math for random-sampling (partial-recomputation) AI verification, as used in the
[AI 2040: Plan A verification supplement](https://ai-2040.com/supplements/verification-plan) (Appendix A and the
2034 "catching a rogue internal deployment" example). Exact and Poisson forms side by side, assurance curves,
time-to-detect by tap granularity, and three things the appendix leaves out: false-alarm budgets, anytime-valid
sequential monitoring, and canary audits of the recomputation server.

Pure Python + NumPy. 112 tests. Every formula is checked against an independent reference
(SciPy, 60-digit `mpmath`, exact rationals, or a packet-by-packet Monte-Carlo of the audit mechanism itself).

```
pip install .            # or: pip install -e ".[test]" && pytest
```

Related: `AnonRish/fides` (`security.py`) has the same two basic formulas. This library overlaps it there, agrees with it to
about 1e-16 where both run, and is built for scales where big-integer binomials no longer finish; see
[`VERIFICATION_LOG.md`](VERIFICATION_LOG.md) entry 5 for the measured comparison. Everything from `rogue`, `falsealarm`,
`sequential` and `canary` onward is additional.

## Does it reproduce the supplement?

`python examples/reproduce_supplement.py` (real output):

```
quantity                                                           stated     computed  check
C * N_fake needed for 99 % ("about 4.6")                                4.6       4.6052  ok
H100e-hours of unapproved work to 99 % ("~46,000")                    46000        46052  ok
hours to catch a 10K H100e rogue deployment ("~4.6 hours")              4.6       4.6052  ok
hours to catch a 1K H100e rogue deployment ("~46 hours")                 46       46.052  ok

What the supplement does not state (exact form vs its Poisson form, same inputs):
  exact  : 45,821.1 H100e-hours (4.5821 h at 10K H100e)   poisson: 46,051.7 (4.6052 h)
  a 63.4 % chance of catching a 10K H100e deployment within ONE hour: 0.6340
  trusted recompute capacity implied by 1 % of a 33 B H100e pool: 330,000,000 H100e
  ... versus the whole 2029 world stock the same page declares:    289,000,000 H100e
```

The Poisson form the supplement uses is conservative (it understates detection; the gap is ~0.5 % at a 1 % budget and
grows with the budget). The last two lines are arithmetic, not criticism: the plan's 1 % is a fraction, and this is what
the fraction is in absolute trusted compute.

## Use

```python
import assurance_curves as ac

ac.p_detected_exact(c=0.01, n_fake=460)            # 0.990...
ac.min_fake_packets_exact(0.01, 0.99)              # 459  (Poisson form says 460.5)
ac.required_budget(n_fake=1000, confidence=0.999999)  # budget to catch 1,000 fakes at six nines
ac.p_detected_hypergeometric(10**9, 1000, 10**6)   # audit exactly 1e6 of 1e9, without replacement

m = ac.RogueDeploymentModel(budget=0.01, packet_size=100.0)   # 100 H100e-hour packets
m.hours_to_detect(10_000, 0.99)                    # 4.58 h for a 10K H100e rogue deployment
ac.assurance_curve(n_verified=1e6).as_rows()       # coverage / confidence / nines

# streaming: keep looking after every packet without inflating the false-alarm rate
e = ac.BernoulliMixtureEProcess(p0=1e-4)
e.update(n=10**6, k=180)
e.rejects(alpha=1e-6)                              # True once evidence crosses 1/alpha
ac.e_bh(e_values_of_many_clusters, alpha=0.05)     # FDR control across clusters, any dependence
```

CLI: `assurance-curves rogue --budget 0.01 --packet-size 100 --size 10000 --hours 1 --pool 33e9`
(also `detect`, `budget`, `min-fake`, `granularity`, `false-alarm`, `canary`; JSON on stdout).

## What is in it

| module | what it gives you |
| --- | --- |
| `core` | exact `(1-c)^n`, Poisson form, hypergeometric (audit exactly n), inverses, nines |
| `curves` | assurance curves in the tolerated-fraction parameterisation (avoids `1 - coverage` cancellation at 8 nines) |
| `rogue` | rogue-deployment detection time, tap-granularity table (per-server / per-shelf / per-GPU), recompute-capacity cost |
| `falsealarm` | per-packet false-flag rate that a year of audits can tolerate; honest packets needed to certify it |
| `sequential` | mixture e-process for a stream of flags (Ville-valid at every step); e-BH across clusters |
| `canary` | how many known-bad packets prove a recomputation server is not suppressing alarms |

## How it was verified

* Exact and Poisson forms against `scipy.stats.binom`; hypergeometric against `scipy.stats.hypergeom` and against
  60-digit `mpmath` at N from 30 to 1e15 (13 cases, relative error <= 1e-12).
* Monte-Carlo of the audit itself (12,000 to 40,000 trials per case, 5-sigma bands): independent sampling, fixed-count sampling,
  and a demonstration that the Poisson form falls outside the band when the budget is large.
* Property tests (Hypothesis): Poisson <= exact; monotone in fakes and budget; sampling without replacement never
  worse than with; hypergeometric symmetry in (audited, fake); `min_fake_packets_exact` is minimal.
* e-process: martingale property checked *exactly* by summing over every binomial outcome (`E[E_n] = 1` to 1e-9);
  type-I error over 1,000 looks per stream (3,000 streams) stays under alpha while a z-test that peeks after every
  packet blows through it; e-BH FDR checked over 600 replications against the `alpha * m0 / m` guarantee.
* Console script and clean-venv wheel install exercised.

Defects found along the way, including two in the tests and one real precision bug in the library, are in
[`VERIFICATION_LOG.md`](VERIFICATION_LOG.md).

## Limits, stated plainly

* Appendix A's own assumptions carry over: uniform packets, independent random sampling, **perfectly reproducible
  packets**. Nothing here helps make packets reproducible.
* Packet counts are real-valued ("fluid"). Rogue-deployment times are means of a continuous approximation.
* The e-process is exactly valid only if honest flags are i.i.d. Bernoulli(`p0`) with `p0` known. It does not estimate
  `p0`. Drift, bursts or hardware-correlated flags break the guarantee, and a `p0` set too low produces false alarms.
* `gaussian_threshold_sigma` assumes a Gaussian honest tail; real nondeterminism tails are usually heavier, which makes
  the true threshold higher for the same rate.
* Canary audits assume the server cannot tell a canary from a real fake. If it can, they prove nothing.
* No recomputation happens here and no model is involved. This is the statistics layer only.
* The code and tests share an author and have had no external review. The references above are independent of the
  library's code, not of its author's assumptions.

## References

Romeo Dean, *Verification Plan*, AI 2040: Plan A (2026), Appendix A. Rinberg et al. (2025), arXiv:2511.02620, which the
appendix says matches its detection math. Karvonen et al. (2025), *DiFR*, arXiv:2511.20621. Wang & Ramdas (2022),
*False discovery rate control with e-values*, JRSSB (e-BH).

## License

Apache-2.0. Copyright 2026 AnonRish.
