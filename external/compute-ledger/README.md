# compute-ledger

Chip-stock accounting and declared-versus-estimated reconciliation with uncertainty, checked against the compute
figures in the AI 2040 "Plan A" supplements.

The plan's verification regime starts with parties declaring how much AI compute they hold, in H100-equivalents
(H100e), and the plan puts the world total at 289M H100e on 1 January 2029 and the compute a diversion effort could
hide at about 0.5% of it. Two things are needed to work with those numbers: accounting that conserves chips, and a
way to say how much an independent estimate allows to be undeclared. This repository has both, and a command that
re-derives the plan's headline figures from their own inputs so the arithmetic can be checked.

```bash
pip install -e ".[dev]"
compute-ledger plan-a                       # 35 checks of the plan's figures against their inputs; exit 1 on any failure
compute-ledger roll --stock0 8.6M --production 14.2M,35.7M,80.6M,159.7M --half-life 15
compute-ledger reconcile --declared 224M --lo 222M --hi 226M --exceeds 4M
compute-ledger ledger accounts.json         # replay a ledger file and check conservation
python -m pytest                            # 87 tests
python tools/mutation_check.py              # 26 injected bugs, all caught
```

## What it reproduces

Real output of `compute-ledger plan-a` (excerpt):

```
ok   world stock, Jan 1 2029, from 2025-28 production with a 15-year half-life            computed 288.72M    published 289.00M    tolerance 0.48M
ok   same, as a pure running sum (no retirement)                                          computed 298.80M    published 289.00M    tolerance 0.48M
ok   US stock from the 85/15 rule                                                         computed 223.63M    published 224.00M    tolerance 0.60M
ok   datacenter bins + in-transit + AI consumer = world stock                             computed 288.94M    published 289.00M    tolerance 1.12M
ok   hidden compute: median / world stock (%)                                             computed 0.519%     published 0.500%     tolerance 0.050%
```

| figure | how it is re-derived | result |
| --- | --- | --- |
| 289M world stock | 8.6M Jan-2025 stock rolled forward through 14.2M, 35.7M, 80.6M, 159.7M of production with a 15-year survival half-life | 288.72M (tolerance 0.48M, from the rounding of the inputs plus the approximate half-life) |
| 224M / 26M / 39M by owner | China's 25.9M from its four-channel build-up; the rest of the 289.0M split 85/15 between the US and the rest of the world | 223.63M / 25.90M / 39.47M; shares 77.4% / 9.0% / 13.7% against 77 / 9 / 14 |
| compute by datacenter size | six size bins, in-transit and AI-consumer compute against the 289M denominator | every published share within rounding; the parts sum to 288.94M |
| about 2,850 datacenters | sum of the six bins' site counts | 2,852 |
| 0.5% hidden | median 1.5M H100e over the 289M stock | 0.519%, which is the "about 0.5%" |
| about 4M at the top of the 80% interval | 1.4% of 289M | 4.05M; the lower end, 0.1%, is 0.29M |
| H100e units | 15,800 TPP per H100e; the 4,000 TPP AI-relevance floor; a B200 | 0.253, "about 0.25"; 2.28, "about 2.3" |

Tolerances come from the rounding of the published inputs, propagated through the arithmetic, never from the size of
the result. Eight negative controls change one input at a time and require at least one check to fail.

## A finding about the plan's own numbers

The published world stock series (8.6M, 22.4M, 57.1M, 135.2M, 289.0M against 14.2M, 35.7M, 80.6M, 159.7M of
production) is **not a running sum of production**: a running sum gives 298.8M, 3.4% too high. It follows
`S(t+1) = f*S(t) + P(t)` with `f = 2^(-1/15)` (a 15-year half-life): the survival factor implied by each of the four
published steps is 0.9535, 0.9554, 0.9562 and 0.9564 against 0.9548. As I read the supplement, one passage describes
the fleet as cumulative with no retirement while a footnote gives the 15-year half-life; the numbers follow the
footnote. China's much shorter series (1.3M to 25.9M) is consistent with a plain running sum within rounding, which a
half-life that slow cannot distinguish.

## How much could be undeclared?

