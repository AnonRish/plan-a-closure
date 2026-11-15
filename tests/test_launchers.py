"""The launchers for GPUs this kit has not run on yet: scripts/modal_tier0.py (Modal, from your own computer) and
scripts/slurm_tier0.sh (a Slurm batch job on a research cluster). Neither can be run here
for real; these tests pin what they would do: the commands, the costs they quote, where results go, the image they ask
Modal to build, and the Slurm job's time-limit guard."""
import hashlib
import importlib.util
import os
import pathlib
import stat
import subprocess
import sys
import types

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODAL_SCRIPT = ROOT / "scripts" / "modal_tier0.py"
SLURM_SCRIPT = ROOT / "scripts" / "slurm_tier0.sh"


def _load(name, modal_module):
    saved = sys.modules.get("modal", "absent")
    sys.modules["modal"] = modal_module
    try:
        spec = importlib.util.spec_from_file_location(name, MODAL_SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if saved == "absent":
            sys.modules.pop("modal", None)
        else:
            sys.modules["modal"] = saved


@pytest.fixture
def mt():
    return _load("modal_tier0_plain", None)                      # as on a computer without Modal installed


def test_costs_follow_the_published_rates(mt):
    # 2 h 20 min of an H100 with 4 cores and 32 GiB: 8400 s x (0.001097 + 4 x 0.0000131 + 32 x 0.00000222) dollars
    assert mt.estimate("H100", "smoke") == pytest.approx(8400 * (0.001097 + 4 * 0.0000131 + 32 * 0.00000222))
    assert mt.estimate("H100!", "smoke") == mt.estimate("H100", "smoke")          # pinned H100: same price
    assert mt.estimate("B200+", "medium") == mt.estimate("B200", "medium")         # billed as a B200
    # what the docstring promises the $30 a month covers
    smoke, medium = (lambda g: mt.estimate(g, "smoke")), (lambda g: mt.estimate(g, "medium"))
    assert smoke("B300") < 30 < 2 * smoke("B300") and smoke("B200") < 30 < 2 * smoke("B200")
    assert 2 * smoke("H200") < 30 and 2 * smoke("H100") < 30
    assert medium("H200") < 30 and medium("H100") < 30 < medium("B200")
    table = mt.cost_table()
    assert "| B200 |" in table and "14 November 2026" in table and table.count("\n|") == len(mt.RATES) + 2          # header, rule, one row per GPU


def test_parse_names_gpus_and_modes(mt):
    a = mt.parse(["--gpu", "b200+", "--profile", "medium", "--mock-run"])
    assert (a.gpu, a.profile, a.mode, a.mock_run) == ("B200+", "medium", "pilot", True)
    assert a.name.startswith("b200-plus-medium-")
    assert mt.parse(["--gpu", "h100!", "--check"]).name.startswith("check-h100-pinned-")
    assert mt.parse(["--rehearse"]).mode == "rehearse" and mt.parse(["--estimate"]).mode == "estimate"
    for bad in (["--gpu", "MI300X"], ["--check", "--rehearse"], ["--name", "../x"], ["--profile", "short"]):
        with pytest.raises(SystemExit):
            mt.parse(bad)


def test_remote_commands(mt):
    check = mt.remote_commands("check", "/runs/x/attempt-1/check")
    assert check[0][3:] == ["doctor", "--out", "/runs/x/attempt-1/check"] and check[1][3:] == ["preflight", "--gpu", "0"]
    (pilot,) = mt.remote_commands("pilot", "/o", "long", skip_tests=True, mock_run=True)
    assert pilot[:4] == ["bash", "scripts/run_anywhere.sh", "--hardware", "--no-venv"]
    assert pilot[pilot.index("--profile") + 1] == "long" and "--skip-tests" in pilot and "--mock-run" in pilot
    (rehearse,) = mt.remote_commands("rehearse", "/o")
    assert "--hardware" not in rehearse and "--no-venv" in rehearse
    with pytest.raises(ValueError):
        mt.remote_commands("train", "/o")


def _fake_repo(tmp_path, exit_code=0):
    """A stand-in for the repository in the container: a run_anywhere.sh that writes what the real one writes."""
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    (repo / "scripts" / "run_anywhere.sh").write_text(
        "#!/usr/bin/env bash\nwhile [ $# -gt 0 ]; do [ \"$1\" = --out ] && OUT=\"$2\"; shift; done\n"
        "mkdir -p \"$OUT/T1-smoke\" \"$OUT/mock-run\"\necho 'pilot output line'\n"
        "printf '# Tier 0 pilot: summary\\n' > \"$OUT/SUMMARY.md\"\nprintf 'bundle' > \"$OUT/tier0_bundle.tar.gz\"\n"
        "printf 'key' > \"$OUT/T1-smoke/signing_key.bin\"\nprintf '{}' > \"$OUT/mock-run/drill.json\"\n"
        f"exit {exit_code}\n")
    return repo


def test_execute_keeps_every_attempt_and_never_returns_the_private_key(mt, tmp_path):
    repo, mount = _fake_repo(tmp_path), tmp_path / "volume"
    commits = []
    r1 = mt.execute("pilot", "h100-smoke-1", "smoke", False, True, "H100", root=str(repo), mount=str(mount),
                    commit=lambda: commits.append(1))
    r2 = mt.execute("pilot", "h100-smoke-1", "smoke", False, True, "H100", root=str(repo), mount=str(mount))
    assert (r1["attempt"], r2["attempt"]) == ("attempt-1", "attempt-2") and commits == [1]
    assert r1["exit"] == 0 and set(r1["files"]) == {"SUMMARY.md", "tier0_bundle.tar.gz", "mock-run/drill.json",
                                                    "console.log", "launcher.txt"}
    assert not any("signing_key" in k for k in r1["files"]) and b"signing" not in b"".join(r1["files"].values())
    assert b"pilot output line" in r1["files"]["console.log"] and b"GPU requested: H100" in r1["files"]["launcher.txt"]
    assert (mount / "h100-smoke-1" / "attempt-1" / "pilot" / "T1-smoke" / "signing_key.bin").exists()   # kept in Modal


def test_execute_reports_a_failed_pilot(mt, tmp_path):
    r = mt.execute("pilot", "r", "smoke", True, False, "B200", root=str(_fake_repo(tmp_path, exit_code=3)),
                   mount=str(tmp_path / "v"))
    assert r["exit"] == 3 and b"[exit 3]" in r["files"]["console.log"]


class _FakeFunction:
    def __init__(self, result):
        self.result, self.calls, self.options = result, [], []

    def with_options(self, **kw):
        self.options.append(kw)
        return self

    def remote(self, *args):
        self.calls.append(args)
        return self.result


def test_local_starts_the_run_and_saves_what_comes_back(mt, tmp_path):
    res = {"run": "n", "attempt": "attempt-1", "exit": 0,
           "files": {"SUMMARY.md": b"# s", "tier0_bundle.tar.gz": b"bundle-bytes", "console.log": b"log"}}
    gpu, cpu, lines = _FakeFunction(res), _FakeFunction(res), []
    rc = mt.local(["--gpu", "B200", "--profile", "medium", "--name", "n"], gpu_fn=gpu, cpu_fn=cpu, dest_root=tmp_path,
                  echo=lines.append)
    assert rc == 0 and gpu.options == [{"gpu": "B200", "timeout": 8 * 3600}]
    assert gpu.calls == [("pilot", "n", "medium", False, False, "B200")] and not cpu.calls
    assert (tmp_path / "n" / "attempt-1" / "tier0_bundle.tar.gz").read_bytes() == b"bundle-bytes"
    text = "\n".join(lines)
    assert "$37.93" in text and hashlib.sha256(b"bundle-bytes").hexdigest() in text and "modal volume get" in text
    lines.clear()
    assert mt.local(["--check", "--gpu", "H200", "--name", "c"], gpu_fn=gpu, cpu_fn=cpu, dest_root=tmp_path,
                    echo=lines.append) == 0
    assert gpu.options[-1] == {"gpu": "H200", "timeout": mt.CHECK_TIMEOUT_S} and gpu.calls[-1][0] == "check"
    assert mt.local(["--rehearse", "--name", "r"], gpu_fn=gpu, cpu_fn=cpu, dest_root=tmp_path, echo=lines.append) == 0
    assert cpu.calls == [("r",)]


def test_local_without_modal_says_how_to_install_it(mt):
    lines = []
    assert mt.local(["--gpu", "H100"], echo=lines.append) == 2 and "pip install modal" in lines[0]
    assert mt.local(["--estimate"], echo=lines.append) == 0                      # needs no Modal


def _fake_modal():
    log = []

    class Img:
        def __getattr__(self, name):
            def step(*a, **k):
                log.append((name, a, k))
                return self
            return step

    class Fn:
        def __init__(self, f, kw):
            self.f, self.kw = f, kw

    class App:
        def __init__(self, name):
            self.name, self.functions, self.entry = name, {}, None

        def function(self, **kw):
            def deco(f):
                self.functions[f.__name__] = Fn(f, kw)
                return self.functions[f.__name__]
            return deco

        def local_entrypoint(self):
            def deco(f):
                self.entry = f
                return f
            return deco

    def debian_slim(**kw):
        log.append(("debian_slim", (), kw))
        return Img()

    m = types.ModuleType("modal")
    m.Image = types.SimpleNamespace(debian_slim=debian_slim)
    m.App = App
    m.Volume = types.SimpleNamespace(from_name=lambda name, create_if_missing=False:
                                     types.SimpleNamespace(name=name, create=create_if_missing, commit=lambda: None))
    return m, log


def test_the_image_and_functions_modal_is_asked_for():
    fake, log = _fake_modal()
    mod = _load("modal_tier0_fake", fake)
    steps = {name: (a, k) for name, a, k in log}
    assert steps["debian_slim"][1] == {"python_version": "3.12"}
    a, k = steps["add_local_dir"]
    assert a == (ROOT, mod.REMOTE) and k["copy"] is True                 # copied, so the install step can follow
    assert {".venv", "runs", "**/signing_key.bin"} <= set(k["ignore"])
    assert "torch" in steps["pip_install"][0] and "nvidia-ml-py>=12" in steps["pip_install"][0]
    assert "[test,hw]" in steps["run_commands"][0][0]
    assert [n for n, _, _ in log].index("add_local_dir") < [n for n, _, _ in log].index("run_commands")
    fns = mod.app.functions
    assert fns["on_gpu"].kw["gpu"] == "H100" and fns["on_gpu"].kw["volumes"][mod.MOUNT].name == mod.VOLUME
    assert "gpu" not in fns["on_cpu"].kw and mod.runs_volume.create is True and mod.app.entry is not None
    assert mod.app.name == "plan-a-closure-tier0"


def test_the_script_runs_without_modal_for_the_estimate():
    r = subprocess.run([sys.executable, "-I", str(MODAL_SCRIPT), "--estimate"], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and "| H100 |" in r.stdout


# ---- scripts/slurm_tier0.sh -------------------------------------------------------------------------------------------
def _slurm(*args, env=None, cwd=None):
    e = {**os.environ, **(env or {})}
    for k in ("SLURM_JOB_ID", "SLURM_SUBMIT_DIR"):
        if env is None or k not in env:
            e.pop(k, None)
    return subprocess.run(["bash", str(SLURM_SCRIPT), *args], capture_output=True, text=True, timeout=60, env=e,
                          cwd=cwd or ROOT)


def test_slurm_script_is_valid_bash_and_asks_for_a_whole_h100():
    assert subprocess.run(["bash", "-n", str(SLURM_SCRIPT)]).returncode == 0
    text = SLURM_SCRIPT.read_text()
    assert "#SBATCH --gpus=h100:1" in text and "#SBATCH --time=0-04:00" in text
    h = _slurm("--help")
    assert h.returncode == 0 and "sbatch --account=<account>" in h.stdout and "#SBATCH --" not in h.stdout


def test_slurm_dry_run_prints_the_job(tmp_path):
    r = _slurm("--dry-run", "--profile", "medium", "--mock-run", "--skip-tests",
               env={"SLURM_JOB_ID": "4242", "SLURM_SUBMIT_DIR": str(ROOT), "PATH": os.environ["PATH"]})
    assert r.returncode == 0, r.stderr
    tier0 = [li for li in r.stdout.splitlines() if " tier0 " in li]
    assert tier0 and "--trial-profile medium" in tier0[0] and "--skip-tests" in tier0[0] and "runs/slurm-4242" in tier0[0]
    assert "--confirm-hardware --gpu 0" in tier0[0] and any("treaty mock-run" in li for li in r.stdout.splitlines())
    s = _slurm("--setup", "--dry-run")
    assert s.returncode == 0 and "pip install -q -e .[test,hw]" in s.stdout.replace('"', "")


def test_slurm_job_refuses_a_time_limit_shorter_than_the_profile(tmp_path):
    fake = tmp_path / "bin"
    fake.mkdir()
    sq = fake / "squeue"
    sq.write_text("#!/usr/bin/env bash\necho '3:10:00'\n")                  # three hours ten minutes left
    sq.chmod(sq.stat().st_mode | stat.S_IEXEC)
    env = {"SLURM_JOB_ID": "7", "SLURM_SUBMIT_DIR": str(ROOT), "PATH": f"{fake}:{os.environ['PATH']}"}
    r = _slurm("--dry-run", "--profile", "medium", env=env)
    assert r.returncode == 1 and "190 minutes left" in r.stderr and "0-08:00" in r.stderr
    assert _slurm("--dry-run", "--profile", "smoke", env=env).returncode == 0    # 190 >= 140
    sq.write_text("#!/usr/bin/env bash\necho '1-02:03:04'\n")                   # a day and a bit: enough for long
    assert _slurm("--dry-run", "--profile", "long", env=env).returncode == 0


def test_slurm_job_needs_a_checkout_and_a_setup(tmp_path):
    r = _slurm("--profile", "smoke", env={"SLURM_SUBMIT_DIR": str(tmp_path), "PATH": os.environ["PATH"]})
    assert r.returncode == 1 and "not a plan-a-closure checkout" in r.stderr
    r = _slurm(env={"SLURM_SUBMIT_DIR": str(ROOT), "CLOSURE_VENV": str(tmp_path / "none"), "PATH": os.environ["PATH"]})
    assert r.returncode == 1 and "--setup" in r.stderr
