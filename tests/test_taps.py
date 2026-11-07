"""Hashing taps (SITREP: new tap types and bandwidth limits) and keyed canaries (SITREP: tap installation and monitoring)."""
import json

import numpy as np

from closure import taphash as H
from closure import tapwatch as W
from closure.cli import main
from closure.traffic import Pkt, iter_pcap, read_pcap, write_pcap


def _capture(path, n=300, size=1000, flip=None, seed=0):
    rng = np.random.default_rng(seed)
    pays = [bytes(rng.integers(0, 256, size, dtype=np.uint8)) for _ in range(n)]
    if flip is not None:
        b = bytearray(pays[flip[0]])
        b[flip[1]] ^= 1
        pays[flip[0]] = bytes(b)
    pk = [Pkt(1000 + i * 0.01, "10.0.0.1", "10.0.0.2", 5000, 443, 6, size) for i in range(n)]
    write_pcap(path, pk, pays)
    return pays


def test_payload_mode_returns_the_bytes_and_the_default_mode_is_unchanged(tmp_path):
    f = tmp_path / "a.pcap"
    pays = _capture(f, n=5, size=40)
    pairs = list(iter_pcap(f, with_payload=True))
    assert [p for p, _ in pairs] == read_pcap(f) and [b for _, b in pairs] == pays


def test_one_flipped_byte_is_located_to_its_group(tmp_path):
    _capture(tmp_path / "a.pcap")
    _capture(tmp_path / "b.pcap", flip=(150, 7))
    ca, cb = H.commit_pcap(tmp_path / "a.pcap", 4096), H.commit_pcap(tmp_path / "b.pcap", 4096)
    (flow,) = ca
    assert len(ca[flow]["digests"]) == -(-300 * 1000 // 4096) and ca[flow]["payload_bytes"] == ca[flow]["declared_bytes"]
    assert H.mismatched_groups(ca[flow]["digests"], cb[flow]["digests"]) == [(150 * 1000 + 7) // 4096]
    assert ca[flow]["root"] != cb[flow]["root"]


def test_merkle_proofs_open_one_group_and_bind_its_position():
    data = bytes(range(256)) * 50
    leaves = H.group_digests(data, 1000)
    root = H.merkle_root(leaves)
    for i in (0, 5, len(leaves) - 1):
        chunk = data[i * 1000:(i + 1) * 1000]
        assert H.verify_proof(i, chunk, H.merkle_proof(leaves, i), root)
        assert not H.verify_proof(i, chunk[:-1] + b"x", H.merkle_proof(leaves, i), root)
    assert not H.verify_proof(1, data[:1000], H.merkle_proof(leaves, 0), root)          # right bytes, wrong position
    assert H.group_digests([data[:7], data[7:]], 1000) == leaves                          # chunking does not matter


def test_challenges_come_from_the_nonce_and_the_detection_math_is_exact():
    root = H.merkle_root(H.group_digests(b"x" * 10000, 100))
    a, b = H.challenge_indices(b"n1", root, 100, 10), H.challenge_indices(b"n2", root, 100, 10)
    assert len(set(a)) == 10 and a != b and a == H.challenge_indices(b"n1", root, 100, 10)
    assert H.detection_probability(100, 0, 10) == 0.0 and H.detection_probability(100, 95, 10) == 1.0
    assert abs(H.detection_probability(100, 1, 10) - 0.10) < 1e-12
    k = H.samples_needed(0.01, 0.95)
    assert 1 - 0.99 ** k >= 0.95 > 1 - 0.99 ** (k - 1)
    assert H.bandwidth_reduction(65536) == 2048


def test_tap_commit_and_compare_cli(tmp_path, capsys):
    _capture(tmp_path / "a.pcap")
    _capture(tmp_path / "b.pcap", flip=(10, 0))
    assert main(["tap-commit", str(tmp_path / "a.pcap"), "--group-bytes", "4096", "--out", str(tmp_path / "tap.json")]) == 0
    assert main(["tap-commit", str(tmp_path / "a.pcap"), "--group-bytes", "4096", "--out", str(tmp_path / "same.json")]) == 0
    assert main(["tap-commit", str(tmp_path / "b.pcap"), "--group-bytes", "4096", "--out", str(tmp_path / "prov.json")]) == 0
    capsys.readouterr()
    assert main(["tap-compare", str(tmp_path / "tap.json"), str(tmp_path / "same.json")]) == 0
    capsys.readouterr()
    assert main(["tap-compare", str(tmp_path / "tap.json"), str(tmp_path / "prov.json")]) == 1
    assert json.loads(capsys.readouterr().out)["detail"]
    snap = tmp_path / "snap.pcap"
    write_pcap(snap, [Pkt(1.0, "10.0.0.1", "10.0.0.2", 1, 2, 17, 100)])                 # payload cut by the snaplen
    assert main(["tap-commit", str(snap), "--out", str(tmp_path / "s.json")]) == 0
    assert "snaplen" in json.loads((tmp_path / "s.json").read_text())["warning"]


def _canaries(path, key, sched, keep=None, delay=0.001):
    keep = len(sched) if keep is None else keep
    pk = [Pkt(t + delay, "10.0.0.9", "10.0.0.2", 9, 9, 17, W.PAYLOAD_BYTES) for _, t in sched[:keep]]
    write_pcap(path, pk, [W.payload(key, s) for s, _ in sched[:keep]])


def test_canaries_confirm_a_present_tap_and_a_removed_one_is_caught_within_the_bound(tmp_path):
    key = b"v" * 32
    sched = W.schedule(key, 2000.0, 10.0, 5.0)
    _canaries(tmp_path / "ok.pcap", key, sched)
    ok = W.check(iter_pcap(tmp_path / "ok.pcap", with_payload=True), key, sched)
    assert ok["pass"] and ok["seen"] == 50 and ok["longest_unconfirmed_s"] <= W.detection_bound_s(5.0)
    _canaries(tmp_path / "cut.pcap", key, sched, keep=20)                    # tap removed after the 20th canary
    cut = W.check(iter_pcap(tmp_path / "cut.pcap", with_payload=True), key, sched)
    assert not cut["pass"] and cut["missing"] == list(range(20, 50))
    _canaries(tmp_path / "late.pcap", key, sched, delay=0.5)                 # replayed from a recording, 0.5 s late
    assert not W.check(iter_pcap(tmp_path / "late.pcap", with_payload=True), key, sched)["pass"]


def test_canary_times_and_payloads_cannot_be_predicted_without_the_key():
    a, b = W.schedule(b"a" * 32, 0.0, 5.0, 10.0), W.schedule(b"b" * 32, 0.0, 5.0, 10.0)
    assert [t for _, t in a] != [t for _, t in b]
    assert all(s * 0.1 <= t <= (s + 1) * 0.1 for s, t in a)                  # one canary inside each interval
    assert W.payload(b"a" * 32, 3) != W.payload(b"b" * 32, 3) and len(W.payload(b"a" * 32, 3)) == W.PAYLOAD_BYTES
