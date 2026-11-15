"""MIRI's draft agreement (arXiv:2511.10783) and FLI's Draft Articles, as code: every number against the text, every
protocol against tampering, and the findings the computations make (docs/AGREEMENTS_COVERAGE.md)."""
import itertools
import json
import re
from pathlib import Path

import numpy as np
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from closure.cli import main
from closure.treaty import asi_agreement as A
from closure.treaty import bandwidth as W
from closure.treaty import chipauth as CA
from closure.treaty import coverage as V
from closure.treaty import fli_articles as F
from closure.treaty import obligations as O
from closure.treaty import quorum as Q

DAY = 86400.0


def _key():
    k = Ed25519PrivateKey.generate()
    return k, Q.public_hex(k)


# ==== MIRI's draft agreement: Article II definitions ==================================================================
def test_h100e_tpp_and_the_ccc_reference_values():
    assert A.tpp_from_tflops(989, 16) == 15_824 == A.H100E_TPP                 # Art. II s.15
    assert A.tpp(989 / 2, 16) == 15_824                                        # 2 x MacTOPS x bit length
    assert A.chip_tpp({16: 989, 8: 1979}) == 15_832                            # the larger format wins
    ref = A.ccc_reference()
    assert ref["tpp"] == 253_184 and ref["memory_gb"] == 1_280                 # the s.16 note's 16 H100s
    assert A.h100e_compute(253_184) == 16 and A.h100e_memory(1_280) == 16


def test_flop_counting_takes_the_higher_of_fp16_equivalent_and_native():
    assert A.counted_flop(1e22, bits=16) == 1e22
    assert A.counted_flop(1e22, bits=8) == 1e22                                # FP8: its own count is higher
    assert A.counted_flop(1e22, bits=32) == 2e22                               # FP32: two FP16 operations each
    assert A.counted_flop(1e22, bits=32, fp16_per_op=14.8) == pytest.approx(1.48e23)   # a time-based conversion


def test_advanced_chips_are_28nm_or_better():
    assert A.is_advanced_chip(28) and A.is_advanced_chip(4) and not A.is_advanced_chip(40)


# ==== Article IV: training runs =====================================================================================
def test_run_classes_follow_article_iv():
    assert A.classify_run(1e22).category == "unmonitored"                      # "above" is strict
    assert A.classify_run(1.0001e22).category == "monitored"
    assert A.classify_run(1e24).category == "monitored"
    assert A.classify_run(1.0001e24).category == "prohibited"
    assert A.classify_run(1e22, 1.01e23).category == "prohibited"              # post-training above 1e23
    assert A.classify_run(5e21, 2e22).category == "monitored"                  # post-training above 1e22
    assert A.classify_run(9.5e23, 9e22).category == "prohibited"               # 1.04e24 in all
    assert A.classify_run(9.5e23, 9e22, cumulative=False).category == "monitored"
    assert len(A.classify_run(2e22).needs) == 3


def test_a_monitored_run_needs_both_sides_inspectors_and_the_whitelist():
    (u, uh), (p, ph), (x, _) = _key(), _key(), _key()
    inspectors = {uh: {"name": "US inspector", "party": "US"}, ph: {"name": "PRC inspector", "party": "PRC"}}
    wl = {"transformer-pretraining", "rlhf"}
    d = A.declaration("run-1", "site-7", "sha256:code", "sha256:data", 5e22, ["transformer-pretraining"])
    assert A.declaration_problems(d) == []
    only_us = A.approve_monitored_run(d, [Q.sign(u, d)], inspectors, wl)
    assert not only_us["may_start"] and any("PRC" in s for s in only_us["problems"])   # either side may withhold
    both = A.approve_monitored_run(d, [Q.sign(u, d), Q.sign(p, d)], inspectors, wl)
    assert both["may_start"] and both["category"] == "monitored"
    tampered = {**d, "flop_estimate": 9e23}
    assert not A.approve_monitored_run(tampered, [Q.sign(u, d), Q.sign(p, d)], inspectors, wl)["may_start"]
    off = A.declaration("run-2", "site-7", "c", "d", 5e22, ["transformer-pretraining", "new-optimizer"])
    r = A.approve_monitored_run(off, [Q.sign(u, off), Q.sign(p, off)], inspectors, wl)
    assert not r["may_start"] and any("Whitelist" in s for s in r["problems"])
    stranger = A.approve_monitored_run(d, [Q.sign(u, d), Q.sign(p, d), Q.sign(x, d)], inspectors, wl)
    assert any("not on the CTB's inspector list" in s for s in stranger["problems"])
    banned = A.declaration("run-3", "s", "c", "d", 2e24, [])
    assert not A.approve_monitored_run(banned, [Q.sign(u, banned), Q.sign(p, banned)], inspectors, wl)["may_start"]
    small = A.declaration("run-4", "s", "", "", 1e21, [])
    assert A.approve_monitored_run(small, [], inspectors, wl)["may_start"]      # Art. IV s.3: nothing needed
    missing = {**d, "training_data": ""}
    assert "missing training_data (Art. IV s.2(a))" in A.declaration_problems(missing)


