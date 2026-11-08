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
from closure.treaty import beacon as B
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
