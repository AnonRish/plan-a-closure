"""Ground truth: the live Linux TCP stack.  Needs root and /dev/net/tun (skipped otherwise); the recorded
observations in corpus/kernel_observed.json are also checked without a kernel."""
import json

import pytest

from packet_forge import corpus as C
from packet_forge import kernel_replay as kr
from packet_forge.corpus import all_cases, expected_for_case, get_case

STREAM = C.STREAM


def test_recorded_observations_vs_model(kernel_recorded):
    """No kernel needed: the recorded kernel bytes agree with the `linux` model except where documented."""
    cases = kernel_recorded["cases"]
    assert len(cases) == sum(c.handshake for c in all_cases())
    unexplained = [k for k, v in cases.items() if not v["linux_model_matches"] and k not in kr.KNOWN_DEVIATIONS]
    assert unexplained == []
    for k in kr.KNOWN_DEVIATIONS:
        assert not cases[k]["linux_model_matches"], "documented deviation %s no longer deviates" % k


def test_recorded_semantics(kernel_recorded):
    obs = {k: bytes.fromhex(v["observed_hex"]) for k, v in kernel_recorded["cases"].items()}
    assert obs["ins-bad-checksum-decoy"] == STREAM[:10] + b"R" * 10            # bad-checksum segment discarded
    assert obs["ins-bad-checksum-fills-hole"] == STREAM[:10]                    # ...so the stream stalls at the hole
    assert obs["anom-syn-data"] == b"REALDATA!!"                                # SYN payload ignored
    assert obs["anom-ip-fragment"] == STREAM[:40]                               # kernel reassembles IP fragments
    assert obs["ok-wrap-out-of-order"] == b"0123456789WORLD"
    assert obs["ov-conflicting-retransmit"] == b"AAAA"
    assert obs["ov-same-range-ooo-qp"] == STREAM[:10] + b"Q" * 10              # buffered: first arrival wins (Q came first)
    assert obs["ov-same-range-inorder"] == STREAM[:10] + b"P" * 10             # delivered data is never rewritten


def test_recorded_statistics(kernel_recorded):
    fz = kernel_recorded["fuzz"]
    n = fz["scenarios"]
    assert n >= 1000
    agree = fz["agree"]
    assert agree["linux"] / n > 0.99
    assert agree["linux"] > agree["lowseq"] > agree["first"] > agree["last"]
    perm = kernel_recorded["permutations"]
    assert perm["model_matches"] / perm["replayed"] > 0.98


def test_live_corpus_matches_recording(kernel_bench, kernel_recorded):
    cases = [c for c in all_cases() if c.handshake]
    res = kr.kernel_verify(cases, kernel_bench)
    same_kernel = kernel_bench.kernel == kernel_recorded["kernel"]
    for cid, r in res.items():
        assert r["handshake_ok"], cid
        if cid in kr.KNOWN_DEVIATIONS:
            assert not r["linux_model_matches"], cid
        else:
            assert r["linux_model_matches"], (cid, r["observed_hex"], r["expected_linux_hex"])
        if same_kernel:
            assert r["observed_hex"] == kernel_recorded["cases"][cid]["observed_hex"], cid


def test_live_fuzz_agreement(kernel_bench):
    fz = kr.kernel_fuzz(300, 777, kernel_bench)
    a, n = fz["agree"], fz["scenarios"]
    assert a["linux"] / n >= 0.98
    assert a["linux"] > a["lowseq"] > a["first"] and a["linux"] > a["last"]


def test_live_kernel_ignores_what_a_tap_must_ignore(kernel_bench):
    obs = kernel_bench.run_case(get_case("anom-syn-data"))
    assert obs.data == b"REALDATA!!"
    obs = kernel_bench.run_case(get_case("ins-bad-checksum-fills-hole"))
    assert obs.data == STREAM[:10]


@pytest.mark.parametrize("case_id", ["ov-tail-ooo-pq", "ov-head-ooo-qp", "ov-same-start-longer-ooo-qp",
                                     "ov-covering-ooo-pq", "ov-contained-inorder", "ov-aba-ooo"])
def test_live_permutations_of_core_geometries(kernel_bench, case_id):
    ok = n = 0
    for c in C.permutations(get_case(case_id)):
        obs = kernel_bench.run_case(c)
        n += 1
        ok += bytes.fromhex(expected_for_case(c)["streams"]["linux"]["hex"]) == obs.data
    assert ok == n, "%s: model reproduces %d/%d arrival orders" % (case_id, ok, n)
