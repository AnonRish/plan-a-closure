"""Interval-based stream assembler implementing the policies in :mod:`packet_forge.model`.

State is a sorted list of non-overlapping *pieces*, each pointing at the claim that currently owns
those offsets.  Adding a claim splits the pieces it touches, compares bytes against the owner of every
overlapped piece (any difference is a conflict, whatever the policy decides), and lets the policy pick
the new owner of each overlapped sub-range.
"""
from __future__ import annotations

from bisect import bisect_right
from typing import List, NamedTuple, Tuple

from .model import Claim, Policy


class ConflictEvent(NamedTuple):
    start: int
    end: int
    new: Claim       # the claim being added
    old: Claim       # the owner of these bytes when the new claim arrived


class Piece:
    __slots__ = ("start", "end", "claim")

    def __init__(self, start: int, end: int, claim: Claim):
        self.start, self.end, self.claim = start, end, claim

    def data(self) -> bytes:
        return self.claim.data[self.start - self.claim.start:self.end - self.claim.start]


def _coalesce(pieces: List[Piece]) -> List[Piece]:
    out: List[Piece] = []
    for p in pieces:
        if p.start >= p.end:
            continue
        if out and out[-1].end == p.start and out[-1].claim is p.claim:
            out[-1].end = p.end
        else:
            out.append(p)
    return out


class StreamAssembler:
    def __init__(self, policy: Policy, stream_start: int = 0):
        self.policy = policy
        self.stream_start = stream_start
        self.delivered = stream_start
        self._starts: List[int] = []
        self._pieces: List[Piece] = []
        self.conflicts: List[ConflictEvent] = []

    # -- mutation ---------------------------------------------------------------------------------
    def add(self, claim: Claim) -> List[ConflictEvent]:
        if not claim.data:
            return []
        if self.policy.drop_flags and set(claim.flags) & set(self.policy.drop_flags):
            return []
        if claim.start < self.stream_start:
            raise ValueError("claim starts before the stream; trim it first")
        events: List[ConflictEvent] = []
        a, b = claim.start, claim.end
        frozen_below = self.delivered
        i = bisect_right(self._starts, a) - 1
        if i < 0 or self._pieces[i].end <= a:
            i += 1
        j = i
        out: List[Piece] = []
        cursor = a
        while j < len(self._pieces) and self._pieces[j].start < b:
            p = self._pieces[j]
            if p.start > cursor:
                out.append(Piece(cursor, p.start, claim))
            ov_a, ov_b = max(p.start, a), min(p.end, b)
            if p.start < ov_a:
                out.append(Piece(p.start, ov_a, p.claim))
            self._compare(claim, p.claim, ov_a, ov_b, events)
            lo = ov_a
            if self.policy.freeze and ov_a < frozen_below:
                mid = min(ov_b, frozen_below)
                out.append(Piece(ov_a, mid, p.claim))
                lo = mid
            if lo < ov_b:
                winner = claim if self.policy.key(claim) < self.policy.key(p.claim) else p.claim
                out.append(Piece(lo, ov_b, winner))
            if ov_b < p.end:
                out.append(Piece(ov_b, p.end, p.claim))
            cursor = ov_b
            j += 1
        if cursor < b:
            out.append(Piece(cursor, b, claim))
        merged = _coalesce(out)
        self._pieces[i:j] = merged
        self._starts[i:j] = [m.start for m in merged]
        self._advance()
        self.conflicts.extend(events)
        return events

    @staticmethod
    def _compare(new: Claim, old: Claim, a: int, b: int, events: List[ConflictEvent]) -> None:
        nb = new.data[a - new.start:b - new.start]
        ob = old.data[a - old.start:b - old.start]
        if nb == ob:
            return
        i, n = 0, b - a
        while i < n:
            if nb[i] != ob[i]:
                j = i
                while j < n and nb[j] != ob[j]:
                    j += 1
                events.append(ConflictEvent(a + i, a + j, new, old))
                i = j
            else:
                i += 1

    def _advance(self) -> None:
        while True:
            k = bisect_right(self._starts, self.delivered) - 1
            if k >= 0 and self._pieces[k].start <= self.delivered < self._pieces[k].end:
                self.delivered = self._pieces[k].end
            else:
                return

    # -- queries ----------------------------------------------------------------------------------
    def runs(self) -> List[Tuple[int, bytes]]:
        """Canonical content as maximal contiguous runs, including data buffered beyond holes."""
        out: List[Tuple[int, bytearray]] = []
        for p in self._pieces:
            if out and out[-1][0] + len(out[-1][1]) == p.start:
                out[-1][1].extend(p.data())
            else:
                out.append((p.start, bytearray(p.data())))
        return [(s, bytes(d)) for s, d in out]

    def contiguous(self) -> bytes:
        """Bytes from the stream start up to the first hole."""
        for s, d in self.runs():
            if s == self.stream_start:
                return d
        return b""

    def holes(self) -> List[Tuple[int, int]]:
        out: List[Tuple[int, int]] = []
        pos = self.stream_start
        for p in self._pieces:
            if p.start > pos:
                out.append((pos, p.start))
            pos = max(pos, p.end)
        return out

    def read(self, a: int, b: int) -> bytes:
        """Canonical bytes for ``[a, b)``; the whole range must be covered."""
        out = bytearray()
        pos = a
        i = bisect_right(self._starts, a) - 1
        if i < 0 or self._pieces[i].end <= a:
            i += 1
        while pos < b:
            if i >= len(self._pieces) or self._pieces[i].start > pos:
                raise KeyError("offset %d is not covered" % pos)
            p = self._pieces[i]
            hi = min(b, p.end)
            out += p.claim.data[pos - p.claim.start:hi - p.claim.start]
            pos, i = hi, i + 1
        return bytes(out)

    def end_offset(self) -> int:
        return self._pieces[-1].end if self._pieces else self.stream_start


def merge_ranges(ranges: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    out: List[Tuple[int, int]] = []
    for a, b in sorted(ranges):
        if out and a <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out
