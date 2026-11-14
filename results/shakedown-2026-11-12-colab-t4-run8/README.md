# Shakedown run 8: Colab T4, the medium trial with clocks locked, 12 November 2026

The second prospective test of amendment v0.6, and the first with the trial's clocks locked
(`closure tier0 --trial-profile medium`, plan-a-closure 0.8.0, commit `438fcbd`, clean), on the Tesla T4 of a free
Google Colab session, inside Colab's virtual machine, with NVML as the only power source. It is a shakedown on a
non-target device: assumption A6 does not hold and nothing here is a Plan A claim. The full account is section 7 of
`docs/DEVIATIONS.md`.

| file | what it is |
| --- | --- |
| `tier0_bundle.tar.gz` | the bundle as returned (seed 1773548153), sha256 `3efade48adb610882a635fc18f7644b4fbba4b4a09800e43510d5d445911f569` |
| `drill.json` | A Narrow Path's mock training run on the same GPU after the trial (compliant, 12.2% of the budget) |
| `extracted/` | the bundle's summary, logs, probe and trial files without `raw.npz`, for reading in a browser |
| `reread.json`, `physics.json` | written by `python results/reread.py results/shakedown-2026-11-12-colab-t4-run8` from the bundle |

## What the registered reading says

Every step ran and exited 0. **The trial fails the detection rule H1.3**, by one block in each of two classes.

| rule | this trial |
| --- | --- |
| H1.1 the threshold is conformal | holds |
| H1.2 false alarms, at most 3% of at least 200 null blocks | holds: 0/204 (95% upper bound 1.5%) |
| H1.3 primary: detection at 5% of capacity or more, each class at least 95% | **fails: constant 17/18, dilute 17/18**; duty 9/9 holds; idle_gap had no block at 5% (43/45 in all) |
| H1.3 stretch: detection at 2% or more | fails: constant 20/24, dilute 20/24, duty 17/18 (58/67 in all) |
| H1.4 the time bound covers the seconds the hidden load ran, in at least 95% of hidden blocks | holds: 73/73 |
| closure gap; with the measured slack | 17.8%; 25.9% |
| outcome | **FAIL** |

- The medium trial has 18 blocks at 5% or more in a class, so one miss (94.4%) fails that class's 95%.
- Amendment v0.6 expected the 2% level to fail at blocks this short (30 s), and it did. It did not expect the 5% level
  to fail.
- Probe: 10 stack variants (Colab allows clock and power-limit changes), `s_max` 0.108, energy floor 2.03e-12 J/FLOP.
- Residency (T2) passes: honest false alarms 0.3%, parked-block detection 100%.
- Calibration drift: +0.02 SD, spread 1.00x.
- `closure verify` passes. The signed results reproduce from `raw.npz` (every flag and count the same; the largest
  relative difference in any number is 7.1e-13).
- The pre-registration was stamped with OpenTimestamps before the trial (`extracted/T1-medium/prereg.json.ots`).

## Why, read off the raw data (after the run: it describes, it decides nothing)

`reread.json` holds the numbers.

1. **Two reference blocks set a threshold more than twice as high as the rest would.** The threshold is the largest of
   the 150 reference scores, 4.73 (in spreads of the reference blocks). The next are 4.39 and then 1.73. On Kaggle the
   thresholds were 2.29 and 2.43. No null audit block scored above 2.91, which is why there were no false alarms; the
   two blocks missed at 5% scored 3.78 and 2.78, above both Kaggle thresholds and under this one.
2. **Both are blocks at full load in which the GPU slowed while its power stayed at the limit.** The trial locked the
   clocks at 870 MHz, the highest clock the probe had seen held within 95% of the 70 W limit. The probe measures at
   requested levels up to 0.9. At that level, locked at 870 MHz, the GPU was busy 81.5% of the time and drew 64.9 W;
   busy all the time it needs an estimated 72.4 W, above the limit. So at full load the power limiter took over from
   the lock: power sat at 69.5 W, each unit of work took 9.2 ms of busy time against 8.7 ms at every level up to 0.7,
   and the rate of verified work moved between 99.7 and 112.7 units a second (1st and 99th percentile), with an hourly
   mean that rose from 105.6 to 110.1 through the run. A lock that does not hold at full load is not a lock there.
3. **The curve misfits at the top of the load range**, as on Kaggle: reference blocks with the GPU flat out throughout
   scored +1.44 on average, against 0.27 for all others.

## What changes for the next run (amendment v0.7, made before any further run)

- The clock the trial locks must hold flat out: the highest clock whose estimated flat-out power is at most 95% of the
  power limit. On this run's probe that is 645 MHz (64.9 W flat out) instead of 870 MHz.
- The `link-full` analysis is declared as a comparison that decides nothing. On this run's data (post hoc) it gives no
  false alarms in 204, detection at 5% or more of 45/45 with every decided class holding, 60/67 at 2% or more, a
  closure gap of 5.62% and a slack-inflated gap of 13.7%: still FAIL on the slack.
- Nothing else. The registered analysis, the thresholds and the outcome rule are as they were.
