# Verification log

Every defect found while building and testing this repository, including ones in
the tests themselves, in the order they were found. Nothing here was fixed quietly.

## 1. Test expectation off by 1000x (found by the test failing; library was correct)

`test_2034_scale_false_alarm_budget` asserted 2.8908e13 audited packets per year for the
supplement's 2034 example (33e9 H100e pool x 1 % budget x 8760 h / 100 H100e-hours per packet).
The library returned 2.8908e10. The library was right: 33e9 x 0.01 x 8760 / 100 = 28,908,000,000.
Confirmed independently with exact rational arithmetic (`fractions.Fraction`) and 60-digit
`mpmath`, sharing no code with the library.

Three further claims in that draft test were wrong for the same reason and were corrected:

| Claim in the draft test | Correct value |
| --- | --- |
| threshold about 7.4 sigma | 6.5224 sigma |
| honest packets to certify the rate: 8.66e13 | 8.66e10 |
| certification needs "more than 1000x" the entire 2029 world stock recomputed for a year | 3.42x |

The last one is now pinned as an exact identity instead of a loose inequality: certifying a
false-flag rate equal to one spurious alarm per year at delta = 5 % requires `ln(20) = 2.9957`
years of audited throughput, and the test asserts `need / n_per_year == ln(20)`.

## 2. Unmeasured error-order claim in a docstring

`p_detected_hypergeometric` said its large-N midpoint branch had relative error
`O((n/N)^2 F/N)`. That was written from intuition and never checked. It has been replaced by
measurements against 60-digit log-gamma: worst observed relative error 6.7e-7 (at n/N = 0.2),
below 1e-8 for n/N <= 1e-4. No closed-form bound is claimed. The measurements are pinned in
`tests/test_core.py::test_midpoint_branch_error_is_measured`.

## 3. Hypergeometric detection lost precision at scale (real library bug, found by a 60-digit cross-check)

The first `p_detected_hypergeometric` took a difference of four `lgamma` values below N = 2e9 and
used a midpoint approximation above. The 2e9 switch-over was chosen by intuition, not measurement.
Measured against 60-digit `mpmath.loggamma` at moderate detection probability (where exponent error
shows up as relative error in the answer):

| N | F | n | P(detect) | old relative error |
| --- | --- | --- | --- | --- |
| 1e6 | 100 | 5e3 | 0.394 | 6.8e-10 |
| 1e8 | 100 | 1e5 | 0.0952 | 3.5e-6 |
| 1e9 | 1e3 | 1e6 | 0.632 | 1.6e-6 |
| 1.9e9 | 100 | 1e6 | 0.0513 | 9.3e-5 |
| 5e9 | 50 | 1e9 | 0.99999 | 6.7e-7 |

Cause: each `lgamma(N)` is about N ln N ~ 4e10 and carries ~1e-16 relative error, so the exponent has
absolute error ~4e-6 no matter how small n and F are. The plan lives in exactly this regime (billions of
packets, tens to hundreds of fakes).

Fix: `C(N-F, n)/C(N, n) = prod_{i<n}(1 - F/(N-i))`, which by hypergeometric symmetry also equals the same
product with n and F swapped, so the shorter one (at most 2e6 terms) is summed exactly with `log1p`.
No `lgamma` remains. Above that (both n and F > 2e6, unsaturated, so N >= 1e11) a two-term midpoint
expansion runs. Result: relative error <= 1e-12 on every case in `tests/test_core.py::_HG_CASES` (13 cases
from N = 30 to N = 1e15) and <= 1e-15 in the midpoint regime, all against 60-digit references. The
symmetry `P(N, F, n) == P(N, n, F)` is now also a property test.

## 4. My own error bound for the midpoint rule was wrong (found by a forced small-scale test)

While replacing the old branch I wrote that the midpoint rule's error was at most about
`(nF/N)/(12 N^2)`. A test that forces the branch at N = 1e6, F = n = 1e3 failed: observed error in the exponent
8.35e-8 against a claimed <= 4e-12. The derivation had dropped a factor: the central-sum correction is
`g''(m) n (n^2 - 1)/24`, not `n g''(m)/24`, giving `F n^3 / (12 N^3)` = 8.33e-8 for that case (matches the
observation). The branch now includes the second-order term, and the docstring states the first omitted
term (`(nF/N)(n/N)^4/80`), pinned by
`test_midpoint_expansion_error_matches_the_first_omitted_term_when_forced_at_small_scale`.

## 5. Overlap with the existing `AnonRish/fides` repo (`src/fides/security.py`), measured

`fides/security.py` already has the two basic formulas: an exact hypergeometric `detection_probability(n, k, m)`
(`1 - comb(n-k, m) / comb(n, m)`) and the Poisson form. This repository does not claim them as new. Compared on the same inputs
against 60-digit `mpmath.loggamma` (timeout 30 s per call):

| N packets | F fake | m audited | fides exact: time, rel. error | assurance-curves: time, rel. error |
| --- | --- | --- | --- | --- |
| 1e5 | 100 | 1e3 | 0.00 s, 1.1e-16 | < 1 ms, 1.1e-16 |
| 1e7 | 100 | 1e4 | 0.03 s, 5.6e-16 | < 1 ms, 1.9e-17 |
| 1e8 | 100 | 1e5 | 1.11 s, 1.7e-16 | < 1 ms, 1.3e-16 |
| 1e9 | 1,000 | 1e6 | timeout | < 1 ms, 2.3e-17 |
| 2.89e10 | 460 | 2.89e8 | timeout | < 1 ms, 4.0e-17 |
| 1e12 | 1e4 | 1e7 | timeout | < 1 ms, 4.0e-17 |

So the fides formula is correct wherever it finishes (big-integer binomials are exact) but its cost grows with the size of
`comb(n, m)`; it does not finish at the scale of the supplement's own 2034 example (2.89e10 audited packets a year). Both
implementations agree to about 1e-16 where both run, which is independent evidence for each. This repository additionally
uses Python big-integer arithmetic as an exact oracle in its tests (`test_hypergeometric_matches_exact_integer_arithmetic*`).
What is new here beyond those two formulas: numerically stable evaluation at any scale, inverses (`required_budget`,
`min_fake_packets_exact`), assurance curves, the tap-granularity table, false-alarm budgets, anytime-valid sequential
monitoring with e-BH, and canary audits. `fides.security.repeated_detection_probability` (compounding over epochs) has no
counterpart here.

## Observations about the source material (not defects in this repository)

* The supplement's 2034 example fixes a recomputation *budget* of 1 % of a ~33 B H100e pool.
  In absolute terms that is 330 M H100e of trusted recompute capacity, more than the entire
  289 M H100e world stock the same supplement declares for 2029 (224 M US + 26 M China + 39 M rest of world).
  The detection maths is unaffected; the bill is worth stating. `RogueDeploymentModel.recompute_capacity_h100e`.
* The appendix prices detection only. It says nothing about false flags, which at that scale
  must be below roughly 3.5e-11 per packet to keep spurious alarms to one a year (`falsealarm.py`).
