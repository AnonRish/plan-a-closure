"""The adversarial overlap corpus.

Every case is an *abstract* TCP conversation: a client opens a connection to a server and sends data
segments in a chosen arrival order.  Offsets are stream offsets (0 = first byte after the SYN).  The
expected outcome is computed by :mod:`packet_forge.oracle` straight from the abstract events, never
from the generated pcap, so the pcap -> parser -> reassembler pipeline can be checked against it.
"""
from __future__ import annotations

import hashlib
import itertools
import json
import os
from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional, Sequence, Tuple, Union

from . import frames as fr
from .analyze import FAIL_KINDS
from .model import DEFAULT_POLICIES, POLICIES, Claim
from .oracle import oracle
from .pcap import LINKTYPE_ETHERNET, LINKTYPE_RAW, write_pcap

STREAM = b"0123456789abcdefghijklmnopqrstuvwxyz" * 4


@dataclass(frozen=True)
class Seg:
    off: int
    data: bytes = b""
    fin: bool = False          # FIN flag set on this segment
    syn: bool = False          # payload carried on the SYN itself (off must be 0)
    bad_csum: bool = False     # wrong TCP checksum: every conforming endpoint discards it
    frag: bool = False         # sent as two IPv4 fragments


@dataclass(frozen=True)
class Ack:
    off: int                   # the server acknowledges stream offsets below `off`


Event = Union[Seg, Ack]


@dataclass(frozen=True)
class Case:
    id: str
    title: str
    category: str              # benign | overlap | insertion | anomaly
    description: str
    isn: int
    events: Tuple[Event, ...]
    handshake: bool = True
    expect_anomalies: Tuple[str, ...] = ()

    def segs(self) -> List[Seg]:
        return [e for e in self.events if isinstance(e, Seg)]


def S(off: int, data: bytes, **kw) -> Seg:
    return Seg(off, data, **kw)


def _geometry_cases() -> List[Case]:
    geoms = [
        ("tail", (15, 25), "Q starts inside P and runs past its end"),
        ("head", (5, 15), "Q starts before P and ends inside it"),
        ("contained", (12, 17), "Q lies strictly inside P"),
        ("covering", (5, 25), "Q strictly contains P"),
        ("same-start-longer", (10, 25), "Q starts where P starts and is longer"),
        ("same-start-shorter", (10, 15), "Q starts where P starts and is shorter"),
        ("same-end-longer", (5, 20), "Q ends where P ends and starts earlier"),
        ("same-end-shorter", (15, 20), "Q ends where P ends and starts later"),
        ("same-range", (10, 20), "Q covers exactly P's range"),
        ("one-byte-tail", (19, 29), "Q overlaps P by its last byte only"),
        ("one-byte-head", (1, 11), "Q overlaps P by its first byte only"),
    ]
    P = (10, 20)
    out: List[Case] = []
    for gi, (name, (qs, qe), what) in enumerate(geoms):
        p = S(P[0], b"P" * (P[1] - P[0]))
        q = S(qs, b"Q" * (qe - qs))
        # inorder: the prefix and P are delivered (and ACKed) before Q arrives
        out.append(Case(
            "ov-%s-inorder" % name, "Overlap, %s, after P is delivered" % name, "overlap",
            "%s. The bytes before P and P itself reach the endpoint in order and are ACKed before Q "
            "arrives, so Q tries to rewrite data the application may already have." % what,
            0x10000000 + gi, (S(0, STREAM[:10]), p, Ack(20), q)))
        lo = min(P[0], qs)
        prefix = S(0, STREAM[:lo])
        out.append(Case(
            "ov-%s-ooo-pq" % name, "Overlap, %s, buffered beyond a hole (P first)" % name, "overlap",
            "%s. P then Q arrive while the stream prefix is still missing; the prefix arrives last." % what,
            0x20000000 + gi, (p, q, prefix)))
        out.append(Case(
            "ov-%s-ooo-qp" % name, "Overlap, %s, buffered beyond a hole (Q first)" % name, "overlap",
            "%s. Same as the P-first case with the arrival order of P and Q swapped." % what,
            0x30000000 + gi, (q, p, prefix)))
    return out