An owner declares a stock `D` (audited, taken as exact). An independent party estimates the true stock from outside and
states a central interval, say 80%, which fixes a Gaussian error `s`. The true stock is `D + H` with `H >= 0`
undeclared, and Bayes' rule with a prior on `H` gives the posterior of `H`, computed on a fine grid so every number is
deterministic. With a flat prior it is a truncated normal; the tests compare the grid against scipy's.

```
$ compute-ledger reconcile --declared 224M --lo 222M --hi 226M --exceeds 1.5M --exceeds 4M
declared 224.00M; independent estimate 222.00M to 226.00M (80% interval, sigma 1.56M)
estimate centre is 0.00 sigma above the declaration; chance of an estimate this high if the declaration is complete: 0.500
undeclared stock, posterior: median 1.05M, mean 1.25M, 10%-90% 0.20M to 2.57M, 99% 4.02M
as a share of the declared stock: median 0.47%, 90th percentile 1.15%
P(undeclared > 1.50M) = 0.336
P(undeclared > 4.00M) = 0.010
```

Those two intervals (222M to 226M for the US as seen from China; 25M to 27M for China as seen from the US) are the
plan's 2028 uncertainty bands as I read them earlier in the working session; that page was not re-fetched when the data
file was written (`provenance` in `src/compute_ledger/data/plan_a_2029.json`), so check them before citing. With them
the undeclared stock has a median of about 1.05M for the US and 0.53M for China. That is a scale check, not a
reproduction: the plan's 1.5M median and 4M upper figure describe the size of a covert diversion project from a different
model, which this repository does not contain. The prior is a parameter (`flat`, `halfnormal:TAU`, or `fitted:P10,P50,P90`
using a quantile-matched two-piece lognormal that reproduces the plan's 0.1%, 0.5% and 1.4% points exactly).

## The ledger

`compute_ledger.ledger.Ledger` keeps balances by `(owner, category)` and changes them only through posted events:
`produce`, `retire`, `transfer`. Events are atomic (an overdraw raises and leaves the ledger untouched; `post_all` is all
or nothing), a transfer never changes the total, and `total == opening + produced - retired` always holds (a stateful
hypothesis test runs random event sequences against it). A ledger serialises to its opening position and event history,
reloads by replay, and has a SHA-256 `digest()` that changes if any event is altered, reordered or appended.

## Inputs and provenance

Every plan number is in `src/compute_ledger/data/plan_a_2029.json` with its source and how well it was checked:

* the compute supplement was fetched and read in full on 2026-10-04 (world series, China build-up, ownership rule, size
  bins, TPP definitions): the main source;
* the hidden-compute median and 0.1% to 1.4% interval come from a public comment quoting the covert-projects
  supplement, which I did not open: secondary;
* the 2028 uncertainty bands were read from the verification plan earlier and not re-fetched.

Numbers only are transcribed; no text is reproduced.

## Limits

* The reconciliation model is mine: a standard Bayesian update with Gaussian measurement error and independent
  owners. It is not the plan's model, and the plan's covert-project figure is an input here, not an output.
* The flat prior is improper (the posterior is proper); real priors on hiding are a modelling choice this repository
  cannot settle. Estimate errors are assumed Gaussian and unbiased.
* No chip-tracking data of any kind is used: the stock figures are the plan's projections for 2029, not observations.
* The ownership split is only as good as the plan's 85/15 rule; the repository checks the arithmetic, not the rule.
* Units beyond the plan's own (H100e = 15,800 TPP, four AI-relevance floors) are not modelled.

## Overlap with existing repositories

Nothing found. `ai-2040-verification/undeclared_compute.py` is adjacent (fab concentration and satellite detectability
of covert datacenters) but contains no stock accounting or reconciliation. The similarly named `verification-ledger` is a
tracker of verification R&D projects and shares only a word.

## Layout

`src/compute_ledger/` (`ledger`, `stock`, `units`, `distributions`, `reconcile`, `planA`, `cli`, `data/`) ·
`tests/` · `tools/mutation_check.py` · `docs/MODEL.md` · `VERIFICATION_LOG.md`.

Apache-2.0, copyright AnonRish.
