# Efficiency slack left under each rule a regime could adopt

A descriptive reading of the probes on record. **It decides nothing**: the registered outcome uses s_max with nothing fixed, and these readings were made after the data were seen (from amendment v0.8 on, the pilot reports the same reading for every run, declared before its data). This page is written by `python results/slack_left.py --write` from the bundles in this folder, each checked against its SHA-256, and a test fails if it is out of date. The method is `closure slack-left` ([src/closure/slack_left.py](../src/closure/slack_left.py)); on one unpacked bundle, `closure slack-left --run <the trial folder inside it>` prints the same rows.

Why it matters. Closure bounds hidden work by the energy the verified work does not explain. An operator who can do the declared work for less energy than the energy model expects (a lower clock, another library, cheaper data) can run hidden work in the difference, so the registered reading adds that efficiency slack, times the load, to the closure gap. A treaty could take some of those choices away. Which ones would it have to take?

The probe changes one setting at a time from its reference and measures power at the same work rate, at load levels 0, 0.25, 0.5 and 0.9 of capacity. A rule here removes the kinds of setting it fixes, and the slack left is the largest one-sided 95% upper bound on a saving among the variants it leaves free. A variant whose numerics fail the accuracy check never counts, as in the registered s_max (int8 here; fp8 does not run on a T4).

## 1. Where the slack is on each GPU

| run | when and where | settings the probe could try | rounds | registered s_max (95% upper bound) | measured saving there | largest measured saving under load | twin's bound: all levels; under load | twin's largest measured saving |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | 8 Nov 2026, Colab VM | SM clocks, power limit, precision, BLAS library, data | 3 | 13.5% (clock-405MHz, load 0.5) | 9.7% | 9.8% (clock-645MHz, load 0.5) | 6.9%; 6.9% | 1.6% |
| 4 | 8 to 9 Nov 2026, Colab VM | SM clocks, power limit, precision, BLAS library, data | 3 | 12.6% (operand-lowent, load 0.25) | 3.6% | 10.0% (clock-645MHz, load 0.9) | 9.0%; 9.0% | 2.6% |
| 5 | 8 to 9 Nov 2026, Kaggle container | precision, BLAS library, data (not SM clocks, power limit: no device control) | 3 | ≥ 9.6% (operand-zeros, load 0.5) | 6.7% | 6.7% (operand-zeros, load 0.5) | 8.5%; 6.7% | 2.2% |
| 6 | 11 to 12 Nov 2026, Kaggle container, GPU 0 | precision, BLAS library, data (not SM clocks, power limit: no device control) | 3 | ≥ 9.1% (operand-sparse90, load 0.25) | 3.4% | 5.2% (operand-zeros, load 0.5) | 7.9%; 7.9% | 1.8% |
| 7 | 11 to 12 Nov 2026, Kaggle container, GPU 1 | precision, BLAS library, data (not SM clocks, power limit: no device control) | 3 | ≥ 8.4% (operand-sparse90, load 0.25) | 1.2% | 4.9% (operand-zeros, load 0.5) | 6.8%; 4.6% | 0.9% |
| 8 | 12 Nov 2026, Colab VM | SM clocks, power limit, precision, BLAS library, data | 3 | 10.8% (operand-zeros, load 0.5) | 6.6% | 6.6% (operand-zeros, load 0.5) | 6.8%; 6.8% | 1.7% |

The twin is the fp16 variant, the reference computation itself on a T4, so its true saving is zero. A **≥** marks a lower bound: the probe could not try every kind of setting the rule leaves free.

## 2. What each rule leaves: 95% upper bound over all load levels, as s_max counts them