def test_a_run_is_checked_against_its_declaration():
    d = A.declaration("r", "s", "c", "d", 2e22, [])
    assert A.within_declaration(d, 1.9e22)["within_estimate"]
    r = A.within_declaration(d, 3e22)
    assert not r["within_estimate"] and r["below_strict"]


# ==== Article II s.16: covered chip clusters ========================================================================
def _h(i, site, h100e):
    return A.Host(i, site, h100e * A.H100E_TPP, h100e * A.H100E_MEMORY_GB)


def test_covered_clusters_by_site_bandwidth_and_shared_work():
    two = [_h("a", "s1", 16), _h("b", "s2", 16)]
    apart = A.covered_clusters(two, [("a", "b", 25.0)])
    assert len(apart) == 2 and not any(c["covered"] for c in apart)           # 16 is not more than 16; 25 is not > 25
    joined = A.covered_clusters(two, [("a", "b", 20.0), ("a", "b", 6.0)])      # links add up: 26 Gbit/s
    assert len(joined) == 1 and joined[0]["covered"] and joined[0]["h100e_compute"] == 32
    work = A.covered_clusters(two, [("a", "b", 1.0)], together=[["a", "b"]])
    assert work[0]["covered"] and work[0]["joined_by"] == "networked to perform workloads together"
    same = A.covered_clusters([_h("a", "s1", 9), _h("b", "s1", 9)])
    assert len(same) == 1 and same[0]["covered"]                               # co-located
    memory_only = A.covered_clusters([A.Host("m", "s", 8 * A.H100E_TPP, 1_300.0)])
    assert memory_only[0]["covered"] and memory_only[0]["h100e_compute"] == 8  # memory alone can make a CCC
    three = A.covered_clusters([_h("a", "s1", 8), _h("b", "s2", 8), _h("c", "s3", 8)],
                               [("a", "b", 10.0), ("b", "c", 10.0), ("a", "c", 10.0)])
    assert len(three) == 3                                                     # pairwise 10 Gbit/s: not merged


def test_25_gbits_does_not_stop_training_across_two_sub_ccc_sets():
    r = A.cross_site_training_gbps()                                           # 2 x 16 H100e, 40%, 4M tokens a step
    assert r["needs_gbps"] == pytest.approx(8.44, abs=0.01) and r["slowdown_at_cap"] == 1.0
    assert not r["each_set_is_a_ccc"] and not r["link_counts_as_networked"]
    small_batch = A.cross_site_training_gbps(tokens_per_step=1e6)
    assert small_batch["needs_gbps"] == pytest.approx(33.76, abs=0.01)
    assert small_batch["slowdown_at_cap"] == pytest.approx(1.35, abs=0.01)
    assert A.cross_site_training_gbps(sync_every=100)["needs_gbps"] == pytest.approx(0.0844, abs=1e-4)
    assert A.cross_site_training_gbps(sites=10, sync_every=100)["needs_gbps"] < 1.0
    flop_s = 2 * 16 * A.H100E_FP16_FLOP_S * 0.4                                # the model size cancels
    need = [W.needed_gbps(p, flop_s / (6 * p * 4e6), 2) for p in (1e8, 1e9, 7e10)]
    assert max(need) == pytest.approx(min(need), rel=1e-12)


# ==== Appendix D.3: Tables 1 and 2, staged registration ================================================================
def test_tables_1_and_2_reproduce_at_990_and_differ_at_989_in_four_cells():
    assert A.compare_tables() == []                                            # every printed cell at 990 TFLOP/s
    assert A.compare_tables(989e12) == [("days_to_monitored", 1, "116.9", "117.0"),
                                        ("days_to_strict", 100, "116.9", "117.0"),
                                        ("days_to_strict", 16, "730.7", "731.4"),
                                        ("days_to_strict", 1, "11691.0", "11702.8")]


def test_registration_stages_and_the_16_h100e_boundary():
    assert [A.registration_stage(s) for s in A.TABLE_SIZES] == list(A.TABLE_PRINTED["days_to_register"])
    assert A.registration_stage(16) == "Year 2" and A.registration_stage(16, "text") == "Never"
    assert A.registration_stage(10_000, "text") == "Day 10" and A.registration_stage(10_001, "text") == "Day 1"
    assert not A.covered_clusters([_h("x", "s", 16)])[0]["covered"]            # a 16-H100e cluster is no CCC
    assert A.registration_stage(16.5, "text") == "Year 2"


def test_the_fp8_note_gives_7_3_days_and_2_years():
    r = A.fp8_note_days()
    assert round(r["days_to_monitored"], 1) == 7.3 and round(r["years_to_strict"], 1) == 2.0


# ==== Article III: the Council and the CTB ==========================================================================
def test_council_consensus_and_vetoes_over_the_ctb():
    (u, uh), (p, ph), (x, _) = _key(), _key(), _key()
    council = {uh: "US", ph: "PRC"}
    rec = {"type": "amendment", "text": "lower the Monitored Threshold"}
    assert not A.council_consensus(rec, [Q.sign(u, rec)], council)["approved"]
    assert A.council_consensus(rec, [Q.sign(u, rec), Q.sign(p, rec)], council)["approved"]
    dec = {"type": "ctb-decision", "what": "approve carve-out 4"}
    assert A.ctb_decision_stands(dec, [], council)["stands"]
    assert not A.ctb_decision_stands(dec, [Q.sign(p, A.veto_record(dec))], council)["stands"]
    assert A.ctb_decision_stands(dec, [Q.sign(x, A.veto_record(dec))], council)["stands"]   # not a member
    assert A.ctb_decision_stands(dec, [Q.sign(p, dec)], council)["stands"]     # signing the decision is no veto


