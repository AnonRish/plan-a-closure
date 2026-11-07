# The hardwired-pause layer

Executable versions of the quantitative parts of **"The Feasibility of a Hardwired Pause of Frontier AI Training"**
(Working Group on AI Pause Feasibility; organizers William Fithian and Wesley H. Holliday, UC Berkeley; working paper
v1.0.1, 10 October 2026). Code is in `src/closure/pause/`, tests in `tests/test_pause_*.py`, commands under `closure pause`.

## What the paper proposes, and how it relates to Plan A

A *hardwired pause* stops frontier training by governing the hardware: it halts production of training-capable chips,
accounts for the stock that already exists (a global census), and phases that stock out in favour of *inference-only* chips
that run approved models but cannot practically train. Verification is quantitative. Each state gets a **covert-evasion
ledger** and an **overt-breakout ledger**, sums of the training capacity each compute source could contribute, which must stay
under a fraction of fleet thresholds derived from the frontier's training budget. As training gets more efficient the
thresholds shrink, and the ledgers have to shrink with them.

Plan A reaches a similar end state differently: it retrofits existing datacentres into inference-only sites with passive
taps and partial recomputation, rather than replacing the chips. The two share a problem, which is checking what a cluster of
training-capable chips actually does while it is allowed to serve inference. The paper says so itself: verification measures
bound covert evasion but do not, in general, reduce breakout exposure. That is the leg this kit's closure accounting addresses,
and `bridge.py` connects the two (below).

## What was added

| module | paper section | what it does | command |
| --- | --- | --- | --- |
| `thresholds.py` | 3.2.2, 6.2, Table 3.1 | frozen frontier to ceilings and fleet thresholds `F_E`, `F_B`, `F_P`; research overhead with blind-leap ladder; erosion with efficiency gains; sensitivity to the leader's timeline, horizon and pause date | `closure pause thresholds` |
| `treaty_ledger.py` | 3.2.3, 6.4, 6.5 | sources with political and technical discounts, both ledgers, headroom line by line and summed, years of durability, licence budget, shrinking allowance, reserves, preserves, offshore custody | `closure pause ledger` |
| `census.py` | 5.4, 5.5, Table 5.1 | missing-chip estimator by holding type, failure model by vintage, dark-compute scenarios, reconciliation of a declared registry against record sets, capture-recapture floors (an addition) | `closure pause census` |
| `inference_only.py` | 3.2.1, 4.1, 6.4.4 | residual training factor, fleet exposure, the token-interface bound (about 12 GFLOP/s) | |
| `gemm_audit.py` | 4.2 | screen of an accelerator dataflow graph against the licensing criterion for dynamic matrix multiplications | `closure pause gemm-audit` |
| `fab.py` | 3.3.4, 5.3, 6.5.4 | wafer and die mass balance, consumables balance, sampling detection, lithography-machine census, component custody | `closure pause diversion` |
| `whitelist.py` | 3.2.4, 4.3, 7.3.4 | model whitelist by architecture-and-weights hash, deadline, deployed-weights check, recall and re-whitelisting, approved fine-tunes, authenticated-weight chip rule, all hash-chained | |
| `supply_chain.py` | 3.1, 3.3.2, 5.2 | the chokepoint stages and their jurisdictions; which stages a coalition leaves open, which member's departure opens which, which chip hosts a census would miss | `closure pause coalition` |
| `registry.py` | 3.3.2 | chip lifecycle, latency-based location checks, lost chips charged as dark compute | |
| `transition.py` | 1.1, 3.4, 4.4 | phase classifier, Phase 1 and Phase 2 duration, licence auctions with a falling cap and trade-in | `closure pause transition` |
| `msic_econ.py` | 7.3 | adoption rule for model-specific chips, designs built, token share, savings, stranded capital on de-whitelisting | `closure pause msic` |
| `pausegame.py` | 2.3, 8.4.3 | Prisoner's Dilemma versus Stag Hunt, equilibria, patience and detection thresholds for a repeated pause | `closure pause game` |
| `bridge.py` | 3.3.3 (an addition) | closure trial results to a ledger line, and measured detection to the game threshold | `closure pause bridge RUN_DIR` |
| `paper_claims.py` | throughout | re-derives 114 numbers the paper prints | `closure pause claims` |
| `coverage.py` | throughout | 75-row matrix of the paper's requirements against code, tests and repos | `closure pause coverage` |

