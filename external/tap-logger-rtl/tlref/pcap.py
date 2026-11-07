"""Minimal classic-pcap reader/writer (frames and nanosecond timestamps)."""
from __future__ import annotations

import struct
from typing import Iterable, List, Tuple

_MAGIC = {b"\xd4\xc3\xb2\xa1": ("<", 1000), b"\xa1\xb2\xc3\xd4": (">", 1000),
          b"\x4d\x3c\xb2\xa1": ("<", 1), b"\xa1\xb2\x3c\x4d": (">", 1)}


def read_pcap(path: str) -> List[Tuple[int, bytes]]:
    """Returns ``[(timestamp_ns, frame_bytes)]``."""
    with open(path, "rb") as f:
        head = f.read(24)
        if len(head) < 24 or head[:4] not in _MAGIC:
            raise ValueError("not a classic pcap file")
        endian, mult = _MAGIC[head[:4]]
        out = []
        while True:
            rh = f.read(16)
            if not rh:
                return out
            if len(rh) < 16:
                raise ValueError("truncated record header")
            sec, frac, incl, _orig = struct.unpack(endian + "IIII", rh)
            data = f.read(incl)
            if len(data) < incl:
                raise ValueError("truncated record")
            out.append((sec * 1_000_000_000 + frac * mult, data))


def write_pcap(path: str, records: Iterable[Tuple[int, bytes]], linktype: int = 1) -> None:
    with open(path, "wb") as f:
        f.write(struct.pack("<IHHiIII", 0xA1B23C4D, 2, 4, 0, 0, 262144, linktype))
        for ts_ns, data in records:
            f.write(struct.pack("<IIII", ts_ns // 1_000_000_000, ts_ns % 1_000_000_000, len(data), len(data)))
            f.write(data)
