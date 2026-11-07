
# Track 3 tail audit

The AI 2040 Plan A scenario proposes exhaustive auditing above a threshold and
random sampling of the remaining small-owner tail, with sampled units traced
through resales until they reach physically inspected inventory or fail.

This repository now has a reproducible implementation of the tail sampling and
account-reconciliation layer. It does not claim that the public registry has a
closed global population or authoritative serial-level records.

The sampling frame must be frozen before the seed is revealed to the party being
audited. The sample is weighted by delivered compute so a large tail recipient
cannot hide behind being one legal entity among many.

A field implementation should replace the example data structures with:
vendor-sales records, resale/transfer records, inventory records, decommissioning
records, stable serial identifiers, and independent physical inspection evidence.

## How a sampled unit is resolved

A unit is drawn uniformly from all units recorded as delivered into the tail, then mapped to its recipient by cumulative delivered units, so memory grows with the number of recipients rather than the number of units. Within a recipient, the units it received are split in order into held, sold-onward and attrition units:

| Sampled unit lands in | Outcome |
|---|---|
| held inventory (`current_holdings`) | `PASS`: a physical inspection is required |
| a unit sold onward (`onward_sales`) | `TRACE_FORWARD`: the trace continues at the buyer |
| an attrition claim (`documented_attrition`) | `FAIL`: the claim is not independently verified |
| an account that does not reconcile, or a missing account | `FAIL` |

## What the bound treats as a failure

`TRACE_FORWARD` traces have not reached a physically inspected unit, so they count as failures in the bound until they are followed to the end. Following them needs a buyer-to-buyer transfer graph, which this flat model does not have; `track3_audit_chain.py` models it (see `docs/TRACK3_AUDIT_CHAIN.md`). The reported `upper_failure_rate` is the exact one-sided binomial (Clopper-Pearson) limit from `track3_certificate.one_sided_failure_upper_bound`, computed in log space, so it still works when the binomial coefficients are too large for floating point (for example 100,000 samples with 100 failures). The finite-population correction is not applied, which makes the bound slightly conservative.
