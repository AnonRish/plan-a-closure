"""Reference/flawed taps and scoring, the normaliser, and the command line."""
import json
import os

import pytest
from scapy.all import Ether, TCP, raw as scapy_raw

from packet_forge import corpus as C
from packet_forge.analyze import analyze_pcap, parse_capture
from packet_forge.cli import main
from packet_forge.normalize import normalize_pcap
from packet_forge.pcap import LINKTYPE_RAW
from packet_forge.taps import TAPS, TapVerdict, run_tap, score


# ---------------------------------------------------------------- taps -----------------------------

def card(name, manifest, corpus_dir, kernel=None):
    return score(run_tap(TAPS[name], manifest, corpus_dir), manifest, kernel)


def failing(sc):
    return {k for k, r in sc["cases"].items() if not r["pass"]}


def test_reference_tap_passes_everything(manifest, corpus_dir):
    sc = card("reference", manifest, corpus_dir)
    assert sc["passed"] == sc["total"] == len(manifest["cases"])


def test_every_flawed_tap_is_caught(manifest, corpus_dir):
    ambiguous = {e["id"] for e in manifest["cases"] if e["expected"]["ambiguous"]}
    for name in TAPS:
        if name == "reference":
            continue
        assert failing(card(name, manifest, corpus_dir)), "%s passes the whole corpus" % name
    # specific, explainable failures
    assert failing(card("checksum-blind", manifest, corpus_dir)) == {"ins-bad-checksum-fills-hole"}
    assert failing(card("first-silent", manifest, corpus_dir)) == ambiguous       # silent taps cannot flag
    assert {"ok-reordered", "ok-wrap-out-of-order", "ok-resegmented-retransmit"} <= failing(
        card("naive-append", manifest, corpus_dir))


def test_linux_silent_tap_is_faithful_but_not_safe(manifest, corpus_dir, kernel_recorded):
    sc = card("linux-silent", manifest, corpus_dir, kernel_recorded["cases"])
    assert sc["fidelity_matches"] >= sc["fidelity_total"] - 2       # chain-of-three deviation + IP fragments
    assert failing(sc) == {e["id"] for e in manifest["cases"] if e["expected"]["ambiguous"]}


def test_scorer_handles_missing_and_external_results(manifest, corpus_dir):
    verdicts = run_tap(TAPS["reference"], manifest, corpus_dir)
    del verdicts["ok-in-order"]
    sc = score(verdicts, manifest)
    assert failing(sc) == {"ok-in-order"} and sc["cases"]["ok-in-order"]["missing"]
    verdicts["ok-in-order"] = TapVerdict(b"wrong", False)
    assert failing(score(verdicts, manifest)) == {"ok-in-order"}


# ------------------------------------------------------------ normaliser -----------------------------

@pytest.mark.parametrize("policy", ["first", "last", "lowseq"])
def test_normalised_capture_has_no_conflicts_and_one_stream(policy, tmp_path, manifest, corpus_dir):
    for e in manifest["cases"]:
        src, dst = os.path.join(corpus_dir, e["pcap"]), str(tmp_path / "n.pcap")
        normalize_pcap(src, dst, policy)
        before = analyze_pcap(src, policies=(policy,), include_hex=True)
        after = analyze_pcap(dst, policies=("first", "last", "lowseq"), include_hex=True)
        a = next(d for d in before.directions if d.flow.startswith(e["client"] + ">"))
        b = next(d for d in after.directions if d.flow.startswith(e["client"] + ">"))
        assert b.conflicts == [], e["id"]
        assert len({s.hex for s in b.streams.values()}) == 1, e["id"]
        assert b.streams["first"].hex == a.streams[policy].hex, e["id"]


def test_normaliser_rewrites_checksums_and_is_idempotent(tmp_path, corpus_dir):
    src = os.path.join(corpus_dir, "ov-covering-ooo-pq.pcap")
    once, twice = str(tmp_path / "1.pcap"), str(tmp_path / "2.pcap")
    st = normalize_pcap(src, once, "first")
    assert st.rewritten >= 1
    segs, _, _ = parse_capture(once)
    assert all(s.tcp_csum_ok and s.ip_csum_ok for s in segs)
    # scapy (independent) agrees every rewritten frame still carries a valid TCP checksum
    from packet_forge.pcap import read_pcap
    _, recs = read_pcap(once)
    checked = 0
    for rec in recs:
        e = Ether(rec.data)
        if TCP not in e:
            continue
        good = e[TCP].chksum
        del e[TCP].chksum
        assert Ether(scapy_raw(e))[TCP].chksum == good
        checked += 1
    assert checked >= 6
    normalize_pcap(once, twice, "first")
    assert open(once, "rb").read() == open(twice, "rb").read()


