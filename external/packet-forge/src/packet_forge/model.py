"""Claims and overlap-resolution policies.

A *claim* is one captured TCP segment's payload, placed at a stream offset (offset 0 is the first
byte after the SYN).  When several claims cover the same byte the *policy* decides which one is the
canonical value of that byte.  A policy is a ranking (lower key wins) plus an optional *freeze* rule:
bytes that were already delivered in order to the application are never replaced.

All policies pick a value that was actually sent, so the canonical stream is always some mixture of
the claims; a conflict (two claims with different values on one byte) is policy independent.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Tuple


@dataclass(frozen=True, eq=False)
class Claim:
    arrival: int                     # 0-based position in capture order within the flow direction
    start: int                       # stream offset of the first payload byte
    data: bytes
    frame: int = 0                   # 1-based capture frame number (reporting only)
    acked_at_arrival: int = 0        # stream offset the peer had cumulatively acknowledged
    flags: Tuple[str, ...] = ()      # annotations, e.g. ("syn-data",)

    @property
    def end(self) -> int:
        return self.start + len(self.data)


@dataclass(frozen=True)
class Policy:
    name: str
    key: Callable[[Claim], tuple]    # lower key wins an overlapped byte
    freeze: bool                     # delivered bytes are immutable
    doc: str
    drop_flags: Tuple[str, ...] = () # claims carrying any of these annotations are ignored by the policy


POLICIES: Dict[str, Policy] = {
    "first": Policy(
        "first", lambda c: (c.arrival,), False,
        "Earliest-captured claim wins every byte (retransmitted data never replaces what was seen)."),
    "last": Policy(
        "last", lambda c: (-c.arrival,), False,
        "Latest-captured claim wins every byte (a naive 'overwrite on retransmit' tap)."),
    "lowseq": Policy(
        "lowseq", lambda c: (c.start, c.arrival), False,
        "Claim with the lowest start offset wins; ties go to the earlier capture."),
    "linux": Policy(
        "linux", lambda c: (c.start, -c.end, c.arrival), True,
        "Model of the Linux receive path: lowest start offset wins, then the longer claim, then the earlier "
        "capture; bytes already delivered in order are frozen; payload on a SYN is ignored (no Fast Open).  "
        "Checked against a live kernel by `packet-forge kernel-verify`.",
        ("syn-data",)),
}

DEFAULT_POLICIES = ("first", "last", "lowseq", "linux")
