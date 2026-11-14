# Deviations and hardware runs

Every deviation from [PREREGISTRATION.md](PREREGISTRATION.md) is appended here with its date and reason, and the
original analysis is still reported. Every run on real hardware is listed here too, whatever it showed.

## 1. Colab T4 shakedown, 8 November 2026 (plan-a-closure 0.5.4, commit 579a533)

**What ran.** `closure tier0 --confirm-hardware --gpu 0` from [notebooks/tier0_colab.ipynb](../notebooks/tier0_colab.ipynb)
on a free Google Colab GPU, 2026-11-08 02:32:50Z to 02:44:31Z. A labelled shakedown, not the registered pilot: a cloud
VM, no independent power meter (assumption A6 does not hold; NVML only), and a T4 rather than an H100, H200 or B300.

**Device.** Tesla T4, compute capability 7.5, driver 580.82.07, torch 2.14.1+cu130, Python 3.13.16, running as root;
power limit 70 W (settable 60 to 70 W), 87 SM clocks from 300 to 1590 MHz, 15.5 GB free.

**Record.** [results/shakedown-2026-11-08-colab-t4/](../results/shakedown-2026-11-08-colab-t4/) holds the bundle as
returned (`tier0_bundle.tar.gz`, sha256 `2fd41f34f679dc061b899e89bfce1c9fcdc62fbf2840f89205561fa2ec409a5f`) and its
extracted summary and logs.

| step | result |
| --- | --- |
| unit tests | 249 passed, 1 skipped (8.9 min) |
| selftest | passed |
| preflight | passed: NVML energy counter advancing, GPU matched by UUID, root, int8 GEMM available. Warnings: no fp8 (needs compute capability 8.9), persistence mode off, clock sync not confirmed (no systemd in the VM) |
| hw-selftest | **failed**: r2 = 0.719 (needs > 0.9), residual SD 7.89 J, idle 30.0 W, fitted 38.3 J per window-second plus 15.95 J per unit |
| hw-probe, hw-state, hw-trial, verify | skipped (the run stops when hw-selftest fails) |
| hw-restore | clocks unlocked, power limit put back to 70 W |

**Diagnosis: the load generator, not the physics.** The unit of verified work was a fixed 8192 x 8192 bf16 GEMM plus a
1 GiB memory pass, 2 to 3 ms on an H100. Turing has no bf16 tensor cores, so on the T4 the GEMM ran on a slow path
(a public benchmark measured bf16 4.3 times slower than fp16 for a whole training step on a T4; for a bare GEMM the gap is
larger): about 0.54 s per unit, more than five times the 100 ms slot. A load level L runs units while the first L x 100 ms
of each slot have not elapsed, so every level above zero ran at least one whole unit per slot, and 25%, 50%, 75% and
100% load all ran flat out at the 70 W cap. Energy per window was then the same at every loaded level (about 68 J),
while the number of units finished in a window flickered between 1 and 2 (units were counted at slot ends). There was
nothing for the fit to explain.

The evidence:

1. The fitted numbers say so. Loaded windows: 38.3 + 15.95 x 1.86 = 68 W, at the cap; 1.86 units per one-second window
   means 0.54 s per unit.
2. A model in the loop reproduces the failure. `results/shakedown-2026-11-08-colab-t4/model/repro_t4.py` runs the real
   0.5.4 load generator, window logic and hw-selftest fit, with only the GPU replaced by a timing and power model (0.54 s
   per bf16 unit, 30 W idle, 68 W while a unit runs). With an exact meter it fails with r2 = 0.84; with 25% unit-time
   jitter and 4 W of power ripple (a capped T4 throttles its clock) r2 = 0.77, residual SD 7.3 J and coefficients
   (36.7 J/s, 16.3 J per unit), against the observed 0.72, 7.9 J and (38.3, 16.0).
3. The same model with the 0.5.5 load generator passes: the unit is sized to 4096 x 4096 fp16 (6 ms), power rises
   30, 40, 49, 59, 68 W across the five levels, and r2 = 1.000 (0.998 with jitter and ripple). Outputs are in `model/`.
   `tests/test_torch_cpu.py::test_a_unit_longer_than_the_slot_reproduces_the_t4_failure_and_sizing_fixes_it` runs a
   time-scaled copy of both runs in every CI build.

**What the run shows.** The hardware plumbing works on a T4 in a VM: the NVML energy counter, matching the CUDA device
to its NVML GPU by UUID, root clock and power control, restoring them, and the unit tests. **It shows nothing about
whether energy tracks verified work on a GPU**, because the work did not vary. That question is still open.

**Changes in response** (0.5.5, before any audit data exist; amendment v0.3 in PREREGISTRATION.md):

1. The unit of work is sized to the slot: halved from 8192 until one unit takes at most 20 ms, a fifth of the slot.
   On an H100 the 8192 unit already fits, so nothing changes there.
2. Native half precision: bf16 from compute capability 8.0, fp16 before it (V100, T4), in the load generator and in the
   probe's reference stack alike.
