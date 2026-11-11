# Closure report (HARDWARE (NVML energy counter; spoofable))

Status **HARDWARE (NVML energy counter; spoofable)**. A SIMULATED report validates the estimators only; only a HARDWARE report with a DC-bus channel supports physical claims.

## Headline
- False-positive rate on null blocks (combined, alpha=0.01): 0/23 (95% upper bound 12.212%).
- Closure gap (smallest hidden-energy fraction of cluster capacity detected >=95% of the time, non-slack classes, combined channels): 31.62%.
- Implied hidden compute at that gap, one week: 6.82e+18 FLOP (1.92 H100-hours, energy floor 1.96e-12 J/FLOP, source: measured by hw-probe (HARDWARE-PROBE (NVML energy counter; spoofable)), sha256 d7d186395d77c29c).
- Hidden-energy upper bound coverage (non-slack): 100.00%; slack class (expected to evade): n/a.
- Efficiency slack (pre-registered H1.6): s_max = 12.55% of verified-work power (measured by hw-probe (HARDWARE-PROBE (NVML energy counter; spoofable)), sha256 d7d186395d77c29c); slack-inflated gap = 39.65% (closure gap + s_max x 63.99% mean predicted share of capacity).

## Pooled f95 by channel (fraction of cluster capacity)
- energy: 31.62%
- busy: 31.62%
- combined: 31.62%

## Detection rate by class and intensity (combined)

| class | 0.05 | 0.2 |
| --- | --- | --- |
| constant | 1.00 (n=4) | 1.00 (n=5) |
| idle_gap | 0.00 (n=1) | 1.00 (n=5) |
| duty | 0.40 (n=5) | 1.00 (n=3) |
| dilute | n/a | 1.00 (n=7) |

## Pre-registered T1 decision rules, read at this run's scale
- scope: shakedown reading: NVML only, so assumption A6 does not hold; what these data would decide, not a Plan A claim
- H1.1 calibration valid (Jarque-Bera p >= 0.01 and n_eff >= 15 in every regime): fails (energy: Jarque-Bera p 0.078, n_eff 12.4; busy: Jarque-Bera p 0.17, n_eff 7.4)
- H1.2 false alarms (at most 3 x alpha = 3.0% on at least 200 null blocks): not decided: 0/23 (95% upper bound 12.2%)
- H1.3 primary: detection >= 95% at hidden fraction >= 5%, per class (decided once a class has 8 such blocks): constant 9/9 holds; idle_gap 5/5 not decided; duty 3/3 not decided; dilute 7/7 not decided. Pooled over classes: 24/24, 95% lower bound 88.3% (not certified at 95%)
- H1.3 stretch: detection >= 95% at hidden fraction >= 2%, per class (decided once a class has 8 such blocks): constant 9/9 holds; idle_gap 5/5 not decided; duty 5/5 not decided; dilute 7/7 not decided. Pooled over classes: 26/26, 95% lower bound 89.1% (not certified at 95%)
- H1.4 hidden-energy bound covers at least 95% of non-slack hidden blocks (against the hidden energy recorded; on hardware, what the load was set to inject): holds (100.0%)
- outcome: **UNDERPOWERED** (H1.1 fails, so no false-alarm claim is made); closure gap 31.62%, slack-inflated 39.65%

## Assumptions (a failed assumption voids the claim)
- A1 additivity: hidden work adds energy/busy-time on top of verified work (no free lunch from sharing).
- A2 exchangeability: calibration and audit blocks come from the same regime mix (same stack, clocks, cooling, firmware).
- A3 approximate normality of block residual sums, checked by the Jarque-Bera diagnostic stored with the calibration.
- A4 no efficiency slack: the adversary is no more energy-efficient than the calibration reference (the 'slack' class tests this and is expected to evade).
- A5 the verified-work features are trustworthy (they come from the tap/recompute evidence, not from the prover).
- A6 the power meter is independent of the prover (DC-bus instrument); NVML-only runs are labelled as spoofable.
