"""The treaty mechanisms (src/closure/treaty, docs/TREATY_COVERAGE.md): each closed form against a simulation or an
enumeration, each protocol against tampering."""
import itertools
import json
import math
import threading

import numpy as np
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from closure.cli import main
from closure.treaty import bandwidth as W
from closure.treaty import beacon as B
from closure.treaty import clauses as K
from closure.treaty import coalition as C
from closure.treaty import deterrence as D
from closure.treaty import geoloc as G
from closure.treaty import inspection as I
from closure.treaty import quorum as Q
from closure.treaty import thresholds as T


# ---- thresholds ----------------------------------------------------------------------------------------------------
def test_licences_are_needed_strictly_above_the_narrow_path_thresholds():
    assert T.licences_needed(1e25, 1e17) == []
    assert T.licences_needed(1.0001e25, 2e17) == ["Training Licence", "Compute Licence"]
    assert T.narrow_path_regime_ratio_s(1e25, 1e17) == pytest.approx(1e8)       # 3.2 years, not 12 days


def test_covert_days_follow_from_the_gap_the_floor_and_the_fleet():
    r = T.covert_days(1e25, 0.005, 100_000, 700.0, 0.5e-12)
    assert r.hidden_flop_per_s == pytest.approx(0.005 * 100_000 * 700.0 / 0.5e-12)
    assert r.days == pytest.approx(1e25 / r.hidden_flop_per_s / 86400.0) and 165 < r.days < 166
    assert T.covert_days(1e25, 0.01, 100_000).days == pytest.approx(r.days / 2)   # twice the gap, half the time


def test_covert_days_from_a_trial_use_the_slack_inflated_gap_and_its_floor():
    res = {"status": "SIMULATED", "closure_gap_fraction": 0.02, "slack": {"slack_inflated_gap_fraction": 0.04},
           "hidden_compute_at_gap_per_week": {"energy_floor_j_per_flop": 1e-12, "energy_floor_source": "probe"}}
    r = T.covert_days_from_trial(res, {"p_max_w": 70.0}, 1e25, 1000)
    assert r.gap_fraction == 0.04 and r.p_max_w == 70.0 and "slack-inflated" in r.source
    assert T.covert_days_from_trial(res, {"p_max_w": 70.0}, 1e25, 1000, use_slack=False).gap_fraction == 0.02
    with pytest.raises(ValueError, match="no closure gap"):
        T.covert_days_from_trial({**res, "closure_gap_fraction": None, "slack": {}}, {}, 1e25, 1000)


# ---- deterrence ----------------------------------------------------------------------------------------------------
def test_per_period_deterrence_threshold_is_independent_of_the_discount():
    p = D.per_period_threshold(3.0, 7.0)
    assert p == pytest.approx(0.3)
    for d in (0.5, 0.9, 0.999):
        assert D.per_period_value(p, 3.0, 7.0, d) == pytest.approx(0.0, abs=1e-12)
        assert D.per_period_value(p + 0.01, 3.0, 7.0, d) < 0 < D.per_period_value(p - 0.01, 3.0, 7.0, d)


def test_winner_take_all_needs_cumulative_detection_of_w_over_w_plus_c():
    W, C_, T_ = 100.0, 1.0, 30
    p = D.race_threshold(T_, W, C_)
    assert p == pytest.approx(1 - (C_ / (W + C_)) ** (1 / T_))
    assert 1 - (1 - p) ** T_ == pytest.approx(D.required_cumulative_detection(W, C_)) == pytest.approx(100 / 101)
    assert D.race_value(p, T_, W, C_) == pytest.approx(0.0, abs=1e-9)
    se = (W + C_) / math.sqrt(400_000)                                    # payoff takes two values W apart
    assert D.simulate_race(p + 0.03, T_, W, C_, n=400_000) < 3 * se and D.simulate_race(p - 0.03, T_, W, C_, n=400_000) > 0
    pd = D.race_threshold(T_, W, C_, discount=0.95)                         # a discounted prize needs less detection
    assert pd < p and D.race_value(pd, T_, W, C_, 0.95) == pytest.approx(0.0, abs=1e-6)


