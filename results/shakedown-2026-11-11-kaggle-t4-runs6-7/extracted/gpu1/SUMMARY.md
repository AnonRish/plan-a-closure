# Tier 0 pilot: summary

- plan-a-closure 0.8.0 (commit 438fcbd41c1c, clean); mode: HARDWARE
- started 2026-11-11T20:13:08Z, finished 2026-11-12T06:01:39Z; host Linux-6.18.55+-x86_64-with-glibc2.39, Python 3.13.16
- outcome: every step ran

| # | step | what it checks | exit | minutes | log |
| --- | --- | --- | --- | --- | --- |
| 1 | selftest | simulated end-to-end self-test | 0 | 0.09 | logs/01-selftest.log |
| 2 | preflight | NVML, energy counter, torch, clock sync, which physical GPU | 0 | 0.04 | logs/02-preflight.log |
| 3 | hw-selftest | energy tracks verified work on this GPU | 0 | 2.65 | logs/03-hw-selftest.log |
| 4 | hw-probe | efficiency slack and energy floor | 0 | 20.48 | logs/04-hw-probe.log |
| 5 | hw-state | device-memory residency | 0 | 12.76 | logs/05-hw-state.log |
| 6 | hw-trial | long trial (about 9 h): interleaved calibration, balanced blind hidden-load schedule | 0 | 552.43 | logs/06-hw-trial.log |
| 7 | verify | evidence chain, signature, commitments | 0 | 0.0 | logs/07-verify.log |
| 8 | hw-restore | clocks unlocked, power limit as found | 0 | 0.03 | logs/08-hw-restore.log |

## Energy tracks verified work (hw-selftest)

- pass = True: r2 0.9517 (needs > 0.9), idle 29.2 W, work at 25% load / work at 100% load = 0.28 (needs < 0.8)
- unit of work: 4096x4096 float16 GEMM + 268435456-element pass, 9.3 ms against a 100 ms slot

## Probe (H1.6 slack, H1.7 floor)

- s_max = 0.0839 (stack 0.0684, operand 0.0839); allowed stack variants 3, operand variants 3
- e_floor = 2.14e-12 J/FLOP at kernel-cublaslt; band/floor = 4.73
- probe.json sha256 5db96ed13113204c46393b1cb8c0333a4b28fd59c82e6689f37f71d6b345a766
- note: variant clock-1110MHz dropped: device control needs root (`nvidia-smi -rgc`: The current user does not have permission to change clocks for GPU 00000000:00:05.0.
Terminating early due to previous errors.); clock and power-limit variants dropped
- note: variant clock-1335MHz dropped: device control needs root (`nvidia-smi -rgc`: The current user does not have permission to change clocks for GPU 00000000:00:05.0.
Terminating early due to previous errors.); clock and power-limit variants dropped
- note: variant clock-645MHz dropped: device control needs root (`nvidia-smi -rgc`: The current user does not have permission to change clocks for GPU 00000000:00:05.0.
Terminating early due to previous errors.); clock and power-limit variants dropped
- note: variant clock-870MHz dropped: device control needs root (`nvidia-smi -rgc`: The current user does not have permission to change clocks for GPU 00000000:00:05.0.
Terminating early due to previous errors.); clock and power-limit variants dropped
- note: variant clock-405MHz dropped: device control needs root (`nvidia-smi -rgc`: The current user does not have permission to change clocks for GPU 00000000:00:05.0.
Terminating early due to previous errors.); clock and power-limit variants dropped
- note: variant powercap-87pct dropped: device control needs root (`nvidia-smi -rgc`: The current user does not have permission to change clocks for GPU 00000000:00:05.0.
Terminating early due to previous errors.); clock and power-limit variants dropped
- note: variant clock-1575MHz dropped: device control needs root (`nvidia-smi -rgc`: The current user does not have permission to change clocks for GPU 00000000:00:05.0.
Terminating early due to previous errors.); clock and power-limit variants dropped
- note: variant precision-fp8 dropped: precision 'fp8': RuntimeError: torch._scaled_mm is only supported on CUDA devices with compute capability >= 9.0 or 8.9, or ROCm MI300+

## Device-memory residency (T2 pilot)

- pass = True: honest false alarm 0.0055, parked-block detection 1.0000 (block 64 MB, k = 17, judged by slowest block of each challenge)
- 2000 honest and 1000 parked-prover challenges, judged against a threshold from 4000 more honest ones (one pass, interleaved at random, back to back); challenges that touched exactly one parked block: 9/9 caught; digests recomputed by the verifier: 140, wrong: 0
- by total time, the statistic until 0.8.0: false alarm 0.0040, detection 1.0000; slowest block 3.2 ms honest against 18.1 ms parked (medians)

## Long trial (T1)

