"""The repositories from github.com/AnonRish that this archive carries under external/, pinned and testable.

Each vendored repository keeps its own packaging, dependencies and tests. external/MANIFEST.json records, for each one,
where the code came from (repository and commit), a hash of the vendored tree, its licence, and the result of its own
test suite as run here: counts from pytest's JUnit XML, the reasons for any skips, and the outcome of every vendored test
that the coverage matrices cite.

    closure external list              # the manifest as a table
    closure external check             # re-hash every vendored tree and compare with the manifest
    closure external test [repo ...]   # run each repository's suite in its own pytest process
    closure external test --record     # ... and write the results and tree hashes into the manifest

Every suite runs from its own directory with its own pytest configuration (or an empty one), with the repository and
its src/ first on PYTHONPATH, so neither this repository's configuration nor another repository's modules leak into it.
The union of the suites' dependencies is the `external` extra: pip install -e ".[external]".
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

SKIP_DIRS = frozenset({"__pycache__", ".pytest_cache", ".hypothesis", ".mypy_cache", ".ruff_cache", ".venv", "venv",
                       "build", "dist", "target", ".git"})
SKIP_FILES = frozenset({".DS_Store"})
SKIP_SUFFIXES = (".pyc", ".pyo")
LICENCE_FILES = ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING")
_SKIPPED = re.compile(r"^SKIPPED \[(\d+)\] [^\n]*?:\d+: (.*)$", re.M)


def find_root(root=None) -> Path:
    """The repository root: the one given, else this package's checkout, else the current directory."""
    if root:
        return Path(root).resolve()
    here = Path(__file__).resolve().parents[2]
    for cand in (here, Path.cwd()):
        if (cand / "external").is_dir():
            return cand
    return here


def repos(root=None) -> list:
    ext = find_root(root) / "external"
    if not ext.is_dir():
        return []
    return sorted(p.name for p in ext.iterdir() if p.is_dir() and not p.name.startswith((".", "_")))


def tree_files(repo) -> list:
    """Every file in a vendored tree except generated ones (caches, bytecode, build output, egg-info)."""
    repo, out = Path(repo), []
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.endswith(".egg-info")]
        out += [Path(dirpath, f) for f in filenames if f not in SKIP_FILES and not f.endswith(SKIP_SUFFIXES)]
    return sorted(out, key=lambda p: p.relative_to(repo).as_posix())


def tree_digest(repo) -> dict:
    """sha256 over (relative path, sha256 of the contents) of every file in tree_files order; the same on any machine."""
    repo, h, n, size = Path(repo), hashlib.sha256(), 0, 0
    for p in tree_files(repo):
        data = p.read_bytes()
        h.update(p.relative_to(repo).as_posix().encode("utf-8") + b"\0" + hashlib.sha256(data).hexdigest().encode() + b"\n")
        n, size = n + 1, size + len(data)
    return {"tree_sha256": h.hexdigest(), "files": n, "bytes": size}


def has_licence(repo) -> bool:
    return any((Path(repo) / f).is_file() for f in LICENCE_FILES)


def manifest_path(root=None) -> Path:
    return find_root(root) / "external" / "MANIFEST.json"


def load_manifest(root=None) -> dict:
    p = manifest_path(root)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"repos": {}}


def save_manifest(m: dict, root=None) -> Path:
    p = manifest_path(root)
    p.write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
    return p


def cited_tests(rows=None) -> dict:
    """{repo: [path::name, ...]} for every vendored test cited by the Plan A and hardwired-pause matrices."""
    if rows is None:
        from .coverage import ROWS
        from .pause.coverage import ROWS as PAUSE_ROWS
        rows = list(ROWS) + list(PAUSE_ROWS)
    out = {}
    for r in rows:
        for t in r["tests"]:
            if t.startswith("external/"):
                repo, _, rest = t[len("external/"):].partition("/")
                out.setdefault(repo, set()).add(rest)
    return {k: sorted(v) for k, v in sorted(out.items())}


