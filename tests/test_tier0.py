"""`closure tier0`: the whole pilot as one unattended command, bundled without the private key."""
import json
import tarfile

from closure.cli import main


def test_tier0_mock_runs_every_step_and_bundles_everything_but_the_private_key(tmp_path, capsys):
    out = tmp_path / "t0"
    assert main(["tier0", "--mock", "--skip-tests", "--out", str(out)]) == 0
    summary = (out / "SUMMARY.md").read_text()
    for step in ("selftest", "preflight", "hw-selftest", "hw-probe", "hw-state", "hw-trial", "verify"):
        assert f"| {step} |" in summary
    assert "every step ran" in summary and "MOCK" in summary and "skipped" not in summary
    assert "probe_hash_ok: True" in summary and "operand" in summary
    with tarfile.open(out / "tier0_bundle.tar.gz") as tf:
        names = tf.getnames()
    assert any(n.endswith("T1-smoke/chain.jsonl") for n in names) and any(n.endswith("logs/05-hw-state.log") for n in names)
    assert not any(n.endswith("signing_key.bin") for n in names)
    assert (out / "T1-smoke" / "signing_key.bin").exists()                  # kept on the machine, never bundled
    pre = json.loads((out / "T1-smoke" / "prereg.json").read_text())
    assert pre["cfg"]["probe_sha256"] == json.loads((out / "probe.json").read_text())["sha256"]
    assert "--confirm-hardware" not in (out / "logs" / "06-hw-trial.log").read_text().splitlines()[0]
    assert "## Calibration drift (assumption A2" in summary and "drift suspected:" in summary
    assert "## Pre-registered T1 decision rules" in summary and "H1.2 false alarms" in summary
    from closure.tier0 import provenance
    line = summary.splitlines()[2]
    assert f"({provenance()})" in line and (provenance().startswith("commit ") or "git" in provenance())
    # the smoke trial is the long trial's design in miniature (amendment v0.6)
    cfg = pre["cfg"]
    assert (cfg["calibration"], cfg["schedule"], cfg["analysis"], cfg["L"]) == ("interleaved", "balanced", "link", 20)
    assert (cfg["n_ref_blocks"], cfg["n_audit_blocks"], cfg["warmup_blocks"], cfg["seed"]) == (100, 80, 3, 1)
    assert "link.py" in pre["analysis"] and "order_commitment" in pre
    assert "the threshold is conformal" in summary and "/40 " in summary and "- analysis: link" in summary
    assert "H1.4 the time bound covers the seconds the hidden load really ran" in summary
    assert "judged by slowest block of each challenge" in summary and "by total time, the statistic until 0.8.0" in summary
    assert "trial seed 1 " in capsys.readouterr().out
    assert "--seed 1" in (out / "logs" / "06-hw-trial.log").read_text().splitlines()[0]
    assert "--verify-every 5 --threshold-alpha 1e-6" in (out / "logs" / "05-hw-state.log").read_text().splitlines()[0]
    assert "120 honest and 60 parked-prover challenges, judged against a threshold from 240 more honest ones" in summary
    assert "wrong: 0" in summary and "touched exactly one parked block" in summary
    assert "- pass = True: honest false alarm " in summary and "parked-block detection 1.0000 (block 1 MB, k = 24" in summary


def test_tier0_refuses_without_confirmation_and_into_a_used_directory(tmp_path):
    assert main(["tier0", "--out", str(tmp_path / "a")]) == 2
    used = tmp_path / "b"
    used.mkdir()
    (used / "old.txt").write_text("earlier run")
    assert main(["tier0", "--mock", "--skip-tests", "--out", str(used)]) == 2


def test_stamp_prereg_never_waits_for_the_keyboard(tmp_path, monkeypatch, capsys):
    def no_input(*a, **k):
        raise AssertionError("input() was called")
    monkeypatch.setattr("builtins.input", no_input)
    monkeypatch.setattr("closure.cli.shutil.which", lambda name: None)       # no `ots` client installed
    assert main(["hw-trial", "--mock", "--profile", "smoke", "--stamp-prereg", "--out", str(tmp_path / "r")]) == 0
    out = capsys.readouterr().out
    assert "sha256(canonical)" in out and "not externally timestamped" in out
    assert main(["verify", str(tmp_path / "r")]) == 0


