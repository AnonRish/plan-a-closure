"""closure.physics: what the GPU did in a finished trial, by requested load level (a diagnostic, never a criterion)."""
import json

import numpy as np

from closure import physics
from closure.cli import main
from closure.evidence import Signer
from closure.trial import TrialConfig, run_trial

from test_link import CAPPED, CappedGpu


def _run(tmp_path):
    cfg = TrialConfig(**{**CAPPED, "analysis": "link", "seed": 5})
    run_trial(CappedGpu(5), cfg, tmp_path / "t", Signer())
    return tmp_path / "t"


def test_report_tabulates_work_power_and_busy_time_by_level_and_what_hidden_load_did(tmp_path, capsys):
    run = _run(tmp_path)
    rep = physics.report(run)
    assert rep["levels_source"] == "load levels as recorded"
    by = {r["level"]: r for r in rep["by_level"]}
    assert by[0.0]["units_per_s"] < 0.5 and by[0.0]["busy_ms_per_unit"] is None
    watts = [r["watts"] for r in rep["by_level"]]
    assert watts == sorted(watts) and sum(r["windows"] for r in rep["by_level"]) > 0
    # the toy GPU is run 5's: flat near its power limit, so power is no straight line in work
    mid, top = by[0.5], by[1.0]
    line = by[0.0]["watts"] + (top["watts"] - by[0.0]["watts"]) * mid["units_per_s"] / top["units_per_s"]
    assert mid["watts"] - line > 2.0
    assert all(r["level"] == 0 for r in rep["hidden_load_on_an_idle_gpu"])
    assert main(["physics", "--run", str(run)]) == 0
    text = capsys.readouterr().out
    assert "| requested level | windows |" in text and "load levels as recorded" in text
    assert main(["physics", "--run", str(run), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["by_level"][0]["level"] == 0.0


def test_levels_are_only_regenerated_for_a_hardware_run_and_are_checked(tmp_path, capsys):
    run = _run(tmp_path)
    z = dict(np.load(run / "raw.npz"))
    np.savez(run / "raw.npz", **{k: v for k, v in z.items() if not k.endswith("_lev")})   # as before 0.8.0
    assert main(["physics", "--run", str(run)]) == 2                                      # not a hardware run
    assert "only a hardware run's can be regenerated" in capsys.readouterr().out
    pre = json.loads((run / "prereg.json").read_text())
    pre["cfg"]["status"] = "HARDWARE (NVML energy counter; spoofable)"
    (run / "prereg.json").write_text(json.dumps(pre))
    assert main(["physics", "--run", str(run)]) == 2      # the toy's levels were not drawn the way hw/source.py draws
    assert "do not match the work done" in capsys.readouterr().out


def test_regenerated_levels_are_the_ones_the_load_generator_draws():
    """Runs before 0.8.0 did not record the load level of each window; hw/source.py draws the levels from one generator
    seeded with the trial's seed, in time order, so they can be drawn again."""
    from closure.hw.source import FakeHardware, HwSource
    fh = FakeHardware(seed=9)
    src = HwSource(fh, fh, dt=1.0, n_gpu=8, time_fn=fh.now, sleep_fn=fh.sleep, seed=9)
    recorded = np.concatenate([src.run_block(40, None)["level"] for _ in range(15)])
    assert np.array_equal(physics._regenerated_levels(9, 600), recorded)
    assert not np.array_equal(physics._regenerated_levels(10, 600), recorded)
