# Model

## Units

One H100e is 15,800 TPP (the plan's definition). A chip counts as AI-relevant only if it clears all four floors: 4,000
TPP, 1.0 TB/s memory bandwidth, 32 GB memory, 100 Gb/s networking (set just below an A100). An RTX 4090 clears compute
and bandwidth and fails capacity and networking, which is how the plan excludes it.

## Roll-forward

`S(t+1) = f * S(t) + P(t)` with `f = 2^(-1/h)` for a survival half-life `h` years (`f = 1` for none): the opening stock
decays over the year and the year's production is added in full. `implied_survival` inverts one step to give the `f`
that makes it exact.

## Reproduction tolerances

A check passes when `|computed - published| <= tol`. `tol` is the worst-case rounding of the published inputs carried
through the arithmetic. For the world stock: half a unit in the last printed digit (0.05M) times the sum of the
survival factors each input passes through, plus the published figure's own rounding, plus 0.2M because "15 years" is
itself approximate. For a percentage: half a unit in its last printed decimal plus the rounding of the published
H100e figure over the denominator. For the eight-part location sum: the root-sum-square of the parts' rounding. A
check marked `expect_match = False` passes only when the value does not match (the running-sum convention).

## Reconciliation

Declared `D` (exact), true `T = D + H`, `H >= 0`. Independent estimate `E ~ Normal(T, s^2)` with `s` from the stated
central interval: `s = (hi - lo) / (2 * z)` where `z` is the standard-normal quantile at `0.5 + level/2`.
Posterior: `p(H | E) ~ p(H) * Normal(E; D + H, s^2)` on a grid of 40,001 points from 0 to `max(E - D, 0) + 12 s`
(wider if the prior has a longer tail), integrated by the trapezoid rule in log-weight form so that an estimate far
below the declaration cannot underflow. Closed forms used as test references:

* flat prior: `Normal(E - D, s^2)` truncated at 0;
* half-normal prior with scale `tau`: `Normal(mu', sd'^2)` truncated at 0 with `1/sd'^2 = 1/tau^2 + 1/s^2` and
  `mu' = (E - D) * sd'^2 / s^2`.

`consistency` reports `z = (E - D)/s` and `P(estimate this high | declaration complete) = 1 - Phi(z)`.
Sums over owners are Monte Carlo from the exact posteriors with a seeded generator.

## Two-piece lognormal

For a hidden-compute prior given as three quantiles: `Q(p) = p50 * exp(sigma * z_p)` with `sigma_lo` below the median and
`sigma_hi` above, `sigma_lo = ln(p50/p10)/z90`, `sigma_hi = ln(p90/p50)/z90`. Both halves carry probability 1/2, so all
three quantiles are exact (a lognormal cannot match a skewed interval's endpoints and median together). The density
jumps at the median. Mean: `p50 * (exp(sigma_lo^2/2) Phi(-sigma_lo) + exp(sigma_hi^2/2) Phi(sigma_hi))`.

## Ledger invariants

Balances are non-negative; `total = opening + produced - retired`; a transfer changes no total; failed events change
nothing; a ledger is determined by its opening position and event history.