def test_emergency_changes_lapse_after_30_days_without_council_approval():
    (u, uh), (p, ph) = _key(), _key()
    council = {uh: "US", ph: "PRC"}
    rec = A.emergency_change({"monitored": 1e21}, issued=0.0)
    change = [{"record": rec, "approvals": []}]
    assert A.thresholds_in_force(10 * DAY, change, council)["monitored"] == 1e21
    assert A.classify_run(5e21, thresholds=A.thresholds_in_force(10 * DAY, change, council)).category == "monitored"
    assert A.thresholds_in_force(31 * DAY, change, council)["monitored"] == 1e22
    approved = [{"record": rec, "approvals": [Q.sign(u, rec), Q.sign(p, rec)]}]
    assert A.thresholds_in_force(31 * DAY, approved, council)["monitored"] == 1e21
    with pytest.raises(ValueError):
        A.emergency_change({"research_boundary": 1}, 0.0)


# ==== Articles V and VI: register, transfers, destruction ================================================================
def test_register_entries_and_transfers():
    ok = {"location": "site-7", "type": "H100 SXM", "quantity": 4096, "interconnect": "NVLink + 400G IB",
          "identifiers": ["s1", "s2"]}
    assert A.register_problems([ok]) == []
    bad = A.register_problems([{"location": "x", "quantity": -1}, ok, {**ok, "identifiers": ["s2"]}])
    assert "entry 0: missing type" in bad and any("twice" in b for b in bad) and any("non-negative" in b for b in bad)
    t = lambda **k: A.transfer_check("ai_chips", **k)
    assert t(notified_at=0, planned_at=14 * DAY, ctb_approved=True)["may_proceed"]
    assert not t(notified_at=0, planned_at=13 * DAY, ctb_approved=True)["may_proceed"]
    assert not t(notified_at=0, planned_at=20 * DAY)["may_proceed"]                       # the CTB must approve
    assert t(notified_at=5 * DAY, emergency=True)["may_proceed"]                         # notify, verified after
    assert t(notified_at=0, planned_at=15 * DAY, from_production=True)["may_proceed"]    # presumed approved
    assert not t(notified_at=0, planned_at=15 * DAY, from_production=True, ctb_objected=True)["may_proceed"]
    assert not t(notified_at=0, planned_at=15 * DAY, from_production=True, to_non_party=True)["may_proceed"]
    assert t(notified_at=0, planned_at=15 * DAY, from_production=True, to_non_party=True, ctb_approved=True)["may_proceed"]
    assert not A.transfer_check("manufacturing_equipment")["may_proceed"]
    assert A.transfer_check("manufacturing_equipment", council_consensus_given=True)["may_proceed"]
    assert A.transfer_check("non_ai_advanced_chips")["may_proceed"]
    assert not A.transfer_check("non_ai_advanced_chips", to_non_party=True)["may_proceed"]
    assert A.transfer_check("non_ai_advanced_chips", to_non_party=True, ctb_approved=True)["may_proceed"]


def test_decommissioned_chips_count_until_destruction_is_certified():
    (c, ch), (x, _) = _key(), _key()
    s = A.ChipStock({ch: "CTB"})
    for i in range(4):
        s.declare(f"s{i}", 1.0, "site")
    s.decommission("s0")
    assert s.functional_h100e() == 4                                           # decommissioned is still functional
    cert = {"type": "destruction-certificate", "serials": ["s0"], "method": "shredding"}
    assert not s.certify_destruction(cert, [Q.sign(x, cert)])["certified"]     # not the CTB
    assert not s.certify_destruction({**cert, "method": "drawer"}, [Q.sign(c, {**cert, "method": "drawer"})])["certified"]
    assert s.certify_destruction(cert, [Q.sign(c, cert)])["certified"] and s.functional_h100e() == 3
    s.decommission("s1")
    assert not s.resale_allowed("s1") and s.resale_allowed("s1", ctb_authorised=True)


def test_airport_reach():
    assert A.airport_reach_problems({"a": 11.5, "b": 12.0}) == []
    assert A.airport_reach_problems({"c": 13})


def test_powered_off_needs_low_power_and_no_gaps():
    t = np.arange(0, 3600, 1.0)
    p = np.full_like(t, 35.0)
    assert A.powered_off(t, p, off_w=50, max_gap_s=5)["verified_off"]
    p2 = p.copy(); p2[1000] = 400.0
    assert not A.powered_off(t, p2, 50, 5)["verified_off"]
    t3 = np.delete(t, np.arange(2000, 2100))
    r = A.powered_off(t3, np.full_like(t3, 35.0), 50, 5)
    assert not r["verified_off"] and r["longest_gap_s"] == 101


