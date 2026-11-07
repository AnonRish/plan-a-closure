"""`closure tier0`: the whole Tier 0 pilot (docs/HARDWARE_CONFIG.md section A) as one unattended command.

An operator can run it alone: it needs one GPU with root for clock and power-limit control, takes about two hours on
hardware, never waits for keyboard input, and leaves one bundle to send back. Steps, in order:

  unit tests    from a source checkout with pytest installed (skipped otherwise, or with --skip-tests)
  selftest      simulated end to end: estimators, signature, commitments                (stops the run on failure)
  preflight     NVML, energy counter, torch, clock sync                                 (stops the run on failure)
  hw-selftest   does energy track verified work on this GPU? (r2 > 0.9)                 (stops the run on failure)
  hw-probe      efficiency slack over clocks, caps, precisions and operands; the energy floor, int8 and fp8 included
  hw-state      device-memory residency: blocks parked in host memory are caught by time
  hw-trial      smoke T1 (30 min reference, 30 min blind audit with hidden-load injection), the probe bound into the
                pre-registration, prereg.json stamped with `ots` if installed before any audit data exist
  verify        hash chain, signature, schedule commitment, prereg, results and probe hashes

Each step's exact command, output, exit status and duration go to OUT/logs/. OUT/SUMMARY.md collects the headline
numbers, and OUT/tier0_bundle.tar.gz holds everything except the private signing key (signing_key.bin), which stays on
the machine. With --mock every hardware step runs on the fake rigs, so the sequence can be rehearsed, and is tested,
without a GPU. A mock run makes no physical claim.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import platform
import shlex
import subprocess
import sys
import tarfile
import time
from pathlib import Path

from . import __version__

PRIVATE_KEY = "signing_key.bin"
BUNDLE = "tier0_bundle.tar.gz"


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _json_in(text: str):
    """The outermost JSON object a step printed (hw-selftest, hw-state and verify print one), or None."""
    i, j = text.find("{"), text.rfind("}")
    if i < 0 or j <= i:
        return None
    try:
        return json.loads(text[i:j + 1])
    except ValueError:
        return None


def _read(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _fmt(x, spec=".4f") -> str:
    if x is None:
        return "n/a"
    return format(x, spec) if isinstance(x, (int, float)) and not isinstance(x, bool) else str(x)


def plan(out: Path, gpu: int, mock: bool, run_tests: bool) -> list:
    """(key, title, argv, stops_the_run_on_failure). hw-trial gets --probe at run time if the probe wrote a file."""
    py = sys.executable
    cli = [py, "-m", "closure.cli"]
    hw, mk = (["--mock"], ["--mock"]) if mock else (["--confirm-hardware"], [])
    steps = []
    tests = Path(__file__).resolve().parents[2] / "tests"
    if (run_tests and tests.is_dir() and importlib.util.find_spec("pytest") is not None
            and not os.environ.get("CLOSURE_TIER0_INNER")):
        steps.append(("unit-tests", "unit tests", [py, "-m", "pytest", "-q", "-p", "no:cacheprovider", str(tests)], True))
    steps += [
        ("selftest", "simulated end-to-end self-test", cli + ["selftest"], True),
        ("preflight", "NVML, energy counter, torch, clock sync", cli + ["preflight"] + mk, True),
        ("hw-selftest", "energy tracks verified work on this GPU", cli + ["hw-selftest", "--gpus", str(gpu)] + mk, True),
        ("hw-probe", "efficiency slack and energy floor",
         cli + ["hw-probe", "--gpu", str(gpu), "--out", str(out / "probe.json")] + hw, False),
        ("hw-state", "device-memory residency",           # mock: the small, fast configuration tests/test_cli.py uses
         cli + ["hw-state", "--device", f"cuda:{gpu}"]
         + (["--mock", "--block-mb", "1", "--blocks", "32", "--k", "16", "--trials", "60", "--park-frac", "0.3"] if mock
            else []), False),
        ("hw-trial", "smoke trial with blind hidden-load injection",
         cli + ["hw-trial", "--profile", "smoke", "--gpus", str(gpu), "--out", str(out / "T1-smoke"), "--stamp-prereg"] + hw,
         True),
        ("verify", "evidence chain, signature, commitments", cli + ["verify", str(out / "T1-smoke")], True),
    ]
    return steps


def run(out: Path, gpu: int = 0, mock: bool = False, run_tests: bool = True, echo=print) -> int:
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        echo(f"refusing: {out} is not empty; choose a new --out so that no earlier run is mixed into this one")
        return 2
    logs = out / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "CLOSURE_TIER0_INNER": "1", "PYTHONUNBUFFERED": "1"}
    started, results, stopped = _now(), [], None
    echo(f"plan-a-closure {__version__} tier0 ({'MOCK: fake hardware' if mock else 'HARDWARE'}) -> {out}")
    for i, (key, title, argv, critical) in enumerate(plan(out, gpu, mock, run_tests), 1):
        if stopped:
            results.append({"key": key, "title": title, "exit": None, "minutes": 0.0, "log": None, "skipped": True})
            continue
        if key == "hw-trial" and (out / "probe.json").exists():
            argv = argv + ["--probe", str(out / "probe.json")]
        lf = logs / f"{i:02d}-{key}.log"
        echo(f"[{i}] {key}: {title} (log: {lf})")
        t0 = time.time()
        with open(lf, "w", encoding="utf-8") as fh:
            fh.write("$ " + " ".join(shlex.quote(x) for x in argv) + "\n\n")
            fh.flush()
            rc = subprocess.run(argv, stdout=fh, stderr=subprocess.STDOUT, env=env).returncode
        mins = (time.time() - t0) / 60.0
        results.append({"key": key, "title": title, "exit": rc, "minutes": round(mins, 2),
                        "log": str(lf.relative_to(out)), "skipped": False})
        echo(f"    exit {rc} after {mins:.1f} min")
        if rc != 0 and critical:
            stopped = key
    (out / "SUMMARY.md").write_text(summary(out, results, mock, started, stopped), encoding="utf-8")
    tgz, digest = bundle(out)
    echo(f"wrote {out / 'SUMMARY.md'}")
    echo(f"wrote {tgz} (sha256 {digest}): send this file back. {PRIVATE_KEY} was left out on purpose; keep it private.")
    return 1 if stopped else 0


def _step_output(out: Path, results: list, key: str) -> str:
    for r in results:
        if r["key"] == key and r["log"]:
            try:
                text = (out / r["log"]).read_text(encoding="utf-8")
            except OSError:
                return ""
            return text.split("\n\n", 1)[1] if "\n\n" in text else text      # drop the command line
    return ""


def summary(out: Path, results: list, mock: bool, started: str, stopped) -> str:
    L = ["# Tier 0 pilot: summary", "",
         f"- plan-a-closure {__version__}; mode: "
         + ("MOCK (fake hardware: a rehearsal, no physical claim)" if mock else "HARDWARE"),
         f"- started {started}, finished {_now()}; host {platform.platform()}, Python {platform.python_version()}",
         "- outcome: " + ("every step ran" if not stopped else f"stopped after `{stopped}` failed; later steps were skipped"),
         "", "| # | step | what it checks | exit | minutes | log |", "| --- | --- | --- | --- | --- | --- |"]
    for i, r in enumerate(results, 1):
        L.append(f"| {i} | {r['key']} | {r['title']} | {'skipped' if r['skipped'] else r['exit']} | {r['minutes']} "
                 f"| {r['log'] or ''} |")
    pr = _read(out / "probe.json")
    if pr:
        L += ["", "## Probe (H1.6 slack, H1.7 floor)", "",
              f"- s_max = {_fmt(pr.get('s_max'))} (stack {_fmt(pr.get('s_stack'))}, operand {_fmt(pr.get('s_operand'))}); "
              f"allowed stack variants {pr.get('n_allowed_variants')}, operand variants {pr.get('n_operand_variants')}",
              f"- e_floor = {_fmt(pr.get('e_floor_j_per_flop'), '.3g')} J/FLOP at "
              f"{(pr.get('e_floor_at') or {}).get('variant')}; band/floor = {_fmt(pr.get('band_over_floor'), '.3g')}",
              f"- probe.json sha256 {pr.get('sha256')}"]
        L += [f"- note: {n}" for n in pr.get("notes", [])]
    st = _json_in(_step_output(out, results, "hw-state"))
    if st:
        L += ["", "## Device-memory residency (T2 pilot)", "",
              f"- pass = {st.get('pass')}: honest false alarm {_fmt(st.get('honest_false_alarm'))}, parked-block detection "
              f"{_fmt(st.get('parked_detection'))} (block {st.get('block_mb')} MB, k = {st.get('k')})"]
    res = _read(out / "T1-smoke" / "results.json")
    if res:
        fp = (res.get("false_positive") or {}).get("combined") or {}
        sl = res.get("slack") or {}
        L += ["", "## Smoke trial (T1)", "",
              f"- status: {res.get('status')}",
              f"- false positives {fp.get('k')}/{fp.get('n')} (95% upper {_fmt(fp.get('cp95_upper'))})",
              f"- closure gap {_fmt(res.get('closure_gap_fraction'))} of capacity energy; slack-inflated gap "
              f"{_fmt(sl.get('slack_inflated_gap_fraction'))}",
              "- the smoke profile checks the pipeline; the registered numbers come from the Tier 1 run (`hw-full`)"]
    ver = _json_in(_step_output(out, results, "verify"))
    if ver:
        L += ["", "## Verification", "", "- " + ", ".join(f"{k}: {v}" for k, v in ver.items())]
    L += ["", "## What to send back", "",
          f"- `{BUNDLE}`: everything in this folder except `{PRIVATE_KEY}`.",
          f"- Keep `T1-smoke/{PRIVATE_KEY}` private or delete it: anyone holding it can forge this run's signature. "
          "The public key is in `T1-smoke/signature.json`.",
          "- If an independent power meter logged during the trial, export it as `timestamp_s,power_w` and run "
          f"`closure dcbus-analyze --run {out / 'T1-smoke'} --csv bus.csv`, then send `results_dcbus.json` as well."]
    return "\n".join(L) + "\n"


def bundle(out: Path):
    tgz = out / BUNDLE
    with tarfile.open(tgz, "w:gz") as tf:
        for p in sorted(out.rglob("*")):
            if p.is_file() and p.name != PRIVATE_KEY and p != tgz:
                tf.add(p, arcname=str(Path(out.name) / p.relative_to(out)))
    with tarfile.open(tgz) as tf:                      # the private key must never leave the machine in the bundle
        if any(Path(n).name == PRIVATE_KEY for n in tf.getnames()):
            tgz.unlink()
            raise RuntimeError("refusing to keep a bundle that contains the private signing key")
    return tgz, hashlib.sha256(tgz.read_bytes()).hexdigest()
