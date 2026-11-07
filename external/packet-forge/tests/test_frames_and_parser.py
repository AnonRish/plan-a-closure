"""Frame builder + parser, cross-checked against scapy (an independent implementation)."""
import ipaddress
import random
import struct

import pytest
from hypothesis import given, settings, strategies as st
from scapy.all import Ether, IP, IPv6, TCP, Padding, raw as scapy_raw

from packet_forge import frames as fr, seqspace
from packet_forge.parse import parse_frame
from packet_forge.pcap import (LINKTYPE_ETHERNET, LINKTYPE_RAW, PcapError, read_pcap, read_pcap_stream,
                               write_pcap)

V4 = ("192.0.2.1", "192.0.2.2")
V6 = ("2001:db8::1", "2001:db8::2")
MAC = ("02:00:00:00:00:02", "02:00:00:00:00:01")


def build(addrs, seq, ack, flags, payload, options=b"", vlans=()):
    pkt = fr.tcp_ip_packet(addrs[0], addrs[1], 40000, 80, seq, ack, flags, payload, options=options)
    return fr.ethernet_frame(MAC[0], MAC[1], pkt, ipv6=":" in addrs[0], vlans=vlans)


@settings(max_examples=300, deadline=None)
@given(seq=st.integers(0, 2**32 - 1), ack=st.integers(0, 2**32 - 1), flags=st.integers(0, 0x3F),
       payload=st.binary(max_size=200), v6=st.booleans(), vlans=st.lists(st.integers(1, 4094), max_size=2),
       opts=st.sampled_from([b"", bytes([1, 1, 1, 0]), bytes([2, 4, 5, 0xB4]),
                             bytes([1, 1, 8, 10]) + bytes(8)]))
def test_builder_and_parser_agree_with_scapy(seq, ack, flags, payload, v6, vlans, opts):
    addrs = V6 if v6 else V4
    frame = build(addrs, seq, ack, flags, payload, opts, vlans)
    seg, note = parse_frame(1, 0, frame, LINKTYPE_ETHERNET)
    assert note is None and seg is not None
    assert (seg.seq, seg.ack, seg.flags, seg.payload) == (seq, ack, flags, payload)
    assert seg.tcp_csum_ok is True and (seg.ip_csum_ok in (True, None))
    assert (seg.src, seg.dst, seg.sport, seg.dport) == (addrs[0], addrs[1], 40000, 80)
    # scapy: parse the very same bytes
    e = Ether(frame)
    t = e[TCP]
    body = bytes(t.payload)
    pad = t.getlayer(Padding)
    if pad is not None and len(pad.load):
        body = body[:-len(pad.load)]      # scapy keeps Ethernet padding in the payload chain
    assert (t.seq, t.ack, int(t.flags), body) == (seq, ack, flags, payload)
    # scapy: recompute checksums from scratch and compare with ours
    ours = t.chksum
    del t.chksum
    if v6:
        del e[IPv6].plen
    else:
        del e[IP].chksum
        del e[IP].len
    assert Ether(scapy_raw(e))[TCP].chksum == ours


def test_ethernet_padding_is_not_payload():
    frame = build(V4, 100, 0, fr.ACK | fr.PSH, b"x")
    assert len(frame) == 60                               # padded to the Ethernet minimum
    seg, _ = parse_frame(1, 0, frame, LINKTYPE_ETHERNET)
    assert seg.payload == b"x"


@pytest.mark.parametrize("v6", [False, True])
def test_bad_checksum_is_detected(v6):
    addrs = V6 if v6 else V4
    pkt = fr.tcp_ip_packet(addrs[0], addrs[1], 1, 2, 5, 6, fr.ACK, b"abc", bad_tcp_checksum=True)
    seg, _ = parse_frame(1, 0, fr.ethernet_frame(*MAC, pkt, ipv6=v6), LINKTYPE_ETHERNET)
    assert seg.tcp_csum_ok is False


def test_bad_ip_checksum_is_detected():
    pkt = fr.tcp_ip_packet(*V4, 1, 2, 5, 6, fr.ACK, b"abc", bad_ip_checksum=True)
    seg, _ = parse_frame(1, 0, fr.ethernet_frame(*MAC, pkt), LINKTYPE_ETHERNET)
    assert seg.ip_csum_ok is False and seg.tcp_csum_ok is True


