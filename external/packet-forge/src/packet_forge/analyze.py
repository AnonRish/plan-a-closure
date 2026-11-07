"""Flow-level analysis: capture -> per-direction claims -> canonical streams, conflicts, anomalies."""
from __future__ import annotations

import hashlib
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from . import seqspace
from .assembler import StreamAssembler, merge_ranges
from .model import DEFAULT_POLICIES, POLICIES, Claim
from .parse import FrameNote, TcpSeg, parse_frame
from .pcap import read_pcap_stream

# anomaly kinds that make `packet-forge check` exit non-zero (besides conflicts)
FAIL_KINDS = frozenset({"syn-data", "data-after-fin", "conflicting-fin", "conflicting-syn", "bad-checksum",
                        "ip-fragment", "before-isn", "truncated", "rst-with-data"})


@dataclass
class Anomaly:
    kind: str
    frames: List[int]
    detail: str = ""


@dataclass
class ConflictRange:
    start: int
    end: int
    claims: List[dict]            # every claim covering the range: frame, start, end, sha256 of its bytes there
    distinct_values: int
    late_after_ack: List[int]     # frames of claims that arrived after the peer had ACKed the range start
    hint: str = ""


@dataclass
class StreamResult:
    length: int
    sha256: str
    complete: bool
    hex: Optional[str] = None


@dataclass
class DirectionReport:
    flow: str
    base_seq: Optional[int]
    syn_seen: bool
    claims: int
    bytes_claimed: int
    stream_end: int
    fin_offset: Optional[int]
    holes: List[Tuple[int, int]]
    conflicts: List[ConflictRange]
    anomalies: List[Anomaly]
    streams: Dict[str, StreamResult]
    policy_divergent: bool

    def kinds(self) -> List[str]:
        return sorted({a.kind for a in self.anomalies})


@dataclass
class Report:
    frames: int
    tcp_segments: int
    directions: List[DirectionReport]
    frame_notes: List[Anomaly]
    checksum_mode: str

    @property
    def conflict_count(self) -> int:
        return sum(len(d.conflicts) for d in self.directions)

    def failing(self, fail_kinds: Iterable[str] = FAIL_KINDS) -> bool:
        fk = set(fail_kinds)
        if self.conflict_count:
            return True
        if any(a.kind in fk for a in self.frame_notes):
            return True
        return any(a.kind in fk for d in self.directions for a in d.anomalies)

    def to_dict(self) -> dict:
        def conv(o):
            if hasattr(o, "__dataclass_fields__"):
                return {k: conv(v) for k, v in o.__dict__.items()}
            if isinstance(o, dict):
                return {k: conv(v) for k, v in o.items()}
            if isinstance(o, (list, tuple)):
                return [conv(v) for v in o]
            return o
        return conv(self)


def _fmt_flow(k: Tuple[str, int, str, int]) -> str:
    a = "[%s]:%d" % (k[0], k[1]) if ":" in k[0] else "%s:%d" % (k[0], k[1])
    b = "[%s]:%d" % (k[2], k[3]) if ":" in k[2] else "%s:%d" % (k[2], k[3])
    return a + ">" + b


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


@dataclass
class _Dir:
    key: Tuple[str, int, str, int]
    segs: List[TcpSeg] = field(default_factory=list)
    bad: List[TcpSeg] = field(default_factory=list)
    base32: Optional[int] = None
    syn_seen: bool = False
    anomalies: List[Anomaly] = field(default_factory=list)
    claims: List[Claim] = field(default_factory=list)
    frame_claim: Dict[int, Claim] = field(default_factory=dict)
    fin_offsets: List[Tuple[int, int]] = field(default_factory=list)   # (offset, frame)
    acked: int = 0
    ref: int = 0


def _determine_base(d: _Dir) -> None:
    syns = [s for s in d.segs if s.syn and not s.rst]
    if syns:
        d.syn_seen = True
        d.base32 = seqspace.add(syns[0].seq, 1)
        if len({s.seq for s in syns}) > 1:
            d.anomalies.append(Anomaly("conflicting-syn", [s.frame_no for s in syns],
                                       "SYNs with different initial sequence numbers"))
        return
    data = [s for s in d.segs if (s.payload or s.fin) and not s.rst]
    if not data:
        return
    prov = data[0].seq
    ref, lo = 0, 0
    for s in data:
        off = seqspace.unwrap(s.seq, prov, ref)
        ref = off
        lo = min(lo, off)
    d.base32 = seqspace.add(prov, lo)


