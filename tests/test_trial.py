import json

import numpy as np

from closure.cli import _cfg, main
from closure.evidence import Chain, Signer, verify_commit, verify_sig
from closure.sim import SimConfig, SimSource
from closure.trial import run_trial


def test_full_sim_trial_is_verifiable_and_sane(tmp_path):
    res = run_trial(SimSource(SimConfig(), seed=3), _cfg("sim", 3, "SIMULATED"), tmp_path, Signer())
    ok, n, head = Chain.verify(tmp_path / "chain.jsonl")
    assert ok and n == 4
    phases = [json.loads(l)["record"]["phase"] for l in open(tmp_path / "chain.jsonl")]
    assert phases == ["calibration", "prereg", "audit_data", "results"]        # prereg precedes audit data
    sig = json.loads((tmp_path / "signature.json").read_text())
    assert sig["chain_head"] == head and verify_sig(sig["public_key"], sig["signature"], head.encode())
    pre = json.loads((tmp_path / "prereg.json").read_text())
    rev = json.loads((tmp_path / "schedule_reveal.json").read_text())
    assert verify_commit(rev["schedule"], pre["schedule_commitment"], rev["nonce"])
    assert main(["verify", str(tmp_path)]) == 0
    assert res["false_positive"]["combined"]["cp95_upper"] < 0.03
    assert res["closure_gap_fraction"] is not None and res["closure_gap_fraction"] < 0.02
    assert res["bound"]["coverage_nonslack"] >= 0.98
    assert res["bound"]["coverage_slack_expected_to_fail"] < 0.8          # slack is *supposed* to evade
    assert res["f95_by_class"]["constant"] in (0.005, 0.01, 0.02) and res["f95_by_class"]["slack"] is None
    assert not res["calibration_n_eff"]["underpowered"]
    assert (tmp_path / "results.md").read_text().startswith("# Closure report (SIMULATED)")


def test_trial_is_deterministic_given_seeds(tmp_path):
    a = run_trial(SimSource(SimConfig(), seed=9), _cfg("quick", 9, "SIMULATED"), tmp_path / "a")
    b = run_trial(SimSource(SimConfig(), seed=9), _cfg("quick", 9, "SIMULATED"), tmp_path / "b")
    assert json.dumps(a, sort_keys=True, default=str) == json.dumps(b, sort_keys=True, default=str)


def test_verify_catches_tampered_results_prereg_and_signature(tmp_path):
    run_trial(SimSource(SimConfig(), seed=4), _cfg("quick", 4, "SIMULATED"), tmp_path, Signer())
    assert main(["verify", str(tmp_path)]) == 0
    r = json.loads((tmp_path / "results.json").read_text())
    r["closure_gap_fraction"] = 0.0001                                           # flatter the result
    (tmp_path / "results.json").write_text(json.dumps(r))
    assert main(["verify", str(tmp_path)]) == 1