def _special_cases() -> List[Case]:
    c: List[Case] = []
    A, B, C = b"A" * 10, b"B" * 10, b"C" * 10
    # ---- benign controls: overlap or reorder that carries identical bytes -------------------------
    c.append(Case("ok-in-order", "Three contiguous segments", "benign",
                  "Plain in-order delivery. No overlap, no ambiguity.", 0x01000001,
                  (S(0, STREAM[0:10]), S(10, STREAM[10:20]), S(20, STREAM[20:30]))))
    c.append(Case("ok-reordered", "Three segments, reordered", "benign",
                  "Segments arrive 3, 1, 2. Reordering alone is not ambiguity.", 0x01000002,
                  (S(20, STREAM[20:30]), S(0, STREAM[0:10]), S(10, STREAM[10:20]))))
    c.append(Case("ok-duplicate-retransmit", "Exact retransmission", "benign",
                  "A segment is retransmitted byte for byte.", 0x01000003,
                  (S(0, STREAM[0:10]), S(10, STREAM[10:20]), S(10, STREAM[10:20]), S(20, STREAM[20:30]))))
    c.append(Case("ok-resegmented-retransmit", "Retransmission with different segmentation", "benign",
                  "Lost data is resent as larger, differently aligned segments (identical bytes). Honest TCP "
                  "stacks do this routinely; a tap must not call it an attack.", 0x01000004,
                  (S(0, STREAM[0:10]), S(10, STREAM[10:20]), S(20, STREAM[20:30]),
                   S(5, STREAM[5:25]), S(0, STREAM[0:30]), S(15, STREAM[15:35]))))
    c.append(Case("ok-hole-then-fill", "Hole filled later", "benign",
                  "Data beyond a hole is buffered until the missing segment arrives.", 0x01000005,
                  (S(0, STREAM[0:10]), S(20, STREAM[20:30]), S(10, STREAM[10:20]))))
    c.append(Case("ok-tiny-segments", "One-byte segments", "benign",
                  "Single-byte segments: every frame is padded to the Ethernet minimum, so a parser that "
                  "trusts the frame length instead of the IP length would append zero bytes.", 0x01000006,
                  tuple(S(i, STREAM[i:i + 1]) for i in range(8))))
    c.append(Case("ok-wrap-in-order", "Sequence wrap, in order", "benign",
                  "The 32-bit sequence number wraps in the middle of the stream.", 0xFFFFFFF5,
                  (S(0, STREAM[0:12]), S(12, STREAM[12:24]), S(24, STREAM[24:36]))))
    c.append(Case("ok-wrap-out-of-order", "Sequence wrap, out of order", "benign",
                  "A segment that lies just past the 32-bit wrap arrives before the bytes that precede it. "
                  "A naive `seq < next_expected` test mistakes it for an old duplicate and drops it.", 0xFFFFFFF5,
                  (S(10, b"WORLD"), S(0, b"0123456789"))))
    # ---- overlaps that are not pure two-segment geometry -------------------------------------------
    c.append(Case("ov-conflicting-retransmit", "Same range, different bytes", "overlap",
                  "The same sequence range is sent twice with different bytes: the tap and the endpoint can "
                  "keep different copies.", 0x02000001, (S(0, b"AAAA"), S(0, b"BBBB"))))
    c.append(Case("ov-aba-inorder", "A, B, A on the same range (delivered)", "overlap",
                  "First and last copies agree but a middle copy differs: 'first' and 'last' reassemble the "
                  "same stream although the flow is ambiguous.", 0x02000002,
                  (S(0, STREAM[:10]), S(10, A), Ack(20), S(10, B), S(10, A))))
    c.append(Case("ov-aba-ooo", "A, B, A on the same range (buffered)", "overlap",
                  "As above, with the range buffered beyond a hole.", 0x02000003,
                  (S(10, A), S(10, B), S(10, A), S(0, STREAM[:10]))))
    c.append(Case("ov-chain-three-ooo", "Chain of three overlapping segments", "overlap",
                  "A overlaps B, B overlaps C, all with different bytes, buffered beyond a hole.", 0x02000004,
                  (S(10, A), S(15, B), S(20, C), S(0, STREAM[:10]))))
    c.append(Case("ov-one-covers-three-ooo", "One large segment over three small ones", "overlap",
                  "A large segment arrives after three small segments it contradicts.", 0x02000005,
                  (S(10, b"s" * 4), S(14, b"t" * 4), S(18, b"u" * 4), S(8, b"G" * 16), S(0, STREAM[:8]))))
    c.append(Case("ov-big-first-ooo", "Large segment, then small contradictions", "overlap",
                  "A large segment arrives first and three smaller segments contradict parts of it.", 0x02000006,
                  (S(8, b"G" * 16), S(10, b"s" * 4), S(14, b"t" * 4), S(18, b"u" * 4), S(0, STREAM[:8]))))
    c.append(Case("ov-wrap-conflict-inorder", "Conflict spanning the sequence wrap (delivered)", "overlap",
                  "A conflicting segment straddles the 2**32 boundary after the original data was delivered.",
                  0xFFFFFFF5, (S(0, STREAM[:10]), S(10, b"P" * 10), Ack(20), S(8, b"Q" * 8))))
    c.append(Case("ov-wrap-conflict-ooo", "Conflict spanning the sequence wrap (buffered)", "overlap",
                  "As above, with both copies buffered beyond a hole.", 0xFFFFFFF5,
                  (S(10, b"P" * 10), S(8, b"Q" * 8), S(0, STREAM[:8]))))
    c.append(Case("ov-before-ack", "Conflicting retransmission before the ACK", "overlap",
                  "The conflicting copy arrives before the server has acknowledged the range.", 0x02000009,
                  (S(0, STREAM[:10]), S(10, b"P" * 10), S(10, b"Q" * 10), Ack(20))))
    c.append(Case("ov-keepalive-garbage-byte", "Keep-alive probe with a garbage octet", "overlap",
                  "RFC 1122 lets a keep-alive probe carry one garbage octet at the last sequence number already "
                  "acknowledged. It contradicts real data, so it is flagged, but it is the one benign-looking "
                  "source of a conflict the corpus knows about.", 0x0200000A,
                  (S(0, STREAM[:10]), Ack(10), S(9, b"\x00"))))
    # ---- insertion tricks the overlap detector must not be fooled by -------------------------------
    c.append(Case("ins-bad-checksum-decoy", "Decoy with a bad TCP checksum", "insertion",
                  "A decoy segment with a wrong checksum precedes the real one. Endpoints discard it; a tap that "
                  "does not verify checksums reassembles the decoy bytes.", 0x03000001,
                  (S(10, b"D" * 10, bad_csum=True), S(10, b"R" * 10), S(0, STREAM[:10])),
                  expect_anomalies=("bad-checksum",)))
    c.append(Case("ins-bad-checksum-fills-hole", "Decoy with a bad checksum fills a hole", "insertion",
                  "A segment with a wrong checksum covers a range no valid segment ever carries. The endpoint "
                  "never receives it and stalls at the hole; a checksum-blind tap splices the decoy into the "
                  "stream and, because nothing overlaps, sees no conflict at all.", 0x03000002,
                  (S(0, STREAM[:10]), S(10, b"D" * 10, bad_csum=True), S(20, STREAM[20:30])),
                  expect_anomalies=("bad-checksum",)))
    # ---- protocol anomalies ----------------------------------------------------------------------------
    c.append(Case("anom-syn-data", "Payload on the SYN", "anomaly",
                  "The SYN carries bytes that a later segment contradicts. Linux without TCP Fast Open ignores "
                  "SYN payload; a tap that counts it disagrees with the endpoint.", 0x04000001,
                  (S(0, b"SYNDATA!!!", syn=True), S(0, b"REALDATA!!")), expect_anomalies=("syn-data",)))
    c.append(Case("anom-data-after-fin", "Payload beyond the FIN", "anomaly",
                  "Bytes are sent past the stream's FIN. The application sees EOF at the FIN.", 0x04000002,
                  (S(0, STREAM[:10]), S(10, b"", fin=True), S(10, b"LATE!")),
                  expect_anomalies=("data-after-fin",)))
    c.append(Case("anom-conflicting-fin", "Two FINs at different offsets", "anomaly",
                  "The stream is closed at two different offsets.", 0x04000003,
                  (S(0, STREAM[:10]), S(10, b"", fin=True), S(10, b"xx", fin=True)),
                  expect_anomalies=("conflicting-fin", "data-after-fin")))
    c.append(Case("anom-ip-fragment", "Segment split into IPv4 fragments", "anomaly",
                  "One segment travels as two IP fragments. Endpoints reassemble them; a tap that does not "
                  "reassemble IP fragments never sees the bytes.", 0x04000004,
                  (S(0, STREAM[:10]), S(10, STREAM[10:30], frag=True), S(30, STREAM[30:40])),
                  expect_anomalies=("ip-fragment",)))
    c.append(Case("anom-midstream", "Capture without the handshake", "anomaly",
                  "The tap joined mid-connection: the stream start has to be inferred.", 0x05000001,
                  (S(0, STREAM[:10]), S(10, STREAM[10:20])), handshake=False, expect_anomalies=("midstream",)))
    c.append(Case("anom-before-isn", "Segment starting before the stream", "anomaly",
                  "A segment begins three bytes before the first data byte; the endpoint trims those bytes.",
                  0x04000006, (S(-3, STREAM[:3] + b"01234567"), S(8, STREAM[8:16])),
                  expect_anomalies=("before-isn",)))
    return c