def test_normaliser_drops_bad_checksum_frames_and_refuses_linux(tmp_path, corpus_dir):
    src = os.path.join(corpus_dir, "ins-bad-checksum-decoy.pcap")
    st = normalize_pcap(src, str(tmp_path / "n.pcap"), "first")
    assert st.dropped_bad_checksum == 1 and st.frames_out == st.frames_in - 1
    with pytest.raises(ValueError):
        normalize_pcap(src, str(tmp_path / "x.pcap"), "linux")


def test_normaliser_on_ipv6_vlan_and_raw(tmp_path):
    for kw in ({"ipv6": True}, {"vlans": (5,)}, {"linktype": LINKTYPE_RAW}):
        d = tmp_path / ("v%d" % len(os.listdir(tmp_path)))
        C.write_corpus(str(d), **kw)
        out = str(d / "n.pcap")
        normalize_pcap(str(d / "ov-tail-ooo-pq.pcap"), out, "last")
        rep = analyze_pcap(out, include_hex=True)
        assert rep.conflict_count == 0 and not rep.failing()


# ---------------------------------------------------------------- CLI --------------------------------

def run(argv, capsys):
    rc = main(argv)
    out = capsys.readouterr()
    return rc, out.out, out.err


def test_cli_exit_codes_and_json(corpus_dir, capsys):
    rc, out, _ = run(["check", os.path.join(corpus_dir, "ok-reordered.pcap")], capsys)
    assert rc == 0 and "verdict: CLEAN" in out
    rc, out, _ = run(["check", os.path.join(corpus_dir, "ov-tail-inorder.pcap")], capsys)
    assert rc == 1 and "CONFLICT stream bytes [15,20)" in out and "late-after-ACK" in out
    rc, out, _ = run(["check", "--json", "--streams", os.path.join(corpus_dir, "ov-conflicting-retransmit.pcap")], capsys)
    j = json.loads(out)
    assert rc == 1 and j["directions"][0]["conflicts"][0]["start"] == 0
    assert j["directions"][0]["streams"]["last"]["hex"] == b"BBBB".hex()
    rc, _, err = run(["check", "/nonexistent.pcap"], capsys)
    assert rc == 2
    rc, _, err = run(["check", "--policies", "bogus", os.path.join(corpus_dir, "ok-in-order.pcap")], capsys)
    assert rc == 2 and "unknown policy" in err


def test_cli_fail_on_and_checksum_flags(corpus_dir, capsys):
    p = os.path.join(corpus_dir, "ins-bad-checksum-fills-hole.pcap")
    assert run(["check", p], capsys)[0] == 1
    assert run(["check", "--fail-on", "syn-data", p], capsys)[0] == 0       # anomaly demoted to informational
    rc, out, _ = run(["check", "--no-checksum", p], capsys)
    assert rc == 0 and "stream[first ]    30 B" in out                    # blind mode splices the decoy in


def test_cli_list_show_generate(tmp_path, capsys):
    rc, out, _ = run(["list"], capsys)
    assert rc == 0 and "ov-tail-inorder" in out
    rc, out, _ = run(["show", "ov-head-ooo-pq"], capsys)
    assert rc == 0 and "conflict ranges: [[10, 15]]" in out
    rc, out, _ = run(["generate", str(tmp_path / "g"), "--ipv6", "--nano"], capsys)
    assert rc == 0 and os.path.exists(tmp_path / "g" / "manifest.json")
    with open(tmp_path / "g" / "ok-in-order.pcap", "rb") as f:
        assert f.read(4) == b"\x4d\x3c\xb2\xa1"                                  # nanosecond magic, little endian


def test_cli_score_and_taps(tmp_path, manifest, corpus_dir, capsys):
    good = {k: {"stream_hex": v.stream.hex(), "flagged": v.flagged}
            for k, v in run_tap(TAPS["reference"], manifest, corpus_dir).items()}
    p = tmp_path / "r.json"
    p.write_text(json.dumps(good))
    rc, out, _ = run(["score", str(p), "--dir", corpus_dir], capsys)
    assert rc == 0 and "passed 59/59" in out
    good["ok-in-order"]["flagged"] = True
    p.write_text(json.dumps(good))
    rc, out, _ = run(["score", str(p), "--dir", corpus_dir], capsys)
    assert rc == 1 and "FAIL ok-in-order" in out
    rc, out, _ = run(["taps", "--dir", corpus_dir], capsys)
    assert rc == 0 and "reference" in out and "59/59" in out


def test_cli_normalize(tmp_path, corpus_dir, capsys):
    rc, out, _ = run(["normalize", os.path.join(corpus_dir, "ov-covering-ooo-pq.pcap"), str(tmp_path / "n.pcap")], capsys)
    assert rc == 0 and "rewritten" in out