def check(root=None) -> list:
    """Problems with the vendored trees or the manifest; empty when every tree is the one that was tested."""
    root = find_root(root)
    m, errs = load_manifest(root), []
    entries = m.get("repos", {})
    present, listed = set(repos(root)), set(entries)
    errs += [f"{n}: vendored but not in the manifest" for n in sorted(present - listed)]
    errs += [f"{n}: in the manifest but not vendored" for n in sorted(listed - present)]
    for name in sorted(present & listed):
        e, repo = entries[name], root / "external" / name
        d = tree_digest(repo)
        if d["tree_sha256"] != e.get("tree_sha256"):
            errs.append(f"{name}: tree hash {d['tree_sha256'][:16]} is not the manifest's {str(e.get('tree_sha256'))[:16]}; "
                        "after changing vendored code, re-run `closure external test --record`")
        if has_licence(repo) != (e.get("license", "none") != "none"):
            errs.append(f"{name}: the licence file and the manifest's licence entry disagree")
        errs += [f"{name}: the manifest entry has no {k}" for k in ("source", "commit") if not e.get(k)]
    for name, tests in cited_tests().items():
        rec = entries.get(name, {}).get("tests", {}).get("cited", {})
        errs += [f"{name}: cited test {t} is {rec.get(t, 'not recorded')} in the manifest" for t in tests if rec.get(t) != "passed"]
    return errs


def _pytest_config(repo: Path):
    for name, marker in (("pytest.ini", ""), ("pyproject.toml", "[tool.pytest.ini_options]"), ("tox.ini", "[pytest]"),
                         ("setup.cfg", "[tool:pytest]")):
        p = repo / name
        if p.is_file() and marker in p.read_text(encoding="utf-8", errors="replace"):
            return p
    return None


def _outcomes(xml: Path) -> tuple:
    """(counts, [(classname, name, outcome)]) from a JUnit XML report."""
    root = ET.parse(xml).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    counts = {k: sum(int(s.get(k, 0) or 0) for s in suites) for k in ("tests", "failures", "errors", "skipped")}
    counts["passed"] = counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"]
    cases = []
    for c in root.iter("testcase"):
        kids = {k.tag for k in c}
        outcome = "failed" if kids & {"failure", "error"} else "skipped" if "skipped" in kids else "passed"
        cases.append((c.get("classname", ""), c.get("name", ""), outcome))
    return counts, cases


def cited_outcome(cited: str, cases) -> str:
    """Outcome of one cited test (path::name) among JUnit cases; parametrised variants all count."""
    path, _, name = cited.partition("::")
    mod = (path[:-3] if path.endswith(".py") else path).replace("/", ".")
    hits = [o for cls, n, o in cases if (cls == mod or cls.startswith(mod + ".")) and (n == name or n.startswith(name + "["))]
    if not hits:
        return "not run"
    return "failed" if "failed" in hits else "passed" if "passed" in hits else "skipped"


def skip_reasons(output: str) -> dict:
    out = {}
    for n, reason in _SKIPPED.findall(output):
        out[reason.strip()] = out.get(reason.strip(), 0) + int(n)
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def _text(b) -> str:
    return b.decode(errors="replace") if isinstance(b, bytes) else (b or "")


def install(repo, python=None) -> tuple:
    """pip install --no-deps -e the repository, so console scripts its tests call exist. Returns (ok, message)."""
    repo = Path(repo)
    if not ((repo / "pyproject.toml").is_file() or (repo / "setup.py").is_file()):
        return True, "nothing to install (no pyproject.toml or setup.py)"
    p = subprocess.run([python or sys.executable, "-m", "pip", "install", "-q", "--no-deps", "-e", str(repo)],
                       capture_output=True, text=True)
    return p.returncode == 0, (p.stdout + p.stderr).strip()[-400:]