def all_cases() -> List[Case]:
    cases = _special_cases() + _geometry_cases()
    ids = [c.id for c in cases]
    assert len(ids) == len(set(ids)), "duplicate case ids"
    return cases


def get_case(case_id: str) -> Case:
    for c in all_cases():
        if c.id == case_id:
            return c
    raise KeyError(case_id)


def permutations(case: Case, max_segments: int = 5) -> Iterator[Case]:
    """All arrival orders of a case's segments (ACK events dropped)."""
    segs = case.segs()
    if len(segs) > max_segments:
        return
    for i, perm in enumerate(itertools.permutations(range(len(segs)))):
        yield Case("%s~p%s" % (case.id, "".join(map(str, perm))), case.title, case.category, case.description,
                   case.isn, tuple(segs[j] for j in perm), case.handshake, case.expect_anomalies)


# ---------------------------------------------------------------------------------------------------
# Expected outcomes, straight from the abstract events
# ---------------------------------------------------------------------------------------------------

def event_claims(case: Case, endpoint_view: bool = False) -> Tuple[List[Claim], List[int]]:
    """Claims a tap sees (and the stream offsets of FINs).  ``endpoint_view`` additionally includes IPv4
    fragmented segments, which every endpoint reassembles but a tap that does not reassemble IP never sees."""
    claims: List[Claim] = []
    fins: List[int] = []
    for ev in case.events:
        if not isinstance(ev, Seg):
            continue
        if ev.bad_csum or (ev.frag and not endpoint_view):
            continue      # discarded by checksum verification / not reassembled at the IP layer
        off, data = ev.off, ev.data
        if data and off < 0:
            cut = min(-off, len(data))
            data, off = data[cut:], off + cut
        if data:
            claims.append(Claim(len(claims), off, data, 0, 0, ('syn-data',) if ev.syn else ()))
        if ev.fin:
            fins.append(ev.off + len(ev.data))
    return claims, fins


