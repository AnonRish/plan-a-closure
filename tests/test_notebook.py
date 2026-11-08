"""The Colab notebook (notebooks/tier0_colab.ipynb): the structure that keeps a run from being lost. Run 2's bundle was
lost because the download lived in a later cell that needed a variable a restarted session had forgotten."""
import json
from pathlib import Path

NB = Path(__file__).resolve().parents[1] / "notebooks" / "tier0_colab.ipynb"


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