# ==== Article X s.3: challenge inspections ==========================================================================
def test_challenge_inspections_consensus_quota_and_inspectors():
    (u, uh), (_, ph) = _key(), _key()
    council = {uh: "US", ph: "PRC"}
    lists = {"US": {"i1", "i2"}, "PRC": {"i2", "i3"}}
    rec = {"type": "challenge-inspection", "requested_by": "US", "territory": "PRC", "site": "s1"}
    plain = A.ChallengeInspections(council, lists)
    r = plain.call(rec, [Q.sign(u, rec)], now=0.0)
    assert not r["approved"] and any("missing PRC" in s for s in r["problems"])   # the inspected Party can refuse
    excl = A.ChallengeInspections(council, lists, exclude_inspected=True)
    r = excl.call(rec, [Q.sign(u, rec)], now=0.0)
    assert r["approved"] and r["access_due"] == 24 * 3600.0
    assert excl.team_problems(["i2"], "PRC", "US") == [] and excl.team_problems(["i1"], "PRC", "US")
    assert A.access_in_time(0, 24 * 3600) and not A.access_in_time(0, 24 * 3600 + 1)
    roll = A.ChallengeInspections(council, lists, exclude_inspected=True)
    for i in range(20):
        assert roll.call(rec, [Q.sign(u, rec)], now=i * DAY)["approved"]
    assert not roll.call(rec, [Q.sign(u, rec)], now=21 * DAY)["approved"]                # the 21st within a year
    assert roll.call(rec, [Q.sign(u, rec)], now=366 * DAY)["approved"]
    start = O.ts("2027-12-20")
    cal, rol = (A.ChallengeInspections(council, lists, exclude_inspected=True, year=y) for y in ("calendar", "rolling"))
    days = [start + i * 0.5 * DAY for i in range(20)] + [O.ts("2028-01-01") + i * 0.5 * DAY for i in range(20)]
    assert sum(cal.call(rec, [Q.sign(u, rec)], t)["approved"] for t in days) == 40    # 40 in about three weeks
    assert sum(rol.call(rec, [Q.sign(u, rec)], t)["approved"] for t in days) == 20


def test_protective_action_statements_need_four_elements():
    full = {"purpose": "p", "targets": "t", "cessation_conditions": "c", "commitment_to_cease": True}
    assert A.statement_problems(full) == []
    assert len(A.statement_problems({"purpose": "p"})) == 3


# ==== FLI Annex C: chip authorization ===============================================================================
def test_an_authorization_is_checked_for_signature_chip_and_reuse():
    ag = CA.Enforcer("Agency")
    chip = CA.GuaranteeProcessor("c1", ag.public())
    rec, sigs = ag.issue("c1", 100)
    assert chip.receive(rec, sigs)["accepted"] and chip.allowance == 100
    assert not chip.receive(rec, sigs)["accepted"]                             # the same file twice
    assert not chip.receive(*CA.Enforcer("Forger").issue("c1", 10 ** 9))["accepted"]
    assert not chip.receive(*ag.issue("c2", 100))["accepted"]                  # another chip's file
    assert not chip.receive({**rec, "cycles": 10 ** 9, "id": 999}, sigs)["accepted"]   # the signature covers it
    inc = CA.GuaranteeProcessor("c3", ag.public(), ids="increasing")
    a1, a2 = ag.issue("c3", 10), ag.issue("c3", 10)
    assert inc.receive(*a2)["accepted"] and not inc.receive(*a1)["accepted"]   # an older file after a newer one
    st = CA.Enforcer("State")
    two = CA.GuaranteeProcessor("c4", {**ag.public(), **st.public()}, k=2)
    rec, sigs = ag.issue("c4", 10)
    assert not two.receive(rec, sigs)["accepted"] and two.receive(rec, sigs + st.cosign(rec))["accepted"]


def test_the_chip_refuses_work_without_allowance_and_resumes_when_reauthorized():
    ag = CA.Enforcer("Agency")
    chip = CA.GuaranteeProcessor("c1", ag.public())
    chip.receive(*ag.issue("c1", 50))
    assert chip.run(80) == 50 and chip.run(10) == 0                            # refuses at zero
    ag.withhold("c1")
    assert ag.issue("c1", 50) is None                                          # violation verified: no renewal
    ag.resume("c1")
    chip.receive(*ag.issue("c1", 50))
    assert chip.run(10) == 10                                                  # corrective action, not destruction
    chip.tamper()
    assert chip.run(10) == 0 and not chip.receive(*ag.issue("c1", 50))["accepted"]