def expected_for_case(case: Case, policies: Sequence[str] = DEFAULT_POLICIES, endpoint_view: bool = False) -> dict:
    claims, fins = event_claims(case, endpoint_view)
    streams: Dict[str, dict] = {}
    conflict_ranges: List[Tuple[int, int]] = oracle(claims, POLICIES["first"]).conflict_ranges
    for name in policies:
        res = oracle(claims, POLICIES[name])
        contiguous = b""
        complete = True
        for start, data in res.runs:
            if start == 0:
                contiguous = data
        end = max((c.end for c in claims), default=0)
        complete = len(contiguous) == end
        if fins:
            complete = complete and len(contiguous) >= min(fins)
            contiguous = contiguous[:min(fins)]
        streams[name] = {"length": len(contiguous), "sha256": hashlib.sha256(contiguous).hexdigest(),
                         "complete": complete, "hex": contiguous.hex()}
    divergent = len({(s["length"], s["sha256"]) for s in streams.values()}) > 1
    return {
        "conflict_ranges": [list(r) for r in conflict_ranges],
        "anomalies": sorted(case.expect_anomalies),
        "streams": streams,
        "policy_divergent": divergent,
        "ambiguous": bool(conflict_ranges) or bool(set(case.expect_anomalies) & FAIL_KINDS),
    }


