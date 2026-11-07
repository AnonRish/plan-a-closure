# Track 3 residual-compute bound

The registry now contains a standalone accounting engine that can turn closed,
site-level independent capacity observations into a conservative residual upper
bound.

It deliberately has a hard epistemic gate:

- open accounting population -> UNKNOWN
- missing independent site evidence -> UNKNOWN
- complete closed population -> numeric bound
- optional sampled tail -> explicit statistical upper bound

This keeps three different claims separate:

1. the repository has complete evidence-accounting coverage of its defined rows;
2. the public evidence implies a numeric upper bound inside a defined closed population;
3. the world contains no material secret compute.

Only the first claim can be closed by repository bookkeeping alone. The third
requires privileged/global evidence outside a public registry.
