# Tier 0 pilot: summary

- plan-a-closure 0.6.0; mode: HARDWARE
- started 2026-11-08T15:53:08Z, finished 2026-11-08T17:50:36Z; host Linux-6.6.159+-x86_64-with-glibc2.39, Python 3.13.16
- outcome: every step ran

| # | step | what it checks | exit | minutes | log |
| --- | --- | --- | --- | --- | --- |
| 1 | unit-tests | unit tests | 0 | 10.77 | logs/01-unit-tests.log |
| 2 | selftest | simulated end-to-end self-test | 0 | 0.1 | logs/02-selftest.log |
| 3 | preflight | NVML, energy counter, torch, clock sync, which physical GPU | 0 | 0.04 | logs/03-preflight.log |
| 4 | hw-selftest | energy tracks verified work on this GPU | 0 | 2.65 | logs/04-hw-selftest.log |
| 5 | hw-probe | efficiency slack and energy floor | 0 | 34.67 | logs/05-hw-probe.log |
| 6 | hw-state | device-memory residency | 1 | 8.54 | logs/06-hw-state.log |
| 7 | hw-trial | smoke trial with blind hidden-load injection | 0 | 60.62 | logs/07-hw-trial.log |
| 8 | verify | evidence chain, signature, commitments | 0 | 0.0 | logs/08-verify.log |
| 9 | hw-restore | clocks unlocked, power limit as found | 0 | 0.04 | logs/09-hw-restore.log |

## Energy tracks verified work (hw-selftest)

- pass = True: r2 0.9411 (needs > 0.9), idle 28.1 W, work at 25% load / work at 100% load = 0.28 (needs < 0.8)
- unit of work: 4096x4096 float16 GEMM + 268435456-element pass, 9.0 ms against a 100 ms slot

## Probe (H1.6 slack, H1.7 floor)

- s_max = 0.1352 (stack 0.1352, operand 0.1187); allowed stack variants 10, operand variants 3
- e_floor = 2.04e-12 J/FLOP at clock-1575MHz; band/floor = 5.32
- probe.json sha256 e07769d9946f59ec2657d65f4f7a1aa2c5fc9fd99e2801c3d67c51e7cf9319b5
- note: variant precision-fp8 dropped: precision 'fp8': RuntimeError: torch._scaled_mm is only supported on CUDA devices with compute capability >= 9.0 or 8.9, or ROCm MI300+

## Device-memory residency (T2 pilot)

- pass = False: honest false alarm 0.0000, parked-block detection 0.9400 (block 64 MB, k = 8)

## Smoke trial (T1)

- status: HARDWARE (NVML energy counter; spoofable)
- false positives 3/23 (95% upper 0.3036)
- closure gap 0.3162 of capacity energy; slack-inflated gap 0.3984
- the smoke profile checks the pipeline; the registered numbers come from the Tier 1 run (`hw-full`)

## Verification

- chain_ok: True, entries: 4, signature_ok: True, schedule_commitment_ok: True, prereg_hash_ok: True, results_hash_ok: True, probe_hash_ok: True

## What to send back

- `tier0_bundle.tar.gz`: everything in this folder except `signing_key.bin`.
- Keep `T1-smoke/signing_key.bin` private or delete it: anyone holding it can forge this run's signature. The public key is in `T1-smoke/signature.json`.
- If an independent power meter logged during the trial, export it as `timestamp_s,power_w` and run `closure dcbus-analyze --run runs/tier0-20261108-155308/T1-smoke --csv bus.csv`, then send `results_dcbus.json` as well.
