"""Ethernet / IPv4 / IPv6 / TCP frame construction with RFC 1071 checksums."""
from __future__ import annotations

import ipaddress
import struct
from typing import Iterable, List, Optional, Sequence

FIN, SYN, RST, PSH, ACK, URG = 0x01, 0x02, 0x04, 0x08, 0x10, 0x20

ETH_MIN_NO_FCS = 60  # minimum Ethernet frame length on the wire, excluding the 4-byte FCS


def ones_sum(data: bytes) -> int:
    """Folded 16-bit ones-complement sum of ``data`` (odd length is zero padded)."""
    if len(data) & 1:
        data += b"\x00"
    if not data:
        return 0
    s = sum(struct.unpack("!%dH" % (len(data) // 2), data))
    while s >> 16:
        s = (s & 0xFFFF) + (s >> 16)
    return s


def checksum(data: bytes) -> int:
    return (~ones_sum(data)) & 0xFFFF


def pseudo_header(src: bytes, dst: bytes, length: int) -> bytes:
    if len(src) == 4:
        return src + dst + struct.pack("!BBH", 0, 6, length)
    return src + dst + struct.pack("!I3xB", length, 6)


def tcp_header(sport: int, dport: int, seq: int, ack: int, flags: int, window: int,
               options: bytes = b"", csum: int = 0, urg: int = 0) -> bytes:
    if len(options) % 4:
        raise ValueError("TCP options must be a multiple of 4 bytes")
    off = (20 + len(options)) // 4
    return struct.pack("!HHIIBBHHH", sport, dport, seq & 0xFFFFFFFF, ack & 0xFFFFFFFF,
                       off << 4, flags & 0xFF, window, csum, urg) + options


def tcp_segment(src_ip: str, dst_ip: str, sport: int, dport: int, seq: int, ack: int, flags: int,
                payload: bytes = b"", window: int = 65535, options: bytes = b"",
                bad_checksum: bool = False) -> bytes:
    """TCP header + payload with a valid (or deliberately wrong) checksum."""
    s = ipaddress.ip_address(src_ip).packed
    d = ipaddress.ip_address(dst_ip).packed
    hdr = tcp_header(sport, dport, seq, ack, flags, window, options)
    seg = hdr + payload
    c = checksum(pseudo_header(s, d, len(seg)) + seg)
    if bad_checksum:
        c ^= 0x5A5A  # can never alias the 0x0000 / 0xFFFF pair
    return hdr[:16] + struct.pack("!H", c) + hdr[18:] + payload


def ipv4_packet(src_ip: str, dst_ip: str, l4: bytes, proto: int = 6, ttl: int = 64, ident: int = 0,
                df: bool = True, mf: bool = False, frag_off8: int = 0,
                bad_checksum: bool = False) -> bytes:
    flags_frag = (0x4000 if df else 0) | (0x2000 if mf else 0) | (frag_off8 & 0x1FFF)
    total = 20 + len(l4)
    hdr = struct.pack("!BBHHHBBH4s4s", 0x45, 0, total, ident & 0xFFFF, flags_frag, ttl, proto, 0,
                      ipaddress.ip_address(src_ip).packed, ipaddress.ip_address(dst_ip).packed)
    c = checksum(hdr)
    if bad_checksum:
        c ^= 0x5A5A
    return hdr[:10] + struct.pack("!H", c) + hdr[12:] + l4


def ipv6_packet(src_ip: str, dst_ip: str, l4: bytes, next_header: int = 6, hop_limit: int = 64) -> bytes:
    hdr = struct.pack("!IHBB16s16s", 0x60000000, len(l4), next_header, hop_limit,
                      ipaddress.ip_address(src_ip).packed, ipaddress.ip_address(dst_ip).packed)
    return hdr + l4


def tcp_ip_packet(src_ip: str, dst_ip: str, sport: int, dport: int, seq: int, ack: int, flags: int,
                  payload: bytes = b"", window: int = 65535, options: bytes = b"", ttl: int = 64,
                  ident: int = 0, bad_tcp_checksum: bool = False, bad_ip_checksum: bool = False) -> bytes:
    """One IP packet (v4 or v6 by address family) carrying one TCP segment."""
    seg = tcp_segment(src_ip, dst_ip, sport, dport, seq, ack, flags, payload, window, options,
                      bad_tcp_checksum)
    if ipaddress.ip_address(src_ip).version == 6:
        return ipv6_packet(src_ip, dst_ip, seg, 6, ttl)
    return ipv4_packet(src_ip, dst_ip, seg, 6, ttl, ident, bad_checksum=bad_ip_checksum)


def fragment_ipv4(packet: bytes, first_payload_len: int) -> List[bytes]:
    """Split an IPv4 packet (no options) into two fragments; first fragment carries
    ``first_payload_len`` bytes of the IP payload (must be a multiple of 8)."""
    if first_payload_len % 8:
        raise ValueError("fragment boundary must be a multiple of 8")
    ihl = (packet[0] & 0xF) * 4
    hdr, payload = packet[:ihl], packet[ihl:]
    src = ipaddress.ip_address(packet[12:16]).compressed
    dst = ipaddress.ip_address(packet[16:20]).compressed
    ident = struct.unpack("!H", packet[4:6])[0]
    ttl, proto = packet[8], packet[9]
    f1 = ipv4_packet(src, dst, payload[:first_payload_len], proto, ttl, ident, df=False, mf=True, frag_off8=0)
    f2 = ipv4_packet(src, dst, payload[first_payload_len:], proto, ttl, ident, df=False, mf=False,
                     frag_off8=first_payload_len // 8)
    return [f1, f2]


def ethernet_frame(dst_mac: str, src_mac: str, l3: bytes, ipv6: bool = False,
                   vlans: Sequence[int] = (), pad: bool = True) -> bytes:
    def mac(s: str) -> bytes:
        return bytes(int(x, 16) for x in s.split(":"))
    out = mac(dst_mac) + mac(src_mac)
    for vid in vlans:
        out += struct.pack("!HH", 0x8100, vid & 0x0FFF)
    out += struct.pack("!H", 0x86DD if ipv6 else 0x0800) + l3
    if pad and len(out) < ETH_MIN_NO_FCS:
        out += b"\x00" * (ETH_MIN_NO_FCS - len(out))
    return out
