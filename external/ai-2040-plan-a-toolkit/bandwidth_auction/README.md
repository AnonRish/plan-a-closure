# Outgoing-bandwidth auction (VCG)

The Transparency Plan caps the outgoing channel between the secure zone and the
public zone and calls for "an ongoing auction for the outgoing bandwidth" without
specifying a mechanism. The naive version — highest bidder wins, pays their own bid
— gives every bidder a reason to shade their bid down, so the allocation stops
reflecting what anyone actually values. This implements Vickrey-Clarke-Groves (VCG)
instead: allocate to maximize declared welfare, charge each winner exactly the cost
their presence imposes on everyone else. VCG's textbook promise is that truthful
reporting is a dominant strategy — never worse than lying, regardless of what anyone
else bids.

That's not asserted here, it's tested: 300 random scenarios × 11 different lie
magnitudes (from reporting 10% of true value to 5x true value) = 3,300 attempts to
find a case where lying beats honesty. **Zero found**, for both the plain mechanism
and the capped variant below.

## A real allocation, from `run_demo.py`

Five bidders, capacity 100:

| Bidder | Qty | Value/unit | Pays | Avg price |
|---|---|---|---|---|
| interp_release | 40.0 | 8.50 | 48.00 | 1.20 |
| external_audit | 25.0 | 6.00 | 30.00 | 1.20 |
| incident_report | 15.0 | 9.00 | 18.00 | 1.20 |
| routine_metrics | 20.0 | 1.20 | 16.00 | 0.80 |
| dataset_export | 0.0 | 0.80 | — | — |

Total welfare 649. Notice `dataset_export` — lowest value, wanted the most — gets
crowded out entirely. That's the mechanism working as intended (capacity goes to
whoever values it most), and it's also the whole reason the capped variant exists:
nothing here favors *diversity* of who gets through, only *value*.

## What the cap actually costs

Capping any bidder at 30% of capacity and re-running: welfare drops to 576 (11.2%
lower) — proven with a constructed worst case in `test_cap_can_reduce_total_welfare_vs_uncapped`,
not just observed in one demo run. That's the real, honest cost of an anti-concentration
rule: less total value extracted from the channel.

What the cap does *not* cost, which I expected going in and was wrong about: truthfulness.
The same 3,300-attempt sweep run against the capped mechanism found zero violations too
(`test_capped_mechanism_is_still_truthful_empirically`). This isn't a coincidence —
VCG stays truthful under any feasibility constraint that doesn't depend on the bidder's
own report, and a fixed percentage cap is exactly that kind of constraint. Worth stating
plainly since it contradicts what the code comments originally assumed before the test
was actually run.

The cap does *not* guarantee everyone gets something, either — in the demo above,
`dataset_export` gets zero under both the capped and uncapped mechanism, because the
other four bidders' demand (even capped) already fills capacity.

## Running it

```
pip install pytest
python3 run_demo.py              # the allocation table above
python3 -m pytest test_auction.py -v   # 11 tests, including the truthfulness sweeps
```

## What this does not do

Bidders here have linear, flat valuations up to a hard quantity cap — a real
simplification. It doesn't model collusion between bidders (VCG is famously
vulnerable to bidder rings splitting up demand), doesn't handle a bidder who can
credibly threaten to sit out entirely to change the reference welfare calculation for
others, and treats "value per unit" as something bidders actually know about
themselves, which for genuinely novel research disclosures is its own hard problem.
