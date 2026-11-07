"""
cuda_guard.network_evidence
=============================
Phase 11 (spec Sec. 19) + Phase 20 (spec Sec. 20). Real PCAP file parsing
(hand-rolled against the actual libpcap file format -- no scapy dependency,
per Sec. 38's "minimize dependency count") plus flow-statistics computation.

Scope discipline: every conclusion here is NETWORK_BEHAVIORAL_CORROBORATION,
never TRAINING_PROVEN or INFERENCE_PROVEN. Every record sourced from a PCAP
file is tagged REPLAYED_NETWORK_EVIDENCE and can never masquerade as live
physical observation (spec Sec. 20). Live-interface and external-tap-feed
capture need raw-socket privileges (CAP_NET_RAW / root) this sandboxed
environment does not have -- those adapters are real, clean interfaces,
correctly marked REAL_BUT_HARDWARE_DEPENDENT, not faked.
"""

from __future__ import annotations

import socket
import struct
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .evidence import EvidenceClass, EvidenceRecord, EvidenceSource, EvidenceStatus, NetworkObservation, TrustRoot
from .ledger import TamperEvidentLedger

PCAP_MAGIC_LE = 0xA1B2C3D4  # microsecond-resolution, little-endian


def write_synthetic_pcap(path: Path, packets: list[dict[str, Any]]) -> None:
    """TEST FIXTURE ONLY -- writes a genuinely valid PCAP file (real binary
    format, not a fake stand-in) so parsing can be tested against real
    bytes. `packets`: [{"src": "10.0.0.1", "dst": "10.0.0.2", "proto": 6,
    "sport": 1234, "dport": 443, "payload_len": 100, "ts": 1700000000.0}]"""
    with open(path, "wb") as f:
        f.write(struct.pack("<IHHiIII", PCAP_MAGIC_LE, 2, 4, 0, 0, 65535, 1))  # global header, LINKTYPE_ETHERNET
        for p in packets:
            eth = b"\x00" * 12 + b"\x08\x00"  # dummy MAC src/dst + EtherType IPv4
            src = socket.inet_aton(p["src"])
            dst = socket.inet_aton(p["dst"])
            ip_total_len = 20 + 20 + p.get("payload_len", 0)
            ip_header = struct.pack("!BBHHHBBH4s4s", 0x45, 0, ip_total_len, 0, 0, 64,
                                     p.get("proto", 6), 0, src, dst)
            tcp_header = struct.pack("!HHLLBBHHH", p.get("sport", 0), p.get("dport", 0),
                                      0, 0, 0x50, 0, 0, 0, 0)
            payload = b"\x00" * p.get("payload_len", 0)
            frame = eth + ip_header + tcp_header + payload
            ts = p.get("ts", time.time())
            ts_sec, ts_usec = int(ts), int((ts - int(ts)) * 1_000_000)
            f.write(struct.pack("<IIII", ts_sec, ts_usec, len(frame), len(frame)))
            f.write(frame)


class PcapEvidenceSource:
    """Real parser against the actual PCAP global-header + per-packet-record
    binary format. Every result is tagged REPLAYED_NETWORK_EVIDENCE."""

    def __init__(self, ledger: TamperEvidentLedger):
        self._ledger = ledger

    def parse(self, path: Path) -> tuple[list[NetworkObservation], EvidenceRecord]:
        observations: list[NetworkObservation] = []
        try:
            with open(path, "rb") as f:
                header = f.read(24)
                if len(header) < 24:
                    raise ValueError("file too short to be a valid PCAP global header")
                magic = struct.unpack("<I", header[:4])[0]
                if magic != PCAP_MAGIC_LE:
                    raise ValueError(f"unrecognized PCAP magic number: {hex(magic)}")
                while True:
                    rec_header = f.read(16)
                    if len(rec_header) < 16:
                        break
                    ts_sec, ts_usec, incl_len, _orig_len = struct.unpack("<IIII", rec_header)
                    frame = f.read(incl_len)
                    observations.append(self._parse_frame(frame, ts_sec + ts_usec / 1_000_000))
            ev = EvidenceRecord(
                EvidenceClass.NETWORK_OBSERVATION, EvidenceSource.PCAP_FILE, EvidenceStatus.SUCCESS,
                TrustRoot.GOVERNED_PROCESS_SELF,
                # A PCAP file's trust root is whoever captured it, not this parser.
                # GOVERNED_PROCESS_SELF is the honest default for a file just handed to this
                # process; an externally-captured PCAP should instead be ingested via
                # record_external_evidence("network", ...) (Phase 25), which correctly tags
                # TrustRoot.INDEPENDENT_EXTERNAL_VERIFIER.
                establishes=[f"REPLAYED_NETWORK_EVIDENCE: {len(observations)} packet(s) parsed "
                             f"from a real PCAP file at {path}"],
                does_not_establish=["live physical observation (this is replayed from a file)",
                                     "semantic workload intent -- see NETWORK_BEHAVIORAL_CORROBORATION"],
                detail={"packet_count": len(observations), "source_path": str(path)})
        except Exception as exc:
            ev = EvidenceRecord(
                EvidenceClass.NETWORK_OBSERVATION, EvidenceSource.PCAP_FILE, EvidenceStatus.FAILED,
                TrustRoot.GOVERNED_PROCESS_SELF, establishes=[], does_not_establish=[],
                detail={"error": str(exc), "source_path": str(path)})
        self._ledger.record_evidence(ev)
        return observations, ev

    @staticmethod
    def _parse_frame(frame: bytes, ts: float) -> NetworkObservation:
        try:
            if len(frame) >= 34 and frame[12:14] == b"\x08\x00":  # EtherType IPv4
                ip = frame[14:34]
                proto = ip[9]
                src = socket.inet_ntoa(ip[12:16])
                dst = socket.inet_ntoa(ip[16:20])
                return NetworkObservation(source_ip=src, dest_ip=dst, protocol={6: "TCP", 17: "UDP"}.get(proto, str(proto)),
                                           packet_length=len(frame), direction=None, flow_id=f"{src}->{dst}/{proto}",
                                           timestamp=ts, capture_source=EvidenceSource.PCAP_FILE)
        except Exception:
            pass
        return NetworkObservation(source_ip=None, dest_ip=None, protocol=None, packet_length=len(frame),
                                   direction=None, flow_id=None, timestamp=ts, capture_source=EvidenceSource.PCAP_FILE)