@pytest.mark.parametrize("h", [4.0, 5.0])
def test_siegmund_cusum_run_lengths_match_simulation(h):
    for mu in (0.0, 1.0):
        approx, sim = D.cusum_arl(mu, 0.5, h), D.simulate_cusum(mu, 0.5, h, runs=3000, seed=int(10 * h + mu))
        assert sim == pytest.approx(approx, rel=0.08), (h, mu)
    assert D.cusum_arl(0.0, 0.5, 4.0) == pytest.approx(336, rel=0.02)      # published value: 336 (k = 0.5, h = 4)


def test_cusum_threshold_round_trips_and_detection_slows_as_the_load_shrinks():
    h = D.cusum_h_for_arl0(0.25, 1e5)
    assert D.cusum_arl(0.0, 0.25, h) == pytest.approx(1e5, rel=1e-6)
    s = D.sigma_from_min_detectable(0.02, 0.01, 0.05)
    assert 0.02 / s == pytest.approx(2.3263 + 1.6449, rel=1e-3)
    rows = [D.race_against_detection(f, s, 120.0, 1e25, 100_000, 700.0, 0.5e-12) for f in (1e-2, 1e-3, 1e-4)]
    assert all(r["detected_first"] for r in rows)
    assert rows[0]["expected_detection_days"] < rows[1]["expected_detection_days"] < rows[2]["expected_detection_days"]
    assert rows[0]["days_to_threshold"] == pytest.approx(T.covert_days(1e25, 1e-2, 100_000).days)


# ---- inspections and randomness ------------------------------------------------------------------------------------
def test_hypergeometric_detection_matches_enumeration():
    N, Dm, n = 12, 3, 4
    missing = set(range(Dm))
    hit = sum(bool(missing & set(s)) for s in itertools.combinations(range(N), n))
    assert I.detection_probability(N, Dm, n) == pytest.approx(hit / math.comb(N, n))
    assert I.detection_probability(N, 0, n) == 0.0 and I.detection_probability(N, Dm, N - Dm + 1) == 1.0


def test_sample_size_is_the_smallest_that_reaches_the_assurance():
    n = I.sample_size(100_000, 1000, 0.95)
    assert n == 298
    assert I.detection_probability(100_000, 1000, n) >= 0.95 > I.detection_probability(100_000, 1000, n - 1)
    assert I.repeated_detection(100_000, 1000, 150, 4) > 0.99
    from closure.ledger import audit_sample_size                         # the older implementation agrees everywhere
    for N, Dm, a in [(100_000, 1000, 0.95), (1000, 10, 0.99), (500, 5, 0.95), (50, 2, 0.9), (40, 39, 0.5)]:
        assert I.sample_size(N, Dm, a) == audit_sample_size(N, Dm, a), (N, Dm, a)


def _beacon(parties=("IASC", "inspected", "observer")):
    cs = [B.new_contribution(p) for p in parties]
    return {c["party"]: c["commitment"] for c in cs}, {c["party"]: (c["nonce"], c["value"]) for c in cs}


def test_beacon_seed_is_reproducible_and_a_changed_or_withheld_reveal_is_caught():
    comm, rev = _beacon()
    s = B.seed(comm, rev)
    assert s == B.seed(dict(reversed(list(comm.items()))), rev) and len(s) == 32
    bad = dict(rev, inspected=(rev["inspected"][0], "00" * 32))
    with pytest.raises(B.BeaconError, match="inspected"):
        B.seed(comm, bad)
    with pytest.raises(B.BeaconError, match="no reveal from observer"):
        B.seed(comm, {k: v for k, v in rev.items() if k != "observer"})
    # going ahead without a withheld value is allowed only as a step before a public value is mixed in
    part = {k: v for k, v in rev.items() if k != "observer"}
    assert B.missing(comm, part) == ["observer"]
    s2 = B.seed(comm, part, allow_missing=True)
    assert s2 != s and s2 == B.seed({k: v for k, v in comm.items() if k != "observer"}, part)
    pub = bytes(range(32))
    assert B.finalize(s, pub) != s and B.finalize(s, pub) == B.finalize(s, pub) != B.finalize(s2, pub)
    with pytest.raises(ValueError):
        B.finalize(s, b"short")
    with pytest.raises(B.BeaconError, match="no party revealed"):
        B.seed(comm, {}, allow_missing=True)


