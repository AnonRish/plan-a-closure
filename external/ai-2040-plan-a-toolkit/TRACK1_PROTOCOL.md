# Track 1 — Embedded company auditing protocol

This is a software protocol for the deployable-now company-auditing track
described by AI Futures. It does not create legal audit authority or independent
physical access.

## Round

An auditor creates a fresh random challenge. The company must provide every
required artifact with a response bound to that round's challenge. Evidence is
hashed, chained, and later represented by a threshold-signed receipt.

The protocol treats missing evidence as UNKNOWN. It does not infer that a
challenged file is truthful simply because the company produced a valid response.

## Red-team coverage

The included protocol red-team exercises cross-round challenge replay, required
evidence omission, and the remaining content-truthfulness limitation.

The last case is intentionally marked as a limitation: software cannot establish
the honesty of company-provided evidence without an independent observation root.

## Evidence ladder

DECLARED -> CHALLENGE_BOUND -> HASH_CHAINED -> MULTI_SIGNED -> EXTERNALLY_CORROBORATED

The current implementation reaches the fourth layer in software. The fifth layer
requires external auditors and independent evidence sources.
