"""Traffic closure: every payload byte on the tapped link must be explained by a verified exchange.

Necessary, not sufficient: modulation *inside* explained bytes (timing, sizes) is a separate channel,
bounded here only by the capacity formula for a release-grid warden."""
from __future__ import annotations

import math
import socket
import struct
from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class Pkt:
    ts: float
    src: str
    dst: str
    sport: int
    dport: int
    proto: int
    payload_len: int


def flow_key(p: Pkt):
    return (p.proto, tuple(sorted([(p.src, p.sport), (p.dst, p.dport)])))


def _ip(b) -> str:
    return ".".join(str(x) for x in b)


@dataclass
class PcapStats:
    """What a capture contained that could not be attributed to a TCP/UDP flow. Completeness means these count."""
    total_packets: int = 0
    total_wire_bytes: int = 0
    unparsed_packets: dict = field(default_factory=dict)
    unparsed_wire_bytes: dict = field(default_factory=dict)

    def skip(self, reason: str, wire: int) -> None:
        self.unparsed_packets[reason] = self.unparsed_packets.get(reason, 0) + 1
        self.unparsed_wire_bytes[reason] = self.unparsed_wire_bytes.get(reason, 0) + int(wire)


def _parse(pkt: bytes, ts: float, with_payload: bool = False):
    """A Pkt, or the reason this frame cannot be attributed to a TCP/UDP flow (IPv4 or IPv6, one optional VLAN tag).
    With `with_payload`, a (Pkt, captured payload bytes) pair instead of a Pkt (the bytes stop at the snaplen)."""
    if len(pkt) < 14:
        return "short_frame"
    et, p = struct.unpack(">H", pkt[12:14])[0], 14
    if et == 0x8100:
        if len(pkt) < 18:
            return "short_frame"
        et, p = struct.unpack(">H", pkt[16:18])[0], 18
    if et == 0x0800:
        if len(pkt) < p + 20:
            return "short_ip"
        ihl = (pkt[p] & 0x0F) * 4
        total = struct.unpack(">H", pkt[p + 2:p + 4])[0]
        if struct.unpack(">H", pkt[p + 6:p + 8])[0] & 0x1FFF:
            return "ip_fragment"
        proto = pkt[p + 9]
        src_ip, dst_ip, l4, l4len = _ip(pkt[p + 12:p + 16]), _ip(pkt[p + 16:p + 20]), p + ihl, total - ihl
    elif et == 0x86DD:
        if len(pkt) < p + 40:
            return "short_ip"
        proto = pkt[p + 6]
        src_ip, dst_ip = socket.inet_ntop(socket.AF_INET6, pkt[p + 8:p + 24]), socket.inet_ntop(socket.AF_INET6, pkt[p + 24:p + 40])
        l4, l4len = p + 40, struct.unpack(">H", pkt[p + 4:p + 6])[0]
    else:
        return "non_ip"                                   # ARP, LLDP, QinQ, MPLS, ...
    if proto == 6:
        if len(pkt) < l4 + 20:
            return "truncated_l4"
        sport, dport = struct.unpack(">HH", pkt[l4:l4 + 4])
        start = l4 + (pkt[l4 + 12] >> 4) * 4
        pay = max(0, l4len - (pkt[l4 + 12] >> 4) * 4)
    elif proto == 17:
        if len(pkt) < l4 + 8:
            return "truncated_l4"
        sport, dport = struct.unpack(">HH", pkt[l4:l4 + 4])
        start = l4 + 8
        pay = max(0, l4len - 8)
    else:
        return "non_tcp_udp"                              # ICMP, SCTP, IPv6 extension headers, ...
    rec = Pkt(ts, src_ip, dst_ip, sport, dport, proto, pay)
    return (rec, bytes(pkt[start:start + pay])) if with_payload else rec


def iter_pcap(src, stats: "PcapStats | None" = None, with_payload: bool = False):
    """Yield Pkt records one at a time, in constant memory. Classic pcap, Ethernet only (tcpdump -w). Frames that cannot be
    attributed to a TCP/UDP flow are counted in `stats` by reason, never dropped silently. With `with_payload`, yield
    (Pkt, captured payload bytes) pairs; capture with a large snaplen (`tcpdump -s 0`) when payloads matter."""
    import io
    raw = isinstance(src, (bytes, bytearray))
    f = io.BytesIO(bytes(src)) if raw else open(src, "rb")
    st = stats if stats is not None else PcapStats()
    try:
        hdr = f.read(24)
        magic = hdr[:4]
        if magic == b"\x0a\x0d\x0d\x0a":
            raise ValueError("pcapng is not supported: capture with `tcpdump -w` or convert with `editcap -F pcap in.pcapng out.pcap`")
        if magic in (b"\xd4\xc3\xb2\xa1", b"\x4d\x3c\xb2\xa1"):
            end, nano = "<", magic == b"\x4d\x3c\xb2\xa1"
        elif magic in (b"\xa1\xb2\xc3\xd4", b"\xa1\xb2\x3c\x4d"):
            end, nano = ">", magic == b"\xa1\xb2\x3c\x4d"
        else:
            raise ValueError("not a classic pcap file")
        if struct.unpack(end + "I", hdr[20:24])[0] != 1:
            raise ValueError("only Ethernet (linktype 1) is supported")
        while True:
            rh = f.read(16)
            if len(rh) < 16:
                break
            sec, frac, incl, orig = struct.unpack(end + "IIII", rh)
            pkt = f.read(incl)
            st.total_packets += 1
            st.total_wire_bytes += orig
            if len(pkt) < incl:
                st.skip("truncated_file", orig)
                break
            got = _parse(pkt, sec + frac / (1e9 if nano else 1e6), with_payload)
            if isinstance(got, str):
                st.skip(got, orig)
            else:
                yield got
    finally:
        if not raw:
            f.close()


