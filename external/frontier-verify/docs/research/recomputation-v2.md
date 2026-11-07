# Track 2 recomputation v2

This router is the integrated, executable software path for randomized partial
recomputation while the legacy Phase 6 endpoints remain unchanged.

Sequence:

1. Auditor creates a challenge commitment.
2. Prover submits every claimed chunk plus its actual input data.
3. Inputs are stored content-addressably and each claimed digest is checked.
4. The complete chunk set receives a stable claim-set digest and becomes locked.
5. Auditor reveals the challenge implicitly by invoking the check endpoint.
6. Existing HMAC commit-reveal sampling chooses the chunks.
7. A dependency-free deterministic kernel recomputes selected inputs.
8. The verifier compares claimed vs recomputed output digests and emits a signed receipt.

This is EXPERIMENTAL software infrastructure. It is not evidence that a frontier
model can be economically recomputed, and it does not validate passive optical
taps, GPU behavior, physical security or organizational independence.