# ---------------------------------------------------------------------------------------------------
# Materialisation
# ---------------------------------------------------------------------------------------------------

@dataclass
class Addressing:
    client_ip: str = "192.0.2.1"
    server_ip: str = "192.0.2.2"
    client_mac: str = "02:00:00:00:00:01"
    server_mac: str = "02:00:00:00:00:02"
    client_port: int = 40000
    server_port: int = 80

    @classmethod
    def v6(cls, **kw) -> "Addressing":
        return cls(client_ip="2001:db8::1", server_ip="2001:db8::2", **kw)


MSS_OPT = bytes([2, 4, 0x05, 0xB4])
EPOCH_NS = 1_760_000_000 * 1_000_000_000


def server_isn(case: Case) -> int:
    return (case.isn * 2654435761 + 0x9E3779B9) & 0xFFFFFFFF


def case_frames(case: Case, addr: Optional[Addressing] = None, vlans: Sequence[int] = (),
                linktype: int = LINKTYPE_ETHERNET, ts0_ns: int = EPOCH_NS) -> List[Tuple[int, bytes]]:
    addr = addr or Addressing()
    v6 = ":" in addr.client_ip
    if v6 and any(e.frag for e in case.events if isinstance(e, Seg)):
        raise ValueError("IPv4 fragmentation cases cannot be rendered over IPv6")
    isn, sisn = case.isn & 0xFFFFFFFF, server_isn(case)
    out: List[Tuple[int, bytes]] = []
    state = {"t": ts0_ns, "ident": 1}

    def emit(l3: bytes, from_client: bool) -> None:
        if linktype == LINKTYPE_RAW:
            data = l3
        else:
            src, dst = (addr.client_mac, addr.server_mac) if from_client else (addr.server_mac, addr.client_mac)
            data = fr.ethernet_frame(dst, src, l3, ipv6=v6, vlans=vlans)
        out.append((state["t"], data))
        state["t"] += 1_000_000

    def pkt(from_client: bool, seq: int, ack: int, flags: int, payload: bytes = b"", options: bytes = b"",
            bad_tcp: bool = False) -> bytes:
        if from_client:
            a, b, sp, dp = addr.client_ip, addr.server_ip, addr.client_port, addr.server_port
        else:
            a, b, sp, dp = addr.server_ip, addr.client_ip, addr.server_port, addr.client_port
        state["ident"] += 1
        return fr.tcp_ip_packet(a, b, sp, dp, seq, ack, flags, payload, options=options, ident=state["ident"],
                                bad_tcp_checksum=bad_tcp)

    base = (isn + 1) & 0xFFFFFFFF            # sequence number of stream offset 0
    if case.handshake:
        syn_ev = next((e for e in case.events if isinstance(e, Seg) and e.syn), None)
        emit(pkt(True, isn, 0, fr.SYN, syn_ev.data if syn_ev else b"", MSS_OPT), True)
        emit(pkt(False, sisn, base, fr.SYN | fr.ACK, b"", MSS_OPT), False)
        emit(pkt(True, base, (sisn + 1) & 0xFFFFFFFF, fr.ACK), True)
    else:
        base = (isn + 1) & 0xFFFFFFFF
    sack = (sisn + 1) & 0xFFFFFFFF
    for ev in case.events:
        if isinstance(ev, Ack):
            emit(pkt(False, sack, (base + ev.off) & 0xFFFFFFFF, fr.ACK), False)
            continue
        if ev.syn:
            continue                          # already carried by the SYN above
        flags = fr.ACK | (fr.PSH if ev.data else 0) | (fr.FIN if ev.fin else 0)
        seq = (base + ev.off) & 0xFFFFFFFF
        if ev.frag:
            full = pkt(True, seq, sack, flags, ev.data)
            for f in fr.fragment_ipv4(full, 24):
                emit(f, True)
        else:
            emit(pkt(True, seq, sack, flags, ev.data, bad_tcp=ev.bad_csum), True)
    return out


