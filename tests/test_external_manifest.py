"""external/: the vendored AnonRish repositories are the trees that were tested, and every test the matrices cite passed."""
from pathlib import Path

from closure import external as E
from closure.cli import main

ROOT = Path(__file__).resolve().parents[1]


def test_every_vendored_tree_matches_the_manifest_and_every_cited_test_passed():
    assert E.check(ROOT) == []


def test_every_entry_has_provenance_a_licence_record_and_a_clean_run():
    m = E.load_manifest(ROOT)
    assert set(m["repos"]) == set(E.repos(ROOT)) and len(m["repos"]) == 13
    for name, e in m["repos"].items():
        assert e["source"].startswith("https://github.com/AnonRish/") and len(e["commit"]) == 40, name
        assert e["license"] in ("MIT", "Apache-2.0", "none"), name
        t = e["tests"]
        assert t["status"] == "pass" and t["failures"] == t["errors"] == 0 and t["passed"] > 0, name
    cited = E.cited_tests()
    assert len(cited) >= 8 and sum(map(len, cited.values())) >= 30           # the matrices cite tests in 8 repositories


def test_the_readme_table_is_the_recorded_run():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    m = E.load_manifest(ROOT)
    for name, e in m["repos"].items():
        assert f"| {name} | `{e['commit'][:12]}` | {e['tests']['passed']} / {e['tests']['skipped']} |" in readme, name
    passed = sum(e["tests"]["passed"] for e in m["repos"].values())
    skipped = sum(e["tests"]["skipped"] for e in m["repos"].values())
    assert f"{passed:,} passed, {skipped} skipped, none failed" in readme


def test_tree_digest_ignores_generated_files_and_sees_every_edit(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "a.py").write_text("x = 1\n")
    d0 = E.tree_digest(tmp_path)
    for junk in ("__pycache__/a.cpython-312.pyc", ".pytest_cache/v", "pkg.egg-info/PKG-INFO", ".hypothesis/db", "build/lib/a.py"):
        (tmp_path / junk).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / junk).write_text("generated")
    assert E.tree_digest(tmp_path) == d0
    (tmp_path / "pkg" / "a.py").write_text("x = 2\n")
    assert E.tree_digest(tmp_path)["tree_sha256"] != d0["tree_sha256"]
    (tmp_path / "pkg" / "a.py").write_text("x = 1\n")
    (tmp_path / "pkg" / "a.py").rename(tmp_path / "pkg" / "b.py")
    assert E.tree_digest(tmp_path)["tree_sha256"] != d0["tree_sha256"]       # paths are hashed, not only contents


def test_cited_outcomes_come_from_the_junit_report(tmp_path):
    xml = tmp_path / "j.xml"
    xml.write_text('<testsuites><testsuite tests="4" failures="1" errors="0" skipped="1">'
                   '<testcase classname="tests.test_a" name="test_ok"/>'
                   '<testcase classname="tests.test_a" name="test_param[1]"/>'
                   '<testcase classname="tests.test_a" name="test_skip"><skipped message="no tool"/></testcase>'
                   '<testcase classname="tests.test_a.TestK" name="test_bad"><failure message="x"/></testcase>'
                   '</testsuite></testsuites>')
    counts, cases = E._outcomes(xml)
    assert counts == {"tests": 4, "failures": 1, "errors": 0, "skipped": 1, "passed": 2}
    assert [E.cited_outcome(f"tests/test_a.py::{n}", cases) for n in ("test_ok", "test_param", "test_skip", "test_bad")] == \
        ["passed", "passed", "skipped", "failed"]
    assert E.cited_outcome("tests/test_b.py::test_ok", cases) == "not run"


def test_a_suite_runs_in_its_own_process_with_its_src_on_the_path_and_failures_are_reported(tmp_path):
    repo = tmp_path / "toyrepo"
    (repo / "tests").mkdir(parents=True)
    (repo / "src" / "toypkg").mkdir(parents=True)
    (repo / "src" / "toypkg" / "__init__.py").write_text("VALUE = 3\n")
    (repo / "tests" / "test_toy.py").write_text(
        "import pytest\nfrom toypkg import VALUE\n\n"
        "def test_value():\n    assert VALUE == 3\n\n"
        "def test_wrong():\n    assert VALUE == 4\n\n"
        "@pytest.mark.skip(reason='needs a tool')\ndef test_tool():\n    pass\n")
    r = E.run_suite(repo, timeout=120, cited=["tests/test_toy.py::test_value", "tests/test_toy.py::test_wrong"])
    assert r["status"] == "fail" and (r["passed"], r["failures"], r["skipped"]) == (1, 1, 1)
    assert r["cited"] == {"tests/test_toy.py::test_value": "passed", "tests/test_toy.py::test_wrong": "failed"}
    assert r["skip_reasons"] == {"needs a tool": 1} and not r["tests_wrote_into_tree"]


def test_external_cli_list_and_check(capsys):
    assert main(["external", "list"]) == 0
    out = capsys.readouterr().out
    assert "| fides |" in out and "| tap-logger-rtl |" in out
    assert main(["external", "check"]) == 0
    assert main(["external", "test", "no-such-repo"]) == 2
