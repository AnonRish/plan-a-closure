# Tier 0 pilot: summary

- plan-a-closure 0.7.0 (commit 1656ad44f933, clean); mode: HARDWARE
- started 2026-11-08T21:03:49Z, finished 2026-11-09T07:11:14Z; host Linux-6.18.55+-x86_64-with-glibc2.39, Python 3.13.16
- outcome: every step ran

| # | step | what it checks | exit | minutes | log |
| --- | --- | --- | --- | --- | --- |
| 1 | unit-tests | unit tests | 0 | 13.02 | logs/01-unit-tests.log |
| 2 | selftest | simulated end-to-end self-test | 0 | 0.09 | logs/02-selftest.log |
| 3 | preflight | NVML, energy counter, torch, clock sync, which physical GPU | 0 | 0.04 | logs/03-preflight.log |
| 4 | hw-selftest | energy tracks verified work on this GPU | 0 | 2.65 | logs/04-hw-selftest.log |
| 5 | hw-probe | efficiency slack and energy floor | 1 | 20.67 | logs/05-hw-probe.log |
| 6 | hw-state | device-memory residency | 1 | 21.52 | logs/06-hw-state.log |
| 7 | hw-trial | long trial (about 9 h): interleaved calibration, balanced blind hidden-load schedule | 0 | 549.35 | logs/07-hw-trial.log |
| 8 | verify | evidence chain, signature, commitments | 0 | 0.0 | logs/08-verify.log |
| 9 | hw-restore | clocks unlocked, power limit as found | 0 | 0.04 | logs/09-hw-restore.log |

## Energy tracks verified work (hw-selftest)

- pass = True: r2 0.9691 (needs > 0.9), idle 31.4 W, work at 25% load / work at 100% load = 0.34 (needs < 0.8)
- unit of work: 4096x4096 float16 GEMM + 268435456-element pass, 9.3 ms against a 100 ms slot

## Probe (H1.6 slack, H1.7 floor)

- s_max = 0.0963 (stack 0.0846, operand 0.0963); allowed stack variants 2, operand variants 3
- e_floor = 2.06e-12 J/FLOP at kernel-cublaslt; band/floor = 0.533
- probe.json sha256 53b5268b296ef60dbe2d1dc350cdf9e8f6de0d6434a218f67701b5f3085e8cca
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
- note: only 2 allowed variants were measurable above idle; H1.6 needs at least 3

## Device-memory residency (T2 pilot)

- pass = False: honest false alarm 0.0000, parked-block detection 0.9750 (block 64 MB, k = 17)

## Long trial (T1)

- status: HARDWARE (NVML energy counter; spoofable)
- false positives 11/204 (95% upper 0.0877)
- closure gap 0.1778 of capacity energy; slack-inflated gap 0.2485
- the long profile reads the registered decision rules at shakedown scale (below); the registered numbers come from the Tier 1 run (`hw-full`)
- SM clocks: not locked

## Calibration drift (assumption A2; a diagnostic, not a criterion)

- audit blocks without hidden energy (234) against calibration (144): mean shift +0.15 calibration SDs, spread 0.97x; drift suspected: False (flags at 0.5 SD and 1.5x)
- idle power 33.4 W during calibration, 33.6 W during audit
- energy per unit of work 0.349 J during calibration, 0.350 J during audit
- calibration blocks, last third against first third: +0.17 SDs; reference blocks were interleaved with the audit, so drift reaches both alike

## Pre-registered T1 decision rules, read at this run's scale

- scope: shakedown reading: NVML only, so assumption A6 does not hold; what these data would decide, not a Plan A claim
- H1.1 calibration valid (Jarque-Bera p >= 0.01 and n_eff >= 15 in every regime): fails (energy: Jarque-Bera p 3e-10, n_eff 105.3; busy: Jarque-Bera p 1.7e-07, n_eff 100.8)
- H1.2 false alarms (at most 3 x alpha = 3.0% on at least 200 null blocks): fails: 11/204 (95% upper bound 8.8%)
- H1.3 primary: detection >= 95% at hidden fraction >= 5%, per class (decided once a class has 8 such blocks): constant 35/36 holds; dilute 36/36 holds; duty 22/24 fails; idle_gap 6/6 not decided. Pooled over classes: 99/102, 95% lower bound 92.6% (not certified at 95%)
- H1.3 stretch: detection >= 95% at hidden fraction >= 2%, per class (decided once a class has 8 such blocks): constant 37/48 fails; dilute 37/48 fails; duty 23/36 fails; idle_gap 8/13 fails. Pooled over classes: 105/145, 95% lower bound 65.7% (not certified at 95%)
- H1.4 hidden-energy bound covers at least 95% of non-slack hidden blocks (against the hidden energy recorded; on hardware, what the load was set to inject): holds (100.0%)
- outcome: **UNDERPOWERED** (H1.1 fails, so no false-alarm claim is made); closure gap 17.78%, slack-inflated 24.85%

## Verification

- chain_ok: True, entries: 4, signature_ok: True, schedule_commitment_ok: True, order_commitment_ok: True, prereg_hash_ok: True, results_hash_ok: True, probe_hash_ok: True

## What to send back

- `tier0_bundle.tar.gz`: everything in this folder except `signing_key.bin`.
- Keep `T1-long/signing_key.bin` private or delete it: anyone holding it can forge this run's signature. The public key is in `T1-long/signature.json`.
- If an independent power meter logged during the trial, export it as `timestamp_s,power_w` and run `closure dcbus-analyze --run /tmp/plan-a-closure-runs/tier0-20261108-210349/T1-long --csv bus.csv`, then send `results_dcbus.json` as well.
