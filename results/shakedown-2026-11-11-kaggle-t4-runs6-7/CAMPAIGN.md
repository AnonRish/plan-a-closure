# Campaign kaggle-20261111-195848: 2 trials read as one

POOLED (campaign 'kaggle-20261111-195848', 2 of 2 trials); written to /kaggle/working/tier0-20261111-195848/pooled.json
- scope: shakedown reading of several trials pooled: NVML only, so assumption A6 does not hold; what these data would decide, not a Plan A claim
- H1.1 calibration valid (the threshold is conformal: no distribution assumed, at least 1/alpha - 1 effective reference blocks): holds (threshold: conformal; reported only: energy 0: Jarque-Bera p 5.3e-09, n_eff 144.0; energy 1: Jarque-Bera p 8.1e-10, n_eff 144.0; busy 0: Jarque-Bera p 0, n_eff 144.0; busy 1: Jarque-Bera p 8.5e-05, n_eff 144.0)
- H1.2 false alarms (at most 3 x alpha = 3.0% on at least 200 null blocks): holds: 3/408 (95% upper bound 1.9%)
- H1.3 primary: detection >= 95% at hidden fraction >= 5%, per class (decided once a class has 8 such blocks): constant 72/72 holds; idle_gap 18/18 holds; duty 48/48 holds; dilute 72/72 holds. Pooled over classes: 210/210, 95% lower bound 98.6% (certified at 95%)
- H1.3 stretch: detection >= 95% at hidden fraction >= 2%, per class (decided once a class has 8 such blocks): constant 92/96 holds; idle_gap 26/26 holds; duty 72/72 holds; dilute 95/96 holds. Pooled over classes: 285/290, 95% lower bound 96.4% (certified at 95%)
- H1.4 the time bound covers the seconds the hidden load really ran in at least 95% of non-slack hidden blocks: holds (100.0% of 321, by the floor bound: busy time above the least the verified work can take). Reported only, as checks on additivity (A1): the calibrated time bound covers 99.1%; the energy bound covers the hidden load's solo energy in 97.5% (calibrated) and 100.0% (floor)
- outcome: **FAIL** (slack-inflated gap 12.3% is above 5%); closure gap 5.62%, slack-inflated 12.26%
