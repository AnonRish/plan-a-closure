
# Track 3 tail audit

This module implements the small-owner tail part of the AI 2040 Plan A
accounting proposal as a reproducible software model:

1. freeze a tail population;
2. sample units with a recorded seed;
3. audit the recipient account;
4. follow declared onward transfers;
5. end at physically held inventory or a documented failure;
6. turn observed failure frequency into a conservative upper bound.

The model is intentionally not presented as a treaty certificate. Real
deployment additionally needs serial/asset identity, audited primary records,
independent physical inspectors, finite-population sampling design, and
independent replication.

The implementation uses deterministic representative branching after an account
is selected. A production version should replace this with exact unit-level
proportional trace sampling when serial-less sales are represented.