def test_as_written_a_provider_banks_authorizations_and_runs_on_after_renewal_stops():
    r = CA.simulate("as-written", 300, 600, 1.0, days=2)                       # renew every 5 min, 10 min each
    assert r["run_on_days"] == pytest.approx(2.0, rel=1e-3) == r["predicted_bank_days"]
    assert r["seconds_short_before_stop"] == 0                                 # the chip never went short
    assert CA.simulate("as-written", 300, 360, 1.0, days=2)["run_on_days"] == pytest.approx(0.4, rel=1e-3)
    assert CA.simulate("as-written", 300, 300, 0.9, days=2)["run_on_days"] == pytest.approx(0.2, rel=1e-3)
    capped = CA.simulate("as-written", 300, 600, 1.0, days=2, cap_s=600)
    assert capped["run_on_days"] == pytest.approx(2.0, rel=1e-3)               # a cap in the chip does not reach
    honest = CA.simulate("as-written", 300, 600, 1.0, days=2, hoard=False, cap_s=600)   # what the provider holds
    assert honest["run_on_s"] <= 600
    assert CA.bank_days(30, 300, 600) == 30 and CA.bank_days(30, 300, 360) == pytest.approx(6.0)


def test_fresh_nonces_and_a_cap_bound_the_run_on_to_about_one_period():
    r = CA.simulate("fresh", 300, 600, 1.0, days=2)
    assert r["run_on_s"] <= 1200 and r["held_by_provider_at_stop"] <= 1
    filling = CA.simulate("fresh", 300, 600, 0.5, days=2, hoard=False)         # no cap: an idle chip fills up
    assert filling["run_on_days"] == pytest.approx(3.0, rel=1e-2)
    capped = CA.simulate("fresh", 300, 600, 0.5, days=2, hoard=False, cap_s=600)
    assert capped["run_on_s"] <= 600
    worst = max(CA.simulate("fresh", 300, 600, d, days=1, hoard=h, cap_s=600)["run_on_s"]
                for d in (0.3, 1.0) for h in (True, False))
    assert worst <= 1200                                                       # cap + the one file held back
    ag = CA.Enforcer("Agency")
    chip = CA.GuaranteeProcessor("c", ag.public(), mode="fresh")
    early = ag.issue("c", 10, nonce="guessed")
    n = chip.challenge()
    assert not chip.receive(*early)["accepted"] and chip.receive(*ag.issue("c", 10, nonce=n))["accepted"]
    assert ag.issue("c", 10, nonce=n) is None                                  # one file per challenge


def test_signed_firmware_updates_refuse_rollback_and_can_rotate_keys():
    ag, new = CA.Enforcer("Agency"), CA.Enforcer("Agency, new key")
    chip = CA.GuaranteeProcessor("c1", ag.public())
    up = CA.firmware_update(2, trusted=new.public(), cap_cycles=600)
    assert not chip.install_firmware(up, new.sign(up))["installed"]            # not signed by a trusted key
    assert chip.install_firmware(up, ag.sign(up))["installed"] and chip.cap == 600
    old = CA.firmware_update(1, trusted=ag.public())
    assert not chip.install_firmware(old, new.sign(old))["installed"]          # rollback
    assert not chip.receive(*ag.issue("c1", 10))["accepted"] and chip.receive(*new.issue("c1", 10))["accepted"]


def test_national_or_agency_signing_and_two_key_authorizations():
    state, agency = CA.Enforcer("State Party"), CA.Enforcer("Agency")
    c1 = CA.GuaranteeProcessor("x", state.public())                            # Annex C.1: the State signs
    agency.withhold("x")
    assert c1.receive(*state.issue("x", 10))["accepted"]                       # the Agency's finding does not stop it
    c2 = CA.GuaranteeProcessor("y", agency.public())                           # Annex C.2: the Agency signs
    c2.receive(*agency.issue("y", 10))
    agency.withhold("y")
    assert agency.issue("y", 10) is None and c2.run(20) == 10
    both = CA.GuaranteeProcessor("z", {**state.public(), **agency.public()}, k=2)   # 2 of 2: either can stop it
    rec, sigs = state.issue("z", 10)
    assert both.receive(rec, sigs + agency.cosign(rec))["accepted"]
    agency.withhold("z")
    rec, sigs = state.issue("z", 10)
    assert agency.cosign(rec) == [] and not both.receive(rec, sigs + agency.cosign(rec))["accepted"]


# ==== obligations: deadlines in both texts ==========================================================================
def _status(rows, rule, subject=""):
    return [r["status"] for r in rows if r["rule"] == rule and r["subject"] == subject]


