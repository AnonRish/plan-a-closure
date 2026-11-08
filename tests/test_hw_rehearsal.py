"""The real hardware code path end to end, on CPU torch against a fake NVML and a fake nvidia-smi (tests/fakegpu).

This is what an operator's first `closure tier0 --confirm-hardware` exercises, minus CUDA itself: the GPU found by
UUID, NVML energy reads, clock locks and power caps through nvidia-smi on that GPU only, both put back on exit, on
SIGTERM and after SIGKILL (`closure hw-restore`), clock and power variants dropped without root, locks that do not take
effect refused, and the bundle. It says nothing about CUDA kernels or timing on a real GPU. Skipped without torch.
"""
import json
import os
import signal
import subprocess
import sys
import tarfile
import time
from pathlib import Path

import pytest

pytest.importorskip("torch")

FAKE = Path(__file__).resolve().parent / "fakegpu"
UUID0 = "GPU-fa4e0000-0000-4000-8000-000000000000"
SMALL = ["--dim", "64", "--window-s", "0.3", "--levels", "0,0.5", "--repeats", "1"]


def _env(tmp_path, **extra):
    """A PATH with `nvidia-smi` -> tests/fakegpu/nvidia_smi.py, and the fake pynvml first on PYTHONPATH."""
    bin_ = tmp_path / "bin"
    bin_.mkdir(exist_ok=True)
    smi = bin_ / "nvidia-smi"
    smi.write_text(f"#!{sys.executable}\nimport runpy, sys\nsys.argv[0] = 'nvidia-smi'\n"
                   f"runpy.run_path({str(FAKE / 'nvidia_smi.py')!r}, run_name='__main__')\n")
    smi.chmod(0o755)
    pp = os.environ.get("PYTHONPATH")
    env = {**os.environ, "PATH": f"{bin_}{os.pathsep}{os.environ.get('PATH', '')}",
           "PYTHONPATH": os.pathsep.join([str(FAKE)] + ([pp] if pp else [])),
           "FAKEGPU_STATE": str(tmp_path / "gpu.json"), "FAKEGPU_LOG": str(tmp_path / "smi.log"),
           "CLOSURE_REHEARSAL_CPU": "1", "CUDA_VISIBLE_DEVICES": "", "PYTHONDONTWRITEBYTECODE": "1"}
    env.update({k: str(v) for k, v in extra.items()})
    return env


def _closure(env, *args, timeout=600):
    return subprocess.run([sys.executable, "-m", "closure.cli", *args], env=env, capture_output=True, text=True,
                          timeout=timeout)


def _gpu(tmp_path) -> dict:
    p = tmp_path / "gpu.json"
    return json.loads(p.read_text())["0"] if p.exists() else {"clock": None, "limit_w": 700.0}


def _smi_calls(tmp_path) -> list:
    p = tmp_path / "smi.log"
    return p.read_text().splitlines() if p.exists() else []


def _wait_for_lock(tmp_path, proc, seconds=240):
    end = time.time() + seconds
    while time.time() < end and proc.poll() is None:
        if any("-lgc" in c for c in _smi_calls(tmp_path)) and _gpu(tmp_path)["clock"]:
            return True
        time.sleep(0.1)
    return False


