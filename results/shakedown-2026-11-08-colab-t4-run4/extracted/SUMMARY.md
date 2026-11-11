# Tier 0 pilot: summary

- plan-a-closure 0.7.0 (commit 1656ad44f933, clean); mode: HARDWARE
- started 2026-11-08T23:13:46Z, finished 2026-11-09T01:23:20Z; host Linux-6.6.159+-x86_64-with-glibc2.39, Python 3.13.16
- outcome: every step ran

| # | step | what it checks | exit | minutes | log |
| --- | --- | --- | --- | --- | --- |
| 1 | unit-tests | unit tests | 0 | 13.15 | logs/01-unit-tests.log |
| 2 | selftest | simulated end-to-end self-test | 0 | 0.09 | logs/02-selftest.log |
| 3 | preflight | NVML, energy counter, torch, clock sync, which physical GPU | 0 | 0.04 | logs/03-preflight.log |
| 4 | hw-selftest | energy tracks verified work on this GPU | 0 | 2.67 | logs/04-hw-selftest.log |
| 5 | hw-probe | efficiency slack and energy floor | 0 | 34.32 | logs/05-hw-probe.log |
| 6 | hw-state | device-memory residency | 0 | 18.55 | logs/06-hw-state.log |
| 7 | hw-trial | smoke trial with blind hidden-load injection | 0 | 60.65 | logs/07-hw-trial.log |
| 8 | verify | evidence chain, signature, commitments | 0 | 0.01 | logs/08-verify.log |
| 9 | hw-restore | clocks unlocked, power limit as found | 0 | 0.05 | logs/09-hw-restore.log |

## Energy tracks verified work (hw-selftest)

- pass = True: r2 0.9660 (needs > 0.9), idle 28.2 W, work at 25% load / work at 100% load = 0.29 (needs < 0.8)
- unit of work: 4096x4096 float16 GEMM + 268435456-element pass, 9.0 ms against a 100 ms slot

## Probe (H1.6 slack, H1.7 floor)

- s_max = 0.1255 (stack 0.1245, operand 0.1255); allowed stack variants 10, operand variants 3
- e_floor = 1.96e-12 J/FLOP at clock-1575MHz; band/floor = 5.15
- probe.json sha256 d7d186395d77c29c7141f2c82e15c813bf7877405f7b693dbae4411252c708cd
- note: variant precision-fp8 dropped: precision 'fp8': RuntimeError: torch._scaled_mm is only supported on CUDA devices with compute capability >= 9.0 or 8.9, or ROCm MI300+

## Device-memory residency (T2 pilot)

- pass = True: honest false alarm 0.0000, parked-block detection 1.0000 (block 64 MB, k = 17)

## Smoke trial (T1)

- status: HARDWARE (NVML energy counter; spoofable)
- false positives 0/23 (95% upper 0.1221)
- closure gap 0.3162 of capacity energy; slack-inflated gap 0.3965
- the smoke profile checks the pipeline; the registered numbers come from the Tier 1 run (`hw-full`)
- SM clocks: locked at 1110 MHz

## Calibration drift (assumption A2; a diagnostic, not a criterion)

- audit blocks without hidden energy (30) against calibration (60): mean shift +0.60 calibration SDs, spread 0.88x; drift suspected: True (flags at 0.5 SD and 1.5x)
- idle power 31.5 W during calibration, 31.6 W during audit
- energy per unit of work 0.320 J during calibration, 0.323 J during audit
- calibration blocks, last third against first third: -0.05 SDs

## Pre-registered T1 decision rules, read at this run's scale

- scope: shakedown reading: NVML only, so assumption A6 does not hold; what these data would decide, not a Plan A claim
- H1.1 calibration valid (Jarque-Bera p >= 0.01 and n_eff >= 15 in every regime): fails (energy: Jarque-Bera p 0.078, n_eff 12.4; busy: Jarque-Bera p 0.17, n_eff 7.4)
- H1.2 false alarms (at most 3 x alpha = 3.0% on at least 200 null blocks): not decided: 0/23 (95% upper bound 12.2%)
- H1.3 primary: detection >= 95% at hidden fraction >= 5%, per class (decided once a class has 8 such blocks): constant 9/9 holds; dilute 7/7 not decided; duty 3/3 not decided; idle_gap 5/5 not decided. Pooled over classes: 24/24, 95% lower bound 88.3% (not certified at 95%)
- H1.3 stretch: detection >= 95% at hidden fraction >= 2%, per class (decided once a class has 8 such blocks): constant 9/9 holds; dilute 7/7 not decided; duty 5/5 not decided; idle_gap 5/5 not decided. Pooled over classes: 26/26, 95% lower bound 89.1% (not certified at 95%)
- H1.4 hidden-energy bound covers at least 95% of non-slack hidden blocks (against the hidden energy recorded; on hardware, what the load was set to inject): holds (100.0%)
- outcome: **UNDERPOWERED** (H1.1 fails, so no false-alarm claim is made); closure gap 31.62%, slack-inflated 39.65%

## Verification

- chain_ok: True, entries: 4, signature_ok: True, schedule_commitment_ok: True, prereg_hash_ok: True, results_hash_ok: True, probe_hash_ok: True

## What to send back

- `tier0_bundle.tar.gz`: everything in this folder except `signing_key.bin`.
- Keep `T1-smoke/signing_key.bin` private or delete it: anyone holding it can forge this run's signature. The public key is in `T1-smoke/signature.json`.
- If an independent power meter logged during the trial, export it as `timestamp_s,power_w` and run `closure dcbus-analyze --run /content/plan-a-closure/runs/tier0-20261108-231346/T1-smoke --csv bus.csv`, then send `results_dcbus.json` as well.
