"""Corpus: pipeline (pcap -> parser -> reassembler) vs expectations derived straight from the abstract
events by the per-byte oracle; plus hand-computed expectations that do not use the oracle at all."""
import json
import os

import pytest

from packet_forge import corpus as C
from packet_forge.analyze import analyze_pcap, analyze_segments
from packet_forge.cli import main
from packet_forge.corpus import STREAM, all_cases, case_addressing, case_frames, expected_for_case, get_case
from packet_forge.parse import parse_frame
from packet_forge.pcap import LINKTYPE_ETHERNET, LINKTYPE_RAW, write_pcap

F10 = STREAM[:10]


def pipeline(case, idx=0, ipv6=False, vlans=(), linktype=LINKTYPE_ETHERNET, tmp=None, nano=False):
    addr = case_addressing(idx, ipv6)
    fr_ = case_frames(case, addr, vlans, linktype)
    path = os.path.join(str(tmp), "%s.pcap" % case.id.replace("~", "_"))
    write_pcap(path, fr_, linktype, nano=nano)
    rep = analyze_pcap(path, include_hex=True)
    flow = "%s:%d" % (addr.client_ip if ":" not in addr.client_ip else "[%s]" % addr.client_ip, addr.client_port)
    d = next(x for x in rep.directions if x.flow.startswith(flow + ">"))
    return rep, d


def check_against_expected(case, rep, d):
    exp = expected_for_case(case)
    assert [[c.start, c.end] for c in d.conflicts] == exp["conflict_ranges"], case.id
    assert {k: v.hex for k, v in d.streams.items()} == {k: v["hex"] for k, v in exp["streams"].items()}, case.id
    assert {k: v.complete for k, v in d.streams.items()} == {k: v["complete"] for k, v in exp["streams"].items()}
    assert set(d.kinds()) | {n.kind for n in rep.frame_notes} == set(exp["anomalies"]), case.id
    assert d.policy_divergent == exp["policy_divergent"], case.id
    assert rep.failing() == exp["ambiguous"], case.id


def test_case_catalogue_is_sane():
    cases = all_cases()
    assert len(cases) >= 55
    assert len({c.id for c in cases}) == len(cases)
    for c in cases:
        assert c.description and c.title and c.category in ("benign", "overlap", "insertion", "anomaly")
    cats = {c.category for c in cases}
    assert cats == {"benign", "overlap", "insertion", "anomaly"}


def test_every_ambiguous_case_has_a_reason():
    for c in all_cases():
        exp = expected_for_case(c)
        if c.category == "benign":
            assert not exp["ambiguous"] and not exp["conflict_ranges"], c.id
        if c.category == "overlap":
            assert exp["conflict_ranges"], c.id          # an overlap case that conflicts on no byte is a bug


VARIANTS = {
    "ipv4": {}, "ipv6": {"ipv6": True}, "vlan": {"vlans": (100,)}, "qinq": {"vlans": (100, 200)},
    "raw": {"linktype": LINKTYPE_RAW}, "nano": {"nano": True},
}


@pytest.mark.parametrize("variant", sorted(VARIANTS))
def test_pipeline_matches_oracle_for_every_case(variant, tmp_path):
    kw = VARIANTS[variant]
    n = 0
    for i, c in enumerate(all_cases()):
        if kw.get("ipv6") and any(s.frag for s in c.segs()):
            continue
        rep, d = pipeline(c, i, tmp=tmp_path, **kw)
        check_against_expected(c, rep, d)
        n += 1
    assert n >= 55


def test_pipeline_matches_oracle_for_every_arrival_order():
    """All arrival orders of every case with up to five segments, in memory (no files)."""
    checked = 0
    for base in all_cases():
        if any(s.syn or s.frag for s in base.segs()):
            continue                      # SYN payload always travels first; fragments are covered above
        for c in C.permutations(base):
            frames_ = case_frames(c, case_addressing(3))
            segs, notes = [], []
            for n, (ts, data) in enumerate(frames_, 1):
                sg, nt = parse_frame(n, ts, data, LINKTYPE_ETHERNET)
                segs.append(sg) if sg else notes.append(nt)
            rep = analyze_segments(segs, notes, len(frames_), include_hex=True)
            d = next(x for x in rep.directions if x.flow.startswith("192.0.2.1:40003>"))
            check_against_expected(c, rep, d)
            checked += 1
    assert checked > 450


def test_checked_in_corpus_is_regenerated_byte_for_byte(corpus_dir):
    assert main(["verify-corpus", corpus_dir]) == 0


def test_manifest_is_valid_json_with_all_cases(manifest):
    assert [e["id"] for e in manifest["cases"]] == [c.id for c in all_cases()]
    for e in manifest["cases"]:
        assert os.path.exists(os.path.join(os.path.dirname(__file__), "..", "corpus", e["pcap"]))


# ------------------------------------------------------------------------------------------------------
# Hand-computed expectations (no oracle involved): the numbers below were worked out on paper
# ------------------------------------------------------------------------------------------------------

def S(case_id):
    return expected_for_case(get_case(case_id))


def streams(exp):
    return {k: bytes.fromhex(v["hex"]) for k, v in exp["streams"].items()}


def test_hand_ok_cases():
    for cid, want in [("ok-in-order", STREAM[:30]), ("ok-reordered", STREAM[:30]), ("ok-hole-then-fill", STREAM[:30]),
                      ("ok-duplicate-retransmit", STREAM[:30]), ("ok-tiny-segments", STREAM[:8]),
                      ("ok-wrap-in-order", STREAM[:36]), ("ok-wrap-out-of-order", b"0123456789WORLD"),
                      ("ok-resegmented-retransmit", STREAM[:35])]:
        e = S(cid)
        assert e["conflict_ranges"] == [] and not e["ambiguous"], cid
        assert set(streams(e).values()) == {want}, cid