def test_the_last_revealer_can_steer_a_rerun_and_cannot_steer_a_draw_finalized_with_a_later_public_value():
    """The inspected party hides one chip of five and one chip is sampled. It reveals last, so it knows the seed
    first. Rule A (an abort is answered with one fresh round): it withholds whenever its chip would be drawn, and is
    caught 1 time in 25 instead of 1 in 5. Rule B (the seed is finalized with a public value that does not exist
    yet): it cannot tell which draws to refuse, and withholding leaves the odds where they were."""
    import random
    rng = random.Random(7)
    chips, hidden, rounds = [f"GPU-{i}" for i in range(5)], "GPU-3", 3000

    def one_round():
        cs = [B.new_contribution(p) for p in ("inspector", "inspected")]
        return {c["party"]: c["commitment"] for c in cs}, {c["party"]: (c["nonce"], c["value"]) for c in cs}

    caught_a = caught_b = caught_b_withholding = 0
    for _ in range(rounds):
        comm, rev = one_round()
        if B.draw(B.seed(comm, rev), chips, 1)[0] == hidden:           # rule A: it sees this before revealing
            comm, rev = one_round()                                    # ... refuses, and the round is run again
            caught_a += B.draw(B.seed(comm, rev), chips, 1)[0] == hidden
        comm, rev = one_round()
        pub = rng.randbytes(32)                                        # rule B: published after the reveal deadline
        caught_b += B.draw(B.finalize(B.seed(comm, rev), pub), chips, 1)[0] == hidden
        part = {"inspector": rev["inspector"]}                         # ... and withholding blind changes nothing
        caught_b_withholding += B.draw(B.finalize(B.seed(comm, part, allow_missing=True), pub), chips, 1)[0] == hidden
    assert caught_a / rounds < 0.07                                    # about 1/25
    assert 0.17 < caught_b / rounds < 0.23 and 0.17 < caught_b_withholding / rounds < 0.23      # about 1/5


def test_draws_are_distinct_reproducible_and_uniform():
    comm, rev = _beacon()
    s = B.seed(comm, rev)
    ids = [f"GPU-{i:04d}" for i in range(50)]
    a = I.plan_sample(s, ids, 10, "2026-Q4")
    assert len(set(a)) == 10 and a == I.plan_sample(s, list(reversed(ids)), 10, "2026-Q4")
    assert a != I.plan_sample(s, ids, 10, "2027-Q1")
    r = I.inspect(ids, set(ids) - {a[0]}, a)
    assert r["violation"] and r["missing"] == [a[0]]
    counts = np.zeros(5)
    for i in range(5000):
        counts[int(B.draw(i.to_bytes(32, "big"), list(range(5)), 1)[0])] += 1
    chi2 = float(((counts - 1000.0) ** 2 / 1000.0).sum())
    assert chi2 < 18.47                                                    # chi-square, 4 df, p = 0.001
    lot = B.sortition(s, {"IN": [f"in{i}" for i in range(20)], "US": [f"us{i}" for i in range(20)]}, {"IN": 3, "US": 3})
    assert {k: len(v) for k, v in lot.items()} == {"IN": 3, "US": 3}


