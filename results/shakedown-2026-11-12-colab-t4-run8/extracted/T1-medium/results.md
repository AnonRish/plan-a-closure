# Closure report (HARDWARE (NVML energy counter; spoofable))

Status **HARDWARE (NVML energy counter; spoofable)**. A SIMULATED report validates the estimators only; only a HARDWARE report with a DC-bus channel supports physical claims.

## Headline
- False-positive rate on null blocks (combined, alpha=0.01): 0/204 (95% upper bound 1.458%).
- Closure gap (smallest hidden-energy fraction of cluster capacity detected >=95% of the time, non-slack classes, combined channels): 17.78%.
- Implied hidden compute at that gap, one week: 3.71e+18 FLOP (1.04 H100-hours, energy floor 2.03e-12 J/FLOP, source: measured by hw-probe (HARDWARE-PROBE (NVML energy counter; spoofable)), sha256 e823a6f861246687).
- Hidden-energy upper bound coverage (non-slack): 100.00%; slack class (expected to evade): n/a.
- Efficiency slack (pre-registered H1.6): s_max = 10.78% of verified-work power (measured by hw-probe (HARDWARE-PROBE (NVML energy counter; spoofable)), sha256 e823a6f861246687); slack-inflated gap = 25.89% (closure gap + s_max x 75.26% mean predicted share of capacity).

## Pooled f95 by channel (fraction of cluster capacity)
- energy: 17.78%
- busy: 17.78%
- combined: 17.78%

## Detection rate by class and intensity (combined)

| class | 0.02 | 0.05 | 0.1 | 0.2 |
| --- | --- | --- | --- | --- |
| constant | 0.50 (n=6) | 0.83 (n=6) | 1.00 (n=6) | 1.00 (n=6) |
| idle_gap | 1.00 (n=1) | n/a | n/a | n/a |
| duty | 0.00 (n=6) | 0.83 (n=6) | 1.00 (n=6) | 1.00 (n=6) |
| dilute | 0.50 (n=6) | 0.83 (n=6) | 1.00 (n=6) | 1.00 (n=6) |

## Pre-registered T1 decision rules, read at this run's scale
- scope: shakedown reading: NVML only, so assumption A6 does not hold; what these data would decide, not a Plan A claim
- H1.1 calibration valid (the threshold is conformal: no distribution assumed, at least 1/alpha - 1 effective reference blocks): holds (threshold: conformal; reported only: energy: Jarque-Bera p 4.1e-05, n_eff 150.0; busy: Jarque-Bera p 4e-42, n_eff 150.0)
- H1.2 false alarms (at most 3 x alpha = 3.0% on at least 200 null blocks): holds: 0/204 (95% upper bound 1.5%)
- H1.3 primary: detection >= 95% at hidden fraction >= 5%, per class (decided once a class has 8 such blocks): constant 17/18 fails; idle_gap 0/0 not decided; duty 9/9 holds; dilute 17/18 fails. Pooled over classes: 43/45, 95% lower bound 86.7% (not certified at 95%)
- H1.3 stretch: detection >= 95% at hidden fraction >= 2%, per class (decided once a class has 8 such blocks): constant 20/24 fails; idle_gap 1/1 not decided; duty 17/18 fails; dilute 20/24 fails. Pooled over classes: 58/67, 95% lower bound 77.7% (not certified at 95%)
- H1.4 the time bound covers the seconds the hidden load really ran in at least 95% of non-slack hidden blocks: holds (100.0% of 73, by the floor bound: busy time above the least the verified work can take). Reported only, as checks on additivity (A1): the calibrated time bound covers 100.0%; the energy bound covers the hidden load's solo energy in 100.0% (calibrated) and 100.0% (floor)
- outcome: **FAIL** (slack-inflated gap 25.9% is above 5%); closure gap 17.78%, slack-inflated 25.89%

## Assumptions (a failed assumption voids the claim)
- A1 additivity: hidden work adds energy/busy-time on top of verified work (no free lunch from sharing).
- A2 exchangeability: calibration and audit blocks come from the same regime mix (same stack, clocks, cooling, firmware).
- A3 approximate normality of block residual sums, checked by the Jarque-Bera diagnostic stored with the calibration.
- A4 no efficiency slack: the adversary is no more energy-efficient than the calibration reference (the 'slack' class tests this and is expected to evade).
- A5 the verified-work features are trustworthy (they come from the tap/recompute evidence, not from the prover).
- A6 the power meter is independent of the prover (DC-bus instrument); NVML-only runs are labelled as spoofable.
