"""Normalise a capture so that overlapping segments are mutually consistent.

Every captured data segment is rewritten to carry the canonical bytes (under the chosen policy) for its
sequence range, and segments an endpoint would discard (bad checksum) are removed.  Afterwards no two
segments disagree on any byte, so every policy reassembles the same stream: the capture no longer
depends on which reassembly rules a downstream consumer happens to implement.  Conflicts are *not*
repaired silently: run `packet-forge check` on the input to see what was rewritten.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from . import frames as fr
from .analyze import build_directions, parse_capture
from .assembler import StreamAssembler
from .model import POLICIES
from .parse import TcpSeg
from .pcap import read_pcap_stream, write_pcap


@dataclass
class NormalizeStats:
    frames_in: int = 0
    frames_out: int = 0
    rewritten: int = 0          # frames whose payload bytes changed
    dropped_bad_checksum: int = 0


def _refresh_tcp_checksum(frame: bytearray, seg: TcpSeg) -> None:
    import ipaddress
    tcp = bytes(frame[seg.tcp_off:seg.tcp_off + seg.tcp_len])
    tcp = tcp[:16] + b"\x00\x00" + tcp[18:]
    s = ipaddress.ip_address(seg.src).packed
    d = ipaddress.ip_address(seg.dst).packed
    c = fr.checksum(fr.pseudo_header(s, d, seg.tcp_len) + tcp)
    frame[seg.tcp_off + 16:seg.tcp_off + 18] = struct.pack("!H", c)


def normalize_pcap(src: str, dst: str, policy: str = "first", checksum: str = "verify") -> NormalizeStats:
    pol = POLICIES[policy]
    if pol.drop_flags:
        raise ValueError("policy %r ignores some segments entirely and cannot be used to normalise; "
                         "choose first, last or lowseq" % policy)
    with open(src, "rb") as f:
        hdr, it = read_pcap_stream(f)
        records = list(it)
    segs, notes, _ = parse_capture(src)
    dirs = build_directions(segs, checksum)
    asm: Dict[tuple, StreamAssembler] = {}
    for key, d in dirs.items():
        a = StreamAssembler(pol, 0)
        for c in d.claims:
            a.add(c)
        asm[key] = a
    by_frame: Dict[int, TcpSeg] = {s.frame_no: s for s in segs}
    bad_frames = {s.frame_no for d in dirs.values() for s in d.bad}
    stats = NormalizeStats(frames_in=len(records))
    out: List[Tuple[int, bytes]] = []
    for n, rec in enumerate(records, 1):
        if n in bad_frames:
            stats.dropped_bad_checksum += 1
            continue
        seg = by_frame.get(n)
        data = rec.data
        if seg is not None and seg.payload and not seg.truncated:
            d = dirs[seg.flow_key]
            claim = d.frame_claim.get(n)
            if claim is not None:
                canonical = asm[seg.flow_key].read(claim.start, claim.end)
                cut = len(seg.payload) - len(claim.data)
                new_payload = seg.payload[:cut] + canonical
                if new_payload != seg.payload:
                    buf = bytearray(data)
                    buf[seg.payload_off:seg.payload_off + len(new_payload)] = new_payload
                    _refresh_tcp_checksum(buf, seg)
                    data = bytes(buf)
                    stats.rewritten += 1
        out.append((rec.ts_ns, data))
    write_pcap(dst, out, hdr.linktype, hdr.snaplen, hdr.nano)
    stats.frames_out = len(out)
    return stats
