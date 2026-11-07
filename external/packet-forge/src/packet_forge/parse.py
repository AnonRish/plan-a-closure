"""Frame parsing: Ethernet (+VLAN), raw IP, IPv4, IPv6 -> TCP segments, with checksum validation."""
from __future__ import annotations

import ipaddress
import struct
from dataclasses import dataclass
from typing import Optional, Tuple

from .frames import ones_sum, pseudo_header
from .pcap import LINKTYPE_ETHERNET, LINKTYPE_RAW


@dataclass
class TcpSeg:
    frame_no: int            # 1-based index in the capture
    ts_ns: int
    src: str
    dst: str
    sport: int
    dport: int
    seq: int
    ack: int
    flags: int
    window: int
    payload: bytes
    payload_off: int         # byte offset of the payload inside the captured frame
    l3_off: int              # byte offset of the IP header inside the captured frame
    ip_csum_ok: Optional[bool]   # None: not applicable (IPv6) or unverifiable
    tcp_csum_ok: Optional[bool]  # None: unverifiable (truncated capture)
    ipv6: bool
    ttl: int
    truncated: bool
    declared_len: int = 0    # payload length announced by the IP header (may exceed len(payload) if truncated)
    tcp_off: int = 0         # offset of the TCP header inside the captured frame
    tcp_len: int = 0         # TCP header + payload length announced by the IP header

    @property
    def syn(self) -> bool:
        return bool(self.flags & 0x02)

    @property
    def fin(self) -> bool:
        return bool(self.flags & 0x01)

    @property
    def rst(self) -> bool:
        return bool(self.flags & 0x04)

    @property
    def has_ack(self) -> bool:
        return bool(self.flags & 0x10)

    @property
    def flow_key(self) -> Tuple[str, int, str, int]:
        return (self.src, self.sport, self.dst, self.dport)


@dataclass
class FrameNote:
    frame_no: int
    kind: str      # ip-fragment | not-ip | not-tcp | malformed | ipv6-ext-unsupported
    detail: str = ""


_VLAN = (0x8100, 0x88A8, 0x9100)


def parse_frame(frame_no: int, ts_ns: int, data: bytes, linktype: int):
    """Returns ``(TcpSeg | None, FrameNote | None)``."""
    off = 0
    ethertype = None
    if linktype == LINKTYPE_ETHERNET:
        if len(data) < 14:
            return None, FrameNote(frame_no, "malformed", "short ethernet frame")
        ethertype = struct.unpack("!H", data[12:14])[0]
        off = 14
        tags = 0
        while ethertype in _VLAN:
            if len(data) < off + 4 or tags >= 4:
                return None, FrameNote(frame_no, "malformed", "bad vlan stack")
            ethertype = struct.unpack("!H", data[off + 2:off + 4])[0]
            off += 4
            tags += 1
    elif linktype == LINKTYPE_RAW:
        if not data:
            return None, FrameNote(frame_no, "malformed", "empty raw packet")
        ethertype = 0x0800 if (data[0] >> 4) == 4 else 0x86DD if (data[0] >> 4) == 6 else None
    else:
        return None, FrameNote(frame_no, "not-ip", "unsupported linktype %d" % linktype)

    if ethertype == 0x0800:
        return _parse_v4(frame_no, ts_ns, data, off)
    if ethertype == 0x86DD:
        return _parse_v6(frame_no, ts_ns, data, off)
    return None, FrameNote(frame_no, "not-ip", "ethertype %s" % (hex(ethertype) if ethertype is not None else "?"))