def test_obligation_deadlines_for_the_miri_agreement():
    ev = [{"type": "entry_into_force", "at": "2027-01-01"},
          {"type": "register_submitted", "at": "2027-04-01", "subject": "US"},
          {"type": "register_submitted", "at": "2027-05-15", "subject": "PRC"},
          {"type": "register_submitted", "at": "2027-06-25", "subject": "US"},
          {"type": "consolidated", "at": "2027-04-20", "subject": "US"},
          {"type": "transfer_notified", "at": "2027-03-01", "subject": "t1"},
          {"type": "transfer", "at": "2027-03-11", "subject": "t1"},
          {"type": "transfer_notified", "at": "2027-03-01", "subject": "t2"},
          {"type": "transfer", "at": "2027-03-20", "subject": "t2"},
          {"type": "challenge_called", "at": "2027-03-01T00:00:00Z", "subject": "c1"},
          {"type": "access_granted", "at": "2027-03-02T01:00:00Z", "subject": "c1"},
          {"type": "concern_notified", "at": "2027-03-01", "subject": "k1"},
          {"type": "acknowledged", "at": "2027-03-02T06:00:00Z", "subject": "k1"},
          {"type": "clarified", "at": "2027-03-07", "subject": "k1"},
          {"type": "emergency_change", "at": "2027-02-01", "subject": "e1"},
          {"type": "emergency_change", "at": "2027-02-01", "subject": "e2"},
          {"type": "council_approval", "at": "2027-02-20", "subject": "e2"},
          {"type": "withdrawal_notified", "at": "2027-01-15", "subject": "X"},
          {"type": "withdrawal_effective", "at": "2027-12-01", "subject": "X"}]
    rows = O.check(ev, "2028-01-01", subjects=["US", "PRC"], source="MA")
    assert _status(rows, "ma-register", "US") == ["met"] and _status(rows, "ma-register", "PRC") == ["missed"]
    assert _status(rows, "ma-register-update", "US") == ["met", "overdue"]      # 85 days, then nothing since June
    assert _status(rows, "ma-consolidation", "US") == ["met"] and _status(rows, "ma-consolidation", "PRC") == ["overdue"]
    assert _status(rows, "ma-transfer-notice", "t1") == ["missed"] and _status(rows, "ma-transfer-notice", "t2") == ["met"]
    assert _status(rows, "ma-challenge-access", "c1") == ["missed"]            # 25 hours
    assert _status(rows, "ma-dispute-ack", "k1") == ["met"] and _status(rows, "ma-dispute-clarify", "k1") == ["missed"]
    assert _status(rows, "ma-emergency-change", "e1") == ["lapsed"] and _status(rows, "ma-emergency-change", "e2") == ["met"]
    assert _status(rows, "ma-withdrawal", "X") == ["missed"]                   # ten and a half months
    assert _status(rows, "ma-review-first") == ["pending"]
    assert "lapsed" not in {r["status"] for r in O.failures(rows)}
    assert O.until("2027-01-15", 12, "months") == "2028-01-15T00:00:00Z"


def test_obligation_deadlines_for_the_fli_articles():
    ev = [{"type": "entry_into_force", "at": "2027-01-10"},
          {"type": "rules_of_procedure_adopted", "at": "2027-01-20"},
          {"type": "certificate_issued", "at": "2027-02-01", "subject": "LabA"},
          {"type": "certificate_renewed", "at": "2027-07-15", "subject": "LabA"},
          {"type": "certificate_renewed", "at": "2028-03-01", "subject": "LabA"},
          {"type": "challenge_filed", "at": "2027-03-01", "subject": "ch1"},
          {"type": "challenge_decided", "at": "2027-03-09", "subject": "ch1"},
          {"type": "conference_session", "at": "2027-04-15"}, {"type": "conference_session", "at": "2027-07-15"},
          {"type": "conference_session", "at": "2028-01-15"},
          {"type": "emergency_report", "at": "2027-12-01", "subject": "FR"}]
    rows = O.check(ev, "2028-04-10", subjects=["FR", "JP"], source="FLI")
    assert _status(rows, "fli-rules-of-procedure") == ["met"]
    assert _status(rows, "fli-certificate", "LabA") == ["met", "missed", "pending"]
    assert _status(rows, "fli-challenge", "ch1") == ["missed"]                 # eight days
    q = {r["subject"]: r["status"] for r in rows if r["rule"] == "fli-conference"}
    assert q == {"2027 Q2": "met", "2027 Q3": "met", "2027 Q4": "missed", "2028 Q1": "met"}
    assert _status(rows, "fli-emergency-report", "FR") == ["met", "pending"]
    assert _status(rows, "fli-emergency-report", "JP") == ["overdue"]
    assert _status(rows, "fli-annex-review") == ["overdue"]


def test_calendar_months_and_term_limits():
    assert O.iso(O.add(O.ts("2027-01-31"), 1, "months")) == "2027-02-28T00:00:00Z"
    assert O.iso(O.add(O.ts("2028-01-31"), 1, "months")) == "2028-02-29T00:00:00Z"
    assert O.ts("2027-01-01T05:00:00-05:00") == O.ts("2027-01-01T10:00:00Z")
    terms = [{"person": "A", "start": "2027-01-01"}, {"person": "A", "start": "2030-01-01"},
             {"person": "B", "start": "2033-01-01"}]
    assert O.term_problems(terms, F.DG_MAX_TERMS) == []
    assert O.term_problems(terms + [{"person": "A", "start": "2036-01-01"}], 2) == ["A appointed 3 times; at most 2 terms"]


# ==== FLI's Draft Articles ==========================================================================================
def test_global_catastrophic_scale_is_strictly_more_than_50_people_or_a_billion():
    assert not F.is_global_catastrophic(50)["scale_met"] and F.is_global_catastrophic(51)["scale_met"]
    assert not F.is_global_catastrophic(0, 1e9)["scale_met"] and F.is_global_catastrophic(0, 1e9 + 1)["scale_met"]
    assert not F.is_global_catastrophic(400, single_incident=False)["scale_met"]


def test_enforcement_order_and_lifting():
    assert not F.enforcement_may_start(False, False)["may_start"]
    assert F.enforcement_may_start(False, True)["may_start"] and F.enforcement_may_start(True, False)["may_start"]
    assert F.enforcement_must_lift(True, False) and not F.enforcement_must_lift(True, True)
    assert not F.enforcement_must_lift(False, False)