def test_a_signal_mid_probe_unlocks_the_clock_and_restores_the_power_limit(tmp_path):
    env = _env(tmp_path)
    p = subprocess.Popen([sys.executable, "-m", "closure.cli", "hw-probe", "--confirm-hardware", "--gpu", "0",
                          "--out", str(tmp_path / "probe.json"), "--dim", "64", "--window-s", "2", "--levels", "0,0.5",
                          "--repeats", "3", "--precisions", "tf32", "--operands", ""],
                         env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert _wait_for_lock(tmp_path, p), "the probe never locked a clock"
    p.send_signal(signal.SIGTERM)
    _, err = p.communicate(timeout=120)
    assert p.returncode == 128 + signal.SIGTERM and "restoring the GPU" in err
    assert _gpu(tmp_path) == {"clock": None, "limit_w": 700.0}
    assert all(c.startswith(f"-i {UUID0} ") for c in _smi_calls(tmp_path))     # only the resolved GPU, by UUID
    assert _smi_calls(tmp_path)[-2:] == [f"-i {UUID0} -rgc", f"-i {UUID0} -pl 700"]


def test_after_a_sigkill_hw_restore_puts_the_gpu_back(tmp_path):
    env = _env(tmp_path)
    p = subprocess.Popen([sys.executable, "-m", "closure.cli", "hw-probe", "--confirm-hardware", "--gpu", "0",
                          "--out", str(tmp_path / "probe.json"), "--dim", "64", "--window-s", "2", "--levels", "0,0.5",
                          "--repeats", "3", "--precisions", "tf32", "--operands", "", "--clocks", "900"],
                         env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    assert _wait_for_lock(tmp_path, p)
    p.kill()                                                              # nothing can run on SIGKILL
    p.wait(timeout=60)
    assert _gpu(tmp_path)["clock"] == 900                                 # left locked
    r = _closure(env, "hw-restore", "--gpu", "0")
    assert r.returncode == 0, r.stdout + r.stderr
    assert _gpu(tmp_path) == {"clock": None, "limit_w": 700.0} and "the GPU default" in r.stdout


def test_without_root_clock_and_power_variants_are_dropped_and_the_rest_is_still_measured(tmp_path):
    env = _env(tmp_path, FAKEGPU_DENY=1)
    r = _closure(env, "hw-probe", "--confirm-hardware", "--gpu", "0", "--out", str(tmp_path / "probe.json"), *SMALL,
                 "--precisions", "tf32,fp16", "--operands", "zeros")
    assert r.returncode in (0, 1), r.stderr[-2000:]
    pr = json.loads((tmp_path / "probe.json").read_text())
    kinds = {v["kind"] for v in pr["variants"]}
    assert "clock_cap" not in kinds and "power_cap" not in kinds
    assert any("needs root" in n for n in pr["notes"]) and pr["s_operand"] is not None
    assert len([c for c in _smi_calls(tmp_path) if "-lgc" in c or "-pl" in c or "-rgc" in c]) == 1   # tried once


def test_a_clock_lock_that_does_not_take_effect_is_not_counted(tmp_path):
    env = _env(tmp_path, FAKEGPU_LGC_NOOP=1)
    r = _closure(env, "hw-probe", "--confirm-hardware", "--gpu", "0", "--out", str(tmp_path / "probe.json"), *SMALL,
                 "--precisions", "tf32", "--operands", "", "--clocks", "1500,1005", "--power-caps", "0.7")
    pr = json.loads((tmp_path / "probe.json").read_text())
    names = {v["name"] for v in pr["variants"]}
    assert "clock-1500MHz" not in names and "clock-1005MHz" not in names and "powercap-70pct" in names, r.stderr[-1500:]
    assert sum("was not applied" in n for n in pr["notes"]) == 2


def test_tier0_rehearsal_runs_every_hardware_step_and_leaves_the_gpu_as_found(tmp_path):
    env = _env(tmp_path)
    out = tmp_path / "t0"
    r = _closure(env, "tier0", "--confirm-hardware", "--gpu", "0", "--skip-tests", "--out", str(out), timeout=900)
    assert r.returncode == 0, r.stdout[-3000:]
    s = (out / "SUMMARY.md").read_text()
    assert "REHEARSAL" in s and "every step ran" in s
    for step in ("preflight", "hw-selftest", "hw-probe", "hw-state", "hw-trial", "verify", "hw-restore"):
        assert f"| {step} |" in s
    pre = (out / "logs" / "02-preflight.log").read_text()
    assert UUID0 in pre and "FAIL" not in pre
    for log in (out / "logs").glob("*.log"):                               # every step ran to its end: no crash
        assert "Traceback" not in log.read_text(), log.name
    assert '"r2"' in (out / "logs" / "03-hw-selftest.log").read_text()  # its statistics mean nothing on a fake
    assert "## Energy tracks verified work (hw-selftest)" in s
    if "| hw-selftest | energy tracks verified work on this GPU | 0 |" in s:   # its unit is passed on to the trial
        assert "--dim 128 --mem-elems 65536" in (out / "logs" / "06-hw-trial.log").read_text().splitlines()[0]
    pr = json.loads((out / "probe.json").read_text())
    assert pr["status"].startswith("REHEARSAL") and pr["rig"]["nvidia_smi_id"] == UUID0
    assert {"clock_cap", "power_cap", "precision", "operand"} <= {v["kind"] for v in pr["variants"]}
    res = json.loads((out / "T1-smoke" / "results.json").read_text())
    assert res["status"].startswith("REHEARSAL")
    with tarfile.open(out / "tier0_bundle.tar.gz") as tf:
        assert not any(n.endswith("signing_key.bin") for n in tf.getnames())
    assert _gpu(tmp_path) == {"clock": None, "limit_w": 700.0}
    assert all(c.startswith(f"-i {UUID0} ") for c in _smi_calls(tmp_path))


def test_tier0_without_root_runs_through_and_has_nothing_to_restore(tmp_path):
    env = _env(tmp_path, FAKEGPU_DENY=1)
    out = tmp_path / "t0"
    r = _closure(env, "tier0", "--confirm-hardware", "--gpu", "0", "--skip-tests", "--out", str(out), timeout=900)
    assert r.returncode == 0, r.stdout[-3000:]
    s = (out / "SUMMARY.md").read_text()
    assert "every step ran" in s and "| hw-restore | clocks unlocked, power limit as found | 0 |" in s
    assert "nothing to restore" in next((out / "logs").glob("*-hw-restore.log")).read_text()
    assert _gpu(tmp_path) == {"clock": None, "limit_w": 700.0}
    r = _closure(env, "hw-restore", "--gpu", "0")                    # on its own it cannot know who ran the probe
    assert r.returncode == 1 and "sudo" in r.stdout


def test_tier0_passes_a_signal_to_the_running_step_skips_the_rest_and_still_restores(tmp_path):
    env = _env(tmp_path)
    out = tmp_path / "t0"
    p = subprocess.Popen([sys.executable, "-m", "closure.cli", "tier0", "--confirm-hardware", "--gpu", "0",
                          "--skip-tests", "--out", str(out)], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True)
    assert _wait_for_lock(tmp_path, p, seconds=400), "hw-probe never locked a clock"
    p.send_signal(signal.SIGTERM)                                         # the parent only, as `kill <pid>` would
    p.communicate(timeout=300)
    assert p.returncode == 128 + signal.SIGTERM
    s = (out / "SUMMARY.md").read_text()
    assert "stopped by signal 15" in s and "| hw-trial | smoke trial with blind hidden-load injection | skipped |" in s
    assert "| hw-restore | clocks unlocked, power limit as found | 0 |" in s
    assert _gpu(tmp_path) == {"clock": None, "limit_w": 700.0}
    assert (out / "tier0_bundle.tar.gz").exists()


def test_a_small_gpu_s_own_power_limit_is_the_capacity_and_the_trial_records_it_with_the_unit(tmp_path):
    env = _env(tmp_path, FAKEGPU_LIMITS_W="70,60,70", FAKEGPU_POWER_W="30,45")      # a T4's limits
    r = _closure(env, "hw-selftest", "--gpus", "0", "--windows", "3")
    js = json.loads(r.stdout[r.stdout.find("{"):])
    assert js["power_limit_w"] == 70.0 and js["unit"]["dim"] == 128 and js["unit"]["fits_slot"], r.stderr[-1500:]
    assert 20.0 < js["idle_w_measured_at_start"] < 45.0 and set(js["per_level"]) == {"0", "0.25", "0.5", "0.75", "1"}
    assert "unit of work: 128x128 bfloat16 GEMM" in r.stderr and "power limit 70 W" in r.stderr
    out = tmp_path / "T1"
    r = _closure(env, "hw-trial", "--profile", "rehearsal", "--gpus", "0", "--out", str(out), "--confirm-hardware",
                 "--dim", "96")
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-2000:]
    cfg = json.loads((out / "prereg.json").read_text())["cfg"]
    assert cfg["p_max_w"] == 70.0 and cfg["workload"]["dim"] == 96 and not cfg["workload"]["auto_sized"]
    assert 20.0 < cfg["workload"]["idle_w_measured"] < 45.0
