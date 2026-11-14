# Tier 0 pilot: summary

- plan-a-closure 0.8.0 (commit 438fcbd41c1c, clean); mode: HARDWARE
- started 2026-11-12T16:19:05Z, finished 2026-11-12T21:16:41Z; host Linux-6.6.159+-x86_64-with-glibc2.39, Python 3.13.16
- outcome: every step ran

| # | step | what it checks | exit | minutes | log |
| --- | --- | --- | --- | --- | --- |
| 1 | unit-tests | unit tests | 0 | 14.99 | logs/01-unit-tests.log |
| 2 | selftest | simulated end-to-end self-test | 0 | 0.13 | logs/02-selftest.log |
| 3 | preflight | NVML, energy counter, torch, clock sync, which physical GPU | 0 | 0.04 | logs/03-preflight.log |
| 4 | hw-selftest | energy tracks verified work on this GPU | 0 | 2.66 | logs/04-hw-selftest.log |
| 5 | hw-probe | efficiency slack and energy floor | 0 | 34.75 | logs/05-hw-probe.log |
| 6 | hw-state | device-memory residency | 0 | 12.03 | logs/06-hw-state.log |
| 7 | hw-trial | medium trial (under 4 h): interleaved calibration, balanced blind hidden-load schedule | 0 | 232.91 | logs/07-hw-trial.log |
| 8 | verify | evidence chain, signature, commitments | 0 | 0.01 | logs/08-verify.log |
| 9 | hw-restore | clocks unlocked, power limit as found | 0 | 0.05 | logs/09-hw-restore.log |

## Energy tracks verified work (hw-selftest)

- pass = True: r2 0.9334 (needs > 0.9), idle 28.8 W, work at 25% load / work at 100% load = 0.28 (needs < 0.8)
- unit of work: 4096x4096 float16 GEMM + 268435456-element pass, 8.8 ms against a 100 ms slot

## Probe (H1.6 slack, H1.7 floor)

- s_max = 0.1078 (stack 0.0908, operand 0.1078); allowed stack variants 10, operand variants 3
- e_floor = 2.03e-12 J/FLOP at clock-1575MHz; band/floor = 5.45
- probe.json sha256 e823a6f8612466878f6288fc8ce2a8a61eb952ba1e42a6afa6d06e21d759b605
- note: variant precision-fp8 dropped: precision 'fp8': RuntimeError: torch._scaled_mm is only supported on CUDA devices with compute capability >= 9.0 or 8.9, or ROCm MI300+

## Device-memory residency (T2 pilot)

- pass = True: honest false alarm 0.0030, parked-block detection 1.0000 (block 64 MB, k = 17, judged by slowest block of each challenge)
- 2000 honest and 1000 parked-prover challenges, judged against a threshold from 4000 more honest ones (one pass, interleaved at random, back to back); challenges that touched exactly one parked block: 8/8 caught; digests recomputed by the verifier: 140, wrong: 0
- by total time, the statistic until 0.8.0: false alarm 0.0055, detection 1.0000; slowest block 3.3 ms honest against 18.4 ms parked (medians)

## Medium trial (T1)

- status: HARDWARE (NVML energy counter; spoofable)
- false positives 0/204 (95% upper 0.0146)
- closure gap 0.1778 of capacity energy; slack-inflated gap 0.2589
- the medium profile reads the registered decision rules at shakedown scale (below); the registered numbers come from the Tier 1 run (`hw-full`)
- analysis: link (a calibrated curve for each channel, one conformal threshold) over 150 reference blocks; block residual SD 44.2 J and 0.372 s; partial-load slack 0.057
- hidden load alone, before the trial (its labels are read off this): duty 0.02: 1.1 W, duty 0.05: 2.7 W, duty 0.10: 5.5 W, duty 0.20: 11.7 W, duty 0.40: 23.0 W, duty 0.80: 36.7 W
- SM clocks: locked at 870 MHz

## Calibration drift (assumption A2; a diagnostic, not a criterion)