def test_certificates_expire_after_six_months_and_need_a_licensed_evaluator():
    c = F.Certificates()
    app = {k: True for k in F.LICENCE_CONDITIONS}
    assert c.license("Eval", {**app, "background_check": False}, "2027-01-01")      # (c) missing
    assert c.license("Eval", app, "2027-01-01") == [] and c.license("Eval2", app, "2027-01-01") == []
    assert c.certify("LabA", "Nobody", "2027-02-01")                                # unlicensed evaluator
    assert c.certify("LabA", "Eval", "2027-02-01") == []
    assert c.may_operate("LabA", "2027-07-31")["may_operate"]
    assert not c.may_operate("LabA", "2027-08-02")["may_operate"]                   # not renewed in six months
    assert not c.may_operate("LabB", "2027-03-01")["may_operate"]
    assert not c.challenge("Acme Corp", False, "certificate", "LabA", "2027-03-01")["filed"]   # States only
    ch = c.challenge("FR", True, "certificate", "LabA", "2027-03-01")
    assert ch["filed"] and O.iso(ch["decide_by"]) == "2027-03-08T00:00:00Z"
    assert c.overdue("2027-03-09") == [ch["id"]]
    d = c.decide(ch["id"], accept=True, at="2027-03-06", reasonable_likelihood=True)
    assert d["on_time"] and d["suspended"] and not c.may_operate("LabA", "2027-03-07")["may_operate"]
    c.resolve(ch["id"], upheld=False, at="2027-04-01")
    assert c.may_operate("LabA", "2027-04-02")["may_operate"]
    lic = c.challenge("JP", True, "licence", "Eval", "2027-04-05")
    c.decide(lic["id"], True, "2027-04-07", reasonable_likelihood=True)
    assert c.certify("LabA", "Eval", "2027-04-08")                                  # suspended evaluator
    assert c.certify("LabA", "Eval2", "2027-04-08") == []
    c.evader("LabA")
    assert c.certify("LabA", "Eval2", "2027-05-01") and not c.may_operate("LabA", "2027-05-02")["may_operate"]


def test_conference_majorities_and_weighted_matters():
    assert F.extraordinary_session(10, 30) and not F.extraordinary_session(9, 30) and F.extraordinary_session(11, 31)
    assert not F.extraordinary_session(10, 31)
    r = F.conference_decision("budget", ["a", "b", "c"], ["d", "e"])
    assert r["passed"] and not r["weighted"]
    assert not F.conference_decision("budget", ["a", "b", "c"], ["d"], n_parties=8, base="parties")["passed"]
    w = {"big": 60.0, "s1": 10.0, "s2": 10.0, "s3": 10.0, "s4": 10.0}
    big = F.conference_decision("director_general", ["big"], ["s1", "s2", "s3", "s4"], contributions=w)
    assert big["weighted"] and big["passed"]                                   # one State outweighs four
    assert not F.conference_decision("budget", ["big"], ["s1", "s2", "s3", "s4"])["passed"]
    with pytest.raises(ValueError):
        F.conference_decision("verification_or_enforcement_mechanism", ["big"], [])
    assert F.amendment_adopted(20, 30) and not F.amendment_adopted(19, 30) and F.amendment_adopted(21, 31)
    assert not F.amendment_adopted(20, 31)


def test_four_economies_decide_weighted_matters_under_a_gdp_stand_in():
    w = F.gdp_stand_in()
    few = F.fewest_to_decide(w)
    share = sum(w[s] for s in few) / sum(w.values())
    assert few == ["USA", "CHN", "DEU", "JPN"] and 0.51 < share < 0.52
    p = F.weighted_power(w, permutations=20000)
    assert p["USA"][0] > p["CHN"][0] > p["DEU"][0] and 0.30 < p["USA"][0] < 0.34
    small = {"a": 4.0, "b": 3.0, "c": 2.0, "d": 1.0}                           # the estimator against enumeration
    exact = dict.fromkeys(small, 0)
    for order in itertools.permutations(small):
        acc = 0.0
        for n in order:
            acc += small[n]
            if acc > 5.0:
                exact[n] += 1
                break
    est = F.weighted_power(small, permutations=40000, seed=1)
    for n in small:
        assert abs(est[n][0] - exact[n] / 24) < 4 * est[n][1] + 1e-9


def test_the_agency_may_not_recommend_removing_an_annex_a_item():
    cur = list(F.ANNEX_A)
    assert F.annex_a_change_problems(cur, cur + ["5"], "agency") == []         # adding is fine
    assert F.annex_a_change_problems(cur, [x for x in cur if x != "3(d)"], "agency")
    assert F.annex_a_change_problems(cur, [x for x in cur if x != "3(d)"], "state", yes=20, n_parties=30) == []
    assert F.annex_a_change_problems(cur, [x for x in cur if x != "3(d)"], "state", yes=19, n_parties=30)


def test_agency_funding_and_the_tax():
    assert F.agency_funding(2e9) == pytest.approx(2e7)
    assert F.tax_compliant(0.05) and not F.tax_compliant(0.049)


