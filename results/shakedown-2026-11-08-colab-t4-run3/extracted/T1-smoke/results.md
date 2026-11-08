# Closure report (HARDWARE (NVML energy counter; spoofable))

Status **HARDWARE (NVML energy counter; spoofable)**. A SIMULATED report validates the estimators only; only a HARDWARE report with a DC-bus channel supports physical claims.

## Headline
- False-positive rate on null blocks (combined, alpha=0.01): 3/23 (95% upper bound 30.364%).
- Closure gap (smallest hidden-energy fraction of cluster capacity detected >=95% of the time, non-slack classes, combined channels): 31.62%.
- Implied hidden compute at that gap, one week: 6.57e+18 FLOP (1.84 H100-hours, energy floor 2.04e-12 J/FLOP, source: measured by hw-probe (HARDWARE-PROBE (NVML energy counter; spoofable)), sha256 e07769d9946f59ec).
- Hidden-energy upper bound coverage (non-slack): 96.67%; slack class (expected to evade): n/a.
- Efficiency slack (pre-registered H1.6): s_max = 13.52% of verified-work power (measured by hw-probe (HARDWARE-PROBE (NVML energy counter; spoofable)), sha256 e07769d9946f59ec); slack-inflated gap = 39.84% (closure gap + s_max x 60.77% mean predicted share of capacity).

## Pooled f95 by channel (fraction of cluster capacity)
- energy: 31.62%
- busy: 31.62%
- combined: 31.62%

## Detection rate by class and intensity (combined)

| class | 0.05 | 0.2 |
| --- | --- | --- |
| constant | 1.00 (n=4) | 1.00 (n=5) |
| idle_gap | 0.00 (n=1) | 1.00 (n=5) |
| duty | 0.00 (n=5) | 1.00 (n=3) |
| dilute | n/a | 1.00 (n=7) |

## Assumptions (a failed assumption voids the claim)
- A1 additivity: hidden work adds energy/busy-time on top of verified work (no free lunch from sharing).
- A2 exchangeability: calibration and audit blocks come from the same regime mix (same stack, clocks, cooling, firmware).
- A3 approximate normality of block residual sums, checked by the Jarque-Bera diagnostic stored with the calibration.
- A4 no efficiency slack: the adversary is no more energy-efficient than the calibration reference (the 'slack' class tests this and is expected to evade).
- A5 the verified-work features are trustworthy (they come from the tap/recompute evidence, not from the prover).
- A6 the power meter is independent of the prover (DC-bus instrument); NVML-only runs are labelled as spoofable.
