"""scripts/run_anywhere.sh: the one command a reader runs first. CI's `evidence` job runs it end to end on a simulated
GPU; this checks, in a second, that it parses and refuses what it should before touching anything."""
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_anywhere.sh"
pytestmark = pytest.mark.skipif(shutil.which("bash") is None, reason="needs bash")


def _run(*args):
    return subprocess.run(["bash", str(SCRIPT), *args], capture_output=True, text=True, timeout=60)


def test_it_parses_and_its_help_names_every_mode():
    assert subprocess.run(["bash", "-n", str(SCRIPT)]).returncode == 0
    r = _run("--help")
    assert r.returncode == 0
    for word in ("--check", "--hardware", "--profile", "--no-sudo", "signing key", "VERIFY_IT_YOURSELF.md"):
        assert word in r.stdout, word


@pytest.mark.parametrize("args,why", [(("--gpu", "x"), "--gpu needs a number"),
                                      (("--profile", "huge"), "smoke, medium or long"),
                                      (("--frobnicate",), "unknown option"),
                                      (("--python", "no-such-python-3"), "not found")])
def test_bad_arguments_are_refused_before_anything_is_installed(args, why):
    r = _run(*args)
    assert r.returncode != 0 and why in (r.stdout + r.stderr)


def test_it_never_ships_the_private_key_and_says_so():
    text = SCRIPT.read_text()
    assert "signing_key.bin" in text and "left out of the bundle" in text
    assert "rm -rf" not in text                                  # it only ever writes into a new or empty folder