| rule: what the regime takes away | run 3 | run 4 | run 5 | run 6 | run 7 | run 8 |
| --- | --- | --- | --- | --- | --- | --- |
| nothing fixed (the registered s_max) | 13.5% (clock-405MHz, load 0.5) | 12.6% (operand-lowent, load 0.25) | ≥ 9.6% (operand-zeros, load 0.5) | ≥ 9.1% (operand-sparse90, load 0.25) | ≥ 8.4% (operand-sparse90, load 0.25) | 10.8% (operand-zeros, load 0.5) |
| SM clocks fixed | 11.9% (operand-zeros, load 0.5) | 12.6% (operand-lowent, load 0.25) | ≥ 9.6% (operand-zeros, load 0.5) | ≥ 9.1% (operand-sparse90, load 0.25) | ≥ 8.4% (operand-sparse90, load 0.25) | 10.8% (operand-zeros, load 0.5) |
| SM clocks and power limit fixed | 11.9% (operand-zeros, load 0.5) | 12.6% (operand-lowent, load 0.25) | 9.6% (operand-zeros, load 0.5) | 9.1% (operand-sparse90, load 0.25) | 8.4% (operand-sparse90, load 0.25) | 10.8% (operand-zeros, load 0.5) |
| whole stack pinned: clocks, power limit, precision, BLAS library | 11.9% (operand-zeros, load 0.5) | 12.6% (operand-lowent, load 0.25) | 9.6% (operand-zeros, load 0.5) | 9.1% (operand-sparse90, load 0.25) | 8.4% (operand-sparse90, load 0.25) | 10.8% (operand-zeros, load 0.5) |
| energy predicted from the data the work ran on; stack free | 13.5% (clock-405MHz, load 0.5) | 12.4% (clock-645MHz, load 0.9) | ≥ 8.5% (precision-fp16, load 0) | ≥ 8.0% (kernel-cublaslt, load 0.5) | ≥ 6.8% (precision-fp16, load 0) | 9.1% (clock-645MHz, load 0.5) |
| stack pinned and energy predicted from the data | nothing in the sweep | nothing in the sweep | nothing in the sweep | nothing in the sweep | nothing in the sweep | nothing in the sweep |

## 3. The same under load only (levels above 0; post hoc)

At level 0 the GPU does no work, so a precision, library or data variant cannot change its power: an idle "saving" from one is drift between measurements. This reading sets all idle cells aside.

| rule: what the regime takes away | run 3 | run 4 | run 5 | run 6 | run 7 | run 8 |
| --- | --- | --- | --- | --- | --- | --- |
| nothing fixed (the registered s_max) | 13.5% (clock-405MHz, load 0.5) | 12.6% (operand-lowent, load 0.25) | ≥ 9.6% (operand-zeros, load 0.5) | ≥ 9.1% (operand-sparse90, load 0.25) | ≥ 8.4% (operand-sparse90, load 0.25) | 10.8% (operand-zeros, load 0.5) |
| SM clocks fixed | 11.9% (operand-zeros, load 0.5) | 12.6% (operand-lowent, load 0.25) | ≥ 9.6% (operand-zeros, load 0.5) | ≥ 9.1% (operand-sparse90, load 0.25) | ≥ 8.4% (operand-sparse90, load 0.25) | 10.8% (operand-zeros, load 0.5) |
| SM clocks and power limit fixed | 11.9% (operand-zeros, load 0.5) | 12.6% (operand-lowent, load 0.25) | 9.6% (operand-zeros, load 0.5) | 9.1% (operand-sparse90, load 0.25) | 8.4% (operand-sparse90, load 0.25) | 10.8% (operand-zeros, load 0.5) |
| whole stack pinned: clocks, power limit, precision, BLAS library | 11.9% (operand-zeros, load 0.5) | 12.6% (operand-lowent, load 0.25) | 9.6% (operand-zeros, load 0.5) | 9.1% (operand-sparse90, load 0.25) | 8.4% (operand-sparse90, load 0.25) | 10.8% (operand-zeros, load 0.5) |
| energy predicted from the data the work ran on; stack free | 13.5% (clock-405MHz, load 0.5) | 12.4% (clock-645MHz, load 0.9) | ≥ 8.2% (kernel-cublaslt, load 0.5) | ≥ 8.0% (kernel-cublaslt, load 0.5) | ≥ 6.7% (kernel-cublaslt, load 0.5) | 9.1% (clock-645MHz, load 0.5) |
| stack pinned and energy predicted from the data | nothing in the sweep | nothing in the sweep | nothing in the sweep | nothing in the sweep | nothing in the sweep | nothing in the sweep |

## 4. The slack-inflated gap each rule would give, holding each run's closure gap and load as measured

A trial run under a rule would measure its gap and load again; this only shows how much of each reading the slack accounts for. The first column of readings is the registered one, as signed.

