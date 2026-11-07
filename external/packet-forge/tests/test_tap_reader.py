"""Characterisation of the tap_reader crate (pinned revision in adapters/tap_reader/Cargo.toml) on the corpus.

These tests assert what the crate DOES at the pinned revision, with the live-kernel observations as the
reference for what an endpoint receives.  If the crate is fixed, tests in the 'known failures' set start
failing: that is the signal to update docs/FINDINGS-tap_reader.md and the set below."""
import os

import pytest

from packet_forge import tap_reader as tr
from packet_forge.corpus import STREAM

pytestmark = pytest.mark.rust
ADAPTER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "adapters", "tap_reader")

# Cases where tap_reader (padding trimmed) does not deliver what the Linux receiver delivers, grouped by cause.
WRAP = {"ok-wrap-out-of-order", "ov-wrap-conflict-ooo"}
TAIL_LOST = {"ok-resegmented-retransmit", "ov-tail-inorder", "ov-covering-inorder", "ov-same-start-longer-inorder",
             "ov-one-byte-tail-inorder"}
STUCK_PENDING = {"ov-tail-ooo-pq", "ov-tail-ooo-qp", "ov-one-byte-tail-ooo-pq", "ov-one-byte-tail-ooo-qp",
                 "ov-head-ooo-pq", "ov-head-ooo-qp", "ov-one-byte-head-ooo-pq", "ov-one-byte-head-ooo-qp"}
SAME_SEQ_OVERWRITE = {"ov-same-range-ooo-pq", "ov-same-range-ooo-qp", "ov-same-start-shorter-ooo-pq",
                      "ov-same-start-longer-ooo-qp"}
NO_PROTOCOL_AWARENESS = {"anom-before-isn", "anom-conflicting-fin", "anom-data-after-fin", "anom-ip-fragment",
                         "ins-bad-checksum-fills-hole"}
KNOWN_FAILURES = WRAP | TAIL_LOST | STUCK_PENDING | SAME_SEQ_OVERWRITE | NO_PROTOCOL_AWARENESS


@pytest.fixture(scope="module")
def adapter():
    if not tr.find_cargo():
        pytest.skip("no Rust toolchain")
    return tr.build_adapter(ADAPTER)


@pytest.fixture(scope="module")
def results(adapter, manifest, corpus_dir):
    return {m: tr.run_adapter(adapter, manifest, corpus_dir, m) for m in ("asis", "trim")}


def test_padding_is_delivered_as_payload_as_is(results):
    # frame::parse slices the payload from the frame length: the 6 pad bytes of the handshake ACK arrive as data
    for cid in ("ok-in-order", "ok-reordered", "ov-tail-inorder"):
        assert results["asis"][cid]["stream"].startswith(b"\x00" * 6), cid
    assert results["asis"]["ok-tiny-segments"]["stream"] != STREAM[:8]


def test_failure_set_is_exactly_the_documented_one(results, kernel_recorded):
    kernel = kernel_recorded["cases"]
    differs = {k for k in kernel if results["trim"][k]["stream"].hex() != kernel[k]["observed_hex"]}
    assert differs == KNOWN_FAILURES, (sorted(differs - KNOWN_FAILURES), sorted(KNOWN_FAILURES - differs))


def test_lead_1_wraparound_drops_the_segment_past_the_wrap(results):
    r = results["trim"]["ok-wrap-out-of-order"]
    assert r["stream"] == b"0123456789"            # "WORLD" (seq 0, just past the wrap) was discarded as a duplicate
    assert r["duplicates_dropped"] == 1 and not r["gap_open"]


def test_lead_2_conflicting_retransmission_gives_no_signal(results):
    r = results["trim"]["ov-conflicting-retransmit"]
    assert r["stream"] == b"AAAA" and r["duplicates_dropped"] == 1       # indistinguishable from an honest duplicate
    honest = results["trim"]["ok-duplicate-retransmit"]
    assert honest["duplicates_dropped"] == 1


def test_partial_overlap_loses_the_new_tail(results):
    assert results["trim"]["ok-resegmented-retransmit"]["stream"] == STREAM[:30]     # a correct stream is 35 bytes
    assert results["trim"]["ov-tail-inorder"]["stream"] == STREAM[:10] + b"P" * 10    # Q's last 5 bytes are lost


def test_pending_segment_overlapping_delivered_data_never_drains(results):
    r = results["trim"]["ov-tail-ooo-pq"]
    assert r["gap_open"] and r["stream"] == STREAM[:10] + b"P" * 10


def test_same_start_overwrites_pending_segment_even_if_shorter(results):
    r = results["trim"]["ov-same-start-shorter-ooo-pq"]
    assert r["stream"] == STREAM[:10] + b"Q" * 5        # the 5-byte Q replaced the 10-byte P that arrived first


def test_it_cannot_flag_anything(results, manifest):
    from packet_forge.taps import score
    sc = score(tr.as_verdicts(results["trim"]), manifest)
    ambiguous = {e["id"] for e in manifest["cases"] if e["expected"]["ambiguous"]}
    assert {k for k, r in sc["cases"].items() if not r["detection"]} == ambiguous
