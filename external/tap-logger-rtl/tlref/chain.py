"""Software reference for the log format (docs/FORMAT.md) and the verifier a log consumer would run."""
from __future__ import annotations

import hashlib
import struct
from dataclasses import dataclass
from typing import List, Optional, Sequence

GENESIS_ZERO = bytes(32)


@dataclass(frozen=True)
class Record:
    index: int
    length: int
    ts: int
    digest: bytes


def entry_digest(prev: bytes, index: int, frame: bytes, ts: Optional[int]) -> bytes:
    """D(i) = SHA-256(D(i-1) || be64(i) || [be64(ts)] || frame). ``ts=None`` selects the format without timestamps."""
    if len(prev) != 32:
        raise ValueError("chain digests are 32 bytes")
    h = hashlib.sha256()
    h.update(prev)
    h.update(struct.pack(">Q", index))
    if ts is not None:
        h.update(struct.pack(">Q", ts))
    h.update(frame)
    return h.digest()


def build_chain(frames: Sequence[bytes], timestamps: Optional[Sequence[int]] = None,
                genesis: bytes = GENESIS_ZERO, start_index: int = 0) -> List[Record]:
    out: List[Record] = []
    prev = genesis
    for k, fr in enumerate(frames):
        if not fr:
            raise ValueError("frames must be at least one byte (a stream beat always carries a byte)")
        ts = None if timestamps is None else timestamps[k]
        prev = entry_digest(prev, start_index + k, fr, ts)
        out.append(Record(start_index + k, len(fr), 0 if ts is None else ts, prev))
    return out


@dataclass
class Verdict:
    ok: bool
    first_bad: Optional[int] = None      # position in the supplied sequences of the first inconsistent record
    reason: str = ""


def verify_chain(frames: Sequence[bytes], records: Sequence[Record], ts_in_hash: bool,
                 genesis: bytes = GENESIS_ZERO, start_index: int = 0,
                 expected_head: Optional[bytes] = None) -> Verdict:
    """Recompute the chain from the raw frames and compare with the logged records.

    Detects altered, reordered, inserted or dropped frames at the first affected record.  Truncation of the tail
    cannot be seen from the log alone: pass ``expected_head`` (a digest published or signed out of band)."""
    if len(frames) != len(records):
        n = min(len(frames), len(records))
        bad = verify_chain(frames[:n], records[:n], ts_in_hash, genesis, start_index)
        if not bad.ok:
            return bad
        return Verdict(False, n, "%d frames but %d records" % (len(frames), len(records)))
    prev = genesis
    for k, (fr, rec) in enumerate(zip(frames, records)):
        if rec.index != start_index + k:
            return Verdict(False, k, "record index %d, expected %d" % (rec.index, start_index + k))
        if rec.length != len(fr):
            return Verdict(False, k, "record length %d, frame has %d bytes" % (rec.length, len(fr)))
        want = entry_digest(prev, rec.index, fr, rec.ts if ts_in_hash else None)
        if rec.digest != want:
            return Verdict(False, k, "digest mismatch")
        prev = rec.digest
    if expected_head is not None and prev != expected_head:
        return Verdict(False, len(records), "chain head differs from the published head")
    return Verdict(True)
