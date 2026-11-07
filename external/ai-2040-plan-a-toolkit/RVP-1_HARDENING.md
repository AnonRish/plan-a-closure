# RVP-1 hardening pass

This pass adds four concrete controls:

- machine-checkable adversary coverage;
- exact finite-population statistical bounds;
- a real pcap software-capture benchmark with explicit non-hardware projections;
- a double-entry Track 3 ownership graph.

The formal reference model is tightened so PASS requires evidence, matching the TLA+ safety invariant.

Remaining gaps are empirical: real 400/800/1600GbE capture hardware, production accelerator wipe measurements, live side-channel measurements, physical inspection and independent replication require access to the systems or independent parties.