| run | closure gap | mean load | nothing fixed (registered) | clocks | clocks, power limit | whole stack | data | stack and data |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | 31.62% | 0.61 | 39.8% | 38.8% | 38.8% | 38.8% | 39.8% | 31.6% |
| 4 | 31.62% | 0.64 | 39.7% | 39.7% | 39.7% | 39.7% | 39.6% | 31.6% |
| 5 | 17.78% | 0.73 | 24.8% | 24.8% | 24.8% | 24.8% | 24.0% | 17.8% |
| 6 | 5.62% | 0.73 | 12.3% | 12.3% | 12.3% | 12.3% | 11.5% | 5.6% |
| 7 | 5.62% | 0.73 | 11.7% | 11.7% | 11.7% | 11.7% | 10.6% | 5.6% |
| 8 | 17.78% | 0.75 | 25.9% | 25.9% | 25.9% | 25.9% | 24.6% | 17.8% |

## What these numbers say

1. **Two sources of slack are large and measured, not just bounded: cheap data and low clocks.** Point estimates under load: the data pattern `operand-zeros`, on the reference stack, saves 4.9 to 7.2% at load 0.5 on every GPU; a low clock lock saves 6.0 to 10.0% on the 3 GPUs where clocks could be locked. The BLAS library's largest measured saving is 0.5 to 5.2%.
2. **Pinning the stack leaves the data, and accounting for the data leaves the stack.** The registered bound peaks on a data variant on 5 of 6 GPUs, so pinning the whole stack (clocks, power limit, precision and library) lowers it on 1 of 6 (run 3: 13.5% to 11.9%). Either rule alone leaves 6.8 to 13.5%. With both, nothing in the sweep is left on all 6: that is the edge of what was tried, not a measured zero.
3. **At 3 rounds the bound is mostly noise where the real savings are small.** On a T4 the fp16 variant is the reference computation under another name (a T4's native half precision is fp16), so its true saving is zero. The probe gave it bounds of 6.8 to 9.0%, with measured savings of -0.4 to +2.6%. On runs 5, 6, 7, where only precision, library and data could be tried, s_max (9.6%, 9.1%, 8.4%) is close to the twin's bound (8.5%, 7.9%, 6.8%).
4. **What a PASS would take.** The registered outcome needs the closure gap plus s × load at 5% or less. The gap is reported at the upper edge of a quarter-decade bin, so in practice it has to be in the bin ending at 3.16% or lower, which leaves room for a slack of at most 2.4 to 3.0% at these loads (0.61 to 0.75 of capacity). On these runs no rule would have been enough: with nothing left the reading is the closure gap itself, 5.62% at best (runs 6, 7) and 17.8 to 31.6% on the others.
5. **For the next run (projections, not measurements).** With the spread per round these probes measured and the same point estimates, six rounds (amendment v0.8's default) would put the twin's bound at about 3.8 to 5.8% and s_max at about 6.3 to 11.6%; twelve rounds would put the twin at about 2.8 to 4.6%. The twin's bound would still exceed the slack a PASS leaves on 6 of 6 GPUs at six rounds and on 5 of 6 at twelve, so on GPUs and meters like these more rounds are not enough by themselves: the meter's noise and the probe's own offset (the twin's measured savings) have to come down too. From v0.8 every probe runs a deliberate null twin and keeps each cell's powers, so the next run measures its own noise floor and can be read paired by round.

In treaty terms: on this evidence, energy accounting can bound hidden work only as tightly as the efficiency choices left to the operator, and closing them takes both a pinned stack (clocks and power limit included) and an energy prediction made from the data the declared work actually ran on, for example from committed request logs with a sample recomputed on a verifier's machine. How to predict energy from data is an open problem and outside this kit. Kimpson, Baker and Graham (arXiv 2610.07476) describe the attack this guards against: declared work run on cheap operands, with the energy saved spent on covert work.

## What they do not say

- Runs 3, 4, 5, 6, 7, 8 are shakedowns on Tesla T4s with NVML as the only meter. The registered trial needs an H100-class GPU and an independent power meter; magnitudes there will differ.
- Each saving stays measured against the probe's own reference. A regime that fixes a setting moves the reference too, so a rule's row is the slack among the choices left, not a measurement of that regime.
- Variants change one setting at a time. Savings from two changes made together are in no row, the registered one included.
- "Nothing in the sweep" is not zero: other data patterns, libraries, kernels or settings the probe did not try are not covered.
- On runs where the container refused device control, clock and power-limit savings were not measured; every rule that leaves them free gives a lower bound (**≥**).
