"""The Colab and Kaggle notebooks (notebooks/): the structure that keeps a run from being lost. Run 2's bundle was
lost because the download lived in a later cell that needed a variable a restarted session had forgotten."""
import json
import re
from pathlib import Path

NB = Path(__file__).resolve().parents[1] / "notebooks" / "tier0_colab.ipynb"
KAGGLE = NB.with_name("tier0_kaggle.ipynb")


def _code():
    nb = json.loads(NB.read_text(encoding="utf-8"))
    assert nb["nbformat"] == 4 and nb["metadata"]["accelerator"] == "GPU"
    return ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]


def test_one_cell_runs_tier0_then_the_drill_then_saves_and_downloads():
    run = [s for s in _code() if "closure tier0 --confirm-hardware" in s]
    assert len(run) == 1
    r, i = run[0], run[0].index("closure tier0 --confirm-hardware")
    assert i < r.index("treaty mock-run") < r.index("shutil.copy2(p, dest)") < r.index("files.download")


def test_no_later_cell_needs_the_run_folder():
    code = _code()
    k = next(n for n, s in enumerate(code) if "closure tier0 --confirm-hardware" in s)
    assert all("OUT" not in s for s in code[k + 1:])


def test_setup_pins_and_records_the_code_and_sets_persistence_mode():
    setup = next(s for s in _code() if "git clone" in s)
    assert "REF" in setup and "checkout -q FETCH_HEAD" in setup and "git log -1" in setup
    assert "nvidia-smi -pm 1" in setup
    assert "drive.mount" in setup and "except Exception" in setup          # Google Drive is optional


def test_run_all_skips_the_rehearsal():
    reh = next(s for s in _code() if "--mock" in s)
    assert "REHEARSE = False" in reh and "if REHEARSE:" in reh


def _cells(path):
    nb = json.loads(path.read_text(encoding="utf-8"))
    assert nb["nbformat"] == 4
    return nb, ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]


def test_every_code_cell_is_valid_python_once_the_shell_lines_are_set_aside():
    for path in (NB, KAGGLE):
        for src in _cells(path)[1]:
            compile(re.sub(r"(?m)^(\s*)[!%].*$", r"\1pass", src), str(path), "exec")


def test_kaggle_runs_a_long_trial_on_each_gpu_as_one_campaign_and_saves_only_the_deliverables():
    nb, code = _cells(KAGGLE)
    assert nb["metadata"]["kaggle"]["accelerator"] == "nvidiaTeslaT4" and nb["metadata"]["kaggle"]["isInternetEnabled"]
    run = [s for s in code if '"closure", "tier0"' in s]
    assert len(run) == 1
    r = run[0]
    assert '"--trial-profile", "long"' in r and '"timeout", "--signal=TERM"' in r and '"--confirm-hardware"' in r
    assert '"--campaign", f"{CAMPAIGN}:{i + 1}/{len(GPUS)}"' in r           # declared before either trial starts
    assert "jobs.append(launch(i, GPUS[i], skip_tests=True))" in r          # the unit tests run once, with GPU 0
    assert 'PYTHONUNBUFFERED="1"' in r and 'line.startswith("[2]")' in r    # GPU 1 waits for GPU 0's unit tests
    # each GPU's bundle and summary are copied as soon as the runs end, before anything else can go wrong
    saved = r.index('for name in ("tier0_bundle.tar.gz", "SUMMARY.md")')
    assert r.index("launch(0, GPUS[0])") < saved < r.index('"closure", "pool"') < r.index("treaty mock-run")
    assert "copytree" not in r and "signing_key" not in r and "google.colab" not in "".join(code)
    assert "--allow-partial" not in r                                        # a campaign is read whole or not at all
    assert all("OUT" not in s for s in code[code.index(r) + 1:])


def test_kaggle_does_not_lose_the_session_to_a_failed_unit_test_and_says_so():
    """A ten-hour session and a week's GPU quota should not be lost to one failed unit test: the log of the failed
    attempt is saved, both trials start without the tests, and the output says so."""
    r = next(s for s in _cells(KAGGLE)[1] if '"closure", "tier0"' in s)
    assert "if not past_the_unit_tests(jobs[0]):" in r and 'launch(0, GPUS[0], skip_tests=True, tag="-b")' in r
    assert "gpu0-first-attempt-" in r and "logs/01-unit-tests.log" in r and "say so when you report these runs" in r


def test_kaggle_runs_outside_the_saved_folder_and_stops_before_twelve_hours():
    setup = next(s for s in _cells(KAGGLE)[1] if "git clone" in s)
    assert 'RUNS, SAVE = "/tmp/plan-a-closure", "/tmp/plan-a-closure-runs", "/kaggle/working"' in setup
    assert "P100" in setup and "ls-remote" in setup and "checkout -q FETCH_HEAD" in setup and "git log -1" in setup
    assert "opentimestamps-client" in setup
    run = next(s for s in _cells(KAGGLE)[1] if '"closure", "tier0"' in s)
    assert 'out = f"{RUNS}/tier0-{STAMP}-gpu{gpu}{tag}"' in run and 'dest = os.path.join(SAVE, f"tier0-{STAMP}")' in run
    left = re.search(r"DEADLINE = (\d+) \* 3600 \+ (\d+) \* 60", run)
    assert left and int(left.group(1)) * 60 + int(left.group(2)) < 12 * 60 - 30      # at least 30 min to spare
    assert "int(DEADLINE - (time.time() - T_START))" in run


def test_colab_stamps_the_preregistration_and_runs_the_medium_trial_unless_told_otherwise():
    nb, code = _cells(NB)
    text = "".join("".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "markdown")
    assert any("opentimestamps-client" in s for s in code)
    run = next(s for s in code if "closure tier0 --confirm-hardware" in s)
    assert 'PROFILE = "medium"' in run and "--trial-profile {PROFILE}" in run   # the smallest trial that decides H1.2
    from closure.tier0 import TRIALS
    assert {"medium", "smoke"} <= set(TRIALS) and '`"smoke"`' in text and "about 5 h" in text
    assert run.index("closure tier0") < run.index("files.download")              # saved in the cell that ran it
    # a failed unit test does not cost the session: the log is kept and the run starts again without the tests
    assert 'not os.path.exists(f"{OUT}/logs/02-selftest.log")' in run and "--skip-tests --out {OUT}" in run
    assert "first-attempt-unit-tests.log" in run and run.count("closure tier0 --confirm-hardware") == 2