# ---- quorum --------------------------------------------------------------------------------------------------------
def test_k_of_n_approval_counts_distinct_valid_members_only():
    keys = [Ed25519PrivateKey.generate() for _ in range(5)]
    members = {Q.public_hex(k): f"member{i}" for i, k in enumerate(keys)}
    action = {"action": "halt training cluster X", "expires": 2e9}
    k = Q.majority(5, 0.6)
    assert k == 3 and Q.majority(15, 0.75) == 12
    sigs = [Q.sign(keys[0], action), Q.sign(keys[0], action), Q.sign(keys[1], action)]
    assert not Q.verify(action, sigs, members, k, now=1e9)["approved"]                   # a duplicate counts once
    ok = Q.verify(action, sigs + [Q.sign(keys[2], action)], members, k, now=1e9)
    assert ok["approved"] and ok["valid"] == ["member0", "member1", "member2"]
    other = Q.sign(keys[3], {"action": "something else", "expires": 2e9})
    outsider = Q.sign(Ed25519PrivateKey.generate(), action)
    r = Q.verify(action, sigs + [other, outsider], members, k, now=1e9)
    assert not r["approved"] and any("bad signature" in p for p in r["problems"]) and any("unknown" in p for p in r["problems"])
    assert not Q.verify(action, sigs + [Q.sign(keys[2], action)], members, k, now=3e9)["approved"]   # expired


# ---- location ------------------------------------------------------------------------------------------------------
def test_great_circle_and_light_speed_bounds():
    assert G.great_circle_km(51.5074, -0.1278, 48.8566, 2.3522) == pytest.approx(343.5, abs=1.5)   # London-Paris
    assert G.great_circle_km(0, 0, 0, 90) == pytest.approx(math.pi / 2 * G.EARTH_R_KM)
    assert G.max_distance_km(1e-3) == pytest.approx(149.896, rel=1e-4)


def test_delay_bounds_are_sound_whatever_the_path_and_the_relays():
    rng = np.random.default_rng(1)
    for _ in range(500):
        lat, lon = float(np.degrees(np.arcsin(rng.uniform(-1, 1)))), float(rng.uniform(-180, 180))
        recs = []
        for j in range(4):
            la, lo = float(rng.uniform(-60, 60)), float(rng.uniform(-180, 180))
            d = G.great_circle_km(la, lo, lat, lon)
            v = rng.uniform(G.C_KM_PER_S / 1.6, G.C_KM_PER_S)                # fibre .. vacuum
            rtt = 2 * d / v + rng.exponential(0.002)                         # plus queues, relays, processing
            recs.append(G.Record(f"L{j}", la, lo, "00", 1, 1, rtt, G.max_distance_km(rtt)))
        assert not G.excluded(recs, lat, lon)                               # never excludes where the chip is
        assert G.check(recs, lat, lon)["consistent"]
        assert G.check(recs, lat, lon)["proven_within_km"] >= 0.0


def test_a_nearby_landmark_proves_closeness_and_exposes_a_false_declaration():
    frankfurt, virginia = (50.11, 8.68), (38.95, -77.45)
    near = G.Record("FRA-1", 50.0, 8.6, "00", 10, 10, 2e-3, G.max_distance_km(2e-3))            # 2 ms: < 300 km
    r = G.check([near], *frankfurt)
    assert r["consistent"] and r["proven_within_km"] < 320
    assert G.excluded([near], *virginia) and not G.check([near], *virginia)["consistent"]


def _session(chip_key, expected_pub, rounds=12):
    out = {}
    ready = threading.Event()

    def serve():
        out["rec"] = G.serve_landmark("127.0.0.1", 0, "test-landmark", 45.5, -73.6, expected_pub, rounds, timeout=30,
                                      ready=lambda port: (out.__setitem__("port", port), ready.set()))
    t = threading.Thread(target=serve)
    t.start()
    assert ready.wait(10)
    G.run_chip("127.0.0.1", out["port"], chip_key, timeout=30)
    t.join(30)
    return out["rec"]


