# Independent Verification: Common-Mode Risk Analysis

Section 11 of the Phase 3 brief asks the right skeptical question
directly: is "a different executable" the same thing as "an independent
implementation"? No. This document analyzes exactly where the three
verification paths this repository now has -- the reference
implementation, the Python standalone verifier, and the JavaScript
standalone verifier -- are genuinely independent, and where they still
share risk.

## What exists

1. `frontier_verify.receipts.signing.verify_receipt` -- the reference
   implementation, part of the main package.
2. `tools/standalone-verifier/verify_receipt.py` -- Python, but does not
   import `frontier_verify`; re-implements canonicalization from scratch.
3. `tools/standalone-verifier/verify_receipt.js` -- JavaScript/Node,
   using Node's *native* Ed25519 support (no npm dependencies at all).

All three cross-checked on every test run, including a deliberately
Unicode/emoji-heavy case
(`tests/conformance/test_cross_language_verifier_agrees.py`), and all
three agreed on the first real run against genuine Python-signed receipts
-- not tuned to pass afterward.

## Genuinely independent between (1)/(2) and (3)

- **Language runtime**: CPython vs. V8/Node -- different memory models,
  different string/Unicode handling internals.
- **Crypto binding**: `pyca/cryptography` (Python, wraps OpenSSL via its
  own Rust/C binding layer) vs. Node's built-in `crypto` module (wraps
  OpenSSL via a completely different, V8-native binding layer). If
  `pyca/cryptography`'s Ed25519 binding specifically had a bug, the JS
  verifier would not inherit it, and vice versa -- this is real, not
  cosmetic diversity.
- **JSON serialization**: Python's `json` module vs. V8's `JSON.stringify`
  -- independently implemented parsers/serializers with their own
  histories and edge-case handling.
- **Key material handling**: the JS verifier goes through RFC 8037 JWK
  construction (`crypto.createPublicKey` with a JWK object) to build a
  usable key from raw bytes; the Python implementations decode raw bytes
  directly via `Ed25519PublicKey.from_public_bytes`. Genuinely different
  code paths to the same cryptographic operation.

## NOT independent, stated plainly

- **All three were written by the same author, in the same session, with
  full knowledge of the others.** This is the single biggest limiter on
  what this cross-checking can prove. Genuine implementation independence
  in the sense that catches the most dangerous class of bug -- "the spec
  itself has a subtle flaw everyone who reads it the same way will miss"
  -- requires a different person or team working from the specification
  alone, ideally without seeing this repository's code, ideally separated
  in time. Nothing here provides that. A bug in my own understanding of
  canonical JSON, Ed25519, or the receipt schema could appear in all three
  implementations for the same reason, because I hold the same
  (mis)understanding while writing each one.
- **All three trust the same underlying primitive**: Ed25519 itself. If
  Ed25519 had an undiscovered cryptographic weakness, no amount of
  implementation diversity here would matter -- this is true of any
  Ed25519 usage anywhere and not a gap specific to this project, but worth
  naming rather than leaving implicit.
- **All three implement the same DESIGN**, not just independently-derived
  designs that happen to agree. The canonicalization scheme (sorted-key
  JSON, no floats yet, ADR-0002's known limitation) is a single design
  choice I made once; the JS and second Python implementation both follow
  it because I told them to, not because two independent teams arrived at
  the same scheme separately. A flaw in the SCHEME (as opposed to a coding
  bug in one implementation) would appear in all three.

## What the cross-checking DOES buy, honestly

Real protection against: implementation bugs in any ONE of the three
(a canonicalization typo, an off-by-one, a wrong exclusion of the
`signature` field, a broken base64 path, a language-specific edge case
like Unicode surrogate pair handling). Genuinely caught, not
hypothetically -- the deliberate goal of writing the JS canonicalizer from
the spec description rather than transliterating the Python line-by-line
was to give bugs of exactly this kind a chance to appear, and none did on
first correct-by-construction attempt, which is itself weak evidence (not
proof) that the underlying design is at least simple enough not to invite
transcription errors.

Real protection against: a supply-chain or library-level bug specific to
ONE crypto binding (`pyca/cryptography` vs. Node's native `crypto`).

**Not protection against**: a flaw in the canonicalization design itself,
a flaw in the receipt schema's semantics, or a flaw in my own reasoning
that all three implementations share because I wrote all three with the
same understanding. Calling this "independent verification" in the full
sense the brief's earlier phases used that phrase would overclaim what
same-author, same-session, same-design cross-checking can actually
establish.

## Was a genuine second implementation worth building here?

Yes, on balance -- Node's native Ed25519 support meant zero new external
dependencies, the empirical testing surfaced no bugs but exercised a
real, different code path (JWK key construction, V8's JSON engine), and
it directly answers "is receipt verification portable across languages,"
which matters for the protocol's actual interoperability claim
independent of the common-mode caveat above. What it does NOT do is
retroactively upgrade `docs/ai2040-coverage-matrix.md`'s "verifier
independence" row past what same-author cross-checking can honestly
support -- see that document for the specific, bounded claim this
analysis licenses.
