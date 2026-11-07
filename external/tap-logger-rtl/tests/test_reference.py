"""The software reference and verifier: known answers, an independent hash implementation, tamper detection."""
import os
import random
import re
import struct
import subprocess

import pytest
from hypothesis import given, settings, strategies as st

from tlref.chain import Record, build_chain, entry_digest, verify_chain
from tlref.cli import main
from tlref.pcap import read_pcap, write_pcap

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRAMES = [bytes(range(60)), b"\xff" * 64, b"hello"]
TS = [1, 0x0123456789ABCDEF, 2**64 - 1]


def sha256sum(data: bytes) -> str:
    """coreutils' own SHA-256: independent of Python's hashlib / OpenSSL."""
    return subprocess.run(["sha256sum"], input=data, capture_output=True, check=True).stdout.split()[0].decode()


def test_entry_digest_matches_coreutils_for_hand_built_messages():
    rng = random.Random(11)
    prev = bytes(32)
    for i in range(40):
        frame = bytes(rng.randrange(256) for _ in range(rng.randrange(1, 200)))
        ts = rng.getrandbits(64)
        for with_ts in (True, False):
            msg = prev + struct.pack(">Q", i) + (struct.pack(">Q", ts) if with_ts else b"") + frame
            assert entry_digest(prev, i, frame, ts if with_ts else None).hex() == sha256sum(msg)
        prev = entry_digest(prev, i, frame, ts)


def test_format_document_worked_example_is_real():
    text = open(os.path.join(ROOT, "docs", "FORMAT.md")).read()
    block = text.split("<!-- vectors -->")[1].split("<!-- /vectors -->")[0]
    doc = {(m.group(2), int(m.group(1))): m.group(3)
           for m in re.finditer(r"^D(\d) \((timestamps|no timestamps)\) = ([0-9a-f]{64})$", block, re.M)}
    assert len(doc) == 6
    for label, ts in (("timestamps", TS), ("no timestamps", None)):
        for i, r in enumerate(build_chain(FRAMES, ts)):
            assert doc[(label, i)] == r.digest.hex()


def test_chain_binds_genesis_index_and_timestamp():
    base = build_chain(FRAMES, TS)
    assert build_chain(FRAMES, TS, genesis=bytes([1]) + bytes(31))[0].digest != base[0].digest
    assert build_chain(FRAMES, TS, start_index=5)[0].digest != base[0].digest
    assert build_chain(FRAMES, [2] + TS[1:])[0].digest != base[0].digest
    assert build_chain(FRAMES, None)[0].digest != base[0].digest


def test_frames_must_not_be_empty():
    with pytest.raises(ValueError):
        build_chain([b""])


def make(n=8, seed=3):
    rng = random.Random(seed)
    frames = [bytes(rng.randrange(256) for _ in range(rng.randrange(1, 90))) for _ in range(n)]
    ts = [rng.getrandbits(64) for _ in range(n)]
    return frames, ts, build_chain(frames, ts)


def test_untouched_log_verifies_and_head_check_passes():
    frames, _, recs = make()
    assert verify_chain(frames, recs, True).ok
    assert verify_chain(frames, recs, True, expected_head=recs[-1].digest).ok


@pytest.mark.parametrize("k", [0, 3, 7])
def test_altered_frame_is_found_at_its_position(k):
    frames, _, recs = make()
    bad = list(frames)
    bad[k] = bytes([bad[k][0] ^ 1]) + bad[k][1:]
    v = verify_chain(bad, recs, True)
    assert (v.ok, v.first_bad) == (False, k)


def test_swapped_frames_dropped_frame_and_inserted_frame():
    frames, _, recs = make()
    sw = list(frames); sw[2], sw[3] = sw[3], sw[2]
    assert verify_chain(sw, recs, True).first_bad == 2
    dropped = frames[:4] + frames[5:]
    v = verify_chain(dropped, recs, True)
    assert not v.ok and v.first_bad == 4
    inserted = frames[:4] + [b"x"] + frames[4:]
    v = verify_chain(inserted, recs, True)
    assert not v.ok and v.first_bad == 4


def test_tail_truncation_needs_the_published_head():
    frames, _, recs = make()
    assert verify_chain(frames[:5], recs[:5], True).ok                      # a perfectly valid shorter chain
    v = verify_chain(frames[:5], recs[:5], True, expected_head=recs[-1].digest)
    assert not v.ok and "head" in v.reason


def test_record_tampering_is_found():
    frames, _, recs = make()
    for field, val, frag in (("digest", bytes(32), "digest"), ("length", 999, "length"), ("index", 42, "index")):
        r = recs[3]
        bad = list(recs)
        bad[3] = Record(val if field == "index" else r.index, val if field == "length" else r.length, r.ts,
                        val if field == "digest" else r.digest)
        v = verify_chain(frames, bad, True)
        assert (v.ok, v.first_bad) == (False, 3) and frag in v.reason


def test_timestamp_is_authenticated_only_when_hashed():
    frames, ts, recs = make()
    bad = list(recs)
    bad[2] = Record(recs[2].index, recs[2].length, recs[2].ts ^ 1, recs[2].digest)
    assert verify_chain(frames, bad, True).first_bad == 2
    nots = build_chain(frames, None)
    forged = list(nots)
    forged[2] = Record(nots[2].index, nots[2].length, 12345, nots[2].digest)
    assert verify_chain(frames, forged, False).ok            # documented: TS_EN=0 leaves the timestamp unauthenticated


def test_verification_can_resume_from_a_checkpoint():
    frames, _, recs = make()
    assert verify_chain(frames[4:], recs[4:], True, genesis=recs[3].digest, start_index=4).ok
    assert not verify_chain(frames[4:], recs[4:], True, genesis=bytes(32), start_index=4).ok


@settings(max_examples=150, deadline=None)
@given(st.lists(st.binary(min_size=1, max_size=60), min_size=1, max_size=8), st.data())
def test_any_single_bit_flip_is_detected_at_its_frame(frames, data):
    recs = build_chain(frames, list(range(len(frames))))
    k = data.draw(st.integers(0, len(frames) - 1))
    j = data.draw(st.integers(0, len(frames[k]) * 8 - 1))
    bad = list(frames)
    b = bytearray(bad[k]); b[j // 8] ^= 1 << (j % 8); bad[k] = bytes(b)
    v = verify_chain(bad, recs, True)
    assert not v.ok and v.first_bad == k


# ----------------------------------------------------------------------------- CLI --------------------------

def test_cli_round_trip_and_tamper(tmp_path, capsys):
    cap = str(tmp_path / "c.pcap")
    write_pcap(cap, [(1_700_000_000_000_000_000 + i, bytes([i]) * (60 + i)) for i in range(6)])
    log = str(tmp_path / "log.jsonl")
    assert main(["make-log", cap]) == 0
    open(log, "w").write(capsys.readouterr().out)
    assert main(["verify", cap, log]) == 0
    head = open(log).read().splitlines()[-1]
    import json
    head_hex = json.loads(head)["digest"]
    assert main(["verify", cap, log, "--head", head_hex]) == 0
    # flip one byte of frame 3 in the capture
    recs = read_pcap(cap)
    t, d = recs[3]
    recs[3] = (t, d[:10] + bytes([d[10] ^ 0xFF]) + d[11:])
    bad = str(tmp_path / "bad.pcap")
    write_pcap(bad, recs)
    capsys.readouterr()
    assert main(["verify", bad, log]) == 1
    assert "TAMPERED at record 3" in capsys.readouterr().out
    assert main(["verify", cap, log, "--head", "00" * 32]) == 1
