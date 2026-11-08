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
    assert "--profile long" in (out / "logs" / "06-hw-trial.log").read_text().splitlines()[0]
    with tarfile.open(out / "tier0_bundle.tar.gz") as tf:
        names = tf.getnames()
    assert any(n.endswith("T1-long/raw.npz") for n in names) and not any(n.endswith("signing_key.bin") for n in names)