def read_pcap(src) -> list:
    return list(iter_pcap(src))


def write_pcap(path, pkts, payloads=None) -> None:
    """Minimal writer used for tests and fixtures: payloads are left out (snaplen-truncated) unless `payloads` gives the
    bytes of each packet, which must match its payload_len."""
    out = bytearray(struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1))
    for k, q in enumerate(pkts):
        l4 = (struct.pack(">HHIIBBHHH", q.sport, q.dport, 0, 0, 5 << 4, 0x18, 65535, 0, 0)
              if q.proto == 6 else struct.pack(">HHHH", q.sport, q.dport, 8 + q.payload_len, 0))
        total = 20 + len(l4) + q.payload_len
        ip = struct.pack(">BBHHHBBH4s4s", 0x45, 0, total, 0, 0, 64, q.proto, 0,
                         bytes(int(x) for x in q.src.split(".")), bytes(int(x) for x in q.dst.split(".")))
        body = b"" if payloads is None else bytes(payloads[k])
        if payloads is not None and len(body) != q.payload_len:
            raise ValueError(f"packet {k}: payload has {len(body)} bytes but payload_len is {q.payload_len}")
        frame = bytes(12) + b"\x08\x00" + ip + l4 + body   # without payloads the IP length is authoritative
        sec = int(q.ts)
        out += struct.pack("<IIII", sec, int(round((q.ts - sec) * 1e6)), len(frame), 14 + total)
        out += frame
    open(path, "wb").write(bytes(out))


def flow_bytes(pkts) -> dict:
    d = {}
    for p in pkts:
        if p.payload_len:
            d[flow_key(p)] = d.get(flow_key(p), 0) + p.payload_len
    return d


def traffic_closure(pkts, verified: dict, rel_tol: float = 0.02, abs_tol: int = 256, stats: "PcapStats | None" = None,
                    unparsed_tol_bytes: int = 0) -> dict:
    """verified: {flow_key: payload bytes committed by the verified request/response evidence}.

    `pkts` may be a list or a generator (one pass). Pass the `PcapStats` that `iter_pcap` filled: frames that could not be
    attributed to a TCP/UDP flow (ARP, ICMP, fragments, ...) are unexplained wire bytes, and the check fails unless
    `unparsed_tol_bytes` explicitly accepts them."""
    cap, t_min, t_max, n = {}, math.inf, -math.inf, 0
    for p in pkts:
        n += 1
        t_min, t_max = min(t_min, p.ts), max(t_max, p.ts)
        if p.payload_len:
            k = flow_key(p)
            cap[k] = cap.get(k, 0) + p.payload_len
    unexplained, unknown, missing = 0, [], 0
    for k, c in cap.items():
        v = verified.get(k)
        if v is None:
            unknown.append(k)
            unexplained += c
        else:
            tol = rel_tol * v + abs_tol
            unexplained += max(0.0, c - v - tol)
            missing += max(0.0, v - c - tol)
    dur = (t_max - t_min) if n > 1 else 0.0
    un_b = sum(stats.unparsed_wire_bytes.values()) if stats else 0
    return {"captured_bytes": int(sum(cap.values())), "verified_bytes": int(sum(verified.values())),
            "unexplained_bytes": int(unexplained), "missing_bytes": int(missing),
            "unknown_flows": [list(map(str, k)) for k in unknown], "duration_s": dur,
            "unexplained_bps": (8 * unexplained / dur if dur > 0 else None),
            "unparsed_packets": int(sum(stats.unparsed_packets.values())) if stats else 0, "unparsed_wire_bytes": int(un_b),
            "unparsed_by_reason": (dict(stats.unparsed_wire_bytes) if stats else {}),
            "pass": unexplained == 0 and missing == 0 and un_b <= unparsed_tol_bytes}


def timing_grid_conformance(ts, grid_s: float, tol_s: float, t0: float = 0.0) -> dict:
    """Fraction of release times within tol of the warden's release grid."""
    ph = (np.asarray(ts, float) - t0) % grid_s
    dist = np.minimum(ph, grid_s - ph)
    return {"conforming_fraction": float(np.mean(dist <= tol_s)), "n": int(len(ph)),
            "median_offset_s": float(np.median(dist))}


def covert_capacity_bound_bps(rate_pps: float, max_added_delay_s: float, grid_s: float) -> float:
    """If every release lies on a grid and delay is capped, a sender chooses among floor(D/g)+1 slots:
    bits/packet <= log2(1 + floor(D/g)). Holds only while grid conformance is verified."""
    return rate_pps * math.log2(1 + math.floor(max_added_delay_s / grid_s))