- audit blocks without hidden energy (227) against calibration (150): mean shift +0.02 calibration SDs (standard error 0.11), spread 1.00x; drift suspected: False (flags at 0.5 SD and 1.5x)
- idle power 30.2 W during calibration, 30.7 W during audit
- energy per unit of work 0.354 J during calibration, 0.357 J during audit
- calibration blocks, last third against first third: -1.63 SDs; reference blocks were interleaved with the audit, so drift reaches both alike

## Pre-registered T1 decision rules, read at this run's scale

- scope: shakedown reading: NVML only, so assumption A6 does not hold; what these data would decide, not a Plan A claim
- H1.1 calibration valid (the threshold is conformal: no distribution assumed, at least 1/alpha - 1 effective reference blocks): holds (threshold: conformal; reported only: energy: Jarque-Bera p 4.1e-05, n_eff 150.0; busy: Jarque-Bera p 4e-42, n_eff 150.0)
- H1.2 false alarms (at most 3 x alpha = 3.0% on at least 200 null blocks): holds: 0/204 (95% upper bound 1.5%)
- H1.3 primary: detection >= 95% at hidden fraction >= 5%, per class (decided once a class has 8 such blocks): constant 17/18 fails; dilute 17/18 fails; duty 9/9 holds; idle_gap 0/0 not decided. Pooled over classes: 43/45, 95% lower bound 86.7% (not certified at 95%)
- H1.3 stretch: detection >= 95% at hidden fraction >= 2%, per class (decided once a class has 8 such blocks): constant 20/24 fails; dilute 20/24 fails; duty 17/18 fails; idle_gap 1/1 not decided. Pooled over classes: 58/67, 95% lower bound 77.7% (not certified at 95%)
- H1.4 the time bound covers the seconds the hidden load really ran in at least 95% of non-slack hidden blocks: holds (100.0% of 73, by the floor bound: busy time above the least the verified work can take). Reported only, as checks on additivity (A1): the calibrated time bound covers 100.0%; the energy bound covers the hidden load's solo energy in 100.0% (calibrated) and 100.0% (floor)
- outcome: **FAIL** (slack-inflated gap 25.9% is above 5%); closure gap 17.78%, slack-inflated 25.89%

## What the GPU did, by requested load level (a diagnostic, not a criterion)

| requested level | windows | units of work a second | watts | busy share | busy ms per unit |
| --- | --- | --- | --- | --- | --- |
| 0 | 672 | 0.0 | 30.5 | 0.001 |  |
| 0.1 | 1125 | 20.0 | 38.1 | 0.172 | 8.60 |
| 0.2 | 1714 | 30.1 | 41.9 | 0.261 | 8.70 |
| 0.3 | 1778 | 40.1 | 45.5 | 0.350 | 8.74 |
| 0.5 | 1414 | 60.2 | 52.9 | 0.524 | 8.70 |
| 0.7 | 1280 | 80.4 | 59.9 | 0.704 | 8.75 |
| 0.9 | 1834 | 103.6 | 67.8 | 0.924 | 8.92 |
| 1 | 1971 | 106.9 | 69.5 | 0.985 | 9.21 |

- the same loads at requested level 1, watts added and verified work displaced: 2% label: +0.6 W, -3.8 units a second; 5% label: +0.5 W, -9.4 units a second; 10% label: -0.3 W, -15.2 units a second; 20% label: -0.4 W, -32.6 units a second
- load levels as recorded

## Verification

- chain_ok: True, entries: 4, signature_ok: True, schedule_commitment_ok: True, order_commitment_ok: True, prereg_hash_ok: True, results_hash_ok: True, probe_hash_ok: True

## What to send back

- `tier0_bundle.tar.gz`: everything in this folder except `signing_key.bin`.
- Keep `T1-medium/signing_key.bin` private or delete it: anyone holding it can forge this run's signature. The public key is in `T1-medium/signature.json`.
- If an independent power meter logged during the trial, export it as `timestamp_s,power_w` and run `closure dcbus-analyze --run /content/plan-a-closure/runs/tier0-20261112-161904/T1-medium --csv bus.csv`, then send `results_dcbus.json` as well.
