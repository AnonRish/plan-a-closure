
# Reproducible Verification Research Package

## Objective

RVP-1 is a unified experimental package for the AI 2040 verification problem:
known compute must be verifiable, while unknown compute must be bounded rather
than silently treated as absent.

It combines:
- normative protocol state machine;
- executable reference model;
- raw Ethernet/IPv4/TCP/UDP frame processor;
- whitelist and health-check enforcement;
- TCP reconstruction with gap detection;
- recomputation/sampling assurance math;
- hostile-prover simulations;
- content-addressed commitments and Merkle proofs;
- benchmark runner;
- hardware-prototype acceptance criteria;
- independent replication protocol.

## What is novel in the package

Instead of treating each verification layer separately, the package gives every
observation a common lifecycle:

capture -> parse -> classify -> reconstruct -> commit -> challenge -> sample ->
recompute -> report -> independently replicate.

The design also makes the epistemic boundary explicit: integrity of an evidence
record is not the same thing as truth of the underlying physical observation.

## Comparison discipline

Do not claim superiority merely from repository size or feature count. Compare
measured quantities under equal conditions: capture loss, sustained throughput,
verification throughput, verifier/prover compute ratio, detection probability,
false-positive rate, side-channel capacity, memory-wipe time, and independent
replication success.

This makes the package suitable for direct head-to-head experiments with other
verification prototypes.