def test_landmark_and_chip_over_tcp_and_tampering_is_caught(tmp_path):
    key = G.keygen()
    rec = _session(key, G.pub_hex(key))
    assert rec.valid_rounds == rec.rounds == 12 and rec.min_rtt_s < 0.05 and G.reverify(rec)
    assert G.check([rec], 45.5, -73.6)["consistent"]
    p = tmp_path / "rec.json"
    p.write_text(json.dumps(rec.to_dict()))
    loaded = G.load_records([p])[0]
    nonce, sig, rtt = loaded.samples[0]
    loaded.samples[0] = (nonce, ("00" if sig[:2] != "00" else "11") + sig[2:], rtt)
    assert not G.reverify(loaded)
    imposter = _session(G.keygen(), G.pub_hex(key), rounds=5)                # answers with the wrong key
    assert imposter.valid_rounds == 0 and imposter.max_km is None
    assert not G.check([imposter], 45.5, -73.6)["consistent"]


# ---- the middle-powers agreement -----------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def table():
    countries, world = C.load()
    assert world.iso3 == "WLD" and len(countries) == 213 and all(i in countries for i in C.EU27)
    return C.players(countries, world)


def test_activation_needs_both_twenty_percent_shares(table):
    g, p = C.shares(["EU27", "IND"], table)
    assert g > 0.20 and p > 0.20 and C.activates(["EU27", "IND"], table)
    assert not C.activates(["EU27"], table) and not C.activates(["IND"], table)
    assert "USA" not in table and "CHN" not in table and "DEU" not in table


def test_the_smallest_activating_coalition_is_the_eu_and_india(table):
    r = C.smallest_coalitions(table, max_size=3)
    assert r["size"] == 2 and r["exhaustive"] and r["coalitions"] == [("EU27", "IND")]


def test_without_the_eu_bloc_or_without_india_seven_members_are_needed(table):
    countries, world = C.load()
    each_t = C.players(countries, world, eu_as_bloc=False)

    def top(tab, k, axis, without=()):
        return sum(sorted((v[axis] for n, v in tab.items() if n not in without), reverse=True)[:k])
    # Bounds that make the search exact: no 6 players reach 20% of GDP (each member separately) or, without India,
    # 20% of population; 7 without Germany or without Japan cannot reach 20% of GDP; 7 without India, not 20% of people.
    assert top(each_t, 6, 0) < 0.20 and top(each_t, 7, 0, ("DEU",)) < 0.20 and top(each_t, 7, 0, ("JPN",)) < 0.20
    assert top(each_t, 7, 1, ("IND",)) < 0.20 and top(table, 6, 1, ("IND",)) < 0.20
    each = C.smallest_coalitions(each_t, max_size=7, top=30)
    assert each["size"] == 7 and all({"IND", "DEU", "JPN"} <= set(c) for c in each["coalitions"])
    no_india = C.smallest_coalitions({k: v for k, v in table.items() if k != "IND"}, max_size=7, top=25)
    assert no_india["size"] == 7 and ("EU27", "JPN", "IDN", "PAK", "BRA", "BGD", "RUS") in no_india["coalitions"]
    # the bound proves it without a search: no six players can reach both quotas, so seven is the least
    assert no_india["at_least"] == 7 and no_india["proved_minimal"] and each["at_least"] == 7 and each["proved_minimal"]


def test_the_size_bound_is_a_bound_and_the_search_says_when_it_found_nothing(table):
    assert C.size_bound(table) == 2                                    # the EU and India: found at the bound
    r = C.smallest_coalitions(table, max_size=3)
    assert r["at_least"] == 2 and r["proved_minimal"]
    small = {"A": (0.15, 0.01), "B": (0.01, 0.15), "C": (0.06, 0.06), "D": (0.05, 0.05)}
    assert C.size_bound(small) == 2                                    # A's GDP with C's, B's people with C's
    r = C.smallest_coalitions(small, max_size=4)
    assert r["size"] == 3 and r["at_least"] == 2 and r["proved_minimal"]    # sizes below 3 were searched in full
    assert C.size_bound({"A": (0.1, 0.1)}) is None
    none = C.smallest_coalitions({k: v for k, v in table.items() if k != "IND"}, max_size=6)
    assert none["size"] is None and none["at_least"] == 7 and "fewer than 7" in none["note"]


