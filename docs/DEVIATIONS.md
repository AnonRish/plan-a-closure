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
