# Track 3 audit chain

`track3_audit_chain.py` runs the two-layer audit from AI 2040 Recommendation #2 (the covert-projects supplement, Appendix B) on a declared ledger, end to end, and reports the certificate `D + L`. It is a research model over a synthetic or declared ledger, not a verification result. No real transaction ledger is public, so `data/track3/audit_chain_input.example.json` is invented.

```bash
python track3_audit_chain.py --input data/track3/audit_chain_input.example.json --sample-size 300
```

The exit code is 0 for `PASS` and 1 otherwise.

## Input

| Field | Meaning |
|---|---|
| `population_closed` | must be `true`, otherwise the status is `UNKNOWN` |
| `threshold_T` | `{"value": ..., "unit": "H100e"}`; convert MW with `track3_units.py` |
| `sales` | vendor sales: `vendor`, `buyer`, `units`, optional `buyer_producible` |
| `accounts` | per owner: `held`, `inspected` (held chips actually produced), `transfers` (`buyer`, `units`, optional `buyer_producible`), `decommissions` (`units`, `verified`) |
| `delta`, `seed`, `sample_size` | confidence level, reproducible seed, number of tail traces |

`buyer_producible: false` marks a counterparty that cannot be audited. An owner's account must reconcile: units received equal units held plus units transferred plus units decommissioned.

## Layer 1: audit everything at or above T

1. Every owner whose recorded receipts are at or above T is audited. Each audit reveals that owner's onward sales, which can push further owners over T, so the audit repeats until every unaudited recipient is below T. Receipts are summed over all sellers, so a firm that crosses T only in aggregate is still audited.
2. These events are added in full to the untraced pool `L`: a sale to a counterparty that cannot be produced, an unverified decommissioning claim, units received but not accounted for, and held chips that were not produced for inspection.
3. A single such event of at least T units blocks certification (`status: BLOCKED`). So do records whose dispositions exceed their receipts.

## Layer 2: sample the tail

The tail is everything recorded as delivered to below-T recipients. Units are drawn uniformly without replacement, so a recipient is hit in proportion to what it received. Inside an account the unit lands in held, sold-onward or decommissioned units in proportion to their size.

| Sampled unit lands in | Result |
|---|---|
| a held chip that was produced | pass |
| a held chip that was not produced | fail |
| a unit sold onward to a producible buyer | follow the trace to that buyer and repeat |
| a unit sold to a counterparty that cannot be produced | fail |
| a verified decommissioning | pass |
| an unverified decommissioning claim | fail |
| an unbalanced account | fail |
| an audited firm | pass (its shortfalls are already in `L`) |
| a trace longer than `--max-depth` hops (default 25) | fail |

## Result

`upper_bound_units = L + D`, where `D` is the tail size times the exact one-sided binomial upper failure rate from `track3_certificate.py` at confidence `1 - delta`. With no failures this is close to the supplement's rule of thumb `D ≈ (tail size / n) × ln(1/δ)`. `clean_traces_needed(tail_units, max_d_units, delta)` returns how many clean traces certify a target `D`.

## Not modelled

- Vendor production records (Recommendation #1) and unrecorded sales found by incentives and imagery (Recommendation #3).
- Serial-number continuity and advance-notice rules. They are protocol requirements in `data/track3/serial_continuity_protocol.json` and `data/track3/inspection_protocol.json`; here an inspection passes or fails as recorded.
- The finite-population correction, which makes `D` slightly conservative.

## Tests

`tests/test_track3_audit_chain.py` covers the synthetic population, the recursion, each `L` rule, the blocking rule, tail diversion (the bound covers a known 10% diversion in at least 36 of 40 seeds), proportional resolution, cycles, reproducibility and input validation. Breaking the recursion, the threshold comparison, the decommissioning rule, the bound or the proportional split makes the suite fail.