3. Units are counted as they finish, not at slot ends.
4. Capacity comes from the device. `p_max` was a fixed 700 W; it is now the GPU's NVML power limit (700 W on an H100 or
   H200 SXM, 350 W on an H100 PCIe, 70 W on a T4), and idle power is measured at start. Both are recorded in
   `prereg.json` (`cfg.p_max_w`, `cfg.workload`). With the fixed 700 W, a T4 trial would have labelled each injected
   hidden load with about 15 times the energy actually injected.
5. hw-selftest also requires the load levels to do different work: the units at 25% load must be under 80% of the units
   at 100% load. Otherwise a saturated load generator fails only by accident of the fit, and two clusters of points
   (idle and flat out) could pass while the trial behind them measures nothing. It now prints the units and power per
   level, the unit of work, and a diagnosis when it fails.
6. `closure tier0` passes hw-selftest's unit on to hw-probe and hw-trial, so all three measure the same unit, and
   SUMMARY.md reports the hw-selftest result.

**Not changed:** the r2 > 0.9 threshold, the trial's analysis and thresholds, and the 0.5.4 result above, which stands
as recorded.

**Next:** the same notebook on 0.5.5. If the diagnosis is right, hw-selftest passes and the run goes on to hw-probe,
hw-state and the smoke trial; if it fails again, the per-level table says where. Either result is appended here.

## 2. Colab T4 run, 8 November 2026, 07:11Z (plan-a-closure 0.6.0): bundle lost

**What ran.** The same notebook on 0.6.0, on a different T4 (`GPU-c9928662-06ab-1210-f4b5-093998576a82`), power limit
70 W. **Every step ran:** unit tests, selftest, preflight and hw-selftest passed; hw-probe exit 0 (34.8 min); hw-state
exit 1 (8.6 min); hw-trial exit 0 (60.6 min); verify passed; hw-restore passed.

**What was lost.** The bundle (sha256 `eb9dbb7873036e691d853ab86d66974d23182f086f2fbacec4aaa1ea0e7cdf80`) was not
downloaded before Colab replaced the machine; the download cell then failed because the restarted session had
forgotten the run folder. The only record is the console transcript,
[results/shakedown-2026-11-08-colab-t4-run2/console.txt](../results/shakedown-2026-11-08-colab-t4-run2/console.txt).
Its numbers cannot be checked, so nothing below relies on them. Since 0.6.1 the summary and download cells find the
run folder themselves. Run 3 repeated it with the same code.

## 3. Colab T4 run, 8 November 2026, 15:53Z to 17:50Z (plan-a-closure 0.6.0)

**What ran.** The same notebook and command on 0.6.0, on a third T4 (`GPU-7174a006-6864-a619-70b7-36781e48e9e1`),
NVML only, no independent meter. **Every step ran.** Bundle as returned:
[results/shakedown-2026-11-08-colab-t4-run3/](../results/shakedown-2026-11-08-colab-t4-run3/), sha256
`58a273addfd4419ea39c1fc99a025ed4c21dd0514323ecd2d2311ed2aff0e042`.

| step | result |
| --- | --- |
| unit tests | 293 passed, 1 skipped (10.8 min) |
| selftest, preflight | passed (warnings: fp8 needs compute capability 8.9, persistence mode off, no clock sync, no tcpdump) |
| hw-selftest | **passed**: r2 = 0.941 (needs > 0.9), idle 28.1 W, work at 25% / 100% load = 0.28 (needs < 0.8); unit 4096 x 4096 float16, 9.0 ms. Power by level: 28.1, 38.5, 62.5, 64.7 and 68.0 W at 0, 30, 70, 91 and 108 units per window: the 70 W cap flattens the top half |
| hw-probe | passed: 15 variants measured, fp8 dropped (needs compute capability 8.9), int8 not allowed (1.6% numerical error against a 0.5% tolerance). Efficiency slack s_max = 13.5%, the one-sided 95% bound on a 9.7% saving measured with clocks locked at 405 MHz at 50% load; energy floor 2.04e-12 J/FLOP (locked at 1575 MHz, 90% load); band/floor 5.32 |
| hw-state | **failed as registered**: honest false alarms 0/200, parked-block detection 94.0% (needs 99%). Timing separated the tiers clearly: median 25.7 ms resident, 55.0 ms with parked blocks, threshold 37.1 ms |
| hw-trial (smoke) | ran: false positives 3/23 (combined; energy channel 4/23, busy-time channel 0/23); closure gap 31.6% of capacity, slack-inflated 39.8% |
| verify | passed: chain, signature, schedule commitment, pre-registration, results and probe hashes |
| hw-restore | clocks unlocked, power limit put back to 70 W |

**hw-state: a design limit, not the physics.** With 8 of 32 blocks parked and 8 blocks per challenge, a challenge
samples no parked block with probability C(24, 8) / C(32, 8) = 7.0%, so no timing test could detect more than 93.0%.
The 94.0% measured (188 of 200) is what catching every challenge that touched a parked block gives (probability 0.35 of
at least 188 at 93.0%); the mock prover with the same settings catches 185 of 185 touching challenges. The registered
99% was out of reach with the default challenge size. Since 0.6.1 the size is chosen so that sampling alone touches a
parked block 99.9% of the time (17 of 32 blocks), and the result reports detection among touching challenges
separately (amendment v0.4).