def test_the_coalition_command_reproduces_both_claims_as_documented(capsys):
    for argv, size, member in ((["treaty", "coalition", "--permutations", "200"], 2, "IND"),
                               (["treaty", "coalition", "--exclude", "USA,CHN,IND", "--permutations", "200"], 7, "EU27")):
        assert main(argv) == 0
        out = json.loads(capsys.readouterr().out)
        assert out["smallest"]["size"] == size and out["smallest"]["proved_minimal"]
        assert all(member in c["members"] for c in out["smallest"]["coalitions"])


def test_shapley_shubik_estimate_matches_exact_enumeration():
    small = {"A": (0.10, 0.02), "B": (0.08, 0.15), "C": (0.05, 0.05), "D": (0.02, 0.10), "E": (0.01, 0.01),
             "F": (0.03, 0.04)}
    ex = C.shapley_exact(small)
    mc = C.shapley_shubik(small, permutations=40000, seed=3)
    for k in small:
        assert abs(mc[k][0] - ex[k]) < 4 * mc[k][1] + 1e-9, k
    assert sum(ex.values()) == pytest.approx(1.0)
    assert ex["E"] < ex["A"] and ex["E"] < ex["B"]


def test_redlines_map_to_the_ladder_with_leak_escalation():
    assert C.assess({}) == (0, [])
    assert C.assess({"economy_automated": 0.30})[0] == C.FULL
    assert C.assess({"ai_rnd_engineer_speedup": 4})[0] == C.WIDE
    assert C.assess({"ai_rnd_engineer_speedup": 2, "ai_system_leaked": True})[0] == C.WIDE      # 3 + 1
    assert C.assess({"ai_escaped_or_uncontrolled": True, "ai_system_leaked": True})[0] == C.SELF_DEFENCE
    with pytest.raises(ValueError, match="unknown findings"):
        C.assess({"economy_automatd": 0.3})


def test_six_months_past_a_line_escalates_and_stopping_resets():
    wide = {"ai_rnd_engineer_speedup": 4.0}
    tl = C.run_timeline([wide] * 13 + [{}])
    levels = [m["level"] for m in tl]
    assert levels[:6] == [C.WIDE] * 6 and levels[6:12] == [C.FULL] * 6 and levels[12] == C.SELF_DEFENCE
    assert levels[13] == 0
    assert C.presumed_level(5e25, [(1e24, {"ai_rnd_compute_above_threshold": True}),
                                   (1e26, {"ai_rnd_engineer_speedup": 10})])[0] == 3
    assert C.impromptu_session(3, 10) and not C.impromptu_session(2, 10) and C.impromptu_session(3, 12)


