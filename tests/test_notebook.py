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
    assert i < r.index("treaty mock-run") < r.index("shutil.copy2") < r.index("files.download")


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


def test_kaggle_runs_the_long_trial_then_the_drill_then_saves_only_the_deliverables():
    nb, code = _cells(KAGGLE)
    assert nb["metadata"]["kaggle"]["accelerator"] == "nvidiaTeslaT4" and nb["metadata"]["kaggle"]["isInternetEnabled"]
    run = [s for s in code if "closure tier0 --confirm-hardware" in s]
    assert len(run) == 1
    r = run[0]
    assert "--trial-profile long" in r and "timeout --signal=TERM" in r
    assert r.index("closure tier0") < r.index("treaty mock-run") < r.index("shutil.copy2")
    assert "copytree" not in r and "signing_key" not in r and "google.colab" not in "".join(code)
    keep = r[r.index("keep = "):r.index("\n", r.index("keep = "))]
    assert keep.count("{OUT}/") == 3 and "tier0_bundle.tar.gz" in keep and "drill.json" in keep
    assert all("OUT" not in s for s in code[code.index(r) + 1:])


def test_kaggle_runs_outside_the_saved_folder_and_stops_before_twelve_hours():
    setup = next(s for s in _cells(KAGGLE)[1] if "git clone" in s)
    assert 'RUNS, SAVE = "/tmp/plan-a-closure", "/tmp/plan-a-closure-runs", "/kaggle/working"' in setup
    assert "P100" in setup and "ls-remote" in setup and "checkout -q FETCH_HEAD" in setup and "git log -1" in setup
    run = next(s for s in _cells(KAGGLE)[1] if "closure tier0" in s)
    left = re.search(r"LEFT = int\((\d+) \* 3600 \+ (\d+) \* 60", run)
    assert left and int(left.group(1)) * 60 + int(left.group(2)) < 12 * 60 - 30      # at least 30 min to spare
