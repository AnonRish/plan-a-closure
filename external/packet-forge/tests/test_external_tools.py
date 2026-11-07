"""Independent implementations as referees: tshark (dissection, checksum status, TCP reassembly) and tcpdump."""
import os
import subprocess

import pytest

from packet_forge import corpus as C
from packet_forge.analyze import parse_capture
from packet_forge.corpus import all_cases
from packet_forge.pcap import LINKTYPE_RAW

pytestmark = pytest.mark.external

FIELDS = ["frame.number", "tcp.srcport", "tcp.seq_raw", "tcp.ack_raw", "tcp.flags", "tcp.len", "tcp.checksum.status"]


def tshark_fields(pcap):
    cmd = ["tshark", "-r", pcap, "-o", "tcp.check_checksum:TRUE", "-o", "tcp.analyze_sequence_numbers:FALSE",
           "-T", "fields", "-E", "separator=/t"] + [x for f in FIELDS for x in ("-e", f)]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    rows = {}
    for ln in out.splitlines():
        parts = ln.split("\t")
        parts += [""] * (len(FIELDS) - len(parts))
        rows[int(parts[0])] = dict(zip(FIELDS, parts))
    return rows


def compare_with_parser(pcap):
    rows = tshark_fields(pcap)
    segs, notes, total = parse_capture(pcap)
    assert total == len(rows)
    by_frame = {s.frame_no: s for s in segs}
    fragments = {nt.frame_no for nt in notes if nt.kind == "ip-fragment"}
    assert len(fragments) in (0, 2)     # 2 = the fragmented segment of anom-ip-fragment (absent over IPv6)
    for n, row in rows.items():
        s = by_frame.get(n)
        if n in fragments:
            continue                    # tshark reassembles IP fragments (as endpoints do); we flag them instead
        if s is None:
            assert not row["tcp.seq_raw"], "tshark sees TCP in frame %d that we did not parse" % n
            continue
        assert int(row["tcp.seq_raw"]) == s.seq and int(row["tcp.ack_raw"]) == s.ack, n
        assert int(row["tcp.flags"], 16) & 0x3F == s.flags, n
        assert int(row["tcp.len"]) == len(s.payload), n
        status = row["tcp.checksum.status"]
        assert status in ("0", "1"), (n, status)
        assert (status == "1") == bool(s.tcp_csum_ok), n
    return len(segs)


def test_ipv4_corpus_fields_and_checksums_match_tshark(corpus_dir):
    assert compare_with_parser(os.path.join(corpus_dir, "all-cases.pcap")) > 300


@pytest.mark.parametrize("variant", ["ipv6", "vlan", "raw"])
def test_variants_match_tshark(variant, tmp_path):
    kw = {"ipv6": {"ipv6": True}, "vlan": {"vlans": (7, 8)}, "raw": {"linktype": LINKTYPE_RAW}}[variant]
    C.write_corpus(str(tmp_path), **kw)
    assert compare_with_parser(str(tmp_path / "all-cases.pcap")) > 300


def test_tcpdump_agrees_on_bad_checksums(corpus_dir):
    pcap = os.path.join(corpus_dir, "all-cases.pcap")
    out = subprocess.run(["tcpdump", "-nn", "-vv", "-r", pcap], capture_output=True, text=True).stdout
    segs, _, _ = parse_capture(pcap)
    ours = sum(1 for s in segs if s.tcp_csum_ok is False)
    assert ours == sum(c.expect_anomalies.count("bad-checksum") for c in all_cases()) == 2
    assert out.count("incorrect") == ours


def follow_stream(pcap):
    out = subprocess.run(["tshark", "-r", pcap, "-o", "tcp.reassemble_out_of_order:TRUE", "-q", "-z",
                          "follow,tcp,raw,0"], capture_output=True, text=True).stdout.splitlines()
    data = b""
    for ln in out:
        if ln and not ln.startswith(("\t", "=", "Follow", "Filter", "Node")) and all(c in "0123456789abcdef" for c in ln):
            data += bytes.fromhex(ln)
    return data


def test_tshark_reassembles_every_benign_case_like_we_do(manifest, corpus_dir):
    benign = [e for e in manifest["cases"] if e["category"] == "benign"]
    assert len(benign) == 8
    for e in benign:
        want = bytes.fromhex(e["expected"]["streams"]["first"]["hex"])
        assert follow_stream(os.path.join(corpus_dir, e["pcap"])) == want, e["id"]


def test_tshark_reassembly_of_overlaps_is_a_known_policy_most_of_the_time(manifest, corpus_dir):
    """Informational cross-check: Wireshark's reassembly is a real, independent implementation of *some*
    overlap rule.  We only require that it lands on one of our policies for most overlap cases."""
    hits = total = 0
    for e in manifest["cases"]:
        if e["category"] != "overlap":
            continue
        t = follow_stream(os.path.join(corpus_dir, e["pcap"]))
        total += 1
        hits += any(bytes.fromhex(s["hex"]) == t for s in e["expected"]["streams"].values())
    assert hits / total > 0.8, (hits, total)
