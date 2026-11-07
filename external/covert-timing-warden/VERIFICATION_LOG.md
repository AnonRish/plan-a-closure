# Verification log

Defects found while building and testing this repository, in order, including the ones in the tests.
Nothing here was fixed quietly.

## 1. `capacity.py`: seven test failures, none a library defect

Each was diagnosed against an independent reference before anything was changed.

| failure | cause | resolution |
| --- | --- | --- |
| BPSK mutual information at sigma = 1 expected 0.48642 | the constant was typed from memory and was wrong; independent 30-digit `mpmath.quad` gives 0.4859441541, identical to the library to 10 digits | test now pins the quadrature value |
| plug-in MI estimator vs BSC capacity, p = 0.05, one seed | tolerance 4e-3 was only 2.2 sigma of the estimator (measured sd 1.8e-3); estimator is unbiased (mean error -5.9e-6 over 40 seeds) | replaced by a 24-seed unbiasedness test |
| independent-sample MI bias `> 0.02` | contradicted its own comment; the chi-square prediction is `(k-1)^2 / (2 n ln 2) = 0.0081` bits | now tests the prediction (5 %) and that the Miller-Madow correction removes it |
| fine-grid uniform-noise capacity within 0.03 of 2 | discretisation error is linear in the grid step: 2 - C = 0.149, 0.0748, 0.0374, 0.0187 at h = 0.2, 0.1, 0.05, 0.025 | now checks monotone approach, error halving, and Richardson extrapolation to 2 within 1e-3 (extrapolated value 1.99988) |
| three lattice-noise channels reported `converged=False` | plain Blahut-Arimoto is sublinear when the optimal input is not unique (here the odd lattice is exactly as good as the even one: every input has D_x = C). The bracket contained the target the whole time and `p_opt` was the right lattice, [1/4, 0, 1/4, 0, 1/4, 0, 1/4] | added over-relaxation (2.5 to 4x fewer iterations; certificate unaffected because bounds are computed from the current input distribution, whatever the update rule); tests use 1e-8 bits and check both accelerated and plain agree |

## 2. `traffic.py` and its tests: one real API flaw, two wrong expectations

| failure | cause | resolution |
| --- | --- | --- |
| `to_ipd(to_timestamps(x))` had 49 elements for 50 delays | **real flaw in the library**: `to_timestamps` was a bare cumulative sum, so packet 0 had no timestamp and the first interval was lost on the way back (off-by-one) | `n` delays now map to `n + 1` timestamps starting at `t0`; the round trip is exact and length-checked |
| `stationary_burst() == 0.2/0.28` | wrong constant in the test: the parameters give `(1 - 0.75) / ((1 - 0.92) + (1 - 0.75)) = 0.25/0.33 = 0.7576`, which is what the code returned | test corrected; the sampled marginal already agreed with the mixture CDF to 0.0022 (chain-correlation limit about 0.0021) |
| `cce(iid, 8 symbols) == 3.0 +- 0.06` returned 2.9157 | expectation ignored finite-sample bias: at the minimising pattern length m = 3 the plug-in entropy is low by `((8^3-1)-(8^2-1))/(2 n ln 2) = 0.081` bits, giving 2.919; measured 2.9174 +- 0.0035 over 12 seeds | pinned to the prediction |

Also found while fixing the first item: `load_ipd_csv` silently skipped every unparsable row, so a corrupted trace
would just get shorter and fail later, if at all, with an unrelated message. It now skips only leading header lines
and raises with the line number afterwards. The CSV half of the original test was never reached (the round-trip
assertion failed first). It would have failed anyway: NumPy 2 prints `repr(np.float64(0.5))` as `np.float64(0.5)`,
so the test wrote unparsable rows, the old loader skipped all of them, and the failure would have surfaced only
at `to_ipd` on an empty array.

## 3. `detect.py`: apparent validity violation, actually calibration variance (test-design error); KS made exact and fast

`test_p_values_are_super_uniform...` failed: the CCE detector's p-value was <= 0.2 on 24.3 % of 1,500 fresh honest windows
(tolerance used: test-sample noise only, 0.0103). Hypothesis: conformal p-values are valid *marginally over the choice of
null windows*; for one fixed warden with R null windows the realised rate fluctuates by about `sqrt(a (1-a) / (R+2))`,
which the tolerance ignored. Checked, not assumed: 200 random calibration sets over one bank of 6,000 honest windows.

| R | level | mean rate over calibrations | sd across calibrations | predicted sd |
| --- | --- | --- | --- | --- |
| 150 | 0.05 / 0.2 / 0.5 | 0.0386 / 0.1963 / 0.4911 | 0.0165 / 0.0345 / 0.0459 | 0.0177 / 0.0324 / 0.0406 |
| 520 | 0.05 / 0.2 / 0.5 | 0.0496 / 0.1985 / 0.4995 | 0.0105 / 0.0197 / 0.0245 | 0.0095 / 0.0175 / 0.0219 |

Every mean is at or below its level; the observed 24.3 % was +2.1 sigma of the combined noise. Fixes: the tolerance now
includes calibration noise; an *exact* enumeration test shows the rank p-values are exactly `{1..R+1}/(R+1)` for exchangeable
values (and never alarm on ties); a pooled 60-calibration test over all six detectors checks super-uniformity where it is
true. `detect.py` now documents the effect. Not a library bug, but a property every user needs to know.

Found while profiling that test: `ks_stat` merged the whole 100k-point reference into every window (3 to 5 ms). Replaced
by an exact O(n log m) form (the window's CDF is constant between its distinct values and the reference CDF is monotone,
so the supremum is at interval endpoints; ties handled on distinct values). Verified against `scipy.stats.ks_2samp` on
200 random tie-heavy cases and disjoint supports. Detection tests went from 43 s to 11 s.

## 4. `mitigate.py`

* **A vacuous assertion, found only by re-reading after the whole file passed first time.**
  `assert set(rel) <= grid or rel.max() > 500` could not fail whenever the second clause held. It is replaced by a strict test:
  three arrival processes (uniform, bursty, single burst), every release on a distinct scheduled tick, nothing past the
  horizon, and the observer's view (real ticks plus dummies) identical to the full grid in all three.
* **The natural first design was wrong, and the numbers say by how much.** A Blahut-Arimoto bound on the per-inter-packet-delay
  channel (triangular noise, the difference of two jitters) looks like an upper bound and is not: a receiver with a shared clock
  decodes cumulative timestamps, where each packet's noise does not accumulate. Simulated error-free decoding over 400,000
  packets at each ratio beats the naive bound by 36 %, 29 %, 26 %, 24 %, 20 % at D/w = 1, 2, 3, 4, 8
  (`examples/why_per_ipd_is_unsafe.py`). The library therefore ships only the timestamp-model bracket.
* **The bracket is not tight, and I checked where the truth sits.** A two-packet block channel with output bins aligned to the
  noise equals the lattice rate exactly (1.0, 1.585, 2.0). With finer grids it *exceeds* the lattice rate (per packet: 1.0771
  at D/w = 1, 1.6600 at D/w = 2, 2.0663 at D/w = 3) while staying below the proven upper bound (1.585, 2.0, 2.322). So neither
  end of `[log2(1 + floor(D/w)), log2(2 + D/w)]` is the capacity. (A first, coarse, misaligned grid gave 0.93 < 1.0; that was a
  discretisation artefact of bins straddling the noise support, not a contradiction.) The two-packet figures are for a message
  with known start time and are not claimed as a stream rate.
## Observations about the modelling (not defects in this repository)

See `mitigate.py` and the README.
