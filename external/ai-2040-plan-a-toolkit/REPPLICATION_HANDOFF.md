
# Independent replication handoff

An external lab should not merely rerun unit tests. The intended replication is
a separate environment with a separately controlled verifier and, for hardware
claims, hardware not operated by the original experimenter.

## Minimum software replication

- record repository commit;
- record OS, kernel, Python and dependency lock;
- execute the complete conformance workflow;
- archive benchmark, hostile-prover and readiness outputs;
- recompute every artifact digest;
- compare results against the published scorecard.

## Minimum hardware replication

- independently source or control the TAP/capture hardware;
- record optical/electrical link parameters;
- generate both compliant and adversarial traffic;
- measure frame loss at increasing packet rates;
- test incomplete TCP streams and connection-start midstream;
- measure latency and CPU/DPU utilization;
- attempt timing/header/payload covert channels;
- record raw pcap and instrument logs;
- repeat on a second machine/operator.

## Acceptance

Replication results are reported as:
REPRODUCED, PARTIALLY_REPRODUCED, NOT_REPRODUCED, or INCONCLUSIVE.

A disagreement is preserved as data. It is not edited away to make the project
look successful.
