"""tests/test_network_evidence.py -- Phase 11/19/20."""
import sys, os, tempfile, subprocess
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from pathlib import Path

from cuda_guard.ledger import TamperEvidentLedger
from cuda_guard.network_evidence import write_synthetic_pcap, PcapEvidenceSource, compute_flow_statistics, LiveInterfaceSource
from cuda_guard.evidence import EvidenceStatus


def test_pcap_write_produces_a_real_valid_pcap_file():
    """Verified against an independent tool (the system `file` command),
    not just our own parser round-tripping its own output."""
    tmpdir = Path(tempfile.mkdtemp())
    path = tmpdir / "t.pcap"
    write_synthetic_pcap(path, [{"src": "10.0.0.1", "dst": "10.0.0.2", "proto": 6,
                                  "sport": 1, "dport": 2, "payload_len": 10, "ts": 1700000000.0}])
    result = subprocess.run(["file", str(path)], capture_output=True, text=True)
    assert "pcap capture file" in result.stdout.lower()


def test_pcap_parse_extracts_real_fields():
    tmpdir = Path(tempfile.mkdtemp())
    path = tmpdir / "t.pcap"
    write_synthetic_pcap(path, [
        {"src": "10.0.0.1", "dst": "10.0.0.2", "proto": 6, "sport": 1, "dport": 2, "payload_len": 100, "ts": 1700000000.0},
        {"src": "10.0.0.3", "dst": "10.0.0.4", "proto": 17, "sport": 3, "dport": 4, "payload_len": 50, "ts": 1700000001.0},
    ])
    ledger = TamperEvidentLedger()
    observations, ev = PcapEvidenceSource(ledger).parse(path)
    assert ev.status == EvidenceStatus.SUCCESS
    assert len(observations) == 2
    assert observations[0].source_ip == "10.0.0.1" and observations[0].protocol == "TCP"
    assert observations[1].protocol == "UDP"


def test_pcap_parse_of_corrupt_file_fails_loudly():
    tmpdir = Path(tempfile.mkdtemp())
    bad = tmpdir / "bad.pcap"
    bad.write_bytes(b"not a pcap file")
    ledger = TamperEvidentLedger()
    _, ev = PcapEvidenceSource(ledger).parse(bad)
    assert ev.status == EvidenceStatus.FAILED  # must not silently report empty success


def test_flow_statistics_scope_note_present():
    tmpdir = Path(tempfile.mkdtemp())
    path = tmpdir / "t.pcap"
    write_synthetic_pcap(path, [{"src": "10.0.0.1", "dst": "10.0.0.2", "proto": 6,
                                  "sport": 1, "dport": 2, "payload_len": 10, "ts": 1700000000.0}])
    ledger = TamperEvidentLedger()
    observations, _ = PcapEvidenceSource(ledger).parse(path)
    stats = compute_flow_statistics(observations)
    assert stats["claim"] == "NETWORK_BEHAVIORAL_CORROBORATION"
    assert "does not prove" in stats["scope_note"].lower() or "not prove" in stats["scope_note"].lower()


def test_live_interface_correctly_unavailable_not_faked():
    ev = LiveInterfaceSource("eth0").capture()
    assert ev.status == EvidenceStatus.UNAVAILABLE
    assert ev.detail["capability_status"] == "REAL_BUT_HARDWARE_DEPENDENT"
