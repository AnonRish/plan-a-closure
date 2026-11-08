# Tier 0 pilot: summary

- plan-a-closure 0.5.4; mode: HARDWARE
- started 2026-11-08T02:32:50Z, finished 2026-11-08T02:44:31Z; host Linux-6.6.159+-x86_64-with-glibc2.39, Python 3.13.16
- outcome: stopped after `hw-selftest` failed; later steps were skipped

| # | step | what it checks | exit | minutes | log |
| --- | --- | --- | --- | --- | --- |
| 1 | unit-tests | unit tests | 0 | 8.9 | logs/01-unit-tests.log |
| 2 | selftest | simulated end-to-end self-test | 0 | 0.09 | logs/02-selftest.log |
| 3 | preflight | NVML, energy counter, torch, clock sync, which physical GPU | 0 | 0.06 | logs/03-preflight.log |
| 4 | hw-selftest | energy tracks verified work on this GPU | 1 | 2.57 | logs/04-hw-selftest.log |
| 5 | hw-probe | efficiency slack and energy floor | skipped | 0.0 |  |
| 6 | hw-state | device-memory residency | skipped | 0.0 |  |
| 7 | hw-trial | smoke trial with blind hidden-load injection | skipped | 0.0 |  |
| 8 | verify | evidence chain, signature, commitments | skipped | 0.0 |  |
| 9 | hw-restore | clocks unlocked, power limit as found | 0 | 0.04 | logs/09-hw-restore.log |

## What to send back

- `tier0_bundle.tar.gz`: everything in this folder except `signing_key.bin`.
- Keep `T1-smoke/signing_key.bin` private or delete it: anyone holding it can forge this run's signature. The public key is in `T1-smoke/signature.json`.
- If an independent power meter logged during the trial, export it as `timestamp_s,power_w` and run `closure dcbus-analyze --run runs/tier0/T1-smoke --csv bus.csv`, then send `results_dcbus.json` as well.