`docs/HARDWIRED_PAUSE_COVERAGE.md` is the matrix. Of 75 items, 58 are software-addressable. 40 are implemented here, 7 are
hardware-gated (code here, needs real hardware or design data) and 11 are partial; two of these rest on repositories vendored
under `external/` (TEE and runtime-monitor evidence, and the grid-side search for undeclared facilities). None is unstarted. The
other 17 are physical or policy and are not counted as covered: inspections, seals, treaties and the manufacture of
inference-only chips are not something code delivers.

## Results of re-deriving the paper's numbers

114 printed numbers were recomputed from the modules, not copied: **111 reproduce at the paper's printed precision, 3 hold only
under a stated reading, none are inconsistent.** Tolerances are the half-width of the paper's own rounding (it prints two
significant figures and carries values unrounded, its footnote 50), widened only for words like "roughly". A test perturbs the
model and checks that the matching claims then fail, so the check can fail.

The three readings:

1. **`F_E` from the printed intermediates.** Section 6.2.2 prints `11 * 2e28 / (5 * 0.21) = 6.4M`. With those rounded values the
   expression gives 6.7M. It gives 6.39M with the unrounded `rho_E = 10.6` and `U_F = 0.2128` the paper says it carries.
2. **Two orders of magnitude of headroom, read as a sum.** Section 6.4.3 says the high-cooperation scenario can comfortably
   survive two orders of magnitude of erosion. The authors' calculations notebook reads headroom *line by line* (it says the lines
   are not added, because they apply at different dates), and line by line the binding line has 2.2. The ledger is defined as a sum
   (section 3.2.3), and the summed lines give 1.91 (covert) and 2.00 (overt) for the US.
3. **Twin issues below 0.25%.** Section 6.1: dark compute and transitional service each below 0.25% of their fleet thresholds
   sustains a 25% allowance with two orders of magnitude of headroom. True for either term alone (exactly 2.0). With the other lines added
   (0.20% covert) it is about 1.75.

None of these is an error in the paper. They are places where a reader who adds the lines gets a slightly different answer, and
the code reports both.

| state | scenario | binding line (covert) | per-line covert | summed covert | per-line overt | summed overt | years at 57%/yr (summed) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| US | high cooperation | sovereign supercomputer | 2.24 | 1.91 | 2.15 | 2.00 | 9.7 |
| US | low cooperation | dark compute | 1.43 | 1.34 | 2.15 | 1.95 | 6.9 |
| US | non-deniable | dark compute | 0.73 | 0.71 | 2.15 | 1.78 | 3.6 |
| China | high cooperation | sovereign supercomputer | 2.24 | 1.92 | 2.15 | 2.00 | 9.8 |
| China | low cooperation | dark compute | 1.15 | 1.10 | 2.15 | 1.90 | 5.6 |
| China | non-deniable | dark compute | 0.20 | 0.20 | 1.64 | 1.49 | 1.0 |

(Orders of magnitude of erosion before the allowance is reached, after transitional service has ended, at the paper's 25%
allowances. A sum can never have more headroom than its worst line. A test keeps this table equal to what the code computes.)

**Other things the code makes visible.**

- US transitional service fits the overt allowance at the pause date with only 0.096 orders of magnitude to spare, a 25% erosion
  of the threshold. At 57% a year that is about six months. The paper's mitigations (a one-time exception, an allowance schedule
  that starts near 100%, moving half of it offshore) are load-bearing for the first years, not optional extras. A schedule that
  starts at 100% buys about 3.6 years.
- The non-dark, non-transitional overt lines sum to 0.247% of `F_B`, against the paper's "below 0.25%". It holds, with a 1%
  margin.
- Table 6.1 gives the US-located stock as 26M to 44M H100e (35M central). Transitional service uses 14.8% of `F_B` at the
  bottom of that range and 25.0% at the top, so at the top of the paper's own range it exhausts the whole overt allowance on
  day one (`closure pause ledger --stock 44e6`).
- The section 3.1 participant list controls every stage in the paper's chokepoint table, and every member except the UK is
  required to control at least one stage. A bilateral US-China arrangement leaves six of the nine stages open: EUV lithography, DUV
  lithography, EUV optics, coater/developer, leading-edge foundry and high-bandwidth memory (`closure pause coalition --members
  "United States,China"`). The table is the paper's reading of its own section 5.2, not an independent survey.
- Each half-year of delay in starting a pause removes about one blind step (6.1 months) from a fixed breakout target, which is
  why breakout gets harder to guard against as the pause date recedes while covert evasion gets easier.

## Cross-check against the authors' own code