**hw-trial: the energy channel drifted within the hour.** The smoke trial calibrates for 30 minutes and then audits for
30. On this VM the GPU's power behaviour changed between the two (`drift.py` in the results folder reproduces every
number):

- idle power fell from 29.8 W (first 20 minutes) to 27.4 W (last 20), about 70 J over a 30-second block;
- at mid load, energy per unit of work rose from 0.38 to 0.55 J between the first and second half hour;
- at full load, work per busy second rose from about 111 to 120 units: the clocks changed;
- the probe had already shown the unlocked reference running anywhere from 585 to 1095 MHz depending on load.

So audit blocks with no hidden energy had residuals of mean -36 J and SD 85 J, against SD 28 J during calibration
(skewed: Jarque-Bera p = 3e-12 for the energy channel, so its assumption A3 fails and its claims from this run are void).
That breaks assumption A2 (same clocks and cooling for calibration and audit), and it is where the false alarms come
from. The busy-time channel held: 0/23 false alarms and residuals consistent with normal (p = 0.42); the smallest
hidden load it detects per block is 9.5% of the block's busy time, against 5.0% of capacity energy for the energy
channel. The 31.6% closure gap is the smoke profile's limit (no cell had more than 7 blocks, too few to certify 95%
detection), not a measurement of the method.

*Correction (8 November 2026, 0.7.0).* This paragraph first said the busy-time channel's smallest detectable load was
0.14% of capacity. `results.json` had divided the busy-time figure (seconds) by the block's capacity energy (joules)
instead of its capacity time, which understates it by a factor of `p_max` (70 on this T4). Corrected in the code and
here; no decision rule uses the figure (amendment v0.5).

Since 0.6.1, `closure tier0` locks the trial's SM clocks at the highest clock the probe saw the GPU hold at full load
under its power limit, and records it in `prereg.json` (amendment v0.4). On this GPU that is 1110 MHz, which held at
65.2 W; locks at 1575 and 1335 MHz were pulled down to 1125 and 975 MHz by the cap. A locked clock removes the
frequency drift; idle-power drift from temperature remains, and interleaving calibration with audit blocks is the next
design question for Tier 1.

**What these runs show.** On three T4s in Colab VMs: the whole pipeline runs and restores the GPU; energy tracks verified
work once the unit fits the slot; the probe's clock and power controls work; device-memory residency shows up clearly
as time; and an energy model calibrated in one half hour does not carry over to the next on an unlocked, power-capped
GPU in a VM. None of it is evidence about H100s, independent metering or the registered thresholds.

*Note on hidden-load labels (10 November 2026, 0.8.0).* The hidden-load fractions quoted in this document are
labels: what the load generator was asked to inject. `closure physics` now measures what each label drew on an
otherwise idle GPU in the same run. In run 3 the labels were close: 5% and 20% of capacity (3.5 and 14 W) drew 3.4 and
14.8 W. In runs 4 and 5 they understate the load, for two reasons. The load generator turned a label into a duty
cycle from the power limit less idle power (about 40 W per unit of duty), and it ran whole GEMMs until each slot's
hidden time was used up. On run 4's GPU, with clocks locked at 1110 MHz, the bursts drew 73 W per unit of duty, and
the loads labelled 5% and 20% drew 11% and 37% of capacity. On run 5's, with clocks free, the bursts drew the 40 W
assumed, but whole GEMMs overshot each slot by up to one GEMM (6.6 ms of a 100 ms slot), which doubled the smallest
load: the loads labelled 2, 5, 10 and 20% drew 4.2, 7.2, 11.5 and 22.5% (`physics.json` in each results folder).
"Detection at 5%" in runs 4 and 5 is detection of a load 1.4 to 2.2 times larger. Since 0.8.0 the hidden load is
measured on its own before the trial, a label is its measured power, and hidden GEMMs are paid for from a running
credit so that the average duty is exact (amendment v0.6 (d)).

## 4. Colab T4 run, 8 to 9 November 2026, 23:13Z to 01:23Z (plan-a-closure 0.7.0, commit 1656ad4)

**What ran.** `closure tier0` from the Colab notebook on a fourth T4 (`GPU-ac10dccd...`), NVML only, no independent
meter: a shakedown. **Every step exited 0**, for the first time. Bundle as returned:
[results/shakedown-2026-11-08-colab-t4-run4/](../results/shakedown-2026-11-08-colab-t4-run4/), sha256
`bdcfcb280770b7abe4b4783989d796a0fabc8a0764978eb357a398fbd124d7c6`.

| step | result |
| --- | --- |
| unit tests | passed (13.2 min) |
| hw-selftest | passed: r2 = 0.966, idle 28.2 W, work at 25% / 100% load = 0.29 |
| hw-probe | passed: 10 allowed stack variants, s_max = 12.6% (stack 12.4%, operand 12.6%); energy floor 1.96e-12 J/FLOP |
| hw-state | **passed**: honest false alarms 0/200, parked-block detection 200/200, 17 blocks per challenge (amendment v0.4) |
| hw-trial (smoke) | ran with SM clocks locked at 1110 MHz: false positives 0/23; closure gap 31.6%, slack-inflated 39.7% |
| verify | passed |
| mock training run | compliant: 11.5% of the budget used (`drill.json`) |

