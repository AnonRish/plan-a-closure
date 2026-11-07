import hashlib
import json

import pytest

from closure.evidence import Chain
from closure.pause import registry as R
from closure.pause import whitelist as W

ARCH = {"layers": 32, "d_model": 4096, "heads": 32}
FRA, AMS = (50.1109, 8.6821), (52.3676, 4.9041)       # Frankfurt and Amsterdam, about 365 km apart


def test_manifest_hash_binds_architecture_and_weights():
    w = W.weights_digest([b"abc", b"def"])
    assert w == hashlib.sha256(b"abcdef").hexdigest()
    h = W.manifest_hash(ARCH, w)
    assert h == W.manifest_hash(dict(reversed(list(ARCH.items()))), w)          # canonical JSON: key order is irrelevant
    assert h != W.manifest_hash({**ARCH, "layers": 33}, w)
    assert h != W.manifest_hash(ARCH, W.weights_digest([b"abcdeg"]))


def test_whitelist_deadline_and_duplicates():
    wl = W.Whitelist(submission_deadline=100.0)
    wl.submit("m1", ARCH, "a" * 64, now=50.0)
    with pytest.raises(ValueError, match="deadline"):
        wl.submit("m2", ARCH, "b" * 64, now=101.0)                               # nothing new after the deadline
    with pytest.raises(ValueError, match="already"):
        wl.submit("m1", ARCH, "a" * 64, now=60.0)
    assert wl.counts() == {"pending": 1}


def test_verify_deployed_detects_changed_weights():
    wl, good = W.Whitelist(100.0), hashlib.sha256(b"w").hexdigest()
    wl.submit("m", ARCH, good, 1.0)
    assert wl.verify_deployed("m", good)["ok"]
    r = wl.verify_deployed("m", hashlib.sha256(b"w-trained-further").hexdigest())
    assert not r["ok"] and "changed" in r["reason"]
    assert not wl.verify_deployed("ghost", good)["ok"]


def test_dewhitelist_rewhitelist_conditions():
    wl = W.Whitelist(100.0)
    wl.submit("m", ARCH, "a" * 64, 1.0)
    assert not wl.servable("m")["ok"] and not wl.may_fabricate("m")             # pending is not servable
    wl.decide("m", True, 2.0)
    assert wl.servable("m")["ok"] and wl.may_fabricate("m")
    wl.de_whitelist("m", "critical jailbreak", 3.0)
    assert not wl.servable("m")["ok"] and not wl.may_fabricate("m")
    wl.re_whitelist("m", ("input_classifier", "safety_harness"), 4.0)
    assert wl.entries["m"].status == "conditional"
    assert "missing safeguards" in wl.servable("m")["reason"]
    assert not wl.servable("m", safeguards=("input_classifier",))["ok"]
    assert wl.servable("m", safeguards=("input_classifier", "safety_harness", "extra"))["ok"]
    with pytest.raises(ValueError):
        wl.re_whitelist("m", (), 5.0)                                            # only a de-whitelisted model
    wl.decide("m", False, 7.0)
    assert wl.entries["m"].status == "rejected" and wl.entries["m"].conditions == ()


def test_finetune_requires_servable_base_inherits_conditions_and_follows_recall():
    wl = W.Whitelist(100.0)
    wl.submit("base", ARCH, "a" * 64, 1.0)
    with pytest.raises(ValueError):
        wl.approve_finetune("base", "ft", {"rank": 8}, "b" * 64, 2.0)            # base is still pending
    wl.decide("base", True, 2.0, conditions=("input_classifier",))
    ft = wl.approve_finetune("base", "ft", {"rank": 8}, "b" * 64, 3.0)
    assert (ft.status, ft.conditions, ft.base, ft.kind) == ("conditional", ("input_classifier",), "base", "finetune")
    assert ft.manifest != wl.entries["base"].manifest
    wl.de_whitelist("base", "recall", 4.0)
    assert wl.entries["ft"].status == "de_whitelisted"                           # the fine-tune goes with its base
    wl.re_whitelist("base", ("input_classifier",), 5.0)
    assert wl.entries["ft"].status == "de_whitelisted"                           # and needs fresh approval
    with pytest.raises(ValueError):
        wl.approve_finetune("ft", "ft2", {"rank": 8}, "c" * 64, 6.0)             # a recalled fine-tune is no base


