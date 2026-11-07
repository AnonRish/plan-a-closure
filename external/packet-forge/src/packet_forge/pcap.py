"""Classic libpcap reader/writer (microsecond and nanosecond variants, both byte orders)."""
from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import BinaryIO, Iterable, Iterator, Tuple

LINKTYPE_ETHERNET = 1
LINKTYPE_RAW = 101

_MAGICS = {
    b"\xd4\xc3\xb2\xa1": ("<", False),
    b"\xa1\xb2\xc3\xd4": (">", False),
    b"\x4d\x3c\xb2\xa1": ("<", True),
    b"\xa1\xb2\x3c\x4d": (">", True),
}


class PcapError(ValueError):
    pass


@dataclass
class PcapRecord:
    ts_ns: int          # nanoseconds since the epoch
    data: bytes         # captured bytes
    orig_len: int       # length on the wire


@dataclass
class PcapHeader:
    linktype: int
    snaplen: int
    nano: bool
    endian: str


def write_pcap(path: str, records: Iterable[Tuple[int, bytes]], linktype: int = LINKTYPE_ETHERNET,
               snaplen: int = 262144, nano: bool = False) -> None:
    """Write ``(ts_ns, frame_bytes)`` records as a little-endian classic pcap."""
    magic = 0xA1B23C4D if nano else 0xA1B2C3D4
    with open(path, "wb") as f:
        f.write(struct.pack("<IHHiIII", magic, 2, 4, 0, 0, snaplen, linktype))
        for ts_ns, data in records:
            sec, frac = divmod(ts_ns, 1_000_000_000)
            if not nano:
                frac //= 1000
            f.write(struct.pack("<IIII", sec, frac, len(data), len(data)))
            f.write(data)


def read_pcap_stream(f: BinaryIO) -> Tuple[PcapHeader, Iterator[PcapRecord]]:
    head = f.read(24)
    if len(head) < 24:
        raise PcapError("file too short for a pcap header")
    if head[:4] == b"\x0a\x0d\x0d\x0a":
        raise PcapError("pcapng is not supported; convert with `editcap -F pcap`")
    if head[:4] not in _MAGICS:
        raise PcapError("not a classic pcap file (bad magic %r)" % head[:4].hex())
    endian, nano = _MAGICS[head[:4]]
    _vmaj, _vmin, _tz, _sig, snaplen, linktype = struct.unpack(endian + "HHiIII", head[4:])
    hdr = PcapHeader(linktype=linktype, snaplen=snaplen, nano=nano, endian=endian)

    def it() -> Iterator[PcapRecord]:
        while True:
            rh = f.read(16)
            if not rh:
                return
            if len(rh) < 16:
                raise PcapError("truncated record header")
            sec, frac, incl, orig = struct.unpack(endian + "IIII", rh)
            if incl > 0x4000000:
                raise PcapError("implausible capture length %d" % incl)
            data = f.read(incl)
            if len(data) < incl:
                raise PcapError("truncated record body")
            yield PcapRecord(ts_ns=sec * 1_000_000_000 + (frac if nano else frac * 1000),
                             data=data, orig_len=orig)

    return hdr, it()


def read_pcap(path: str) -> Tuple[PcapHeader, list]:
    with open(path, "rb") as f:
        hdr, it = read_pcap_stream(f)
        return hdr, list(it)
