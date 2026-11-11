# Shakedown run 4: Colab T4, the smoke trial with clocks locked, 8 to 9 November 2026

The first run with no step failing (`closure tier0`, plan-a-closure 0.7.0, commit `1656ad4`), on a Tesla T4 in a
Google Colab VM, with NVML as the only power source. It is a shakedown on a non-target device: assumption A6 does not
hold and nothing here is a Plan A claim. The full account is section 4 of `docs/DEVIATIONS.md`.

| file | what it is |
| --- | --- |
| `tier0_bundle.tar.gz` | the bundle as returned, sha256 `bdcfcb280770b7abe4b4783989d796a0fabc8a0764978eb357a398fbd124d7c6` |
| `extracted/` | the bundle's summary, logs, probe and trial files without `raw.npz`, for reading in a browser |
| `drill.json` | A Narrow Path's mock training run on the same GPU after the trial (compliant, 11.5% of the budget) |
| `reread.json`, `physics.json`, `results_posthoc_link.json` | written by `python results/reread.py results/shakedown-2026-11-08-colab-t4-run4` from the bundle |

## What the registered reading says

- Every step exited 0: energy tracks work (r2 0.966), the probe measured 10 stack variants (`s_max` 0.1255), the
  residency test passed (0/200 false alarms, 200/200 parked provers caught, 17 blocks per challenge), and the trial ran
  with SM clocks locked at 1110 MHz.
- **Trial (T1): UNDERPOWERED**, as a one-hour trial must be. H1.1 fails on the effective number of calibration blocks
  (12.4 and 7.4; the rule needs 15). False alarms 0/23; H1.2 needs 200 null blocks. Detection at 5% or more: 24/24.
- Calibration drift: +0.60 SD between calibration and audit (spread 0.88x). This smoke trial still calibrated before
  the audit; since 0.8.0 the smoke trial interleaves like the long one.
- `closure verify` passes.

## What the raw data add (post hoc)

1. **With clocks locked, time adds up.** A unit of work took 8.0 to 8.4 ms of busy time at every requested level up to
   0.7, and the load labelled 20% added the same busy share at levels 0, 0.2 and 0.3 (0.36, 0.38, 0.40). On Kaggle
   (run 5, clocks not locked) it did not.
2. **The hidden-load labels understate the load.** The loads labelled 5% and 20% (3.5 and 14 W) drew 7.8 and 25.9 W
   on an otherwise idle GPU: with clocks locked at 1110 MHz the bursts drew 73 W per unit of duty, and the duty had
   been computed from the power limit less idle power (41 W).
3. **At full load, hidden work displaces verified work.** At requested level 1 the load labelled 20% changed power by
   -0.6 W and cut verified work by 35 units a second.
4. **The link analysis on this run is underpowered too** (`results_posthoc_link.json`, post hoc): 60 reference blocks
   are too few for a conformal threshold at alpha = 0.01, which needs 99, so it falls back to Student's t and H1.1
   fails. It flags 2 of 23 null blocks. The 0.8.0 smoke trial has 100 reference blocks for this reason.
