"""Canonical encoding utilities.

Frontier Verify needs deterministic, reproducible digests: the same logical
object must hash to the same value regardless of key order, whitespace, or
serialization quirks. This module implements a restricted canonical JSON
encoding *inspired by* RFC 8785 (JSON Canonicalization Scheme, JCS).

MATURITY: EXPERIMENTAL.

This is real code with real tests (see tests/unit/test_canonical.py), not a
placeholder -- but it is not a certified JCS implementation. Specifically:

  * It relies on Python's json.dumps(sort_keys=True, separators=(",", ":"))
    rather than implementing JCS's ECMA-262-derived number formatting rules.
    For the int/str/bool/None-heavy schemas in this repo that distinction
    never bites, but it WILL bite if a float with an unusual representation
    (e.g. very large exponents, -0.0) is ever canonicalized. Do not use this
    module to canonicalize arbitrary untrusted floats without re-reading
    RFC 8785 section 3.2.2.3 first.
  * It does not perform Unicode NFC normalization. JCS does not require this
    either (it canonicalizes UTF-16 code unit order, not grapheme form), but
    it's worth naming explicitly since "canonical" invites the assumption
    that every normalization question has been handled.

If Frontier Verify ever needs byte-for-byte interop with another JCS
implementation, replace this module's internals (not its call sites) with a
real RFC 8785 library and re-run the digest tests -- they'll catch any
behavioral drift because they pin exact digest values, not just equality
between two calls to this same code.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any


def canonicalize(obj: Any) -> bytes:
    """Serialize obj to canonical JSON bytes: sorted keys (recursively, via
    json.dumps), no insignificant whitespace, UTF-8."""
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def digest(obj: Any) -> str:
    """SHA-256 hex digest of the canonical encoding of obj."""
    return hashlib.sha256(canonicalize(obj)).hexdigest()