**The decision rules, read at this scale: UNDERPOWERED,** as a one-hour trial must be. H1.1 fails on the effective
number of calibration blocks (12.4 for energy, 7.4 for busy time; the rule needs 15), H1.2 needs 200 null blocks and
has 23, and detection at labels of 5% or more was 24/24.

**Drift.** Audit blocks without hidden load sat +0.60 calibration SDs above the calibration blocks (spread 0.88x):
with clocks locked the frequency drift of run 3 is gone, and a smaller shift between the first half hour and the second
remains. This smoke trial still calibrated before its audit.

**What the raw data add (post hoc; `python results/reread.py results/shakedown-2026-11-08-colab-t4-run4`).**

- With clocks locked, time adds up: a unit of work took 8.0 to 8.4 ms of busy time at every requested level up to 0.7,
  and the load labelled 20% added the same busy share at levels 0, 0.2 and 0.3 (0.36, 0.38, 0.40).
- The labels understate the load (see the note on labels above): 5% drew 7.8 W, not 3.5; 20% drew 25.9 W, not 14.
- At full load the load labelled 20% changed power by -0.6 W and cut verified work by 35 units a second: hidden work
  displaces verified work on a full GPU.
- The link analysis of amendment v0.6, applied post hoc, is underpowered here too: 60 reference blocks are too few for
  a conformal threshold at alpha = 0.01 (99 needed), it falls back to Student's t, and it flags 2 of 23 null blocks.

## 5. Kaggle T4 run, 8 to 9 November 2026, 21:03Z to 07:11Z (plan-a-closure 0.7.0, commit 1656ad4): H1.2 fails

**What ran.** `closure tier0 --trial-profile long` from [notebooks/tier0_kaggle.ipynb](../notebooks/tier0_kaggle.ipynb)
as a committed Kaggle run, on one T4 of a "GPU T4 x2" session (`GPU-763d3d8a...`, driver 580.178.04, torch
2.11.0+cu130), inside Kaggle's container, NVML only, no independent meter: a shakedown. The first run of the long
profile, and the first large enough to read the decision rules. **Every step ran; two reported a failed check, and the
trial failed the false-alarm rule.** Bundle as returned:
[results/shakedown-2026-11-08-kaggle-t4-run5/](../results/shakedown-2026-11-08-kaggle-t4-run5/), sha256
`dd7e99973459c74557a4fc5707ebef6f16f54d937bfac564c31a6f300d710a1f`.

| step | result |
| --- | --- |
| unit tests | passed (13.0 min) |
| hw-selftest | passed: r2 = 0.969, idle 31.4 W, work at 25% / 100% load = 0.34 |
| hw-probe | **exit 1**: the container does not allow clock or power-limit changes ("The current user does not have permission to change clocks"), so 2 stack variants were measurable and H1.6 needs 3. s_max = 9.6% (stack 8.5%, operand 9.6%) is a lower bound for this GPU; energy floor 2.06e-12 J/FLOP |
| hw-state | **failed**: parked-block detection 97.5% (195/200; needs 99%), honest false alarms 0/200. Median 54.5 ms resident, 113 ms with parked blocks, threshold 70.5 ms |
| hw-trial (long) | ran 549 minutes, SM clocks not locked: **false positives 11/204 (5.4%)**; closure gap 17.8%, slack-inflated 24.9% |
| verify | passed: chain, signature, schedule and order commitments, pre-registration, results and probe hashes |
| mock training run | compliant: 10.4% of the budget used (`drill.json`) |

The pre-registration was stamped with OpenTimestamps before the trial (`T1-long/prereg.json.ots`); the proof was
pending at four calendars when the bundle was written, and `ots upgrade` then `ots verify` complete it.

**The decision rules as registered: UNDERPOWERED, and H1.2 fails.**

| rule | reading |
| --- | --- |
| H1.1 calibration valid | fails: Jarque-Bera p = 3e-10 (energy) and 1.7e-7 (busy time); n_eff 105 and 101 |
| H1.2 false alarms at most 3% on 200 null blocks | **fails: 11/204 = 5.4%** (95% upper bound 8.8%) |
| H1.3 primary, labels of 5% or more | 99/102 pooled (95% lower bound 92.6%, not certified); duty 22/24 fails |
| H1.3 stretch, labels of 2% or more | 105/145 pooled; fails in every class |
| H1.4 energy bound | holds against the labels (100%) |
| drift | +0.15 SD, spread 0.97x: interleaving worked (run 4, calibrated first: +0.60 SD) |

This is the result as registered, and it stands: on this GPU, under 0.7.0's analysis, the false-alarm rate was not
controlled.

**Why (post hoc; `python results/reread.py results/shakedown-2026-11-08-kaggle-t4-run5` reproduces every number).**