def build_directions(segs: Sequence[TcpSeg], checksum: str = "verify") -> "OrderedDict[tuple, _Dir]":
    if checksum not in ("verify", "accept"):
        raise ValueError("checksum must be 'verify' or 'accept'")
    dirs: "OrderedDict[tuple, _Dir]" = OrderedDict()

    def get(k):
        if k not in dirs:
            dirs[k] = _Dir(k)
        return dirs[k]

    for s in segs:
        d = get(s.flow_key)
        if checksum == "verify" and (s.ip_csum_ok is False or s.tcp_csum_ok is False):
            d.bad.append(s)
        else:
            d.segs.append(s)

    for d in dirs.values():
        _determine_base(d)

    def rev(k):
        return (k[2], k[3], k[0], k[1])

    # main pass in capture order so that ACK state is correct at each claim's arrival
    valid = sorted((s for d in dirs.values() for s in d.segs), key=lambda s: s.frame_no)
    for s in valid:
        d = dirs[s.flow_key]
        r = dirs.get(rev(s.flow_key))
        if s.has_ack and r is not None and r.base32 is not None:
            a = seqspace.unwrap(s.ack, r.base32, r.acked)
            if a > r.acked:
                r.acked = a
        if d.base32 is None:
            continue
        if s.rst:
            if s.payload:
                d.anomalies.append(Anomaly("rst-with-data", [s.frame_no], "payload on a RST segment ignored"))
            continue
        start32 = seqspace.add(s.seq, 1 if s.syn else 0)
        off = seqspace.unwrap(start32, d.base32, d.ref)
        if s.payload:
            d.ref = off
            flags: Tuple[str, ...] = ()
            if s.syn:
                flags = ("syn-data",)
                d.anomalies.append(Anomaly("syn-data", [s.frame_no], "payload carried on a SYN"))
            data = s.payload
            if s.truncated:
                d.anomalies.append(Anomaly("truncated", [s.frame_no], "capture shorter than the on-wire segment"))
            if off < 0:
                cut = min(-off, len(data))
                d.anomalies.append(Anomaly("before-isn", [s.frame_no], "%d byte(s) precede the stream start" % cut))
                data, off = data[cut:], off + cut
            if data:
                cl = Claim(len(d.claims), off, data, s.frame_no, d.acked, flags)
                d.claims.append(cl)
                d.frame_claim[s.frame_no] = cl
        if s.fin:
            d.fin_offsets.append((off + s.declared_len, s.frame_no))
    # bad-checksum anomalies
    for d in dirs.values():
        if d.bad:
            withdata = [s.frame_no for s in d.bad if s.payload]
            d.anomalies.append(Anomaly("bad-checksum", [s.frame_no for s in d.bad],
                                       "%d segment(s) excluded; %d carried payload" % (len(d.bad), len(withdata))))
    return dirs


def analyze_segments(segs: Sequence[TcpSeg], notes: Sequence[FrameNote] = (), total_frames: Optional[int] = None,
                     policies: Sequence[str] = DEFAULT_POLICIES, checksum: str = "verify",
                     include_hex: bool = False) -> Report:
    dirs = build_directions(segs, checksum)
    reports: List[DirectionReport] = []
    for k, d in dirs.items():
        if not d.claims and not d.anomalies and not d.fin_offsets:
            continue
        reports.append(_report_direction(d, policies, include_hex))
    frame_notes: List[Anomaly] = []
    by_kind: Dict[str, List[int]] = defaultdict(list)
    for n in notes:
        if n.kind in ("ip-fragment", "malformed", "ipv6-ext-unsupported"):
            by_kind[n.kind].append(n.frame_no)
    for kind, frs in by_kind.items():
        frame_notes.append(Anomaly(kind, frs, "%d frame(s) not analysed" % len(frs)))
    return Report(total_frames if total_frames is not None else len(segs) + len(notes), len(segs), reports,
                  frame_notes, checksum)