def compute_flow_statistics(observations: list[NetworkObservation]) -> dict[str, Any]:
    """NETWORK_BEHAVIORAL_CORROBORATION, never TRAINING_PROVEN/INFERENCE_PROVEN."""
    if not observations:
        return {"packet_count": 0, "claim": "NETWORK_BEHAVIORAL_CORROBORATION", "note": "no packets to analyze"}
    lengths = [o.packet_length for o in observations]
    flows: dict[str, list[NetworkObservation]] = {}
    for o in observations:
        flows.setdefault(o.flow_id or "unknown", []).append(o)
    timestamps = sorted(o.timestamp for o in observations)
    duration = timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 0.0
    return {
        "claim": "NETWORK_BEHAVIORAL_CORROBORATION",
        "packet_count": len(observations),
        "traffic_volume_bytes": sum(lengths),
        "packet_size_min": min(lengths), "packet_size_max": max(lengths),
        "packet_size_mean": sum(lengths) / len(lengths),
        "flow_count": len(flows),
        "flow_duration_s": duration,
        "packets_per_flow": {k: len(v) for k, v in flows.items()},
        "scope_note": "This statistic corroborates traffic patterns. It does NOT prove "
                      "training vs. inference, or R&D vs. deployment intent -- combine with "
                      "other layers (Trust Architecture Sec. 9) for a stronger conclusion.",
    }


class LiveInterfaceSource:
    """REAL_BUT_HARDWARE_DEPENDENT: requires CAP_NET_RAW/root and a live
    network interface, neither available in this sandboxed environment.
    Clean interface only -- not exercised, not faked as if it were."""

    def __init__(self, interface_name: str):
        self.interface_name = interface_name

    def capture(self, duration_s: float = 1.0) -> EvidenceRecord:
        return EvidenceRecord(
            EvidenceClass.NETWORK_OBSERVATION, EvidenceSource.LIVE_INTERFACE, EvidenceStatus.UNAVAILABLE,
            TrustRoot.INDEPENDENT_PHYSICAL_INFRASTRUCTURE, establishes=[],
            does_not_establish=["anything -- REAL_BUT_HARDWARE_DEPENDENT: requires raw-socket "
                                 "privileges (CAP_NET_RAW/root) not available in this environment"],
            detail={"interface": self.interface_name, "capability_status": "REAL_BUT_HARDWARE_DEPENDENT"})


class ExternalTapFeedSource:
    """REAL_BUT_HARDWARE_DEPENDENT: an out-of-band physical/optical tap feed
    (e.g. IOVT). No such feed exists in this environment; use
    record_external_evidence("network", ...) when one is actually connected."""

    def capture(self) -> EvidenceRecord:
        return EvidenceRecord(
            EvidenceClass.NETWORK_OBSERVATION, EvidenceSource.EXTERNAL_TAP_FEED, EvidenceStatus.UNAVAILABLE,
            TrustRoot.INDEPENDENT_EXTERNAL_VERIFIER, establishes=[],
            does_not_establish=["anything -- no external tap feed connected in this environment"],
            detail={"capability_status": "REAL_BUT_HARDWARE_DEPENDENT"})
