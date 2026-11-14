# Tier 0 pilot: summary

- plan-a-closure 0.8.0 (commit 438fcbd41c1c, clean); mode: HARDWARE
- started 2026-11-11T19:58:48Z, finished 2026-11-12T06:01:18Z; host Linux-6.18.55+-x86_64-with-glibc2.39, Python 3.13.16
- outcome: every step ran

| # | step | what it checks | exit | minutes | log |
| --- | --- | --- | --- | --- | --- |
| 1 | unit-tests | unit tests | 0 | 14.04 | logs/01-unit-tests.log |
| 2 | selftest | simulated end-to-end self-test | 0 | 0.09 | logs/02-selftest.log |
| 3 | preflight | NVML, energy counter, torch, clock sync, which physical GPU | 0 | 0.04 | logs/03-preflight.log |
| 4 | hw-selftest | energy tracks verified work on this GPU | 0 | 2.65 | logs/04-hw-selftest.log |
| 5 | hw-probe | efficiency slack and energy floor | 0 | 20.42 | logs/05-hw-probe.log |
| 6 | hw-state | device-memory residency | 0 | 12.77 | logs/06-hw-state.log |
| 7 | hw-trial | long trial (about 9 h): interleaved calibration, balanced blind hidden-load schedule | 0 | 552.42 | logs/07-hw-trial.log |
| 8 | verify | evidence chain, signature, commitments | 0 | 0.0 | logs/08-verify.log |
| 9 | hw-restore | clocks unlocked, power limit as found | 0 | 0.04 | logs/09-hw-restore.log |

## Energy tracks verified work (hw-selftest)

- pass = True: r2 0.9484 (needs > 0.9), idle 29.8 W, work at 25% load / work at 100% load = 0.28 (needs < 0.8)
- unit of work: 4096x4096 float16 GEMM + 268435456-element pass, 9.4 ms against a 100 ms slot

## Probe (H1.6 slack, H1.7 floor)

- s_max = 0.0910 (stack 0.0800, operand 0.0910); allowed stack variants 3, operand variants 3
- e_floor = 2.15e-12 J/FLOP at precision-fp16; band/floor = 4.82
- probe.json sha256 ebfc67d0e8dfc30be82ef9d07f3dcf56a0faef037940a0fcd626c0dcd378e2f0
- note: variant clock-1110MHz dropped: device control needs root (`nvidia-smi -rgc`: The current user does not have permission to change clocks for GPU 00000000:00:04.0.
Terminating early due to previous errors.); clock and power-limit variants dropped
- note: variant clock-1335MHz dropped: device control needs root (`nvidia-smi -rgc`: The current user does not have permission to change clocks for GPU 00000000:00:04.0.
Terminating early due to previous errors.); clock and power-limit variants dropped
- note: variant clock-645MHz dropped: device control needs root (`nvidia-smi -rgc`: The current user does not have permission to change clocks for GPU 00000000:00:04.0.
Terminating early due to previous errors.); clock and power-limit variants dropped
- note: variant clock-870MHz dropped: device control needs root (`nvidia-smi -rgc`: The current user does not have permission to change clocks for GPU 00000000:00:04.0.
Terminating early due to previous errors.); clock and power-limit variants dropped
- note: variant clock-405MHz dropped: device control needs root (`nvidia-smi -rgc`: The current user does not have permission to change clocks for GPU 00000000:00:04.0.
Terminating early due to previous errors.); clock and power-limit variants dropped
- note: variant powercap-87pct dropped: device control needs root (`nvidia-smi -rgc`: The current user does not have permission to change clocks for GPU 00000000:00:04.0.
Terminating early due to previous errors.); clock and power-limit variants dropped
- note: variant clock-1575MHz dropped: device control needs root (`nvidia-smi -rgc`: The current user does not have permission to change clocks for GPU 00000000:00:04.0.
Terminating early due to previous errors.); clock and power-limit variants dropped
- note: variant precision-fp8 dropped: precision 'fp8': RuntimeError: torch._scaled_mm is only supported on CUDA devices with compute capability >= 9.0 or 8.9, or ROCm MI300+

## Device-memory residency (T2 pilot)

- pass = True: honest false alarm 0.0020, parked-block detection 0.9990 (block 64 MB, k = 17, judged by slowest block of each challenge)
- 2000 honest and 1000 parked-prover challenges, judged against a threshold from 4000 more honest ones (one pass, interleaved at random, back to back); challenges that touched exactly one parked block: 8/8 caught; digests recomputed by the verifier: 140, wrong: 0
- by total time, the statistic until 0.8.0: false alarm 0.0060, detection 0.9990; slowest block 3.2 ms honest against 18.1 ms parked (medians)

## Long trial (T1)