def test_chip_registry_needs_unique_ids_and_locations():
    assert F.registry_problems([{"id": "a", "location": "x"}, {"id": "b", "location": "y"}]) == []
    p = F.registry_problems([{"id": "a", "location": "x"}, {"id": "a"}, {"location": "z"}])
    assert len(p) == 3


# ==== the matrix and the commands ===================================================================================
def test_agreements_matrix_references_exist_and_doc_is_current():
    assert V.validate() == []
    doc = Path(__file__).resolve().parents[1] / "docs" / "AGREEMENTS_COVERAGE.md"
    assert doc.read_text(encoding="utf-8") == V.to_markdown(), "run: closure treaty coverage --write docs/AGREEMENTS_COVERAGE.md"


def test_every_article_and_annex_has_a_row():
    src = {r["source"] for r in V.ROWS}
    roman = "I II III IV V VI VII VIII IX X XI XII XIII XIV XV".split()
    for n in roman:
        assert any(s.startswith(f"{V.MA} > Art. {n} ") or s == f"{V.MA} > Art. {n}" for s in src), n
    assert any("Appendix D" in s for s in src)
    for n in range(1, 19):
        assert any(s.startswith(f"{V.FLI} > Art. {n}(") or s == f"{V.FLI} > Art. {n}" for s in src), n
    for annex in ("A", "B.1", "B.2", "C.1", "C.2"):
        assert any(re.search(rf"Annex (\S+ and )?{re.escape(annex)}\b", s) for s in src), annex
    s = V.summary()
    assert s["not-started"] == 0 and s["external"] == 0
    assert all(r["note"] for r in V.ROWS if r["status"] == "partial")


def test_readme_agreements_table_matches_the_matrix():
    readme = (Path(__file__).resolve().parents[1] / "README.md").read_text(encoding="utf-8")
    block = readme.split("## Two draft agreements, article by article", 1)[1].split("\n## ", 1)[0]
    s = V.summary()
    for label, key in (("implemented (code and tests here)", "implemented"),
                       ("hardware-gated (code here; measured on hardware)", "hardware-gated"), ("partial", "partial"),
                       ("physical (outside software)", "physical"), ("policy (outside software)", "policy")):
        assert f"| {label} | {s[key]} |" in block, label
    assert f"Every one of the {s['software_rows']} software rows has code and a test" in block


def test_treaty_commands_for_the_agreements(tmp_path, capsys):
    assert main(["treaty", "asi-tables"]) == 0 and "every cell matches" in capsys.readouterr().out
    assert main(["treaty", "asi-tables", "--flop-s", "989e12"]) == 0 and "731.4" in capsys.readouterr().out
    assert main(["treaty", "asi-run", "--pretraining", "2e22"]) == 0
    assert json.loads(capsys.readouterr().out)["category"] == "monitored"
    hosts = tmp_path / "hosts.json"
    hosts.write_text(json.dumps({"hosts": [{"id": "a", "site": "s1", "h100e": 16}, {"id": "b", "site": "s2", "h100e": 16}],
                                 "links": [["a", "b", 30]]}), encoding="utf-8")
    assert main(["treaty", "asi-cluster", "--hosts", str(hosts)]) == 0
    assert json.loads(capsys.readouterr().out)[0]["covered"]
    assert main(["treaty", "asi-crosssite"]) == 0
    assert json.loads(capsys.readouterr().out)["slowdown_at_cap"] == 1.0
    trace = tmp_path / "bus.csv"
    trace.write_text("timestamp_s,power_w\n" + "".join(f"{i},{30 + (i == 50) * 400}\n" for i in range(100)),
                     encoding="utf-8")
    assert main(["treaty", "asi-off", "--csv", str(trace), "--off-w", "50"]) == 1
    assert json.loads(capsys.readouterr().out)["max_w"] == 430
    assert main(["treaty", "asi-off", "--csv", str(trace), "--off-w", "500"]) == 0
    capsys.readouterr()
    assert main(["treaty", "chip-auth", "--days", "1"]) == 0
    assert json.loads(capsys.readouterr().out)["run_on_days"] == pytest.approx(1.0, rel=1e-3)
    ev = tmp_path / "ev.json"
    ev.write_text(json.dumps({"subjects": ["US"], "events": [{"type": "entry_into_force", "at": "2027-01-01"}]}),
                  encoding="utf-8")
    assert main(["treaty", "obligations", "--events", str(ev), "--now", "2027-02-01", "--source", "MA"]) == 0
    assert main(["treaty", "obligations", "--events", str(ev), "--now", "2027-06-01", "--source", "MA"]) == 1
    assert "overdue" in capsys.readouterr().out
    assert main(["treaty", "fli-weighted", "--permutations", "2000"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert [x["state"] for x in out["fewest_deciding_weighted_matters"]] == ["USA", "CHN", "DEU", "JPN"]
    assert main(["treaty", "coverage", "--write", str(tmp_path / "x" / "agreements.md")]) == 0
    assert (tmp_path / "x" / "agreements.md").read_text(encoding="utf-8") == V.to_markdown()
