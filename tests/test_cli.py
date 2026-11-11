import json

import numpy as np
import pytest

from closure import traffic as T
from closure.cli import main


def test_selftest_passes(capsys):
    assert main(["selftest"]) == 0
    assert "FAIL" not in capsys.readouterr().out


def test_preflight_mock_and_real_do_not_crash(capsys):
    assert main(["preflight", "--mock", "--json"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert all(r["status"] in ("PASS", "SKIP", "WARN") for r in out)
    main(["preflight", "--json"])                                      # no GPU here: may FAIL, must not raise
    real = json.loads(capsys.readouterr().out)
    assert any(r["check"] == "pynvml/NVML init" for r in real)


def test_hw_trial_refuses_without_confirmation(tmp_path):
    assert main(["hw-trial", "--out", str(tmp_path)]) == 2


def test_hw_trial_mock_then_verify(tmp_path, capsys):
    assert main(["hw-trial", "--mock", "--profile", "smoke", "--out", str(tmp_path)]) == 0
    assert main(["verify", str(tmp_path)]) == 0


def test_hw_selftest_mock(capsys):
    assert main(["hw-selftest", "--mock", "--windows", "20"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["r2"] > 0.9 and out["idle_power_w"] > 500


def test_state_sim_cli(capsys):
    assert main(["state-sim"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["honest"]["pass_rate"] >= 0.98 and out["slow_tier_20pct"]["pass_rate"] <= 0.1


def test_traffic_check_cli(tmp_path, capsys):
    pk = [T.Pkt(1 + i * 0.01, "10.0.0.1", "10.0.0.2", 5000, 443, 6, 1000) for i in range(50)]
    T.write_pcap(tmp_path / "a.pcap", pk)
    (tmp_path / "v.json").write_text(json.dumps({"6|10.0.0.1:5000|10.0.0.2:443": 50000}))
    assert main(["traffic-check", str(tmp_path / "a.pcap"), str(tmp_path / "v.json")]) == 0
    (tmp_path / "v2.json").write_text(json.dumps({"6|10.0.0.1:5000|10.0.0.2:443": 20000}))
    assert main(["traffic-check", str(tmp_path / "a.pcap"), str(tmp_path / "v2.json")]) == 1


def test_dcbus_analyze_recovers_clock_skew_and_reanalyses(tmp_path, capsys):
    assert main(["sim-trial", "--profile", "smoke", "--seed", "2", "--out", str(tmp_path)]) == 0
    z = np.load(tmp_path / "raw.npz")
    parts = [n for n in ("warm", "ref", "aud") if f"{n}_t0" in z.files]       # every window, in the order it ran
    t0 = np.concatenate([z[f"{n}_t0"] for n in parts])
    E = np.concatenate([z[f"{n}_E"] for n in parts])
    order = np.argsort(t0)
    t0, E = t0[order], E[order]
    skew = 2.3
    tb = np.arange(0, t0[-1] + 20, 0.1)
    idx = np.clip(np.floor(tb - skew - t0[0]).astype(int), 0, len(E) - 1)
    pb = E[idx] * (1 + 0.003 * np.random.default_rng(0).standard_normal(len(tb)))
    csv = tmp_path / "bus.csv"
    np.savetxt(csv, np.column_stack([tb, pb]), delimiter=",", header="timestamp_s,power_w", comments="")
    capsys.readouterr()
    assert main(["dcbus-analyze", "--run", str(tmp_path), "--csv", str(csv)]) == 0
    out = capsys.readouterr().out
    off = float(out.split("clock offset applied:")[1].split("s")[0])
    assert abs(off - skew) < 0.3
    res = json.loads((tmp_path / "results_dcbus.json").read_text())
    assert res["status"].startswith("HARDWARE+DCBUS")


def test_hw_state_old_challenge_size_was_sampling_limited_and_the_default_now_reaches_99_percent(capsys):
    # Run 3 on a Colab T4 (docs/DEVIATIONS.md section 3): k = 8 with 8 of 32 blocks parked detected 94.0%, under
    # the registered 99%. No 8-block challenge can do better than 93.0% there: the misses sample no parked block.
    # Both checks are on what the design guarantees, not on the luck of 100 random challenges: the sampling limit is
    # combinatorics, and every challenge that touches a parked block is caught, so the misses are exactly the
    # challenges that touched none.
    small = ["--trials", "100", "--threshold-alpha", "1e-6"]       # too few challenges to hold a 1% rate to the letter
    main(["hw-state", "--mock", "--block-mb", "1", "--k", "8", *small])
    old = json.loads(capsys.readouterr().out)
    assert old["parked_blocks"] == 8 and abs(old["sampling_limit"] - 0.9301) < 1e-4 and old["sampling_limit"] < 0.99
    assert old["detected_when_touching_parked"] == 1.0
    assert old["parked_detection"] == pytest.approx(old["challenges_touching_parked"] / 100)
    main(["hw-state", "--mock", "--block-mb", "1", *small])
    new = json.loads(capsys.readouterr().out)
    assert new["k"] == 17 and new["sampling_limit"] > 0.999 and new["k_chosen"].startswith("for 99.9%")
    assert new["detected_when_touching_parked"] == 1.0
    assert new["parked_detection"] == pytest.approx(new["challenges_touching_parked"] / 100)
    assert new["challenges_touching_parked"] >= 97 and new["honest_false_alarm"] <= 0.01


def test_hw_state_mock_separates_parked_from_resident(capsys):
    # a run this small checks the pipeline, not a 1% rate: its threshold sits far out, as tier0's mock run sets it
    # (and 24 of 32 blocks per challenge with 11 parked, so that no challenge can miss them all)
    assert main(["hw-state", "--mock", "--block-mb", "1", "--blocks", "32", "--k", "24", "--trials", "60",
                 "--park-frac", "0.3", "--threshold-alpha", "1e-6"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["status"] == "MOCK" and out["parked_detection"] == 1.0 and out["honest_false_alarm"] <= 0.01
    assert out["parked_blocks"] == 11 and out["sampling_limit"] == 1.0
    assert out["parked_median_slowest_block_s"] > 5 * out["honest_median_slowest_block_s"]
    assert out["statistic"] == "slowest block of each challenge" and out["total_time"]["parked_detection"] >= 0.99
    # one pass in random order: four honest challenges for the threshold and two judged, for every parked-prover one
    assert out["challenges"] == {"calibration": 240, "honest": 120, "parked": 60,
                                 "order": "one pass, interleaved at random, back to back"}
    assert out["threshold_alpha"] == 1e-6 and out["digests_wrong"] == 0 and out["digests_verified"] == 10
    from closure.cli import STATE_ALPHA, STATE_MIX
    assert STATE_ALPHA == 0.005 and STATE_MIX == (4, 2, 1)       # the registered run: half the 1% allowance
    one = out["touching_one_parked_block"]
    assert one["detected"] == one["n"] == 0                       # 24 blocks always include at least three parked


def test_hw_state_fails_a_prover_whose_digests_are_wrong(capsys, monkeypatch):
    from closure import state as S
    monkeypatch.setattr(S.Prover, "answer_blocks", lambda self, idx, K: (12345, [1e-5] * len(idx)))
    assert main(["hw-state", "--mock", "--block-mb", "1", "--trials", "50", "--verify-every", "10"]) == 1
    out = json.loads(capsys.readouterr().out)
    assert out["digests_wrong"] == out["digests_verified"] > 0 and not out["digest_ok_honest"] and not out["pass"]


def test_pause_after_prereg_blocks_until_enter_and_precedes_audit(tmp_path, monkeypatch, capsys):
    seen = {}

    def fake_input(*a):
        seen["audit_started"] = (tmp_path / "raw.npz").exists()      # raw.npz is written only after the audit
        seen["prereg_exists"] = (tmp_path / "prereg.json").exists()
        return ""

    monkeypatch.setattr("builtins.input", fake_input)
    assert main(["hw-trial", "--mock", "--profile", "smoke", "--pause-after-prereg", "--out", str(tmp_path)]) == 0
    assert seen == {"audit_started": False, "prereg_exists": True}
    assert "PRE-REGISTRATION WRITTEN" in capsys.readouterr().out