1. *The model is a straight line and the GPU is not.* All 11 false alarms are among the 22 null blocks that spent most
   of their time at requested level 0.5; the other 182 null blocks raised none. With clocks not locked, the GPU ran
   that level on a faster clock (8.2 ms of busy time per unit of work, against 10.6 ms at level 0.3 and 9.2 ms at 0.7)
   and drew 4 to 5 W more than a straight line in work gives. Between half load and full load, work rose from 70 to
   93 units a second and power from 62.6 to 65.4 W: under its 70 W limit the GPU lowers its clocks.
2. *The combined test ran on a Gaussian fallback and 0.7.0 did not say so.* The combined test gives each channel
   alpha/2 = 0.005, and a conformal threshold at 0.005 needs 199 reference blocks; the run had 144. `methods_used`
   reported the single-channel tests, which were conformal. All 11 alarms are energy-channel residuals of +2.7 to +3.0
   SD against a Gaussian threshold of 2.64 SD.
3. *The labels understate the load* (the note on labels before section 4): 2, 5, 10 and 20% drew 4.2, 7.2, 11.5 and
   22.5%.
4. *Near the power limit hidden work adds no energy; it displaces verified work.* At requested level 1 the load
   labelled 20% changed power by -0.3 W and cut verified work by 33 units a second (35%). At levels of 0.5 and above,
   hidden loads changed power by -0.5 to +2.4 W and removed 2 to 33 units a second. Assumption A1 (hidden energy adds
   to verified energy) fails there. What shows instead is that the verified work done no longer explains the energy
   and busy time observed. At low levels, with clocks free, hidden load sped the verified work up (by about 9 units a
   second at the same requested level in four cells), so time is not additive either unless clocks are locked (run 4,
   where it was).
5. *hw-state: one parked block is lost in the total.* A challenge of 17 blocks that touched a single parked block took
   about 14 ms longer than a 54 ms total with about 5 ms of jitter. About 1% of challenges touch exactly one.
6. *hw-probe:* a platform limit. Kaggle's container runs as root and still may not change clocks.

**What changed (0.8.0, amendment v0.6, written before any further run).** A calibrated curve for each channel instead
of a straight line, and one conformal threshold on the larger channel score, with the method of the deciding test
reported (1, 2). The hidden load measured on its own before the trial, its seconds counted as it runs (3). H1.4 read
on a time bound that does not assume additivity, with the energy bounds reported as checks of A1 (4). Residency judged
by the slowest block of a challenge, timed in one interleaved pass (5). A fresh seed for every hardware run: runs 1 to
5 all used seed 1.

**The same data under the link analysis (post hoc: it describes this run and decides nothing).** The analysis was
chosen after these data were seen, on these data. `results_posthoc_link.json`:

| | registered analysis (signed) | link analysis (post hoc) |
| --- | --- | --- |
| false alarms in 204 null blocks | 11 (5.4%) | 4 (2.0%; 95% upper bound 4.4%) |
| threshold of the combined test | Gaussian fallback | conformal |
| detection, labels of 5% or more | 99/102 | 102/102 (95% lower bound 97.1%) |
| detection, labels of 2% or more | 105/145 | 143/145 (95% lower bound 95.7%) |
| closure gap | 17.8% | 3.2% |
| slack-inflated gap (s_max 9.6%) | 24.9% | 10.3% |
| energy bound covers the labelled hidden energy | 100% | 93.2% |
| outcome | UNDERPOWERED | FAIL |

The post hoc outcome is FAIL twice over. The energy bound covers 93.2% of hidden blocks, under H1.4's 95%: finding 4
in numbers, since that bound assumes additivity. And the slack-inflated gap is above 5% whatever the closure gap, because
the probe's slack alone is 9.6%. The bounds that do not assume additivity held: energy above the least the verified
work can cost covered the labelled hidden energy in 100% of hidden blocks, and both time bounds covered an approximate
truth (the busy time each label added on an idle GPU, since this run did not count hidden seconds) in 162 of 162.

**What runs 4 and 5 show.** On two more T4s: the pipeline runs unattended for ten hours and its evidence verifies;
interleaving removes calibration drift; a straight-line energy model does not hold on a power-limited GPU with free
clocks, and the registered analysis failed its own false-alarm rule because of it; energy closure is blind to hidden
work on a GPU at its power limit, where the time channel and the displaced verified work carry the signal; and the
efficiency slack measured on a T4 (10 to 13%) alone exceeds the 5% the outcome rule allows, so on this GPU the
registered outcome is FAIL however good the detector. None of it is evidence about H100s, independent metering or the registered
thresholds. The prospective test of amendment v0.6 is the next run.

## 6. Kaggle T4 x2 campaign, 11 to 12 November 2026, 19:58Z to 06:01Z (plan-a-closure 0.8.0, commit 438fcbd): every decided rule holds; FAIL on the slack

