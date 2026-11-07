"""Brute-force per-byte reference model.

Deliberately naive and structurally unrelated to :mod:`packet_forge.assembler`: it walks every byte of
every claim, keeps a dict of incumbents, and records every byte value ever claimed for each offset.
The production assembler works on intervals; tests compare the two on thousands of random scenarios.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Set, Tuple

from .model import Claim, Policy


@dataclass
class OracleResult:
    runs: List[Tuple[int, bytes]]            # canonical content as maximal contiguous runs
    conflict_ranges: List[Tuple[int, int]]   # maximal ranges of offsets with >= 2 distinct claimed values
    delivered: int                           # end of the contiguous canonical prefix


def _ranges(offsets: Iterable[int]) -> List[Tuple[int, int]]:
    out: List[Tuple[int, int]] = []
    for x in sorted(offsets):
        if out and out[-1][1] == x:
            out[-1] = (out[-1][0], x + 1)
        else:
            out.append((x, x + 1))
    return out


def oracle(claims: Iterable[Claim], policy: Policy, stream_start: int = 0) -> OracleResult:
    incumbent: Dict[int, Claim] = {}
    values: Dict[int, Set[int]] = {}
    delivered = stream_start
    for c in claims:
        if policy.drop_flags and set(c.flags) & set(policy.drop_flags):
            continue
        frozen_below = delivered          # snapshot taken before this claim is applied
        for i, byte in enumerate(c.data):
            x = c.start + i
            values.setdefault(x, set()).add(byte)
            cur = incumbent.get(x)
            if cur is None:
                incumbent[x] = c
            elif policy.freeze and x < frozen_below:
                continue
            elif policy.key(c) < policy.key(cur):
                incumbent[x] = c
        while delivered in incumbent:
            delivered += 1
    runs: List[Tuple[int, bytes]] = []
    for a, b in _ranges(incumbent.keys()):
        runs.append((a, bytes(incumbent[x].data[x - incumbent[x].start] for x in range(a, b))))
    return OracleResult(runs, _ranges(x for x, v in values.items() if len(v) > 1), delivered)
