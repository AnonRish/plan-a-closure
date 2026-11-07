# Handoff calculator (Capability Scaling Strategy)

The smallest, most contained item in this whole set — a faithful reimplementation
of the "should we hand off or delay" calculator embedded in AI 2040's Capability
Scaling Strategy supplement, plus one small extension.

## Why this one got re-fetched instead of built from memory

Every other piece in this set is new engineering grounded in *general* facts I could
verify independently (FLOP formulas, entropy math, auction theory). This one is
different in kind: the entire point is matching a *specific* existing calculator, and
my notes on its exact formula were from research many turns earlier in this same
conversation. For a fidelity task specifically, working from a fresh, direct
re-fetch of the source page mattered more than it did anywhere else in this set —
so that's what happened before any code got written.

## The formula, verbatim from the source

```
u_handoff_minus_u_delay = d_prob * a_prob * d_loss - a_change
```

- `d_prob` — yearly chance the deal dissolves or is substantially impaired
- `a_prob` — current probability alignment succeeds
- `d_loss` — % of the future's value lost if the deal declines
- `a_change` — extra alignment probability bought per year of delay

Positive → hand off now. Negative → delay. The source page is explicit that this
"only weighs the single most important factor on each side" — not a complete
decision procedure, disclosed there and repeated here.

## Verified against the actual published table, not just self-consistent

The source page includes a full 4×3 grid (4 alignment scenarios × 3 deal-decline
scenarios). All 12 cells, transcribed from the re-fetched page and checked against
this reimplementation exactly:

| | Low risk | Medium risk | High risk |
|---|---|---|---|
| High confidence | -0.05% | +0.50% | +3.38% |
| Probably solved | -0.95% | -0.43% | +2.33% |
| Likely solved | -2.96% | -2.52% | -0.20% |
| Clearly unsolved | -2.00% | -1.94% | -1.65% |

12/12 match to within 0.01 percentage points — `test_matches_published_table_exactly`
is parametrized over all 12 and passes on every one.

## A genuine floating-point curiosity, left visible rather than hidden

Running the demo, the "Clearly unsolved / Low risk" cell prints **-1.99%**, not the
published -2.00%. The true value is exactly -0.01995 in real arithmetic; IEEE-754
double precision stores it as -0.019949999999999998984... — a hair short of the
0.5-boundary that would round up — so Python's default rounding correctly gives
-1.99. This is not a bug in the formula (the test suite's 0.01-point tolerance
correctly treats it as a match, since it is one); it's the ordinary, well-understood
behavior of binary floating point representing a decimal fraction, and it's left
visible in the demo output rather than papered over with a display-rounding hack
tuned to hit one specific published number.

## The extension: breakeven analysis (not on the original page)

Solving the same formula for the crossover point: `d_prob* = a_change / (a_prob *
d_loss)`. Answers a question the point-estimate calculator doesn't: *holding
alignment assumptions fixed, how bad would deal-decline risk need to get before the
recommendation flips?* At "Alignment clearly unsolved," breakeven d_prob is 100%+ —
no realistic deal-decline risk flips that recommendation, which is a real, if
unsurprising, way of seeing why the alignment-scenario assumption dominates deal-
decline risk in that regime. `handoff_breakeven.png` plots this across all four
alignment scenarios.

## Running it

```
pip install matplotlib pytest
python3 run_demo.py                 # worked example, full table, breakeven table + plot
python3 -m pytest test_handoff.py -v   # 19 tests, all 12 published cells + extension
```

## What this does not do

The source page's *other* interactive piece — Stage 1's target-year tradeoff curves
— isn't attempted here. That analysis draws on a separate takeoff-simulation model
(referenced on the page but not exposed as a closed-form formula the way the handoff
calculator is), and reproducing it faithfully would mean guessing at simulation
methodology I don't have, not reimplementing a specified formula. That's a real gap,
named rather than quietly worked around with an invented substitute.
