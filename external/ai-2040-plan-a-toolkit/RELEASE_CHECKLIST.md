# RVP-1 research release checklist

## Software gate

- [ ] Full conformance CI passes on the exact release commit.
- [ ] Benchmark and adversarial outputs are archived.
- [ ] Artifact hashes are recorded.
- [ ] TLA+ model is checked by an independent evaluator.

## Hardware gate

- [ ] Optical/electrical TAP tested at the declared link rate.
- [ ] Sustained capture loss measured under realistic packet mix.
- [ ] Failover and monitor-outage behavior measured.
- [ ] Memory wipe tested against the actual storage/firmware configuration.
- [ ] Side-channel capacity measured before and after mitigation.
- [ ] Physical installation inspected independently.

## Replication gate

- [ ] Independent operator reproduces software outputs.
- [ ] Independent party reproduces hardware measurements.
- [ ] Raw pcaps/instrument logs are archived.
- [ ] Differences are preserved and investigated.

## Claim gate

A claim may only be promoted to its stated evidence level through provenance/gate.py.
No synthetic result may be represented as hardware evidence, and no first-party
experiment may be represented as independent replication.
