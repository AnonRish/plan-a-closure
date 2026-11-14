# Closure report (HARDWARE (NVML energy counter; spoofable))

Status **HARDWARE (NVML energy counter; spoofable)**. A SIMULATED report validates the estimators only; only a HARDWARE report with a DC-bus channel supports physical claims.

## Headline
- False-positive rate on null blocks (combined, alpha=0.01): 3/204 (95% upper bound 3.757%).
- Closure gap (smallest hidden-energy fraction of cluster capacity detected >=95% of the time, non-slack classes, combined channels): 5.62%.
- Implied hidden compute at that gap, one week: 1.11e+18 FLOP (0.311 H100-hours, energy floor 2.15e-12 J/FLOP, source: measured by hw-probe (HARDWARE-PROBE (NVML energy counter; spoofable)), sha256 ebfc67d0e8dfc30b).
- Hidden-energy upper bound coverage (non-slack): 96.88%; slack class (expected to evade): n/a.
- Efficiency slack (pre-registered H1.6): s_max = 9.10% of verified-work power (measured by hw-probe (HARDWARE-PROBE (NVML energy counter; spoofable)), sha256 ebfc67d0e8dfc30b); slack-inflated gap = 12.27% (closure gap + s_max x 73.12% mean predicted share of capacity).

## Pooled f95 by channel (fraction of cluster capacity)
- energy: 17.78%
- busy: 5.62%
- combined: 5.62%

## Detection rate by class and intensity (combined)

| class | 0.02 | 0.05 | 0.1 | 0.2 |
| --- | --- | --- | --- | --- |
| constant | 0.83 (n=12) | 1.00 (n=12) | 1.00 (n=12) | 1.00 (n=12) |
| idle_gap | 0.60 (n=5) | 1.00 (n=2) | 1.00 (n=6) | 1.00 (n=3) |
| duty | 1.00 (n=12) | 1.00 (n=12) | 1.00 (n=12) | 1.00 (n=12) |
| dilute | 1.00 (n=12) | 1.00 (n=12) | 1.00 (n=12) | 1.00 (n=12) |

## Pre-registered T1 decision rules, read at this run's scale
- scope: shakedown reading: NVML only, so assumption A6 does not hold; what these data would decide, not a Plan A claim
- H1.1 calibration valid (the threshold is conformal: no distribution assumed, at least 1/alpha - 1 effective reference blocks): holds (threshold: conformal; reported only: energy: Jarque-Bera p 5.3e-09, n_eff 144.0; busy: Jarque-Bera p 0, n_eff 144.0)
- H1.2 false alarms (at most 3 x alpha = 3.0% on at least 200 null blocks): holds: 3/204 (95% upper bound 3.8%)
- H1.3 primary: detection >= 95% at hidden fraction >= 5%, per class (decided once a class has 8 such blocks): constant 36/36 holds; idle_gap 9/9 holds; duty 24/24 holds; dilute 36/36 holds. Pooled over classes: 105/105, 95% lower bound 97.2% (certified at 95%)
- H1.3 stretch: detection >= 95% at hidden fraction >= 2%, per class (decided once a class has 8 such blocks): constant 46/48 holds; idle_gap 13/13 holds; duty 36/36 holds; dilute 48/48 holds. Pooled over classes: 143/145, 95% lower bound 95.7% (certified at 95%)
- H1.4 the time bound covers the seconds the hidden load really ran in at least 95% of non-slack hidden blocks: holds (100.0% of 160, by the floor bound: busy time above the least the verified work can take). Reported only, as checks on additivity (A1): the calibrated time bound covers 100.0%; the energy bound covers the hidden load's solo energy in 96.9% (calibrated) and 100.0% (floor)
- outcome: **FAIL** (slack-inflated gap 12.3% is above 5%); closure gap 5.62%, slack-inflated 12.27%

## Assumptions (a failed assumption voids the claim)
- A1 additivity: hidden work adds energy/busy-time on top of verified work (no free lunch from sharing).
- A2 exchangeability: calibration and audit blocks come from the same regime mix (same stack, clocks, cooling, firmware).
- A3 approximate normality of block residual sums, checked by the Jarque-Bera diagnostic stored with the calibration.
- A4 no efficiency slack: the adversary is no more energy-efficient than the calibration reference (the 'slack' class tests this and is expected to evade).
- A5 the verified-work features are trustworthy (they come from the tap/recompute evidence, not from the prover).
- A6 the power meter is independent of the prover (DC-bus instrument); NVML-only runs are labelled as spoofable.