# ---- command line --------------------------------------------------------------------------------------------------
def test_treaty_commands_run(capsys, tmp_path):
    assert main(["treaty", "thresholds"]) == 0
    assert "1e+25" in capsys.readouterr().out
    assert main(["treaty", "coalition", "--members", "EU27,IND", "--permutations", "2000", "--max-size", "3"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["members"]["activates"] and out["smallest"]["size"] == 2
    f = tmp_path / "findings.json"
    f.write_text(json.dumps([{"economy_automated": 0.12}] * 8))
    assert main(["treaty", "redlines", "--findings", str(f)]) == 0
    assert json.loads(capsys.readouterr().out)[7]["measure"] == "full embargo"
    assert main(["treaty", "inspect-plan", "--declared", "1000", "--missing", "10"]) == 0
    assert json.loads(capsys.readouterr().out)["sample"] == I.sample_size(1000, 10, 0.95)
    run = tmp_path / "T1"
    run.mkdir()
    (run / "results.json").write_text(json.dumps({"status": "SIMULATED", "closure_gap_fraction": None, "slack": {}}))
    (run / "prereg.json").write_text(json.dumps({"cfg": {"p_max_w": 700.0}}))
    assert main(["treaty", "covert-days", "--run", str(run)]) == 1 and "no closure gap" in capsys.readouterr().out


# ---- suspended clauses, MIRI's thresholds, interconnect arithmetic (0.9.0) -------------------------------------------
def _panel(n=5):
    keys = [Ed25519PrivateKey.generate() for _ in range(n)]
    return keys, {Q.public_hex(k): f"member-{i}" for i, k in enumerate(keys)}


def test_a_suspended_clause_switches_on_only_for_a_finding_the_panel_signed():
    keys, members = _panel(5)
    rec = K.finding("State X", {"ai_rnd_engineer_speedup": 4.0}, issued=1000.0, expires=5000.0)
    three = [Q.sign(k, rec) for k in keys[:3]]
    on = K.in_force(rec, three, members, 3, now=2000.0)
    assert on["in_force"] and on["level"] == 4 and on["measure"] == C.LEVELS[4] and on["actor"] == "State X"
    assert not K.in_force(rec, three[:2], members, 3, now=2000.0)["in_force"]            # short of its quorum
    assert not K.in_force(rec, three, members, 3, now=6000.0)["in_force"]                # expired
    altered = {**rec, "findings": {"ai_rnd_engineer_speedup": 10.0}}                     # altered after signing
    off = K.in_force(altered, three, members, 3, now=2000.0)
    assert not off["in_force"] and off["level"] == 0 and len(off["quorum"]["problems"]) == 3
    outsiders = [Q.sign(Ed25519PrivateKey.generate(), rec) for _ in range(3)]            # not on the panel
    assert not K.in_force(rec, outsiders, members, 3, now=2000.0)["in_force"]
    other = {"type": "transfer", "findings": {"ai_rnd_engineer_speedup": 4.0}}            # signed, but not a finding
    r = K.in_force(other, [Q.sign(k, other) for k in keys[:3]], members, 3, now=0.0)
    assert not r["in_force"] and "not a finding" in r["quorum"]["problems"][-1]
    clean = K.finding("State X", {}, issued=1000.0)                                      # a signed finding of nothing
    assert not K.in_force(clean, [Q.sign(k, clean) for k in keys[:3]], members, 3, now=2000.0)["in_force"]
    with pytest.raises(ValueError, match="unknown findings"):
        K.finding("State X", {"typo": True}, issued=0.0)


def test_a_clause_timeline_counts_only_signed_months_and_keeps_the_persistence_rules():
    keys, members = _panel(4)

    def month(i, findings, signers=3):
        rec = K.finding("State X", findings, issued=float(i))
        return {"record": rec, "approvals": [Q.sign(k, rec) for k in keys[:signers]]}
    wide = {"ai_rnd_engineer_speedup": 4.0}
    rows = K.timeline([month(i, wide) for i in range(8)], members, 3)
    assert [r["level"] for r in rows] == [4] * 6 + [5, 5] and all(r["finding_signed"] for r in rows)
    # the same findings with a month the panel did not sign: that month counts for nothing and the six-month clock restarts
    rows = K.timeline([month(i, wide, signers=2 if i == 3 else 3) for i in range(8)], members, 3)
    assert [r["level"] for r in rows] == [4, 4, 4, 0, 4, 4, 4, 4] and rows[3]["finding_signed"] is False
    assert K.timeline([None, month(1, wide)], members, 3)[0]["finding_signed"] is None


def test_the_clause_command_reads_three_files(tmp_path, capsys):
    keys, members = _panel(3)
    rec = K.finding("State X", {"ai_escaped_or_uncontrolled": True}, issued=10.0)
    (tmp_path / "f.json").write_text(json.dumps(rec)); (tmp_path / "m.json").write_text(json.dumps(members))
    (tmp_path / "a.json").write_text(json.dumps([Q.sign(k, rec) for k in keys[:2]]))
    argv = ["treaty", "clause", "--finding", str(tmp_path / "f.json"), "--approvals", str(tmp_path / "a.json"),
            "--members", str(tmp_path / "m.json")]
    assert main(argv + ["--k", "2"]) == 0 and json.loads(capsys.readouterr().out)["level"] == 6
    assert main(argv + ["--k", "3"]) == 1 and not json.loads(capsys.readouterr().out)["in_force"]


def test_miris_agreement_thresholds_are_named_and_usable(capsys):
    t = T.THRESHOLDS
    assert (t["miri-monitored"].value, t["miri-post-training"].value, t["miri-strict"].value) == (1e22, 1e23, 1e24)
    assert t["miri-cluster"].value == 16 and t["miri-cluster"].unit == "H100e"
    assert T.flop_threshold("miri-strict") == 1e24 and T.flop_threshold("3e24") == 3e24 and T.flop_threshold(1e25) == 1e25
    with pytest.raises(ValueError, match="H100e"):
        T.flop_threshold("miri-cluster")
    with pytest.raises(ValueError, match="neither a number"):
        T.flop_threshold("nonsense")
    # a hundredth of the threshold is reached in a hundredth of the time
    a, b = T.covert_days(T.flop_threshold("miri-strict"), 0.05, 1000), T.covert_days(T.flop_threshold("miri-monitored"), 0.05, 1000)
    assert b.days == pytest.approx(a.days / 100)
    assert main(["treaty", "covert-days", "--threshold", "miri-monitored", "--gap", "0.05", "--fleet", "1000"]) == 0
    assert json.loads(capsys.readouterr().out)["threshold_flop"] == 1e22
    assert main(["treaty", "covert-days", "--threshold", "nonsense", "--gap", "0.05"]) == 2


def test_interconnect_arithmetic():
    # 1e11 values of 2 bytes: 200 GB a pod per exchange; among 4 pods each sends 2 * 3/4 of that
    assert W.payload_bytes(1e11) == 2e11 and W.sent_per_exchange(2e11, 4) == pytest.approx(3e11)
    need = W.needed_gbps(1e11, steps_per_s=1.0, pods=4)
    assert need == pytest.approx(3e11 * 8 / 1e9)                                          # 2400 Gbit/s
    assert W.needed_gbps(1e11, 1.0, 4, sync_every=10, compression=100) == pytest.approx(need / 1000)
    assert W.slowdown(need, 1e11, 1.0, 4) == 1.0 and W.slowdown(need / 50, 1e11, 1.0, 4) == pytest.approx(50)
    assert W.slowdown(0.0, 1e11, 1.0, 4) == float("inf") and W.exchanges_per_s(0.0, 1e11, 4) == 0.0
    assert W.exchanges_per_s(need, 1e11, 4) == pytest.approx(1.0)
    assert W.inference_gbps(1e6, 16.0) == pytest.approx(0.128)
    r = W.assess(cap_gbps=1.0, params=1e11, steps_per_s=1.0, pods=4, tokens_per_s=1e6)
    assert r["cap_separates_them"] and r["inference_fits"] and r["training_slowdown"] == pytest.approx(2400)
    assert r["headroom_between_them"] == pytest.approx(2400 / 0.128)
    assert not W.assess(0.1, 1e11, 1.0, 4, 1e6)["inference_fits"]                         # a cap too thin to serve
    assert not W.assess(5000.0, 1e11, 1.0, 4, 1e6)["cap_separates_them"]                  # a cap too wide to matter
    for bad in (lambda: W.payload_bytes(0), lambda: W.sent_per_exchange(1.0, 1), lambda: W.needed_gbps(1e9, 0, 2)):
        with pytest.raises(ValueError):
            bad()


def test_the_bandwidth_command(capsys):
    assert main(["treaty", "bandwidth", "--cap-gbps", "1", "--params", "1e11", "--pods", "4", "--tokens-per-s", "1e6"]) == 0
    assert json.loads(capsys.readouterr().out)["cap_separates_them"] is True