def test_hand_conflicting_retransmit():
    e = S("ov-conflicting-retransmit")
    assert e["conflict_ranges"] == [[0, 4]]
    assert streams(e) == {"first": b"AAAA", "last": b"BBBB", "lowseq": b"AAAA", "linux": b"AAAA"}


def test_hand_tail_overlap_after_delivery():
    # F=[0,10) P=[10,20) delivered and ACKed, then Q=[15,25)
    e = S("ov-tail-inorder")
    assert e["conflict_ranges"] == [[15, 20]]
    s = streams(e)
    assert s["first"] == F10 + b"P" * 10 + b"Q" * 5
    assert s["last"] == F10 + b"P" * 5 + b"Q" * 10
    assert s["lowseq"] == s["first"] == s["linux"]


def test_hand_head_overlap_buffered():
    # P=[10,20) then Q=[5,15) then the hole [0,5) is filled
    e = S("ov-head-ooo-pq")
    assert e["conflict_ranges"] == [[10, 15]]
    s = streams(e)
    assert s["first"] == b"01234" + b"Q" * 5 + b"P" * 10
    assert s["last"] == b"01234" + b"Q" * 10 + b"P" * 5
    assert s["lowseq"] == s["last"] == s["linux"]


def test_hand_same_start_tie_breaks():
    longer, shorter = streams(S("ov-same-start-longer-ooo-pq")), streams(S("ov-same-start-shorter-ooo-pq"))
    assert longer["first"] == F10 + b"P" * 10 + b"Q" * 5 and longer["lowseq"] == longer["first"]
    assert longer["last"] == F10 + b"Q" * 15 and longer["linux"] == longer["last"]      # linux: longer claim wins
    assert shorter["first"] == F10 + b"P" * 10 and shorter["linux"] == shorter["first"]
    assert shorter["last"] == F10 + b"Q" * 5 + b"P" * 5


def test_hand_aba_is_ambiguous_although_first_equals_last():
    e = S("ov-aba-ooo")
    assert e["conflict_ranges"] == [[10, 20]] and e["ambiguous"]
    assert not e["policy_divergent"]
    assert set(streams(e).values()) == {F10 + b"A" * 10}


def test_hand_insertion_and_anomaly_cases():
    e = S("ins-bad-checksum-decoy")
    assert e["conflict_ranges"] == [] and e["anomalies"] == ["bad-checksum"] and e["ambiguous"]
    assert set(streams(e).values()) == {F10 + b"R" * 10}
    e = S("ins-bad-checksum-fills-hole")
    assert set(streams(e).values()) == {F10} and not e["streams"]["first"]["complete"]
    e = S("anom-syn-data")
    assert e["conflict_ranges"] == [[0, 8]]          # SYNDATA!!! vs REALDATA!!: the last two bytes agree
    assert streams(e) == {"first": b"SYNDATA!!!", "last": b"REALDATA!!", "lowseq": b"SYNDATA!!!", "linux": b"REALDATA!!"}
    e = S("anom-data-after-fin")
    assert e["conflict_ranges"] == [] and set(streams(e).values()) == {F10} and e["anomalies"] == ["data-after-fin"]
    e = S("anom-before-isn")
    assert set(streams(e).values()) == {STREAM[:16]}
    e = S("anom-ip-fragment")
    assert set(streams(e).values()) == {F10} and not e["streams"]["first"]["complete"]
    e = S("ov-keepalive-garbage-byte")
    assert e["conflict_ranges"] == [[9, 10]]
    assert streams(e)["last"] == STREAM[:9] + b"\x00" and streams(e)["first"] == F10


def test_ack_annotation(tmp_path):
    _, d = pipeline(get_case("ov-same-range-inorder"), 7, tmp=tmp_path)
    assert d.conflicts[0].late_after_ack == [7]          # frames 1-3 handshake, 4 prefix, 5 P, 6 ACK, 7 Q
    _, d = pipeline(get_case("ov-before-ack"), 8, tmp=tmp_path)
    assert d.conflicts[0].late_after_ack == []
    _, d = pipeline(get_case("ov-keepalive-garbage-byte"), 9, tmp=tmp_path)
    assert "keep-alive" in d.conflicts[0].hint


def test_conflict_report_names_every_claim(tmp_path):
    _, d = pipeline(get_case("ov-chain-three-ooo"), 4, tmp=tmp_path)
    assert [(c.start, c.end) for c in d.conflicts] == [(15, 25)]
    assert len(d.conflicts[0].claims) == 3 and d.conflicts[0].distinct_values >= 2


def test_ipv6_manifest_and_generation(tmp_path):
    m = C.write_corpus(str(tmp_path), ipv6=True)
    assert all(e["client"].startswith("2001:db8::1:") for e in m["cases"])
    assert "anom-ip-fragment" not in [e["id"] for e in m["cases"]]


def test_conflicts_do_not_depend_on_which_policy_is_listed_first(corpus_dir):
    """`linux` ignores SYN payload; if conflicts were taken from the first listed policy they would vanish."""
    p = os.path.join(corpus_dir, "anom-syn-data.pcap")
    for order in (("linux", "first"), ("first", "linux"), ("linux",), ("last", "lowseq")):
        rep = analyze_pcap(p, policies=order)
        assert [(c.start, c.end) for c in rep.directions[0].conflicts] == [(0, 8)], order