**What ran.** `closure tier0 --trial-profile long --campaign kaggle-20261111-195848:i/2` from
[notebooks/tier0_kaggle.ipynb](../notebooks/tier0_kaggle.ipynb) as a committed Kaggle run: one trial on each T4 of a
"GPU T4 x2" session, at the same time (run 6 on `GPU-71bcb58e...`, run 7 on `GPU-876c9e8c...`; driver 580.178.04,
torch 2.11.0+cu130), inside Kaggle's container, NVML only, no independent meter: a shakedown. It is the first
prospective test of amendment v0.6: the analysis, the labels, the thresholds and the campaign were fixed and published
(commit 438fcbd) before any of these data existed, and each trial drew its own seed. **Every step of both runs ran and
exited 0.** Bundles as returned:
[results/shakedown-2026-11-11-kaggle-t4-runs6-7/](../results/shakedown-2026-11-11-kaggle-t4-runs6-7/), sha256
`b0d99770ef90d069555a4acab85d4d08d9db1d5b431f3fd6dc105ca0ba4345d3` (run 6) and
`9a136d861ea55ee710a7a93b0249762f70fe1661feeebe9c1ced04e4f96cef05` (run 7).

| step | run 6 (GPU 0, seed 1886737444) | run 7 (GPU 1, seed 1231193211) |
| --- | --- | --- |
| unit tests | passed (340 passed, 1 skipped; 14.0 min) | not run: the notebook runs them once, with GPU 0 |
| hw-selftest | passed: r2 = 0.948, idle 29.8 W, work at 25% / 100% load = 0.28 | passed: r2 = 0.952, idle 29.2 W, 0.28 |
| hw-probe | exit 0 with 3 stack variants (H1.6 needs 3). The container refuses clock and power-limit changes, so those variants were dropped and s_max = 9.1% (stack 8.0%, operand 9.1%) is a lower bound for this GPU; energy floor 2.15e-12 J/FLOP | 3 stack variants; s_max = 8.4% (stack 6.8%, operand 8.4%), a lower bound; energy floor 2.14e-12 J/FLOP |
| hw-state | passed: honest false alarms 4/2000 (0.2%), parked-block detection 999/1000 | passed: 11/2000 (0.55%), 1000/1000 |
| hw-trial (long) | ran 552 minutes, SM clocks not locked: false positives 3/204; closure gap 5.62%, slack-inflated 12.3% | ran 552 minutes, not locked: 0/204; 5.62%, 11.7% |
| verify | passed | passed |

**The pre-registered rules, read on the campaign** (`closure pool`; `CAMPAIGN.md` and `pooled.json` as the session
wrote them, reproduced exactly from the two bundles):

| rule | pooled | run 6 | run 7 |
| --- | --- | --- | --- |
| H1.1 the threshold is conformal | holds | holds | holds |
| H1.2 false alarms: at most 3% of at least 200 null blocks | **holds: 3/408** (0.7%; 95% upper bound 1.9%) | 3/204 | 0/204 |
| H1.3 primary: detection at 5% or more, each class at least 95% | **holds in every class: 210/210** (constant 72/72, dilute 72/72, duty 48/48, idle_gap 18/18); 95% lower bound 98.6% | 105/105 | 105/105 |
| H1.3 stretch: detection at 2% or more, each class at least 95% | **holds in every class: 285/290** (constant 92/96, dilute 95/96, duty 72/72, idle_gap 26/26); 95% lower bound 96.4% | 143/145 | 142/145 |
| H1.4 the time bound covers the seconds the hidden load ran in at least 95% of hidden blocks | **holds: 321/321** | 160/160 | 161/161 |
| closure gap; slack-inflated gap | 5.62%; 12.3% | 5.62%; 12.3% | 5.62%; 11.7% |
| outcome (PASS needs a slack-inflated gap of 5% or less) | **FAIL** | FAIL | FAIL |

Reported only, as checks of additivity (A1): the calibrated time bound covered 99.1% of hidden blocks, and the energy
bound covered the hidden load's solo energy in 97.5% (calibrated) and 100% (floor). Calibration drift: -0.18 and -0.01
SD, spread 1.04x and 0.92x. The lower bound of 98.6% on detection at 5% or more is the highest that 210 blocks can
give.

**Against what amendment v0.6 said before the runs.**

| stated beforehand | what happened |
| --- | --- |
| On a T4 the outcome will still be FAIL, because the probe's slack puts the slack-inflated gap above 5% | as stated: FAIL, with s_max 9.1% and 8.4% |
| The 2% level will probably fail at blocks of 60 s or less | wrong here: it held in every class (285/290) |
| The calibrated energy bound will probably cover less than 95% near the power limit | wrong here: 97.5% |
| If H1.2 fails again, the link analysis is wrong on this hardware | H1.2 held: 3/408 |

**What the raw data add (read after the runs; they describe and decide nothing).** `reread.json` in the results
folder holds the numbers.

1. *The thresholds are the largest of 144 reference scores*: 2.29 and 2.43, in spreads of the reference blocks. The
   three false alarms, all in run 6, scored 2.33, 2.40 and 2.59; two were blocks with the GPU flat out throughout.
2. *Every missed block carried a 2% label.* None at 5% or more was missed on either GPU.
3. *The curve misfits at the top of the load range.* Reference blocks with the GPU flat out throughout scored +1.57 and
   +1.54 on average, against 0.37 and 0.41 for the others. Nearly one rate of verified work comes with two busy times
   there: 102 and 105 units a second in run 6, and 100 and 101 in run 7, at requested levels 0.9 and 1, with the GPU
   busy 93% of the time at 0.9, where there are gaps between slots, and 99% flat out. A curve in work alone has to pass
   between the two.