def test_bad_checksum_never_aliases_a_valid_one():
    rng = random.Random(5)
    for _ in range(2000):
        payload = bytes(rng.randrange(256) for _ in range(rng.randrange(0, 40)))
        pkt = fr.tcp_ip_packet(*V4, rng.randrange(65535), 80, rng.randrange(2**32), 0, fr.ACK, payload,
                               bad_tcp_checksum=True)
        seg, _ = parse_frame(1, 0, pkt, LINKTYPE_RAW)
        assert seg.tcp_csum_ok is False


def test_ip_fragments_are_reported_not_parsed():
    pkt = fr.tcp_ip_packet(*V4, 1, 2, 5, 6, fr.ACK, b"0123456789" * 3)
    frags = fr.fragment_ipv4(pkt, 24)
    assert len(frags) == 2
    for f in frags:
        seg, note = parse_frame(1, 0, fr.ethernet_frame(*MAC, f), LINKTYPE_ETHERNET)
        assert seg is None and note.kind == "ip-fragment"
    # scapy reassembly of the fragments gives back the original datagram (the fragments are well formed)
    from scapy.layers.inet import defragment
    out = defragment([IP(f) for f in frags])
    assert scapy_raw(out[0])[20:] == pkt[20:]


def test_truncated_capture_is_marked():
    frame = build(V4, 10, 0, fr.ACK, b"A" * 100)
    seg, _ = parse_frame(1, 0, frame[:80], LINKTYPE_ETHERNET)
    assert seg.truncated and seg.tcp_csum_ok is None and seg.declared_len == 100 and len(seg.payload) == 26


def test_non_tcp_and_garbage_do_not_raise():
    rng = random.Random(9)
    for _ in range(3000):
        data = bytes(rng.randrange(256) for _ in range(rng.randrange(0, 120)))
        for lt in (LINKTYPE_ETHERNET, LINKTYPE_RAW, 12345):
            parse_frame(1, 0, data, lt)           # must not raise


def test_seqspace_unwrap():
    base = 0xFFFFFFF6
    assert seqspace.unwrap(0xFFFFFFF6, base, 0) == 0
    assert seqspace.unwrap(0, base, 0) == 10                       # just past the wrap
    assert seqspace.unwrap(0xFFFFFFF0, base, 0) == -6              # just before the stream
    # offsets beyond 4 GiB stay monotone when ref advances
    assert seqspace.unwrap(7, base, 2**32 + 3) == 2**32 + 17
    assert seqspace.lt(0xFFFFFFFF, 1) and not seqspace.lt(1, 0xFFFFFFFF)


def test_pcap_roundtrip_both_resolutions_and_big_endian(tmp_path):
    recs = [(1_700_000_000_123_456_000, b"\x01\x02\x03"), (1_700_000_001_000_000_000, b"\xff" * 70)]
    for nano in (False, True):
        p = str(tmp_path / ("n%d.pcap" % nano))
        write_pcap(p, recs, LINKTYPE_ETHERNET, nano=nano)
        hdr, got = read_pcap(p)
        assert hdr.nano == nano and [r.data for r in got] == [r[1] for r in recs]
        assert got[0].ts_ns == (recs[0][0] if nano else recs[0][0] // 1000 * 1000)
    # hand-built big-endian file
    be = struct.pack(">IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1) + struct.pack(">IIII", 5, 6, 3, 3) + b"abc"
    p = str(tmp_path / "be.pcap")
    open(p, "wb").write(be)
    hdr, got = read_pcap(p)
    assert hdr.endian == ">" and got[0].data == b"abc" and got[0].ts_ns == 5_000_006_000


def test_pcap_errors(tmp_path):
    p = str(tmp_path / "bad.pcap")
    open(p, "wb").write(b"\x0a\x0d\x0d\x0a" + b"\0" * 40)
    with pytest.raises(PcapError):
        read_pcap(p)
    open(p, "wb").write(b"nope")
    with pytest.raises(PcapError):
        read_pcap(p)
    write_pcap(p, [(0, b"abcdef")])
    data = open(p, "rb").read()
    open(p, "wb").write(data[:-2])
    with pytest.raises(PcapError):
        read_pcap(p)
