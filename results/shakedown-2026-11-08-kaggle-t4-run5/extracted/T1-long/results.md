# Closure report (HARDWARE (NVML energy counter; spoofable))

Status **HARDWARE (NVML energy counter; spoofable)**. A SIMULATED report validates the estimators only; only a HARDWARE report with a DC-bus channel supports physical claims.

## Headline
- False-positive rate on null blocks (combined, alpha=0.01): 11/204 (95% upper bound 8.767%).
- Closure gap (smallest hidden-energy fraction of cluster capacity detected >=95% of the time, non-slack classes, combined channels): 17.78%.
- Implied hidden compute at that gap, one week: 3.65e+18 FLOP (1.03 H100-hours, energy floor 2.06e-12 J/FLOP, source: measured by hw-probe (HARDWARE-PROBE (NVML energy counter; spoofable)), sha256 53b5268b296ef60d).
- Hidden-energy upper bound coverage (non-slack): 100.00%; slack class (expected to evade): n/a.
- Efficiency slack (pre-registered H1.6): s_max = 9.63% of verified-work power (measured by hw-probe (HARDWARE-PROBE (NVML energy counter; spoofable)), sha256 53b5268b296ef60d); slack-inflated gap = 24.85% (closure gap + s_max x 73.40% mean predicted share of capacity).

## Pooled f95 by channel (fraction of cluster capacity)
- energy: 17.78%
- busy: 17.78%
- combined: 17.78%

## Detection rate by class and intensity (combined)

| class | 0.02 | 0.05 | 0.1 | 0.2 |
| --- | --- | --- | --- | --- |
| constant | 0.17 (n=12) | 0.92 (n=12) | 1.00 (n=12) | 1.00 (n=12) |
| idle_gap | 0.00 (n=4) | 0.20 (n=5) | 0.83 (n=6) | 0.67 (n=3) |
| duty | 0.17 (n=12) | 0.08 (n=12) | 0.83 (n=12) | 1.00 (n=12) |
| dilute | 0.08 (n=12) | 1.00 (n=12) | 1.00 (n=12) | 1.00 (n=12) |

## Pre-registered T1 decision rules, read at this run's scale
- scope: shakedown reading: NVML only, so assumption A6 does not hold; what these data would decide, not a Plan A claim
- H1.1 calibration valid (Jarque-Bera p >= 0.01 and n_eff >= 15 in every regime): fails (energy: Jarque-Bera p 3e-10, n_eff 105.3; busy: Jarque-Bera p 1.7e-07, n_eff 100.8)
- H1.2 false alarms (at most 3 x alpha = 3.0% on at least 200 null blocks): fails: 11/204 (95% upper bound 8.8%)
- H1.3 primary: detection >= 95% at hidden fraction >= 5%, per class (decided once a class has 8 such blocks): constant 35/36 holds; idle_gap 6/6 not decided; duty 22/24 fails; dilute 36/36 holds. Pooled over classes: 99/102, 95% lower bound 92.6% (not certified at 95%)
- H1.3 stretch: detection >= 95% at hidden fraction >= 2%, per class (decided once a class has 8 such blocks): constant 37/48 fails; idle_gap 8/13 fails; duty 23/36 fails; dilute 37/48 fails. Pooled over classes: 105/145, 95% lower bound 65.7% (not certified at 95%)
- H1.4 hidden-energy bound covers at least 95% of non-slack hidden blocks (against the hidden energy recorded; on hardware, what the load was set to inject): holds (100.0%)
- outcome: **UNDERPOWERED** (H1.1 fails, so no false-alarm claim is made); closure gap 17.78%, slack-inflated 24.85%

## Assumptions (a failed assumption voids the claim)
- A1 additivity: hidden work adds energy/busy-time on top of verified work (no free lunch from sharing).
- A2 exchangeability: calibration and audit blocks come from the same regime mix (same stack, clocks, cooling, firmware).
- A3 approximate normality of block residual sums, checked by the Jarque-Bera diagnostic stored with the calibration.
- A4 no efficiency slack: the adversary is no more energy-efficient than the calibration reference (the 'slack' class tests this and is expected to evade).
- A5 the verified-work features are trustworthy (they come from the tap/recompute evidence, not from the prover).
- A6 the power meter is independent of the prover (DC-bus instrument); NVML-only runs are labelled as spoofable.
