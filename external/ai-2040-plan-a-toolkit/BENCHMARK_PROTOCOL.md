# Head-to-head benchmark protocol

The package is intended to be compared against any other verification
implementation without relying on repository size, prose, or self-reported
completeness.

Every submission reports the same metric names and conditions:

- capture: line rate, drop rate, loss recovery;
- reconstruction: frames/sec and inference-event reconstruction success;
- verification: prover throughput, verifier throughput and verifier/prover ratio;
- assurance: detection rate for preregistered adversarial cases with confidence intervals;
- security: tamper-detection latency and fail-closed behavior;
- completeness: timing/header/payload covert-channel capacity under a defined traffic policy;
- memory: wipe time per TB and success of challenge-bound readback tests;
- accounting: traced fraction, interval width and residual upper bound;
- reproducibility: independent replication success and artifact hash match.

Conditions, hardware model, software commit, seeds and raw data must be
published alongside each number. Synthetic benchmark numbers and real-hardware
numbers are kept in separate fields.

Current external work already has meaningful hardware benchmarks. Amodo reports
800 requests at concurrency 32 through a passive-TAP prototype with 1 Gbps
irrelevant traffic, as well as early verifier-compute and memory-wipe
measurements. RVP-1 therefore treats those as external baselines to reproduce
or beat experimentally rather than numbers to imitate by simulation.
