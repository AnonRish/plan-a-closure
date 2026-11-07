"""32-bit TCP sequence-space arithmetic (RFC 793 / RFC 1982 style)."""
from __future__ import annotations

MOD = 1 << 32
HALF = 1 << 31


def add(a: int, b: int) -> int:
    return (a + b) & 0xFFFFFFFF


def diff(a: int, b: int) -> int:
    """Signed distance a-b in [-2**31, 2**31)."""
    return ((a - b + HALF) & 0xFFFFFFFF) - HALF


def lt(a: int, b: int) -> bool:
    return diff(a, b) < 0


def unwrap(seq32: int, base32: int, ref: int) -> int:
    """Map a 32-bit sequence number to an unbounded stream offset.

    ``base32`` is the sequence number that corresponds to offset 0 and ``ref`` is
    a recent offset (for example the highest offset seen so far).  The result is
    the offset congruent to ``seq32 - base32`` (mod 2**32) that lies closest to
    ``ref``; it can be negative.
    """
    rel = (seq32 - base32) & 0xFFFFFFFF
    delta = ((rel - ref + HALF) & 0xFFFFFFFF) - HALF
    return ref + delta
