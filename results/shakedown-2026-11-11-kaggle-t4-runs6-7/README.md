# Shakedown runs 6 and 7: Kaggle T4 x2, two long trials read as one campaign, 11 to 12 November 2026

The first prospective test of amendment v0.6: the link analysis, hidden-load labels measured before the trial, a seed
drawn fresh for each trial, and two trials declared as one campaign before either began
(`closure tier0 --trial-profile long --campaign kaggle-20261111-195848:i/2`, plan-a-closure 0.8.0, commit `438fcbd`,
clean). One trial on each Tesla T4 of a Kaggle "GPU T4 x2" session, at the same time, inside Kaggle's container, with
NVML as the only power source. It is a shakedown on a non-target device: assumption A6 does not hold and nothing here
is a Plan A claim. The full account is section 6 of `docs/DEVIATIONS.md`.

| file | what it is |
| --- | --- |
| `gpu0-tier0_bundle.tar.gz` | run 6 (GPU 0, seed 1886737444) as returned, sha256 `b0d99770ef90d069555a4acab85d4d08d9db1d5b431f3fd6dc105ca0ba4345d3` |
| `gpu1-tier0_bundle.tar.gz` | run 7 (GPU 1, seed 1231193211) as returned, sha256 `9a136d861ea55ee710a7a93b0249762f70fe1661feeebe9c1ced04e4f96cef05` |
| `CAMPAIGN.md`, `pooled.json` | the two trials read as one by `closure pool`, as the Kaggle session wrote them |
| `drill.json` | A Narrow Path's mock training run on GPU 0 after the trials (compliant, 12.9% of the budget) |
| `extracted/gpu0/`, `extracted/gpu1/` | each bundle's summary, logs, probe and trial files without `raw.npz`, for reading in a browser |
| `reread.json`, `gpu0-physics.json`, `gpu1-physics.json` | written by `python results/reread.py results/shakedown-2026-11-11-kaggle-t4-runs6-7` from the two bundles |

## What the registered reading says

Every step of both runs ran and exited 0. The campaign is read whole (`CAMPAIGN.md`, `pooled.json`):

| rule | pooled over the two trials | run 6 (GPU 0) | run 7 (GPU 1) |
| --- | --- | --- | --- |
| H1.1 the threshold is conformal | holds | holds | holds |
| H1.2 false alarms, at most 3% of at least 200 null blocks | **holds: 3/408** (0.7%; 95% upper bound 1.9%) | 3/204 | 0/204 |
| H1.3 primary: detection at 5% of capacity or more, each class at least 95% | **holds in every class: 210/210** (constant 72/72, dilute 72/72, duty 48/48, idle_gap 18/18) | 105/105 | 105/105 |
| H1.3 stretch: detection at 2% or more, each class at least 95% | **holds in every class: 285/290** (constant 92/96, dilute 95/96, duty 72/72, idle_gap 26/26) | 143/145 | 142/145 |
| H1.4 the time bound covers the seconds the hidden load ran, in at least 95% of hidden blocks | **holds: 321/321** | 160/160 | 161/161 |
| closure gap; with the measured slack | 5.62%; 12.3% | 5.62%; 12.3% | 5.62%; 11.7% |
| outcome (needs the slack-inflated gap at 5% or less) | **FAIL** | FAIL | FAIL |

- **The detector's rules hold; the outcome is FAIL because of the GPU's efficiency slack.** The probe measured `s_max`
  0.091 and 0.084 on these two T4s: the same verified work can cost that much less energy on another allowed setting of
  the software stack, and that much hidden work fits under the saving. The outcome rule adds it, weighted by the
  trial's average load (0.73 of capacity), to the closure gap: 6.7 and 6.1% of capacity, against 5% allowed in all.
  Amendment v0.6 said before the runs that a T4 would fail on this.
- The pooled lower bound on detection at 5% or more is 98.6%, the highest that 210 blocks can give.
- Where the amendment's stated expectations were wrong: it expected the 2% level to fail at blocks of 60 s, and it held;
  it expected the calibrated energy bound to cover under 95% near the power limit, and it covered 97.5% (reported only).
- Probe: 3 stack variants each (H1.6 needs 3). The container refuses clock and power-limit changes, so those variants
  were dropped and `s_max` is a lower bound for these GPUs. Energy floor 2.15e-12 and 2.14e-12 J/FLOP.
- Residency (T2) passes on both: honest false alarms 0.2% and 0.55%, parked-block detection 99.9% and 100%.
- Calibration drift: -0.18 and -0.01 SD, spread 1.04x and 0.92x.
- `closure verify` passes for both trials. The signed results reproduce from `raw.npz` (every flag and count the same;
  the largest relative difference in any number is 1.3e-12 and 5.0e-12), and the pooled reading reproduces exactly.
- Each pre-registration was stamped with OpenTimestamps before its trial (`extracted/gpu*/T1-long/prereg.json.ots`).

## What the raw data add (read after the runs: they describe, they decide nothing)

`reread.json` holds the numbers.

1. **The thresholds are the largest of 144 reference scores**: 2.29 and 2.43, in spreads of the reference blocks. The
   three false alarms, all on GPU 0, scored 2.33, 2.40 and 2.59; two were blocks in which the GPU ran flat out
   throughout.
2. **Every missed block carried a 2% label.** None at 5% or more was missed on either GPU.
3. **The curve misfits at the top of the load range.** Reference blocks with the GPU flat out throughout scored +1.57
   and +1.54 on average, against 0.37 and 0.41 for all others. At the top of the range nearly one rate of verified
   work comes with two busy times: 102 and 105 units a second on GPU 0, and 100 and 101 on GPU 1, at requested levels
   0.9 and 1, with the GPU busy 93% of the time at 0.9, where there are gaps between slots, and 99% flat out. A curve
   in work alone has to pass between them.
4. **At the power limit hidden work adds no energy; it displaces verified work.** At requested level 1 the load
   labelled 20% changed power by -0.6 W and -0.1 W and cut verified work by 40 and 37 units a second. This is run 5's
   finding again, on two more GPUs, and it is why H1.4 is read on time.

## The same data with the verifier's own request added (post hoc for these runs: it decides nothing)

Finding 3 suggests giving the analysis one more verified feature: the seconds of each window for which the verifier
asked for the GPU flat out. That is the `link-full` analysis, which amendment v0.7 declares as a comparison for
every later run. For these runs it was chosen after the data were seen, on these data.

| | registered analysis (signed) | `link-full` (post hoc) |
| --- | --- | --- |
| false alarms in 408 null blocks | 3 | 2 |
| detection at 5% or more | 210/210 | 210/210 |
| detection at 2% or more | 285/290 | 287/290 |
| time bound covers the hidden seconds | 321/321 | 321/321 |
| block spread of the busy-time residual, GPU 0 and GPU 1 | 0.69 s and 0.65 s | 0.48 s and 0.19 s |
| closure gap | 5.62% | 3.16% |
| slack-inflated gap | 12.3% | 9.8% |
| outcome | FAIL | FAIL |

Read one trial at a time it is not uniformly better: on GPU 0 the 2% level's constant class is 45/48, under that
class's 95%, and on GPU 1 the calibrated time bound, which is reported and decides nothing, covers 84.5%. Two other
features were tried on these data and not adopted, and are named here because they were tried: the seconds of load
the verifier asked for in each window (level times duration), with which GPU 0's constant class at 5% fell to 34/36
and GPU 1's floor time bound covered 91.9%; and both features together, which behaved like the second.