- status: HARDWARE (NVML energy counter; spoofable)
- false positives 3/204 (95% upper 0.0376)
- closure gap 0.0562 of capacity energy; slack-inflated gap 0.1227
- the long profile reads the registered decision rules at shakedown scale (below); the registered numbers come from the Tier 1 run (`hw-full`)
- analysis: link (a calibrated curve for each channel, one conformal threshold) over 144 reference blocks; block residual SD 62.8 J and 0.688 s; partial-load slack 0.163
- hidden load alone, before the trial (its labels are read off this): duty 0.02: 0.7 W, duty 0.05: 1.8 W, duty 0.10: 3.5 W, duty 0.20: 7.3 W, duty 0.40: 18.3 W, duty 0.80: 33.9 W
- trial 1 of 2 in campaign `kaggle-20261111-195848`: read them together with `closure pool`
- SM clocks: not locked

## Calibration drift (assumption A2; a diagnostic, not a criterion)

- audit blocks without hidden energy (236) against calibration (144): mean shift -0.18 calibration SDs (standard error 0.11), spread 1.04x; drift suspected: False (flags at 0.5 SD and 1.5x)
- idle power 29.2 W during calibration, 29.2 W during audit
- energy per unit of work 0.366 J during calibration, 0.372 J during audit
- calibration blocks, last third against first third: +0.39 SDs; reference blocks were interleaved with the audit, so drift reaches both alike

## Pre-registered T1 decision rules, read at this run's scale

- scope: shakedown reading: NVML only, so assumption A6 does not hold; what these data would decide, not a Plan A claim
- H1.1 calibration valid (the threshold is conformal: no distribution assumed, at least 1/alpha - 1 effective reference blocks): holds (threshold: conformal; reported only: energy: Jarque-Bera p 5.3e-09, n_eff 144.0; busy: Jarque-Bera p 0, n_eff 144.0)
- H1.2 false alarms (at most 3 x alpha = 3.0% on at least 200 null blocks): holds: 3/204 (95% upper bound 3.8%)
- H1.3 primary: detection >= 95% at hidden fraction >= 5%, per class (decided once a class has 8 such blocks): constant 36/36 holds; dilute 36/36 holds; duty 24/24 holds; idle_gap 9/9 holds. Pooled over classes: 105/105, 95% lower bound 97.2% (certified at 95%)
- H1.3 stretch: detection >= 95% at hidden fraction >= 2%, per class (decided once a class has 8 such blocks): constant 46/48 holds; dilute 48/48 holds; duty 36/36 holds; idle_gap 13/13 holds. Pooled over classes: 143/145, 95% lower bound 95.7% (certified at 95%)
- H1.4 the time bound covers the seconds the hidden load really ran in at least 95% of non-slack hidden blocks: holds (100.0% of 160, by the floor bound: busy time above the least the verified work can take). Reported only, as checks on additivity (A1): the calibrated time bound covers 100.0%; the energy bound covers the hidden load's solo energy in 96.9% (calibrated) and 100.0% (floor)
- outcome: **FAIL** (slack-inflated gap 12.3% is above 5%); closure gap 5.62%, slack-inflated 12.27%

## What the GPU did, by requested load level (a diagnostic, not a criterion)

| requested level | windows | units of work a second | watts | busy share | busy ms per unit |
| --- | --- | --- | --- | --- | --- |
| 0 | 2979 | 0.0 | 29.3 | 0.001 |  |
| 0.1 | 2945 | 10.2 | 32.7 | 0.112 | 10.97 |
| 0.2 | 2982 | 20.4 | 36.6 | 0.222 | 10.88 |
| 0.3 | 2943 | 31.8 | 40.3 | 0.336 | 10.58 |
| 0.5 | 3243 | 70.3 | 62.2 | 0.541 | 7.70 |
| 0.7 | 2460 | 89.8 | 64.5 | 0.748 | 8.33 |
| 0.9 | 3748 | 101.8 | 65.9 | 0.932 | 9.16 |
| 1 | 3520 | 105.4 | 66.5 | 0.989 | 9.38 |

- hidden load on an otherwise idle GPU, watts added against the label: 2% label (1.4 W): +2.4 W; 10% label (7.0 W): +7.2 W; 20% label (14.0 W): +14.5 W
- the same loads at requested level 1, watts added and verified work displaced: 2% label: -0.1 W, -5.8 units a second; 5% label: -0.5 W, -14.0 units a second; 10% label: -0.3 W, -26.5 units a second; 20% label: -0.6 W, -40.2 units a second
- load levels as recorded

## Verification

- chain_ok: True, entries: 4, signature_ok: True, schedule_commitment_ok: True, order_commitment_ok: True, prereg_hash_ok: True, results_hash_ok: True, probe_hash_ok: True

## What to send back

- `tier0_bundle.tar.gz`: everything in this folder except `signing_key.bin`.
- Keep `T1-long/signing_key.bin` private or delete it: anyone holding it can forge this run's signature. The public key is in `T1-long/signature.json`.
- If an independent power meter logged during the trial, export it as `timestamp_s,power_w` and run `closure dcbus-analyze --run /tmp/plan-a-closure-runs/tier0-20261111-195848-gpu0/T1-long --csv bus.csv`, then send `results_dcbus.json` as well.