def case_addressing(index: int, ipv6: bool = False) -> Addressing:
    return (Addressing.v6 if ipv6 else Addressing)(client_port=40000 + index)


def _event_json(ev: Event) -> dict:
    if isinstance(ev, Ack):
        return {"type": "ack", "off": ev.off}
    d = {"type": "seg", "off": ev.off, "data_hex": ev.data.hex()}
    for k in ("fin", "syn", "bad_csum", "frag"):
        if getattr(ev, k):
            d[k] = True
    return d


def build_manifest(cases: Optional[Sequence[Case]] = None, ipv6: bool = False) -> dict:
    cases = list(cases or all_cases())
    entries = []
    for i, c in enumerate(cases):
        a = case_addressing(i, ipv6)
        entries.append({
            "id": c.id, "title": c.title, "category": c.category, "description": c.description,
            "pcap": c.id + ".pcap", "client": "%s:%d" % (a.client_ip, a.client_port),
            "server": "%s:%d" % (a.server_ip, a.server_port), "isn": c.isn, "handshake": c.handshake,
            "events": [_event_json(e) for e in c.events], "expected": expected_for_case(c),
        })
    return {"format": 1, "generator": "packet-forge", "policies": list(DEFAULT_POLICIES),
            "policy_docs": {n: p.doc for n, p in POLICIES.items()}, "cases": entries}


def write_corpus(outdir: str, ipv6: bool = False, vlans: Sequence[int] = (), linktype: int = LINKTYPE_ETHERNET,
                 nano: bool = False) -> dict:
    os.makedirs(outdir, exist_ok=True)
    # IPv4 fragmentation does not apply to IPv6 captures: those cases are omitted there
    cases = [c for c in all_cases() if not (ipv6 and any(sg.frag for sg in c.segs()))]
    combined: List[Tuple[int, bytes]] = []
    t = EPOCH_NS
    sums = []
    for i, c in enumerate(cases):
        frames_ = case_frames(c, case_addressing(i, ipv6), vlans, linktype, ts0_ns=t)
        t = frames_[-1][0] + 1_000_000_000
        path = os.path.join(outdir, c.id + ".pcap")
        write_pcap(path, frames_, linktype, nano=nano)
        combined.extend(frames_)
    write_pcap(os.path.join(outdir, "all-cases.pcap"), combined, linktype, nano=nano)
    manifest = build_manifest(cases, ipv6)
    with open(os.path.join(outdir, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1, sort_keys=True)
        f.write("\n")
    for name in sorted(os.listdir(outdir)):
        if name == "SHA256SUMS":
            continue
        with open(os.path.join(outdir, name), "rb") as fh:
            sums.append("%s  %s" % (hashlib.sha256(fh.read()).hexdigest(), name))
    with open(os.path.join(outdir, "SHA256SUMS"), "w") as f:
        f.write("\n".join(sums) + "\n")
    return manifest
