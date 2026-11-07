
# Security-testing layer

The RVP-1 package now includes deterministic malformed-input fuzzing for the raw
frame parser and bounded sequence exploration for the reference protocol state
machine.

These tests are intentionally finite. Passing them means the implementation
survived the tested cases; it is not a proof of memory safety, parser
completeness, or protocol security against every possible input.
