# Simulation study (estimator validation only)

10 independent simulated clusters, default profile (600 reference blocks, 1,200 audit blocks, L=300 s, alpha=1e-3 combined). SIMULATED data: says nothing about real GPU physics.

| seed | null FP (combined) | FPR | FPR 95% upper | closure gap | f95 energy-only | f95 busy-only | bound coverage (non-slack) | coverage (slack, expected to fail) | median bound/truth |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0/597 | 0.00% | 0.50% | 1.78% | 3.16% | 1.78% | 100.00% | 47.11% | 1.35 |
| 2 | 3/566 | 0.53% | 1.36% | 1.78% | 1.78% | 1.78% | 100.00% | 38.21% | 1.38 |
| 3 | 0/629 | 0.00% | 0.48% | 1.78% | 1.78% | 1.78% | 100.00% | 39.05% | 1.30 |
| 4 | 0/610 | 0.00% | 0.49% | 1.78% | 1.78% | 1.78% | 100.00% | 41.32% | 1.39 |
| 5 | 1/605 | 0.17% | 0.78% | 1.78% | 3.16% | 3.16% | 100.00% | 38.05% | 1.40 |
| 6 | 1/604 | 0.17% | 0.78% | 1.78% | 1.78% | 1.78% | 100.00% | 40.14% | 1.40 |
| 7 | 3/587 | 0.51% | 1.32% | 1.00% | 1.78% | 1.78% | 99.78% | 38.02% | 1.29 |
| 8 | 0/590 | 0.00% | 0.51% | 1.78% | 1.78% | 1.78% | 100.00% | 36.00% | 1.35 |
| 9 | 1/596 | 0.17% | 0.79% | 1.78% | 1.78% | 1.78% | 100.00% | 40.43% | 1.34 |
| 10 | 2/568 | 0.35% | 1.10% | 1.78% | 1.78% | 1.78% | 100.00% | 38.58% | 1.32 |

Mean FPR 0.189% (max 0.53%); closure gap mean 1.70% (range 1.00% to 1.78%); non-slack bound coverage mean 99.98% (min 99.78%).