The paper's calculations notebook (`Berkeley-AI-Risk/pause-ledger-calculations`) and economics repository
(`Berkeley-AI-Risk/econ-of-MSICs`) are public under the MIT licence. They are not vendored here. The modules were written from the paper's text and then
compared with them:

```bash
git clone https://github.com/Berkeley-AI-Risk/pause-ledger-calculations
git clone https://github.com/Berkeley-AI-Risk/econ-of-MSICs
pip install -r econ-of-MSICs/requirements.txt          # their analysis imports matplotlib (and streamlit for their app)
python scripts/crosscheck_upstream.py --calc pause-ledger-calculations --msic econ-of-MSICs
```

- The 12 cells of Figure 7.1 (design count, token share on chips, saving) are identical between `msic_econ.panel` and the authors'
  `panel_rows` on their one-week OpenRouter demand data, and equal the printed figure.
- On that data the most popular model gives a worst-case savings-to-cost ratio of 120x, and the smallest of the 14 models that
  serve three quarters of tokens still clears 14.7x, matching the paper's claims of roughly 120x and at least 10x.
- `F_E`, `F_B`, `F_P` and the two `K_M` totals agree with the notebook's printed output.

The failure-by-vintage model in `census.py` is implemented but its default inputs are Table 5.1 as the notebook computes it,
because the paper's own vintage data come from Epoch AI sales records that are not included here.

## Closure as the evidence behind a discount

The paper's covert discount for transitional service (`pi_E = 0.001`: 10% of operators evade, each diverting 1%) is an
assumption. A closure trial measures something that can stand in for it: the smallest hidden-energy share of a cluster's
capacity the audit reliably catches (`closure_gap_fraction` in `results.json`). `closure pause bridge RUN_DIR` turns that into a
ledger line, with the measured gap on the audited share of a fleet and an explicit assumption on the rest, and can feed the
measured per-block detection probability into the repeated-game threshold (`bridge.monitoring_supports_pause`).

Cautions, all of which the output repeats:

- It is descriptive and post hoc. It is not one of the pre-registered claims in `docs/PREREGISTRATION.md`.
- A simulated trial validates the method, not any hardware. The quick simulated profile reports a gap near 1.8% of capacity
  energy; reaching the paper's 0.001 by detection alone would need a gap about eighteen times smaller. That is a statement about
  what a hardware trial would have to achieve, not about any real cluster.
- An energy audit cannot see an energy-neutral adversary (efficiency slack, assumption A4). If a `closure hw-probe` result was
  bound into the trial (`--probe`), `bridge` charges the **slack-inflated gap** instead of the plain gap; otherwise slack is
  unmeasured and the bound excludes that class.
- `tau_E` in this line is a conversion from capacity-energy to H100e at the measured energy floor (at least 1), not a
  utilisation discount. Seizing the fleet in a breakout is still charged in full.

## Limits

- Inputs are the paper's illustrative values for a pause at year-end 2026. Nothing here is a claim about real chip stocks, real
  operators or real treaty parties. `ThresholdParams`, the census anchors and the ledger lines take other values.
- `gemm_audit.py` is a design-time screen. It treats fixed linear maps as transparent to an operator and nonlinear stages and
  dynamic products as obstacles, and reports both readings. The paper requires a physical audit of the realised system, tamper
  paths included, and no graph replaces that. `example_attention_block` is a toy built from the channels the paper describes for
  one published design, not that design.
- `census.chao1_unseen` and `census.lincoln_petersen` are not in the paper. They assume record sources miss chips independently;
  shared blind spots (every source missing shell-company diversion) make them floors.
- Recalling a base model also de-whitelists its approved fine-tunes. The paper does not specify this; it is a design choice.
- Exit conditions, inspection regimes, treaty institutions, the economics of section 7.1 and the politics of section 8 are not
  code. They are marked `policy` or `physical` in the matrix and are not counted as covered.

## Reproduce

```bash
pytest tests/test_pause_*.py        # 82 tests
closure pause claims                # 114 numbers: 111 OK, 3 WORDING
closure pause claims --all          # every row
closure pause coverage --write docs/HARDWIRED_PAUSE_COVERAGE.md
closure pause thresholds            # Table 3.1 at full precision, sensitivities
closure pause ledger --state China --scenario low
closure pause gemm-audit --sealed   # exit status 1 if a design fails the licensing criterion
```

Cite the paper for the method. This directory re-implements it from the text and cross-checks it against the authors'
public code; any error in the implementation is this repository's.
