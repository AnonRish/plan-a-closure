
# RVP-1 integrated red-team matrix

The integrated harness performs deliberately bad actions against the core
controls and requires a fail-safe result.

The current matrix covers:
- traffic outside the active gateway envelope;
- unauthorized weight-path protocol;
- tampered memory-wipe evidence;
- altered TAP configuration;
- missing independent server observer;
- broken report chain;
- attempted UNKNOWN -> PASS promotion;
- unjustified multiplication of correlated failure probabilities;
- promotion of software evidence into a hardware claim.

This is a safety test of the verification implementation, not a claim that the
listed attacks exhaust the real-world adversary space.