4. *At the power limit hidden work adds no energy; it displaces verified work.* At requested level 1 the load labelled
   20% changed power by -0.6 W and -0.1 W and cut verified work by 40 and 37 units a second: run 5's finding on two
   more GPUs, and the reason H1.4 is read on time.

**The same data with the verifier's own request added (post hoc: it describes these runs and decides nothing).**
Finding 3 suggests one more verified feature for both curves: the seconds of each window for which the verifier asked
for the GPU flat out. That is the `link-full` analysis, which amendment v0.7 declares as a comparison for every later
run. Here it was chosen after these data were seen, on these data.

| | registered analysis (signed) | `link-full` (post hoc) |
| --- | --- | --- |
| false alarms in 408 null blocks | 3 | 2 |
| detection, 5% or more | 210/210 | 210/210 |
| detection, 2% or more | 285/290 | 287/290 |
| time bound covers the hidden seconds | 321/321 | 321/321 |
| block spread of the busy-time residual, run 6 and run 7 | 0.69 s and 0.65 s | 0.48 s and 0.19 s |
| closure gap | 5.62% | 3.16% |
| slack-inflated gap | 12.3% | 9.8% |
| outcome | FAIL | FAIL |

One trial at a time it is not uniformly better: in run 6 the 2% level's constant class is 45/48, under that class's
95%, and in run 7 the calibrated time bound, which is reported and decides nothing, covers 84.5%. Two other features
were tried on these data and not adopted, and are named because they were tried: the seconds of load the verifier
asked for in each window (level times duration), with which run 6's constant class at 5% fell to 34/36 and run 7's
floor time bound covered 91.9%; and both features together, which behaved like the second.

**Mock training run** (`drill.json`, GPU 0 after the trials): compliant. The provider, who sees only the energy meter,
stopped the job when the energy drawn could have paid for the budget of 1e16 FLOP at the probe's energy floor; the job
had by then logged 1.29e15 FLOP, 12.9% of the budget. The bound is conservative by a factor of about 8 on this GPU.

## 7. Colab T4 run, 12 November 2026, 16:19Z to 21:16Z (plan-a-closure 0.8.0, commit 438fcbd): H1.3 fails by one block in each of two classes

**What ran.** `closure tier0 --trial-profile medium` from [notebooks/tier0_colab.ipynb](../notebooks/tier0_colab.ipynb)
on a free Colab T4 (`GPU-5389cace...`, driver 580.82.07, torch 2.14.1+cu130), inside Colab's virtual machine, NVML
only, no independent meter: a shakedown. The second prospective test of amendment v0.6, the first run of the medium
profile, and the first trial of that amendment with its clocks locked (at 870 MHz, by the rule of amendment v0.4).
**Every step ran and exited 0, and the trial failed the detection rule.** Bundle as returned:
[results/shakedown-2026-11-12-colab-t4-run8/](../results/shakedown-2026-11-12-colab-t4-run8/), sha256
`3efade48adb610882a635fc18f7644b4fbba4b4a09800e43510d5d445911f569`.

| step | result |
| --- | --- |
| unit tests | passed (340 passed, 1 skipped; 15.0 min) |
| hw-selftest | passed: r2 = 0.933, idle 28.8 W, work at 25% / 100% load = 0.28 |
| hw-probe | exit 0 with 10 stack variants (Colab allows clock and power-limit changes; fp8 is not on a T4): s_max = 10.8% (stack 9.1%, operand 10.8%); energy floor 2.03e-12 J/FLOP |
| hw-state | passed: honest false alarms 6/2000 (0.3%), parked-block detection 1000/1000 |
| hw-trial (medium) | ran 233 minutes, SM clocks locked at 870 MHz, seed 1773548153: false positives 0/204; closure gap 17.8%, slack-inflated 25.9% |
| verify | passed |

**The pre-registered rules, read on this trial.**

| rule | result |
| --- | --- |
| H1.1 the threshold is conformal | holds |
| H1.2 false alarms | holds: 0/204 (95% upper bound 1.5%) |
| H1.3 primary: detection at 5% or more, each class at least 95% | **fails: constant 17/18 and dilute 17/18**; duty 9/9 holds; idle_gap had no block at 5% or more. 43/45 in all |
| H1.3 stretch: detection at 2% or more | fails: constant 20/24, dilute 20/24, duty 17/18. 58/67 in all |
| H1.4 the time bound covers the seconds the hidden load ran | holds: 73/73 |
| closure gap; slack-inflated gap | 17.8%; 25.9% |
| outcome | **FAIL** |

The medium trial has 18 blocks at 5% or more in a class, so a single miss (94.4%) fails that class. Amendment v0.6
expected the 2% level to fail at blocks this short (30 s), and it did; it did not expect the 5% level to fail. The
calibrated energy bound, expected to cover under 95%, covered 100%. Calibration drift: +0.02 SD, spread 1.00x.

**Why, read off the raw data (after the run; it describes and decides nothing).**

