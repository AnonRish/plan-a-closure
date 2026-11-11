# Shakedown run 5: Kaggle T4, the long trial, 8 to 9 November 2026

The first run of the long profile (`closure tier0 --trial-profile long`, plan-a-closure 0.7.0, commit `1656ad4`), on
one Tesla T4 of a Kaggle "GPU T4 x2" session, inside Kaggle's container, with NVML as the only power source. It is a
shakedown on a non-target device: assumption A6 does not hold and nothing here is a Plan A claim. The full account
is section 5 of `docs/DEVIATIONS.md`.

| file | what it is |
| --- | --- |
| `tier0_bundle.tar.gz` | the bundle as returned, sha256 `dd7e99973459c74557a4fc5707ebef6f16f54d937bfac564c31a6f300d710a1f` |
| `extracted/` | the bundle's summary, logs, probe and trial files without `raw.npz`, for reading in a browser |
| `drill.json` | A Narrow Path's mock training run on the same GPU after the trial (compliant, 10.4% of the budget) |
| `reread.json`, `physics.json`, `results_posthoc_link.json` | written by `python results/reread.py results/shakedown-2026-11-08-kaggle-t4-run5` from the bundle |

## What the registered reading says

Every step ran. Two reported a failed check, and the trial failed the false-alarm rule.

- **Trial (T1), as pre-registered: UNDERPOWERED, and H1.2 fails.** 11 false alarms in 204 null blocks (5.4%, limit 3%).
  H1.1 fails on normality (Jarque-Bera p 3e-10 and 1.7e-7). Detection at 5% or more: 99/102. Closure gap 17.8%.
- **Probe: exit 1.** Kaggle's container does not let the run change clocks or the power limit, so only 2 stack
  variants could be measured and H1.6 needs 3. `s_max` 0.096 is therefore a lower bound for this GPU.
- **Residency (T2): exit 1.** Detection 97.5% (195/200) against the registered 99%; honest false alarms 0/200.
- Calibration drift: +0.15 SD, spread 0.97x. Interleaving did what amendment v0.5 introduced it for.
- `closure verify` passes: chain, signature, schedule and order commitments, pre-registration, results and probe hashes.
- The pre-registration was stamped with OpenTimestamps before the trial (`extracted/T1-long/prereg.json.ots`). The
  proof was pending at four calendars when the bundle was written; `ots upgrade` and `ots verify` complete it.

## Why, read off the raw data (post hoc)

`reread.json` and `physics.json` hold the numbers; `closure physics --run <trial folder>` prints the table.

1. **All 11 false alarms are in blocks at one load level.** Of the 22 null blocks that spent most of their time at
   requested level 0.5, 11 raised an alarm; of the other 182, none did. With clocks not locked, the GPU ran that level
   on a faster clock (8.2 ms of busy time per unit of work, against 10.6 ms at level 0.3 and 9.2 ms at level 0.7) and
   drew 4 to 5 W more than a straight line in work gives. The registered model is a straight line.
2. **The combined test's threshold was a Gaussian fallback, and 0.7.0 did not say so.** The combined test splits alpha
   between the two channels; a conformal threshold at 0.005 needs 199 effective reference blocks and the run had 144.
   `methods_used` reported the single-channel tests ("conformal"). Since 0.8.0 it reports the combined test's method.
3. **The hidden-load labels understate the load.** On an otherwise idle GPU the loads labelled 2%, 5%, 10% and 20% of
   capacity (1.4, 3.5, 7 and 14 W) drew 2.9, 5.0, 8.1 and 15.8 W. The load generator ran whole GEMMs until each slot's
   hidden time was used up, so every slot overshot by up to one GEMM (6.6 ms of a 100 ms slot), which doubled the
   smallest load: the four loads were busy 6.8, 13.0, 19.7 and 39.2% of the time for duties of 3.7, 9.2, 18.4 and
   36.8%. Power per unit of duty was as estimated here (40 W); on run 4's GPU, with clocks locked high, it was 73 W.
   Detection "at 5%" and "at 2%" in this run is detection of loads 1.1 to 2.1 times larger (1.9 to 2.2 times in run 4).
4. **Near the power limit, hidden work adds no energy: it displaces verified work.** At requested level 1 the load
   labelled 20% changed power by -0.3 W and cut verified work by 33 units a second (35%). Energy closure, which assumes
   hidden energy adds to verified energy (A1), is blind there; what shows is that the verified work no longer
   explains the energy and busy time observed.

## The same data under amendment v0.6 (post hoc: it decides nothing)

`results_posthoc_link.json` is `closure reanalyze --analysis link` on this run's raw data: a calibrated curve for each
channel instead of a straight line, and one conformal threshold on the larger of the two channel scores. The analysis
was chosen after these data were seen, so this reading describes the run and decides nothing. The prospective test is
the next run.

| | registered analysis (signed) | link analysis (post hoc) |
| --- | --- | --- |
| false alarms in 204 null blocks | 11 (5.4%) | 4 (2.0%; 95% upper bound 4.4%) |
| threshold | Gaussian fallback | conformal |
| detection, label 5% or more | 99/102 | 102/102 (95% lower bound 97.1%) |
| detection, label 2% or more | 105/145 | 143/145 (95% lower bound 95.7%) |
| closure gap | 17.8% | 3.2% |
| slack-inflated gap (`s_max` 0.096) | 24.9% | 10.3% |
| energy bound covers the labelled hidden energy | 100% | 93.2% (H1.4 fails on this basis) |
| outcome | UNDERPOWERED | FAIL (H1.4, and the slack-inflated gap is above 5% in any case) |

The energy bound's 93.2% is finding 4 in numbers: it assumes additivity, and on this GPU additivity fails near the
power limit. The bounds that do not assume it held: energy above the least the verified work can cost covered the
labelled hidden energy in 100% of hidden blocks, and both time bounds covered an approximate truth (the busy time each
label added on an idle GPU) in 162 of 162. Amendment v0.6 therefore reads H1.4 on the time bound, against hidden
seconds that the load generator now counts as it runs.