def run_suite(repo, timeout: int = 1800, python=None, log_dir=None, cited=()) -> dict:
    """Run one vendored repository's own tests in a fresh pytest process and report what happened."""
    repo = Path(repo).resolve()
    before = tree_digest(repo)["tree_sha256"]
    with tempfile.TemporaryDirectory(prefix=f"external-{repo.name}-") as td:
        td = Path(td)
        cfg = _pytest_config(repo)
        if cfg is None:                                   # never fall through to this repository's own pytest settings
            cfg = td / "pytest.ini"
            cfg.write_text("[pytest]\n", encoding="utf-8")
        xml = td / "junit.xml"
        env = {k: v for k, v in os.environ.items() if k != "PYTEST_ADDOPTS"}
        env.update(PYTHONPATH=os.pathsep.join(p for p in (str(repo), str(repo / "src"), os.environ.get("PYTHONPATH", "")) if p),
                   PYTHONDONTWRITEBYTECODE="1", HYPOTHESIS_STORAGE_DIRECTORY=str(td / "hypothesis"))
        cmd = [python or sys.executable, "-m", "pytest", "-c", str(cfg), "--rootdir", str(repo), "-p", "no:cacheprovider",
               "-rs", f"--junitxml={xml}", "-o", "junit_family=xunit2"]
        t0 = time.monotonic()
        try:
            p = subprocess.run(cmd, cwd=repo, env=env, capture_output=True, text=True, timeout=timeout)
            rc, out = p.returncode, p.stdout + p.stderr
        except subprocess.TimeoutExpired as e:
            rc, out = -1, f"timed out after {timeout} s\n{_text(e.stdout)}{_text(e.stderr)}"
        seconds = round(time.monotonic() - t0, 1)
        if xml.exists():
            counts, cases = _outcomes(xml)
        else:
            counts, cases = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0, "passed": 0}, []
    if log_dir:
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        (Path(log_dir) / f"{repo.name}.log").write_text(" ".join(cmd) + "\n\n" + out, encoding="utf-8")
    status = {0: "pass", 5: "no tests", -1: "timeout"}.get(rc, "fail")
    return {"repo": repo.name, "status": status, "returncode": rc, "seconds": seconds, **counts,
            "skip_reasons": skip_reasons(out), "cited": {t: cited_outcome(t, cases) for t in cited},
            "tests_wrote_into_tree": tree_digest(repo)["tree_sha256"] != before,
            "tail": out.strip().splitlines()[-3:]}


def record(results, root=None) -> Path:
    """Write test results and current tree hashes into the manifest, keeping the provenance fields already there."""
    root = find_root(root)
    m = load_manifest(root)
    entries = m.setdefault("repos", {})
    when = {"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"), "python": platform.python_version(),
            "platform": f"{platform.system()} {platform.machine()}"}
    for r in results:
        repo = root / "external" / r["repo"]
        e = entries.setdefault(r["repo"], {})
        e.update(tree_digest(repo))
        e.setdefault("license", "see LICENSE" if has_licence(repo) else "none")
        e["tests"] = {**{k: r[k] for k in ("status", "passed", "skipped", "failures", "errors", "seconds")}, **when,
                      "skip_reasons": r["skip_reasons"], "cited": r["cited"]}
    m["repos"] = dict(sorted(entries.items()))
    return save_manifest(m, root)


def table(m: dict) -> str:
    rows = ["| repository | source | commit | files | licence | tests (passed / skipped / failed) | run |",
            "| --- | --- | --- | --- | --- | --- | --- |"]
    for name, e in m.get("repos", {}).items():
        t = e.get("tests", {})
        res = f"{t.get('passed', '-')} / {t.get('skipped', '-')} / {t.get('failures', 0) + t.get('errors', 0)}" if t else "not run"
        rows.append(f"| {name} | {e.get('source', '-')} | {str(e.get('commit', '-'))[:12]} | {e.get('files', '-')} | "
                    f"{e.get('license', '-')} | {res} | {t.get('date', '-')} |")
    return "\n".join(rows)
