
# RVP-1 — Reproducible Verification Protocol

RVP-1 is the canonical package entry point.

## Core claim types

Integrity claim: the evidence bytes, commitment and report chain were not
modified after signing.

Correctness claim: a recomputation or independent check found the declared
result consistent with the committed inputs and policy.

Completeness claim: the observation boundary is demonstrably complete for the
declared population and channel model.

These claims must not be conflated. A valid signature proves integrity, not that
the physical observation was truthful. A passing sample proves the sample, not
zero probability of an unsampled attack.

## Required lifecycle

OPEN -> COMMITTED -> CHALLENGED -> CHECKED -> TERMINAL

The external verifier creates the challenge only after the complete claim set is
committed. Missing observations yield UNKNOWN, not PASS.

## Evidence hierarchy

1. synthetic fixture;
2. reproducible software capture;
3. bench hardware measurement;
4. independently replicated hardware measurement;
5. operational deployment evidence;
6. multi-party/international validation.

Promotion between levels requires new evidence; no level is inferred from the
one below it.

## Composed assurance

Multiple controls are composed with a union bound by default. Multiplication of
failure probabilities is permitted only when independence has been explicitly
certified and common-mode dependencies are absent. This prevents a stack of
nominally independent controls from receiving unjustified confidence.

## Cryptographic proof boundary

The crypto package defines a machine-readable proof envelope and statement
identity. It does not pretend a generic hash or signature is a zero-knowledge
proof. A real proof system must supply and independently verify the proof
artifact.
