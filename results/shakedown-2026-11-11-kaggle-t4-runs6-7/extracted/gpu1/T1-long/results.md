# Closure report (HARDWARE (NVML energy counter; spoofable))

Status **HARDWARE (NVML energy counter; spoofable)**. A SIMULATED report validates the estimators only; only a HARDWARE report with a DC-bus channel supports physical claims.

## Headline
- False-positive rate on null blocks (combined, alpha=0.01): 0/204 (95% upper bound 1.458%).
- Closure gap (smallest hidden-energy fraction of cluster capacity detected >=95% of the time, non-slack classes, combined channels): 5.62%.
- Implied hidden compute at that gap, one week: 1.11e+18 FLOP (0.313 H100-hours, energy floor 2.14e-12 J/FLOP, source: measured by hw-probe (HARDWARE-PROBE (NVML energy counter; spoofable)), sha256 5db96ed13113204c).
- Hidden-energy upper bound coverage (non-slack): 98.14%; slack class (expected to evade): n/a.
- Efficiency slack (pre-registered H1.6): s_max = 8.39% of verified-work power (measured by hw-probe (HARDWARE-PROBE (NVML energy counter; spoofable)), sha256 5db96ed13113204c); slack-inflated gap = 11.73% (closure gap + s_max x 72.76% mean predicted share of capacity).

## Pooled f95 by channel (fraction of cluster capacity)
- energy: 31.62%
- busy: 5.62%
- combined: 5.62%

## Detection rate by class and intensity (combined)

| class | 0.02 | 0.05 | 0.1 | 0.2 |
| --- | --- | --- | --- | --- |
| constant | 0.83 (n=12) | 1.00 (n=12) | 1.00 (n=12) | 1.00 (n=12) |
| idle_gap | 1.00 (n=5) | 1.00 (n=4) | 1.00 (n=3) | 1.00 (n=5) |
| duty | 0.50 (n=12) | 1.00 (n=12) | 1.00 (n=12) | 1.00 (n=12) |
| dilute | 0.92 (n=12) | 1.00 (n=12) | 1.00 (n=12) | 1.00 (n=12) |

## Pre-registered T1 decision rules, read at this run's scale
- scope: shakedown reading: NVML only, so assumption A6 does not hold; what these data would decide, not a Plan A claim
- H1.1 calibration valid (the threshold is conformal: no distribution assumed, at least 1/alpha - 1 effective reference blocks): holds (threshold: conformal; reported only: energy: Jarque-Bera p 8.1e-10, n_eff 144.0; busy: Jarque-Bera p 8.5e-05, n_eff 144.0)
- H1.2 false alarms (at most 3 x alpha = 3.0% on at least 200 null blocks): holds: 0/204 (95% upper bound 1.5%)
- H1.3 primary: detection >= 95% at hidden fraction >= 5%, per class (decided once a class has 8 such blocks): constant 36/36 holds; idle_gap 9/9 holds; duty 24/24 holds; dilute 36/36 holds. Pooled over classes: 105/105, 95% lower bound 97.2% (certified at 95%)
- H1.3 stretch: detection >= 95% at hidden fraction >= 2%, per class (decided once a class has 8 such blocks): constant 46/48 holds; idle_gap 13/13 holds; duty 36/36 holds; dilute 47/48 holds. Pooled over classes: 142/145, 95% lower bound 94.7% (not certified at 95%)
- H1.4 the time bound covers the seconds the hidden load really ran in at least 95% of non-slack hidden blocks: holds (100.0% of 161, by the floor bound: busy time above the least the verified work can take). Reported only, as checks on additivity (A1): the calibrated time bound covers 98.1%; the energy bound covers the hidden load's solo energy in 98.1% (calibrated) and 100.0% (floor)
- outcome: **FAIL** (slack-inflated gap 11.7% is above 5%); closure gap 5.62%, slack-inflated 11.73%

## Assumptions (a failed assumption voids the claim)
- A1 additivity: hidden work adds energy/busy-time on top of verified work (no free lunch from sharing).
- A2 exchangeability: calibration and audit blocks come from the same regime mix (same stack, clocks, cooling, firmware).
- A3 approximate normality of block residual sums, checked by the Jarque-Bera diagnostic stored with the calibration.
- A4 no efficiency slack: the adversary is no more energy-efficient than the calibration reference (the 'slack' class tests this and is expected to evade).
- A5 the verified-work features are trustworthy (they come from the tap/recompute evidence, not from the prover).
- A6 the power meter is independent of the prover (DC-bus instrument); NVML-only runs are labelled as spoofable.