def test_tier0_long_trial_interleaves_calibration_and_reads_the_decision_rules(tmp_path):
    out = tmp_path / "t0"
    assert main(["tier0", "--mock", "--skip-tests", "--trial-profile", "long", "--out", str(out)]) == 0
    summary = (out / "SUMMARY.md").read_text()
    assert "## Long trial (T1)" in summary and "every step ran" in summary
    assert "order_commitment_ok: True" in summary and "`T1-long/signing_key.bin`" in summary
    assert "H1.2 false alarms" in summary and "/204 " in summary              # enough null blocks to decide H1.2
    assert "reference blocks were interleaved with the audit" in summary
    cfg = json.loads((out / "T1-long" / "prereg.json").read_text())["cfg"]
    assert (cfg["calibration"], cfg["schedule"], cfg["L"], cfg["warmup_blocks"]) == ("interleaved", "balanced", 60, 5)
    assert cfg["analysis"] == "link" and "H1.1 calibration valid (the threshold is conformal" in summary
    res = json.loads((out / "T1-long" / "results.json").read_text())
    assert res["methods_used"]["combined"] == ["conformal"] and res["link"]["reference_blocks"] == 144
    assert len(res["blocks"]["kind"]) == 396 and "hidden_busy_s" in res["blocks"]
    assert "--profile long" in (out / "logs" / "06-hw-trial.log").read_text().splitlines()[0]
    with tarfile.open(out / "tier0_bundle.tar.gz") as tf:
        names = tf.getnames()
    assert any(n.endswith("T1-long/raw.npz") for n in names) and not any(n.endswith("signing_key.bin") for n in names)


def test_a_step_that_ran_but_failed_its_check_is_named_in_the_outcome():
    from closure.tier0 import _ran
    ok = {"key": "selftest", "skipped": False, "exit": 0}
    assert _ran([ok]) == "every step ran"
    text = _ran([ok, {"key": "hw-probe", "skipped": False, "exit": 1}, {"key": "hw-state", "skipped": False, "exit": 1}])
    assert text.startswith("every step ran; 2 reported a failed check (hw-probe, hw-state)")


def test_tier0_seed_is_fresh_on_hardware_fixed_in_mock_and_passed_to_the_trial(tmp_path):
    """Runs 1 to 5 all used seed 1: one load sequence and, per profile, one hidden-load schedule. A hardware run now
    draws its own; a mock run stays repeatable, and --seed sets it."""
    from closure.tier0 import plan
    argv = dict((k, a) for k, _, a, _ in plan(tmp_path, 0, mock=False, run_tests=False, seed=424242,
                                              campaign="kaggle-x:2/2"))["hw-trial"]
    assert argv[argv.index("--seed") + 1] == "424242" and argv[argv.index("--campaign") + 1] == "kaggle-x:2/2"
    out = tmp_path / "t0"
    assert main(["tier0", "--mock", "--skip-tests", "--seed", "77", "--out", str(out)]) == 0
    assert json.loads((out / "T1-smoke" / "prereg.json").read_text())["cfg"]["seed"] == 77


def test_two_mock_tier0_runs_declared_as_a_campaign_pool_into_one_reading(tmp_path, capsys):
    """What notebooks/tier0_kaggle.ipynb does with its two GPUs, on the fake rig."""
    runs = []
    for i in (1, 2):
        out = tmp_path / f"gpu{i}"
        assert main(["tier0", "--mock", "--skip-tests", "--campaign", f"kaggle-test:{i}/2", "--out", str(out)]) == 0
        assert f"trial {i} of 2 in campaign `kaggle-test`" in (out / "SUMMARY.md").read_text()
        runs.append(str(out / "T1-smoke"))
    seeds = [json.loads((tmp_path / f"gpu{i}" / "T1-smoke" / "prereg.json").read_text())["cfg"]["seed"] for i in (1, 2)]
    assert seeds == [1, 2]                                              # a mock campaign's trials differ, like real ones
    capsys.readouterr()
    assert main(["pool", "--runs", *runs, "--out", str(tmp_path / "pooled.json")]) == 0
    text = capsys.readouterr().out
    assert "POOLED (campaign 'kaggle-test', 2 of 2 trials)" in text and "/80 " in text      # 40 null blocks from each
    pooled = json.loads((tmp_path / "pooled.json").read_text())
    assert len(pooled["blocks"]["kind"]) == 160 and pooled["pooling"]["complete"]
    assert main(["tier0", "--mock", "--skip-tests", "--campaign", "bad", "--out", str(tmp_path / "x")]) == 2
    assert "--campaign wants NAME:i/N" in capsys.readouterr().out and not (tmp_path / "x" / "logs").exists()