def test_awic_accepts_only_hardwired_hash():
    weights = b"model weights"
    chip = W.AuthenticatedWeightChip(hashlib.sha256(weights).hexdigest())
    assert not chip.load(b"tampered weights") and not chip.loaded
    assert chip.load(weights) and chip.loaded
    assert not chip.load(b"other") and chip.loaded                               # a rejected load does not unload


def test_whitelist_events_are_chained_and_tamper_evident(tmp_path):
    path = tmp_path / "w.jsonl"
    chain = Chain(path)
    wl = W.Whitelist(100.0, chain=chain)
    wl.submit("m1", ARCH, W.weights_digest([b"w"]), 1.0)
    wl.decide("m1", True, 2.0)
    wl.de_whitelist("m1", "jailbreak", 3.0)
    assert chain.n == 3 and Chain.verify(path)[0]
    lines = path.read_text(encoding="utf-8").splitlines()
    forged = json.loads(lines[2])
    forged["record"]["status"] = "whitelisted"                                   # try to un-recall the model
    lines[2] = json.dumps(forged, sort_keys=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert not Chain.verify(path)[0]


def test_latency_location_check():
    assert R.haversine_km(FRA, AMS) == pytest.approx(365, abs=10)
    assert R.max_distance_km(4.0) == pytest.approx(400.0)
    assert R.consistent_with_claim(FRA, [(AMS, 4.0)])                            # 400 km allowed, 365 km claimed
    assert not R.consistent_with_claim(FRA, [(AMS, 2.0)])                        # 200 km allowed: impossible
    assert R.consistent_with_claim(FRA, [(AMS, 50.0)])                           # delay can be added: a long RTT proves nothing
    assert R.verify_in_region(FRA, 100.0, [(FRA, 0.5)])                          # a landmark next door pins it inside 100 km
    assert not R.verify_in_region(FRA, 100.0, [(AMS, 4.0)])
    assert R.consistent_with_claim(FRA, []) is True


def test_impossible_location_marks_chip_silent():
    reg = R.Registry()
    reg.register("S1", 1.0, "pre_pause", "op", "dc", "Germany", now=0.0)
    assert reg.heartbeat("S1", 10.0, claimed=FRA, measurements=[(AMS, 2.0)]).state == "silent"
    assert reg.heartbeat("S1", 20.0, claimed=FRA, measurements=[(AMS, 4.0)]).state == "in_service"


def test_registry_lifecycle_and_dark_charge(tmp_path):
    chain = Chain(tmp_path / "r.jsonl")
    reg = R.Registry(chain=chain, silence_limit_s=60, lost_limit_s=600)
    reg.register("S1", 2.0, "pre_pause", "opA", "dc1", "United States", now=0.0)
    reg.register("S2", 1.0, "manufactured", "opB", "dc2", "China", now=0.0)
    with pytest.raises(ValueError):
        reg.register("S1", 2.0, "pre_pause", "opA", "dc1", "United States", now=0.0)
    reg.heartbeat("S1", 30.0)
    reg.heartbeat("S2", 30.0)
    assert reg.sweep(70.0) == []                                                 # both seen 40 s ago
    reg.heartbeat("S1", 100.0)
    assert reg.sweep(150.0) == ["S2"] and reg.chips["S2"].state == "silent"      # S2 has been quiet for 120 s
    assert reg.sweep(700.0) == ["S1", "S2"]                                      # S1 silent, S2 lost
    assert reg.chips["S1"].state == "silent" and reg.chips["S2"].state == "lost"
    assert reg.charged_as_dark() == {"China": 1.0} and reg.charged_as_dark(0.9) == {"China": 0.9}
    with pytest.raises(ValueError):
        reg.produce_for_inspection("S2", 710.0)                                  # a lost chip stays charged
    reg.produce_for_inspection("S1", 710.0)
    reg.transfer("S1", "opC", "dc3", "Germany", 720.0)                           # change of owner needs re-registration
    assert reg.chips["S1"].host_state == "Germany"
    with pytest.raises(ValueError):
        reg.transfer("S2", "opD", "dc4", "China", 730.0)                         # not in good standing
    assert reg.in_good_standing() == 2.0
    reg.destroy("S1", "inspector-7", 800.0)
    with pytest.raises(ValueError):
        reg.heartbeat("S1", 810.0)
    assert reg.in_good_standing() == 0.0
    ok, n, _ = Chain.verify(chain.path)
    assert ok and n == chain.n and n >= 8
