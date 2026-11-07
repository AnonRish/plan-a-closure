# Verification log

Every defect found while building compute-ledger, with the evidence, then what each check is independent of, then what is
not established.

## Defects in my own work

| # | defect | how it was found | evidence | fix and guard |
| --- | --- | --- | --- | --- |
| 1 | The tolerance for a published percentage assumed values below 1 are printed to two decimals, so the `<1K` share (printed `0.1`) was held to 0.005 instead of 0.05 | the first reproduction run: 1 of 35 checks failed | computed 0.137% against published 0.1%, tolerance 0.0052 | printed precision is derived from the number's own decimals (`printed_halfwidth`, tested on `0.1, 0.32, 12.0, 3.5, 51.4, 0.9`) |
| 2 | A scipy quadrature test integrated the heavy lognormal tail over `[m, inf)` and missed its 1e-9 target (`IntegrationWarning`) | first run of the distribution tests | `0.5 +/- 1e-9` failed | test-side: integrate in log space where the integrand is Gaussian-shaped; the CDF-based checks of the same maths had passed |
| 3 | **Vacuous assertions again**: `... == sorted(...) or True` on the bin ordering, and a source check whose `or "supplement" in ...` clause made it nearly always true; also a leftover `+ 0.5e6 * 0` term in a tolerance | re-reading the new tests and code | none: each could not fail | first removed (the claim it hid was false: the bins are not in descending order), second made precise (each block's source must start with a declared source key), third removed |
| 4 | The CLI printed values in scientific notation (`2.88719e+08`), so a plan figure could not be read off the report and a test looking for `289` failed | first CLI test | output captured in the test failure | values print in millions; the test now checks `288.72M` and `298.80M` |
| 5 | Two README blocks labelled "real output" contained numbers I had typed from memory: US `223.64M` (real: `223.63M`) and a count of 27 mutants (real: 26) | checking the README against fresh tool output before committing | the regenerated output | both blocks replaced with verbatim output; counts corrected |
| 6 | The first mutant list claimed an equivalent mutant (undo order in `opening_position`) without evidence | design review | none yet | kept in `EQUIVALENT` and *required to survive*: the run confirms the tests cannot see it, and the reason is stated (each undo is an additive adjustment) |

## What was checked, and what each check is independent of

| check | against | result |
| --- | --- | --- |
| plan figures re-derived from their inputs | 35 checks with tolerances propagated from the rounding of the published inputs | 35 pass: world stock 288.72M vs 289.0M, owners, size bins, site count, 0.519% hidden |
| the checker can fail | 8 negative controls, each tampering one input | each makes at least one check fail |
| published series convention | implied per-step survival factors; the running-sum alternative | 0.9535 to 0.9564 vs 0.9548; running sum 298.8M vs 289.0M, rejected |
| roll-forward | closed form `f^n S0 + sum f^(n-1-k) P_k` (200 random cases); linearity; half-life semantics | agree to 1e-9 |
| posterior, flat prior | scipy `truncnorm` on 6 declaration/estimate configurations, including estimate below, equal to and above the declaration | quantiles 1% to 99% within 2e-4 sigma; mean and survival function agree |
| posterior, half-normal prior | the closed-form truncated normal, 8 configurations | within 2e-4 sigma |
| posterior, fitted prior | an independent 400,001-point numpy grid | within 2e-3 sigma |
| extreme inputs | declaration 30 sigma above the estimate | finite, normalised, median under 0.05 sigma |
| two-piece lognormal | scipy `lognorm` in the symmetric case (100 random cases); quadrature of the density and mean in log space; 200,000 seeded samples | equal to 1e-9; mass 0.5 + 0.5; sample quantiles within 2% |
| sum over owners | numpy Monte Carlo with a different generator and 1,000,000 draws | quantiles within 2% |
| ledger | stateful hypothesis machine over random produce/transfer/retire sequences; atomicity; JSON round trip; digest sensitivity | invariants hold in every step |
| the tests themselves | mutation: 26 injected bugs, each in a temporary copy; the unmutated copy must pass first | 26 killed; 1 claimed-equivalent mutant confirmed to survive |
| fresh clone | `git clone` into a new virtualenv, full test run | 87 pytest tests pass; `compute-ledger plan-a`: 35 checks, 0 failing; the mutation check there: 26 of 26 killed, and the equivalent mutant confirmed |

## What this does not establish

* The reconciliation model is a standard Bayesian update that I chose; it is not the plan's model, and nothing here
  derives the plan's 1.5M / 0.1% to 1.4% hidden-compute figures, which are inputs.
* Provenance is graded, not uniform: the compute supplement was read in full; the hidden-compute figures come from a
  public comment quoting the covert-projects supplement; the 2028 uncertainty bands were read earlier and not re-fetched.
  A prose observation (the supplement describes the fleet as cumulative in one place and gives a 15-year half-life in a
  footnote) is my reading; the arithmetic finding that the published numbers follow the half-life is computed and tested.
* Independent Gaussian errors and a flat or half-normal prior are assumptions; the posterior is only as good as them.
* The plan's figures are projections for 2029. No observed chip data was used.
* The code, tests and reference have one author and no outside review.
* The GitHub Actions workflow was written from commands run locally and has not run on GitHub.
