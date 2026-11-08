# Colab T4 run 3, 8 November 2026 (plan-a-closure 0.6.0)

Every step ran on a Colab Tesla T4 (NVML only, no independent meter). hw-selftest passed (r2 = 0.941), hw-probe
measured slack and the energy floor, hw-state missed its 99% target for a design reason since fixed, and the smoke
trial's energy channel drifted between calibration and audit. Write-up: [docs/DEVIATIONS.md](../../docs/DEVIATIONS.md)
section 3.

| file | what it is |
| --- | --- |
| `tier0_bundle.tar.gz` | the bundle as returned, sha256 `58a273addfd4419ea39c1fc99a025ed4c21dd0514323ecd2d2311ed2aff0e042` |
| `extracted/` | its contents: `SUMMARY.md`, the step logs, `probe.json` and the smoke trial (`T1-smoke/`), except `raw.npz` (every one-second window), which stays inside the bundle because the repository ignores loose `.npz` files |
| `drift.py`, `drift.json` | the drift analysis quoted in DEVIATIONS.md: `python results/shakedown-2026-11-08-colab-t4-run3/drift.py` |

`closure verify results/shakedown-2026-11-08-colab-t4-run3/extracted/T1-smoke` re-checks the evidence chain, the
signature and every commitment.