def _report_direction(d: _Dir, policies: Sequence[str], include_hex: bool) -> DirectionReport:
    anomalies = list(d.anomalies)
    if not d.syn_seen and d.claims:
        anomalies.append(Anomaly("midstream", [], "no SYN captured; stream start inferred from the lowest sequence number"))
    fin_offset: Optional[int] = None
    if d.fin_offsets:
        offs = sorted({o for o, _ in d.fin_offsets})
        fin_offset = offs[0]        # earliest FIN: deterministic, independent of arrival order
        if len(offs) > 1:
            anomalies.append(Anomaly("conflicting-fin", [f for _, f in d.fin_offsets],
                                     "FIN at different stream offsets: %s" % offs))
        beyond = [c.frame for c in d.claims if c.end > fin_offset]
        if beyond:
            anomalies.append(Anomaly("data-after-fin", beyond, "payload extends past the FIN at offset %d" % fin_offset))

    # conflicts, holes and extent do not depend on the policy: always use a dedicated 'first' pass
    conflict_asm = StreamAssembler(POLICIES["first"], 0)
    for c in d.claims:
        conflict_asm.add(c)
    assemblers: Dict[str, StreamAssembler] = {}
    for name in policies:
        asm = StreamAssembler(POLICIES[name], 0)
        for c in d.claims:
            asm.add(c)
        assemblers[name] = asm

    first_asm = conflict_asm
    ranges = merge_ranges([(e.start, e.end) for e in first_asm.conflicts])
    conflicts: List[ConflictRange] = []
    for a, b in ranges:
        covering = [c for c in d.claims if c.start < b and c.end > a]
        entries = []
        digests = set()
        for c in covering:
            lo, hi = max(a, c.start), min(b, c.end)
            h = _sha(c.data[lo - c.start:hi - c.start])
            digests.add((lo, hi, h))
            entries.append({"frame": c.frame, "start": c.start, "end": c.end, "sha256": h[:16]})
        first_arrival = min(covering, key=lambda c: c.arrival)
        late = [c.frame for c in covering if c is not first_arrival and c.acked_at_arrival > a]
        hint = ""
        if b - a == 1 and any(len(c.data) == 1 for c in covering):
            hint = "single-byte claim: shaped like a TCP keep-alive probe with a garbage octet (RFC 1122 4.2.3.6)"
        # distinct values: compare byte-for-byte at the first conflicting offset
        vals = {c.data[a - c.start] for c in covering if c.start <= a < c.end}
        conflicts.append(ConflictRange(a, b, entries, len(vals), late, hint))

    streams: Dict[str, StreamResult] = {}
    stream_end = first_asm.end_offset()
    for name, asm in assemblers.items():
        data = asm.contiguous()
        complete = not asm.holes()
        if fin_offset is not None:
            data = data[:fin_offset]
            complete = complete and len(asm.contiguous()) >= fin_offset
        streams[name] = StreamResult(len(data), _sha(data), complete, data.hex() if include_hex else None)
    divergent = len({(s.length, s.sha256) for s in streams.values()}) > 1
    holes = first_asm.holes()
    return DirectionReport(
        flow=_fmt_flow(d.key), base_seq=d.base32, syn_seen=d.syn_seen, claims=len(d.claims),
        bytes_claimed=sum(len(c.data) for c in d.claims), stream_end=stream_end, fin_offset=fin_offset,
        holes=holes, conflicts=conflicts, anomalies=anomalies, streams=streams, policy_divergent=divergent)


def parse_capture(path_or_file) -> Tuple[List[TcpSeg], List[FrameNote], int]:
    import io
    f = open(path_or_file, "rb") if isinstance(path_or_file, str) else path_or_file
    try:
        hdr, it = read_pcap_stream(f)
        segs: List[TcpSeg] = []
        notes: List[FrameNote] = []
        n = 0
        for n, rec in enumerate(it, 1):
            seg, note = parse_frame(n, rec.ts_ns, rec.data, hdr.linktype)
            if seg is not None:
                segs.append(seg)
            elif note is not None:
                notes.append(note)
        return segs, notes, n
    finally:
        if isinstance(path_or_file, str):
            f.close()


def analyze_pcap(path: str, policies: Sequence[str] = DEFAULT_POLICIES, checksum: str = "verify",
                 include_hex: bool = False) -> Report:
    segs, notes, n = parse_capture(path)
    return analyze_segments(segs, notes, n, policies, checksum, include_hex)