1. *Two reference blocks set a threshold twice as high as the Kaggle ones.* The threshold is the largest of the 150
   reference scores: 4.73. The next are 4.39 and then 1.73. No null audit block scored above 2.91, so there were no
   false alarms; the two blocks missed at 5% scored 3.78 (constant, GPU flat out) and 2.78 (dilute, requested level
   0.9), above both Kaggle thresholds (2.29 and 2.43) and under this one.
2. *Both are blocks at full load, in which the GPU slowed while its power sat at the limit.* The clock rule of
   amendment v0.4 locks the highest clock the probe saw hold with power within 95% of the limit. The probe measures at
   requested levels up to 0.9. At that level, locked at 870 MHz, the GPU was busy 81.5% of the time and drew 64.9 W of
   its 70 W; busy all the time it needs an estimated 72.4 W. So at full load the power limiter took over from the
   lock: power sat at 69.5 W, a unit of work took 9.2 ms of busy time against 8.7 ms at every level up to 0.7, and the
   rate of verified work moved between 99.7 and 112.7 units a second (1st and 99th percentile), with an hourly mean
   that rose from 105.6 to 110.1 through the run. The rule chose a clock that does not hold where the trial needs it
   most.
3. *The curve misfits at the top of the load range*, as in runs 6 and 7: reference blocks with the GPU flat out
   throughout scored +1.44 on average, against 0.27 for the others.

**What changes, and what does not (amendment v0.7, made before any further run).** The clock the trial locks must
hold flat out: the highest clock whose estimated flat-out power is at most 95% of the power limit, which on this run's
probe is 645 MHz (64.9 W) instead of 870 MHz. The `link-full` analysis is declared as a comparison that decides
nothing; on this run's data, post hoc, it gives 0 false alarms in 204, 45/45 at 5% or more with every decided class
holding, 60/67 at 2% or more, a closure gap of 5.62% and a slack-inflated gap of 13.7%: FAIL on the slack. The
registered analysis, its thresholds, the block counts and the outcome rule are unchanged: the trial failed H1.3 as
registered and that is its result.

**Mock training run** (`drill.json`): compliant, stopped by the provider at the budget's energy with 12.2% of the
budget's FLOP logged.

**What runs 6 to 8 show.** On three more T4s, with everything fixed beforehand: the amended analysis kept false
alarms inside its rule on all three (3/408 and 0/204); on the two-GPU campaign it detected every one of 210 hidden
loads at 5% of capacity or more and 285 of 290 at 2% or more, and its time bound covered every hidden block; on Colab
it missed two of 45 at 5% or more, one in each of two classes, which fails the rule at that trial's size, in a trial
whose clock lock did not hold at full load. On every GPU the outcome is FAIL, because the efficiency slack the probe
measured (8.4 to 10.8%), weighted by the trials' load, adds 6 to 8% of capacity to the gap by itself, more than the 5%
the outcome rule allows: no analysis changes that, and amendment v0.6 said so before the runs. Residency (T2) passed its registered thresholds on all three. None of it is evidence about H100s,
independent metering or the registered thresholds. The next runs are a T4 run under amendment v0.7, to test the clock
rule, and the registered trial on instrumented H100-class hardware.

## 8. No new run: the probes of runs 3 to 8 read by rule, and amendment v0.8 (14 November 2026)

**What was read.** Every probe on record holds one cell per variant and load level: the reference's power and the
variant's at the same rate of verified work. `closure slack-left` (new) takes away the kinds of setting a regime could
fix, one rule at a time, and reports the largest bound left. It is arithmetic on the signed cells: with nothing fixed
it reproduces each trial's `s_max` and slack-inflated gap exactly, and a test checks that on all six bundles.
**Post hoc, and it decides nothing**: it was read after the data were seen, and every outcome stands as registered.
The page is [results/SLACK_LEFT.md](../results/SLACK_LEFT.md), generated from the bundles.

**What it shows.**

1. Two savings are measured, not just bounded: all-zero activations on the reference stack save 4.9 to 7.2% at half
   load on every GPU, and a low clock lock saves 6.0 to 10.0% on the three where clocks could be locked.
2. Pinning the whole stack (clocks, power limit, precision, library) leaves the data saving, and predicting energy
   from the data leaves the stack's: either alone leaves 6.8 to 13.5%. Both together leave nothing the probe tried,
   which is the edge of the sweep, not a measured zero.
3. On a T4 the fp16 variant is the reference computation under another name, so its true saving is zero. With three
   rounds the probe gave it bounds of 6.8 to 9.0%. On runs 5 to 7 that is about the size of `s_max` itself.
4. With nothing left in the sweep, the reading would be the closure gap alone: 5.62% at best (runs 6 and 7). A PASS
   needs the gap in the bin ending at 3.16% or lower and a slack of at most 2.4 to 3.0% at these loads.

**What changed (amendment v0.8, made before any further run; nothing that decides changes).** The probe runs a
deliberate null twin on every GPU and reports its bound `s_null`, never counted; it defaults to six rounds, and the
pilot uses six with the `medium` and `long` profiles; every cell keeps its measured powers; and the slack-left reading
and a round-paired bound are reported for every run from now on, declared beforehand and deciding nothing.
`s_max`, H1.1 to H1.7 and the outcome rule are unchanged. A probe takes about twice as long: about 75 minutes on a T4
whose clocks can be locked.
