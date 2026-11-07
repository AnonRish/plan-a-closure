# Verification threat model

Adversaries considered by the testbed:

1. ordinary software bug;
2. prover attempts selective evidence omission;
3. prover changes workload after approval;
4. prover predicts sampling and adapts;
5. verifier report tampering;
6. physical removal/replacement of a tap;
7. compromised recomputation server;
8. side-channel communication between prohibited systems;
9. hidden compute outside the declared population.

For every threat the desired safe outcome is one of FAIL, UNKNOWN, or an
explicit investigation signal. The system must not silently reinterpret a
missing observation as evidence that a prohibited activity did not occur.

The threat model intentionally distinguishes integrity from truth: a signed
statement can prove who signed it and that it was not modified, but cannot by
itself prove that the underlying observation was honest.
