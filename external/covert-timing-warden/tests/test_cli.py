import json

import numpy as np
import pytest

from covert_timing_warden import cli
from covert_timing_warden.traffic import BurstyMarkov, LogNormalIID, to_timestamps


def run(capsys, *argv):
    assert cli.main(list(argv)) == 0
    return json.loads(capsys.readouterr().out)


def test_bounds_command(capsys):
    q = run(capsys, "bounds", "--mitigation", "quantizer", "--param", "0.01", "--max-extra-delay", "0.03")
    assert q["lower_bits_per_packet"] == pytest.approx(2.0) == pytest.approx(q["upper_bits_per_packet"])
    j = run(capsys, "bounds", "--mitigation", "jitter", "--param", "0.005", "--max-extra-delay", "0.04")
    assert j["lower_bits_per_packet"] == pytest.approx(3.1699, abs=1e-4) and j["upper_bits_per_packet"] > j["lower_bits_per_packet"]
    f = run(capsys, "bounds", "--mitigation", "fixed", "--param", "0.02")
    assert f["upper_bits_per_packet"] == 0.0


def test_exfil_command(capsys):
    r = run(capsys, "exfil", "--secret-bits", "8e12", "--bits-per-packet", "6", "--pps", "50", "--streams", "1000")
    assert r["days"] == pytest.approx(308.6, abs=0.1)


def test_detect_command_on_files(tmp_path, capsys):
    rng = np.random.default_rng(0)
    W = 100
    ref = tmp_path / "ref.csv"
    cand_ok = tmp_path / "ok.csv"
    cand_bad = tmp_path / "bad.csv"
    ref.write_text("t\n" + "\n".join(map(repr, to_timestamps(LogNormalIID().sample(2 * 300 * W, rng)).tolist())) + "\n")
    cand_ok.write_text("t\n" + "\n".join(map(repr, to_timestamps(LogNormalIID().sample(80 * W, rng)).tolist())) + "\n")
    levels = 0.02 + 0.02 * rng.integers(0, 4, 80 * W)
    cand_bad.write_text("t\n" + "\n".join(map(repr, to_timestamps(levels).tolist())) + "\n")
    ok = run(capsys, "detect", "--reference", str(ref), "--candidate", str(cand_ok), "--window", str(W), "--alpha", "0.05")
    bad = run(capsys, "detect", "--reference", str(ref), "--candidate", str(cand_bad), "--window", str(W), "--alpha", "0.05")
    assert ok["windows"] == 79 or ok["windows"] == 80
    assert ok["alarm_rate"] < 0.15
    assert bad["alarm_rate"] > 0.95 and sum(bad["triggered_by_detector"].values()) > 0


def test_detect_refuses_a_short_reference(tmp_path):
    ref = tmp_path / "short.csv"
    ref.write_text("\n".join(map(repr, to_timestamps(LogNormalIID().sample(500, np.random.default_rng(1))).tolist())) + "\n")
    with pytest.raises(ValueError, match="never alarm"):
        cli.main(["detect", "--reference", str(ref), "--candidate", str(ref), "--alpha", "0.01"])


def test_demo_command_tells_the_documented_story(capsys):
    r = run(capsys, "demo", "--windows", "300")["alarm_rate"]
    assert r["naive 4-level channel, 2 bits/packet, vs i.i.d."] > 0.99
    assert r["marginal-only quantile channel, 2 bits/packet, vs bursty"] > 0.9
    for k in ("honest i.i.d. (false-alarm rate)", "honest bursty (false-alarm rate)",
              "exact-marginal quantile channel, 1 bit(s)/packet, vs i.i.d.",
              "exact-marginal quantile channel, 3 bit(s)/packet, vs i.i.d."):
        assert r[k] <= 0.12, k
