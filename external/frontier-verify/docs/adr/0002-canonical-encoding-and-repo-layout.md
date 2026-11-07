# ADR-0002: Canonical Encoding Scheme, and Single-Package Repository Layout

## Status
Accepted (Phase 1)

## Decision 1: JCS-inspired canonical JSON, not full RFC 8785, not CBOR

**Objective:** deterministic digests -- identical content hashes
identically regardless of field order or construction path.

**Options considered:**
- A certified RFC 8785 (JSON Canonicalization Scheme) library.
- Canonical CBOR (RFC 8949 deterministic encoding).
- `json.dumps(sort_keys=True, separators=(",", ":"))` -- what Phase 1 ships.

**Decision:** the third option, implemented in
`frontier_verify/core/canonical.py`.

**Why:** every field in the current schema is a string, bool, dict, or
datetime (rendered as ISO 8601 text). None of the number-formatting edge
cases that separate strict JCS from `json.dumps` (large exponents, `-0.0`)
apply yet. JSON also stays human-readable in test failures and debug logs,
which a canonical CBOR encoding would not. Pulling in a certified JCS
dependency for zero behavioral difference, on a schema with no floats,
would be exactly the kind of unnecessary complexity section 61 of the
source spec warns against.

**What would force a revisit:** the moment a numeric field (a FLOP count, a
confidence score, anything non-integer) enters the evidence or receipt
schema. `frontier_verify/core/canonical.py`'s own docstring flags this
explicitly so it isn't only discoverable here. At that point: swap the
*internals* of `canonicalize()`/`digest()` for a real RFC 8785
implementation, keep every call site unchanged, and re-run
`tests/unit/test_canonical.py` -- which pins an exact byte output
(`test_canonicalize_has_no_insignificant_whitespace`), so any behavioral
drift from the swap fails loudly instead of silently.

## Decision 2: one Python package, not the proposed multi-package monorepo

**Source spec's proposal (section 13):** `packages/core`,
`packages/evidence`, `packages/receipts`, `packages/policies`,
`packages/attestations`, plus a separate `sdk/python/`, each presumably
independently versioned and published.

**Decision:** one installable package, `frontier_verify`, with the
proposed boundaries kept as internal modules
(`frontier_verify.core`, `.evidence`, `.attestations`, `.policies`,
`.receipts`, `.api`, `.sdk`) rather than separate packages.

**Why:** independent package versioning earns its complexity when there's a
second, different consumer that needs a *subset* -- for example, a
second-language verifier implementation (Phase 4/9) that only needs the
evidence and receipt JSON Schemas, not the FastAPI server or the Python
SDK. That consumer doesn't exist yet. Splitting into eight packages for a
single-developer Phase 1 with one consumer (this repository's own tests
and CLI) would be structure serving an imagined future, not a real one --
more `pyproject.toml` files to keep in sync, more places a version bump can
be forgotten, zero present benefit. It also directly matches the source
spec's own usage example in section 16 (`from frontier_verify import
VerifierClient`), which assumes a single top-level package, not a
separately-named SDK distribution.

**What would force a revisit:** a real second consumer of only part of the
system. At that point, the module boundaries already drawn
(`frontier_verify/evidence/`, `frontier_verify/receipts/`, etc.) are
exactly where a package split would happen -- this decision doesn't
foreclose splitting later, it just declines to pay for it before anything
needs it.

## Non-decision: `cli/` stays a separate top-level directory

The CLI (`cli/fv/`) is *not* folded into the `frontier_verify` package
despite the reasoning above, because the source spec's structure (section
13) puts `cli/` at the top level alongside `packages/`, and there's a real
reason to keep that: a CLI entry point (`fv`) is a distribution-level
concern (`[project.scripts]` in `pyproject.toml`), not an
import-level one -- nothing in `frontier_verify` imports from `cli`, only
the reverse. Keeping it structurally separate costs nothing and matches
the one part of the proposed layout that has a real reason behind it
independent of "the spec said so."