def _tcp_from(frame_no, ts_ns, data, l3_off, tcp_off, tcp_len_decl, src, dst, ipv6, ip_ok, ttl):
    captured = data[tcp_off:tcp_off + tcp_len_decl]
    truncated = len(captured) < tcp_len_decl
    if len(captured) < 20:
        return None, FrameNote(frame_no, "malformed", "short tcp header")
    sport, dport, seq, ack, offres, flags, window, csum, _urg = struct.unpack("!HHIIBBHHH", captured[:20])
    doff = (offres >> 4) * 4
    if doff < 20 or doff > tcp_len_decl:
        return None, FrameNote(frame_no, "malformed", "bad tcp data offset %d" % doff)
    if doff > len(captured):
        return None, FrameNote(frame_no, "malformed", "tcp header truncated by snaplen")
    payload = captured[doff:]
    if truncated:
        tcp_ok = None
    else:
        s = ipaddress.ip_address(src).packed
        d = ipaddress.ip_address(dst).packed
        tcp_ok = ones_sum(pseudo_header(s, d, tcp_len_decl) + captured) == 0xFFFF
    seg = TcpSeg(frame_no, ts_ns, src, dst, sport, dport, seq, ack, flags & 0x3F, window, payload,
                 tcp_off + doff, l3_off, ip_ok, tcp_ok, ipv6, ttl, truncated, tcp_len_decl - doff, tcp_off, tcp_len_decl)
    return seg, None


def _parse_v4(frame_no, ts_ns, data, off):
    if len(data) < off + 20:
        return None, FrameNote(frame_no, "malformed", "short ipv4 header")
    vihl = data[off]
    ihl = (vihl & 0xF) * 4
    if vihl >> 4 != 4 or ihl < 20 or len(data) < off + ihl:
        return None, FrameNote(frame_no, "malformed", "bad ipv4 header")
    total = struct.unpack("!H", data[off + 2:off + 4])[0]
    if total < ihl:
        return None, FrameNote(frame_no, "malformed", "ipv4 total length < header length")
    flags_frag = struct.unpack("!H", data[off + 6:off + 8])[0]
    if flags_frag & 0x3FFF:   # MF set or non-zero fragment offset
        return None, FrameNote(frame_no, "ip-fragment", "ipv4 fragment not reassembled")
    if data[off + 9] != 6:
        return None, FrameNote(frame_no, "not-tcp", "ip protocol %d" % data[off + 9])
    ip_ok = ones_sum(data[off:off + ihl]) == 0xFFFF
    src = str(ipaddress.IPv4Address(data[off + 12:off + 16]))
    dst = str(ipaddress.IPv4Address(data[off + 16:off + 20]))
    return _tcp_from(frame_no, ts_ns, data, off, off + ihl, total - ihl, src, dst, False, ip_ok, data[off + 8])


def _parse_v6(frame_no, ts_ns, data, off):
    if len(data) < off + 40:
        return None, FrameNote(frame_no, "malformed", "short ipv6 header")
    if data[off] >> 4 != 6:
        return None, FrameNote(frame_no, "malformed", "bad ipv6 version")
    plen = struct.unpack("!H", data[off + 4:off + 6])[0]
    nh = data[off + 6]
    hop = data[off + 7]
    src = str(ipaddress.IPv6Address(data[off + 8:off + 24]))
    dst = str(ipaddress.IPv6Address(data[off + 24:off + 40]))
    p = off + 40
    remaining = plen
    if plen == 0:
        return None, FrameNote(frame_no, "malformed", "ipv6 payload length 0 (jumbogram?)")
    while nh in (0, 43, 60):
        if len(data) < p + 8:
            return None, FrameNote(frame_no, "malformed", "short ipv6 extension header")
        elen = (data[p + 1] + 1) * 8
        nh = data[p]
        p += elen
        remaining -= elen
    if nh == 44:
        return None, FrameNote(frame_no, "ip-fragment", "ipv6 fragment header not reassembled")
    if nh != 6:
        kind = "not-tcp" if nh in (1, 17, 58) else "ipv6-ext-unsupported"
        return None, FrameNote(frame_no, kind, "ipv6 next header %d" % nh)
    if remaining < 20:
        return None, FrameNote(frame_no, "malformed", "ipv6 payload shorter than tcp header")
    return _tcp_from(frame_no, ts_ns, data, off, p, remaining, src, dst, True, None, hop)