- status: HARDWARE (NVML energy counter; spoofable)
- false positives 0/204 (95% upper 0.0146)
- closure gap 0.0562 of capacity energy; slack-inflated gap 0.1173
- the long profile reads the registered decision rules at shakedown scale (below); the registered numbers come from the Tier 1 run (`hw-full`)
- analysis: link (a calibrated curve for each channel, one conformal threshold) over 144 reference blocks; block residual SD 52.2 J and 0.652 s; partial-load slack 0.123
- hidden load alone, before the trial (its labels are read off this): duty 0.02: 0.6 W, duty 0.05: 1.8 W, duty 0.10: 3.4 W, duty 0.20: 7.4 W, duty 0.40: 17.6 W, duty 0.80: 33.1 W
- trial 2 of 2 in campaign `kaggle-20261111-195848`: read them together with `closure pool`
- SM clocks: not locked

## Calibration drift (assumption A2; a diagnostic, not a criterion)

- audit blocks without hidden energy (235) against calibration (144): mean shift -0.01 calibration SDs (standard error 0.11), spread 0.92x; drift suspected: False (flags at 0.5 SD and 1.5x)
- idle power 31.6 W during calibration, 31.6 W during audit
- energy per unit of work 0.375 J during calibration, 0.370 J during audit
- calibration blocks, last third against first third: -0.16 SDs; reference blocks were interleaved with the audit, so drift reaches both alike

## Pre-registered T1 decision rules, read at this run's scale

- scope: shakedown reading: NVML only, so assumption A6 does not hold; what these data would decide, not a Plan A claim
- H1.1 calibration valid (the threshold is conformal: no distribution assumed, at least 1/alpha - 1 effective reference blocks): holds (threshold: conformal; reported only: energy: Jarque-Bera p 8.1e-10, n_eff 144.0; busy: Jarque-Bera p 8.5e-05, n_eff 144.0)
- H1.2 false alarms (at most 3 x alpha = 3.0% on at least 200 null blocks): holds: 0/204 (95% upper bound 1.5%)
- H1.3 primary: detection >= 95% at hidden fraction >= 5%, per class (decided once a class has 8 such blocks): constant 36/36 holds; dilute 36/36 holds; duty 24/24 holds; idle_gap 9/9 holds. Pooled over classes: 105/105, 95% lower bound 97.2% (certified at 95%)
- H1.3 stretch: detection >= 95% at hidden fraction >= 2%, per class (decided once a class has 8 such blocks): constant 46/48 holds; dilute 47/48 holds; duty 36/36 holds; idle_gap 13/13 holds. Pooled over classes: 142/145, 95% lower bound 94.7% (not certified at 95%)
- H1.4 the time bound covers the seconds the hidden load really ran in at least 95% of non-slack hidden blocks: holds (100.0% of 161, by the floor bound: busy time above the least the verified work can take). Reported only, as checks on additivity (A1): the calibrated time bound covers 98.1%; the energy bound covers the hidden load's solo energy in 98.1% (calibrated) and 100.0% (floor)
- outcome: **FAIL** (slack-inflated gap 11.7% is above 5%); closure gap 5.62%, slack-inflated 11.73%

## What the GPU did, by requested load level (a diagnostic, not a criterion)

| requested level | windows | units of work a second | watts | busy share | busy ms per unit |
| --- | --- | --- | --- | --- | --- |
| 0 | 3428 | 0.0 | 31.6 | 0.001 |  |
| 0.1 | 3159 | 10.3 | 35.2 | 0.112 | 10.95 |
| 0.2 | 2550 | 20.3 | 38.3 | 0.222 | 10.89 |
| 0.3 | 3096 | 32.6 | 43.2 | 0.340 | 10.42 |
| 0.5 | 3745 | 70.3 | 63.3 | 0.554 | 7.88 |
| 0.7 | 2311 | 86.5 | 65.3 | 0.744 | 8.60 |
| 0.9 | 2702 | 100.0 | 66.9 | 0.938 | 9.38 |
| 1 | 3791 | 100.6 | 67.4 | 0.989 | 9.83 |

- hidden load on an otherwise idle GPU, watts added against the label: 2% label (1.4 W): +0.6 W; 5% label (3.5 W): +4.2 W; 10% label (7.0 W): +7.5 W; 20% label (14.0 W): +13.9 W
- the same loads at requested level 1, watts added and verified work displaced: 2% label: +0.1 W, -2.9 units a second; 5% label: -0.1 W, -11.8 units a second; 10% label: -0.1 W, -21.6 units a second; 20% label: -0.1 W, -36.5 units a second
- load levels as recorded

## Verification

- chain_ok: True, entries: 4, signature_ok: True, schedule_commitment_ok: True, order_commitment_ok: True, prereg_hash_ok: True, results_hash_ok: True, probe_hash_ok: True

## What to send back

- `tier0_bundle.tar.gz`: everything in this folder except `signing_key.bin`.
- Keep `T1-long/signing_key.bin` private or delete it: anyone holding it can forge this run's signature. The public key is in `T1-long/signature.json`.
- If an independent power meter logged during the trial, export it as `timestamp_s,power_w` and run `closure dcbus-analyze --run /tmp/plan-a-closure-runs/tier0-20261111-195848-gpu1/T1-long --csv bus.csv`, then send `results_dcbus.json` as well.
