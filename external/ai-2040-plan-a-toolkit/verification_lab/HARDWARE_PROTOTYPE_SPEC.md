# Hardware prototype specification

The software lab is not a substitute for hardware. This document turns its
interfaces into bench-testable acceptance criteria.

## Passive optical tap

Prototype at 400G first, then 800G and 1600G. Measure insertion loss, bit-error
rate, timestamp fidelity, packet loss under sustained load, behavior during
link flaps, and power/cooling envelope. The tap must be passive with respect to
the protected path and expose an independently observable health state.

## Capture system

Drive the tap at declared line rate for hours, not seconds. Record packets
received, packets dropped, storage backlog, recovery after fault, and whether the
captured evidence root remains continuous across failover.

## Recomputation server

Use measured-boot and hardware-rooted identity where available. Put the signing
key behind an independent root of trust. Test power interruption, enclosure open,
unexpected firmware, rollback, and loss of the monitoring path. Every integrity
failure should fail closed rather than produce a normal verification report.

## Tap installation

Maintain a signed asset registry containing tap ID, port mapping, expected
configuration digest, physical inspection evidence, challenge history and current
health. Periodically re-challenge configurations from an independent verifier.

## Memory and side channels

For memory, test every storage mode and firmware state rather than assuming a
generic overwrite algorithm works everywhere. For side channels, establish a
baseline from benign workloads, then run controlled leakage experiments and
measure capacity before and after mitigation. A warden is useful only after
false-positive and false-negative rates are measured on labeled data.

No values in this document are represented as having been experimentally measured
by this repository.
