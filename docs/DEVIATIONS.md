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
from. The busy-time channel held: 0/23 false alarms, residuals consistent with normal (p = 0.42), and the smallest
detectable hidden load per block was 0.14% of capacity against 5.0% for energy. The 31.6% closure gap is the smoke
profile's limit (no cell had more than 7 blocks, too few to certify 95% detection), not a measurement of the method.

Since 0.6.1, `closure tier0` locks the trial's SM clocks at the highest clock the probe saw the GPU hold at full load
under its power limit, and records it in `prereg.json` (amendment v0.4). On this GPU that is 1110 MHz, which held at
65.2 W; locks at 1575 and 1335 MHz were pulled down to 1125 and 975 MHz by the cap. A locked clock removes the
frequency drift; idle-power drift from temperature remains, and interleaving calibration with audit blocks is the next
design question for Tier 1.

**What these runs show.** On three T4s in Colab VMs: the whole pipeline runs and restores the GPU; energy tracks verified
work once the unit fits the slot; the probe's clock and power controls work; device-memory residency shows up clearly
as time; and an energy model calibrated in one half hour does not carry over to the next on an unlocked, power-capped
GPU in a VM. None of it is evidence about H100s, independent metering or the registered thresholds.
