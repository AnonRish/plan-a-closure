"""`closure tier0`: the whole Tier 0 pilot (docs/HARDWARE_CONFIG.md section A) as one unattended command.

An operator can run it alone: it needs one GPU with root for clock and power-limit control, takes about two hours on
hardware, never waits for keyboard input, and leaves one bundle to send back. Steps, in order:

  unit tests    from a source checkout with pytest installed (skipped otherwise, or with --skip-tests)
  selftest      simulated end to end: estimators, signature, commitments                (stops the run on failure)
  preflight     NVML, energy counter, torch, clock sync                                 (stops the run on failure)
  hw-selftest   does energy track verified work on this GPU (r2 > 0.9), and do the load levels do different work?
                its unit of work, sized to the GPU, is passed on to hw-probe and hw-trial (stops the run on failure)
  hw-probe      efficiency slack over clocks, caps, precisions and operands; the energy floor, int8 and fp8 included;
                a null twin (the reference again) measures the bound noise alone gives (amendment v0.8). Six rounds
                with the medium and long profiles, three with smoke
  hw-state      device-memory residency: blocks parked in host memory are caught by the time of the slowest block
                of a challenge; 1,000 parked-prover and 2,000 honest challenges in one interleaved pass (challenge
                size chosen so sampling alone touches a parked block 99.9% of the time)
  hw-trial      T1 with SM clocks locked at the highest clock the probe shows holding with power to spare when
                the GPU is flat out (amendment v0.7; where the machine allows a lock), the probe bound into the
                pre-registration, the hidden load measured on its own first so
                that its labels are its measured power, prereg.json stamped with `ots` if installed before any trial
                data exist, a fresh random seed. Both profiles interleave reference blocks with a balanced blind audit
                and use the link analysis (amendment v0.6).
                --trial-profile smoke (the default): one hour, 100 reference and 80 audit blocks of 20 s; it checks
                the pipeline and cannot decide the false-alarm rule (40 null blocks; the rule needs 200).
                --trial-profile medium: under 4 h, 150 reference and 316 audit blocks of 30 s (204 of them null):
                the smallest trial that can decide the registered rules H1.1 to H1.4, for a session that cannot be
                trusted for twelve hours (free Colab).
                --trial-profile long: about 9 h, 144 reference and 396 audit blocks of 60 s; the same rules with
                blocks twice as long (fits a 12-hour Kaggle session). --campaign NAME:i/N declares the trial one of
                N to be read together (`closure pool`), before any of them has data.
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
import signal
import subprocess
import sys
import tarfile
import time
from pathlib import Path

from . import __version__

PRIVATE_KEY = "signing_key.bin"
BUNDLE = "tier0_bundle.tar.gz"
PROBE_REPEATS = {"smoke": 3}         # medium and long: hw-probe's default, six rounds (amendment v0.8)
TRIALS = {"smoke": "smoke trial (about 1 h): interleaved calibration, balanced blind hidden-load schedule",
          "medium": "medium trial (under 4 h): interleaved calibration, balanced blind hidden-load schedule",
          "long": "long trial (about 9 h): interleaved calibration, balanced blind hidden-load schedule"}


def trial_dir(profile: str = "smoke") -> str:
    return f"T1-{profile}"


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


COMPARISON = "link-full"   # the comparison every hardware profile declares (amendment v0.7 (c); cli.V06)
HEADROOM = 0.95      # a trial lock may draw at most this share of the power limit with the GPU flat out (amendment v0.7)


def trial_clock(pr: dict) -> dict:
    """Which SM clock a trial should lock, read off a probe (amendment v0.7 (a)), and why.

    A lock is only a lock while the power limiter leaves it alone. The probe's top load level is 0.9 and the trial's is
    1.0, so a clock that held at the probe's top level can still be pulled down in the trial. Run 8 showed it
    (docs/DEVIATIONS.md section 7): 870 MHz held at level 0.9 with 64.9 W of a 70 W limit, and at level 1 the GPU sat
    on the limit (69.5 W) while its throughput moved by 5% from one stretch to the next. The work a full GPU gets
    through is the only place hidden work shows there, so that wobble is what hid the two loads the run missed.

    So the power a lock draws flat out is estimated from the probe: idle power, plus the power above idle at the top
    level divided by the share of time the GPU was busy there. The trial locks the highest clock that (1) the probe
    saw held within 2% at its top level, (2) kept up with the work there, and (3) is estimated to draw at most 95% of
    the power limit flat out. `mhz` is None when no clock qualifies, and for a rehearsal or mock probe."""
    out = {"mhz": None, "rule": "v0.7: highest clock held at the probe's top level whose estimated flat-out power is at "
                                f"most {HEADROOM:.0%} of the power limit", "power_limit_w": None, "candidates": []}
    if not pr or not str(pr.get("status", "")).startswith("HARDWARE"):
        return out
    rig = pr.get("rig") or {}
    cap = rig.get("start_power_limit_w") or rig.get("default_power_limit_w")
    out["power_limit_w"] = cap
    for v in pr.get("variants", []):
        if v.get("kind") != "clock_cap" or not v.get("allowed") or v.get("value") is None:
            continue
        f, levels = float(v["value"]), v.get("levels", [])
        top = max(levels, key=lambda lv: lv.get("level", 0.0), default=None)
        if not top or top.get("sm_mhz") is None or top.get("power_w_mean") is None:
            continue
        idle = min(levels, key=lambda lv: lv.get("level", 0.0)).get("power_w_mean")
        idle = v.get("idle_power_w") if idle is None else idle
        busy = top.get("busy_frac")
        p_top = float(top["power_w_mean"])
        if idle is None or not busy or busy <= 0:
            flat = p_top                              # no busy share recorded: the top level is the best estimate
        else:
            flat = float(idle) + (p_top - float(idle)) / min(1.0, float(busy))
        row = {"mhz": f, "held": abs(float(top["sm_mhz"]) - f) <= 0.02 * f, "kept_up": bool(top.get("feasible")),
               "top_level": top.get("level"), "power_at_top_level_w": p_top, "busy_share_at_top_level": busy,
               "flat_out_power_w": flat, "flat_out_share_of_limit": None if not cap else flat / float(cap)}
        row["ok"] = bool(row["held"] and row["kept_up"] and (cap is None or flat <= HEADROOM * float(cap)))
        out["candidates"].append(row)
    ok = [r["mhz"] for r in out["candidates"] if r["ok"]]
    out["mhz"] = max(ok) if ok else None
    # what the rule in force until 0.8.0 chose (amendment v0.4 (b)): held and at most 95% of the limit at the top level
    old = [r["mhz"] for r in out["candidates"] if r["held"] and r["kept_up"]
           and (cap is None or r["power_at_top_level_w"] <= HEADROOM * float(cap))]
    out["mhz_under_v0_4"] = max(old) if old else None
    return out


def _trial_clock_args(probe_path: Path) -> list:
    """`--lock-clock-mhz N` for the trial, from the probe (`trial_clock`), so that the trial calibrates and audits at
    one clock (assumption A2; run 3 on a Colab T4 drifted without a lock, docs/DEVIATIONS.md section 3). Empty for a
    rehearsal or mock probe, or when no clock qualifies."""
    best = trial_clock(_read(Path(probe_path)) or {})["mhz"]
    return ["--lock-clock-mhz", str(int(round(best)))] if best else []


def provenance() -> str:
    """Which code ran: the git commit of the checkout this package was imported from, and whether tracked files differ
    from it. A version number alone does not pin the code; a commit does."""
    root = Path(__file__).resolve().parents[2]
    try:
        h = subprocess.run(["git", "-C", str(root), "rev-parse", "--short=12", "HEAD"], capture_output=True,
                           text=True, timeout=15)
        if h.returncode != 0:
            return "not a git checkout"
        d = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"],
                           capture_output=True, text=True, timeout=15)
        return f"commit {h.stdout.strip()}, {'clean' if d.returncode == 0 and not d.stdout.strip() else 'modified'}"
    except (OSError, subprocess.TimeoutExpired):
        return "git unavailable"


def _unit_args(selftest_output: str) -> list:
    """`--dim N --mem-elems M` from the unit hw-selftest printed, so hw-probe and hw-trial measure the same unit of work
    (on a small GPU the unit is sized down from 8192; see hw/workloads.py). Empty when it printed none (mock runs)."""
    u = (_json_in(selftest_output) or {}).get("unit") or {}
    if u.get("dim") and u.get("mem_elems"):
        return ["--dim", str(int(u["dim"])), "--mem-elems", str(int(u["mem_elems"]))]
    return []


def _read(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _ran(results: list) -> str:
    """Every step ran, but a step that ran can still have reported a failed check (a non-critical step's exit 1)."""
    bad = [r["key"] for r in results if not r["skipped"] and r["exit"] not in (0, None)]
    return "every step ran" + (f"; {len(bad)} reported a failed check ({', '.join(bad)}): see its section below"
                               if bad else "")


def _interrupted(run: Path):
    """The chain's record of a trial stopped before its data were complete (trial.py keeps raw_partial.npz), or None."""
    try:
        recs = [json.loads(line)["record"] for line in (run / "chain.jsonl").read_text(encoding="utf-8").splitlines()]
    except (OSError, ValueError, KeyError):
        return None
    return next((r for r in reversed(recs) if r.get("phase") == "interrupted"), None)


def _fmt(x, spec=".4f") -> str:
    if x is None:
        return "n/a"
    return format(x, spec) if isinstance(x, (int, float)) and not isinstance(x, bool) else str(x)


def plan(out: Path, gpu: int, mock: bool, run_tests: bool, rehearsal: bool = False, profile: str = "smoke",
         campaign: str = None, seed: int = 1) -> list:
    """(key, title, argv, stops_the_run_on_failure). hw-trial gets --probe at run time if the probe wrote a file.
    rehearsal: the hardware steps on CPU torch against a fake NVML and nvidia-smi (tests), with small sizes."""
    py = sys.executable
    cli = [py, "-m", "closure.cli"]
    hw, mk = (["--mock"], ["--mock"]) if mock else (["--confirm-hardware"], [])
    small = rehearsal and not mock
    steps = []
    tests = Path(__file__).resolve().parents[2] / "tests"
    if (run_tests and tests.is_dir() and importlib.util.find_spec("pytest") is not None
            and not os.environ.get("CLOSURE_TIER0_INNER")):
        # test_runs_on_record.py re-reads the published bundles under results/: it checks the repository's records,
        # which a run on this machine does not depend on, so it is left to CI and a rounding difference in it cannot
        # stop a ten-hour run
        steps.append(("unit-tests", "unit tests", [py, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                                                   f"--ignore={tests / 'test_runs_on_record.py'}", str(tests)], True))
    steps += [
        ("selftest", "simulated end-to-end self-test", cli + ["selftest"], True),
        ("preflight", "NVML, energy counter, torch, clock sync, which physical GPU",
         cli + ["preflight", "--gpu", str(gpu)] + mk, True),
        ("hw-selftest", "energy tracks verified work on this GPU",     # a rehearsal's statistics mean nothing
         cli + ["hw-selftest", "--gpus", str(gpu)] + mk + (["--windows", "3"] if small else []), not small),
        ("hw-probe", "efficiency slack and energy floor",
         cli + ["hw-probe", "--gpu", str(gpu), "--out", str(out / "probe.json")] + hw
         + (["--dim", "64", "--window-s", "0.3", "--levels", "0,0.5", "--repeats", "1"] if small
            # amendment v0.8: six rounds (hw-probe's default) where the trial can decide the rules; the smoke
            # profile checks the pipeline and keeps the three rounds runs 1 to 8 used
            else ["--repeats", str(PROBE_REPEATS[profile])] if profile in PROBE_REPEATS else []), False),
        ("hw-state", "device-memory residency",           # mock: the small, fast configuration tests/test_cli.py uses
         cli + ["hw-state", "--device", "cpu" if small else f"cuda:{gpu}"]
         + (["--mock"] if mock else [])
         # a mock or rehearsal run checks the pipeline, not the statistics: 24 of 32 blocks per challenge, so none
         # can miss every parked block, and a threshold far out, so 60 challenges cannot fail a 1% rule by luck
         + (["--block-mb", "1", "--blocks", "32", "--k", "24", "--trials", "60", "--park-frac", "0.3",
             "--verify-every", "5", "--threshold-alpha", "1e-6"] if mock or small else []), False),
        ("hw-trial", TRIALS[profile],
         cli + ["hw-trial", "--profile", "rehearsal" if small else profile, "--gpus", str(gpu), "--out",
                str(out / trial_dir(profile)), "--stamp-prereg", "--seed", str(seed)] + hw
         + (["--campaign", campaign] if campaign else []), True),
        ("verify", "evidence chain, signature, commitments", cli + ["verify", str(out / trial_dir(profile))], True),
        # amendment v0.7 (c): one analysis declared beforehand to be read beside the registered one. It decides
        # nothing and a failure here stops nothing.
        ("compare", "the declared comparison (link-full): the registered analysis told when the GPU was asked to run flat out",
         cli + ["reanalyze", "--run", str(out / trial_dir(profile)), "--analysis", COMPARISON], False),
    ]
    return steps


def _machine_record(out: Path, env: dict, echo) -> None:
    """doctor.json and doctor.md in the run folder: what `closure doctor` read on this machine before anything ran, so
    that every bundle says which GPU model, driver and PyTorch it came from in one place. It runs in its own short
    process, so that its look at CUDA leaves no context on the GPU for the run to share. A record, never a reason to
    stop."""
    try:
        r = subprocess.run([sys.executable, "-m", "closure.cli", "doctor", "--out", str(out)], capture_output=True,
                           text=True, timeout=300, env=env)
        if r.returncode != 0:
            echo(f"machine record not written (closure doctor exit {r.returncode})")
    except (OSError, subprocess.SubprocessError) as e:
        echo(f"machine record not written ({type(e).__name__}: {e})")


def _gpu_at_start(gpu: int, echo):
    """(target, power limit in W) before anything changes, so the final step can put the limit back as found."""
    try:
        import pynvml as N
        from .hw import gpu as G
        N.nvmlInit()
        target = G.resolve(gpu, N=N)
        w = G.current_power_limit_w(N, target.nvml_index)
        echo(f"GPU: {target.describe()}; power limit at start: {'unknown' if w is None else f'{w:.0f} W'}")
        return target, w
    except Exception as e:                            # preflight reports why and stops the run
        echo(f"GPU not resolved yet ({type(e).__name__}: {e}); preflight will say why")
        return None, None


def run(out: Path, gpu: int = 0, mock: bool = False, run_tests: bool = True, echo=print, profile: str = "smoke",
        campaign: str = None, seed: int = None) -> int:
    from .hw.gpu import STOP_SIGNALS
    if echo is print:                   # a line at a time, also when the output is a file someone is watching
        def echo(*a):
            print(*a, flush=True)
    if profile not in TRIALS:
        raise ValueError(f"unknown trial profile '{profile}' ({', '.join(TRIALS)})")
    out = Path(out)
    if out.exists() and any(out.iterdir()):
        echo(f"refusing: {out} is not empty; choose a new --out so that no earlier run is mixed into this one")
        return 2
    camp = None
    if campaign:                        # a malformed NAME:i/N is refused here, not an hour in when hw-trial reads it
        from .cli import _campaign
        try:
            camp = _campaign(campaign)
        except SystemExit as e:
            echo(f"refusing: {e}")
            return 2
    logs = out / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "CLOSURE_TIER0_INNER": "1", "PYTHONUNBUFFERED": "1"}
    started, results, stopped = _now(), [], None
    echo(f"plan-a-closure {__version__} ({provenance()}) tier0 ({'MOCK: fake hardware' if mock else 'HARDWARE'}, "
         f"{profile} trial) -> {out}")
    _machine_record(out, env, echo)
    target, start_w = (None, None) if mock else _gpu_at_start(gpu, echo)
    if seed is None:                    # a hardware run draws its own: until 0.8.0 every run used seed 1, so runs 1
        # to 5 all followed one load sequence and (per profile) one hidden-load schedule. Mock runs stay repeatable:
        # seed 1, or the trial's number in its campaign, so that a mock campaign's trials differ as real ones do.
        seed = (camp["index"] if camp else 1) if mock else 1 + int.from_bytes(os.urandom(4), "big") % (2 ** 31 - 2)
    echo(f"trial seed {seed} (the load sequence and the committed schedule follow from it; recorded in prereg.json)")
    steps = plan(out, gpu, mock, run_tests, rehearsal=bool(target is not None and target.rehearsal), profile=profile,
                 campaign=campaign, seed=seed)
    if not mock:                                      # always last, even after a failure or a signal: the GPU as found
        steps.append(("hw-restore", "clocks unlocked, power limit as found",   # every step runs as this same user
                      [sys.executable, "-m", "closure.cli", "hw-restore", "--gpu", str(gpu), "--same-user"]
                      + (["--power-limit-w", f"{start_w:g}"] if start_w else []), None))

    # A signal (Ctrl-C, a scheduler's SIGTERM, a closed terminal) is passed to the running step as SIGTERM, so it restores
    # the GPU before it exits; then the remaining steps are skipped, except hw-restore, and the summary is still written.
    caught = {"sig": None, "child": None}

    def on_signal(signum, frame):
        if caught["sig"] is not None:
            return
        caught["sig"] = int(signum)
        echo(f"received signal {signum}: stopping after the current step has cleaned up")
        c = caught["child"]
        if c is not None and c.poll() is None:
            try:
                c.send_signal(signal.SIGTERM)
            except OSError:
                pass

    old = {}
    for sg in STOP_SIGNALS:
        try:
            old[sg] = signal.signal(sg, on_signal)
        except (ValueError, OSError):                 # not the main thread
            pass
    unit_args = []                                    # hw-selftest's unit of work, passed on so all steps use one unit
    try:
        for i, (key, title, argv, critical) in enumerate(steps, 1):
            always = critical is None
            if (stopped or caught["sig"] is not None) and not always:
                results.append({"key": key, "title": title, "exit": None, "minutes": 0.0, "log": None, "skipped": True})
                continue
            if key in ("hw-probe", "hw-trial") and unit_args and "--dim" not in argv:
                argv = argv + unit_args
            if key == "hw-trial" and "--lock-clock-mhz" not in argv:
                clock_args = _trial_clock_args(out / "probe.json")
                if clock_args:
                    echo(f"    hw-trial locks SM clocks at {clock_args[1]} MHz, the highest clock probe.json shows "
                         f"this GPU holding with at most {HEADROOM:.0%} of its power limit when flat out")
                argv = argv + clock_args
            if key == "hw-trial" and (out / "probe.json").exists():
                argv = argv + ["--probe", str(out / "probe.json")]
            lf = logs / f"{i:02d}-{key}.log"
            echo(f"[{i}] {key}: {title} (log: {lf})")
            t0 = time.time()
            with open(lf, "w", encoding="utf-8") as fh:
                fh.write("$ " + " ".join(shlex.quote(x) for x in argv) + "\n\n")
                fh.flush()
                child = subprocess.Popen(argv, stdout=fh, stderr=subprocess.STDOUT, env=env)
                caught["child"] = child
                rc = child.wait()
                caught["child"] = None
            mins = (time.time() - t0) / 60.0
            results.append({"key": key, "title": title, "exit": rc, "minutes": round(mins, 2),
                            "log": str(lf.relative_to(out)), "skipped": False})
            echo(f"    exit {rc} after {mins:.1f} min")
            if key == "hw-selftest" and rc == 0:
                unit_args = _unit_args(_step_output(out, results, key))
            if caught["sig"] is not None and not stopped:
                stopped = f"signal {caught['sig']}"
            elif rc != 0 and critical and not stopped:
                stopped = key
        (out / "SUMMARY.md").write_text(summary(out, results, mock, started, stopped,
                                                rehearsal=bool(target is not None and target.rehearsal),
                                                trial=trial_dir(profile)), encoding="utf-8")
        tgz, digest = bundle(out)
    finally:
        for sg, h in old.items():
            try:
                signal.signal(sg, h)
            except (ValueError, OSError):
                pass
    echo(f"wrote {out / 'SUMMARY.md'}")
    echo(f"wrote {tgz} (sha256 {digest}): send this file back. {PRIVATE_KEY} was left out on purpose; keep it private.")
    if caught["sig"] is not None:
        return 128 + caught["sig"]
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


def summary(out: Path, results: list, mock: bool, started: str, stopped, rehearsal: bool = False,
            trial: str = "T1-smoke") -> str:
    L = ["# Tier 0 pilot: summary", "",
         f"- plan-a-closure {__version__} ({provenance()}); mode: "
         + ("MOCK (fake hardware: a rehearsal, no physical claim)" if mock else
            "REHEARSAL (CPU torch against a fake NVML: no physical claim)" if rehearsal else "HARDWARE"),
         f"- started {started}, finished {_now()}; host {platform.platform()}, Python {platform.python_version()}",
         "- outcome: " + (_ran(results) if not stopped else
                          f"stopped by {stopped}; later steps were skipped, except restoring the GPU"
                          if str(stopped).startswith("signal") else
                          f"stopped after `{stopped}` failed; later steps were skipped"),
         "", "| # | step | what it checks | exit | minutes | log |", "| --- | --- | --- | --- | --- | --- |"]
    for i, r in enumerate(results, 1):
        L.append(f"| {i} | {r['key']} | {r['title']} | {'skipped' if r['skipped'] else r['exit']} | {r['minutes']} "
                 f"| {r['log'] or ''} |")
    doc = _read(out / "doctor.json")
    if doc:
        L += ["", "## This machine (`doctor.json`: what `closure doctor` read before the run)", ""]
        seen = [g for g in doc.get("nvidia_gpus") or [] if "error" not in g]
        for g in seen:
            cap = g.get("compute_capability")
            L.append(f"- GPU {g.get('index')}: {g.get('name')}"
                     + (f", compute capability {'.'.join(map(str, cap))}" if cap else "")
                     + (f" ({g['architecture']})" if g.get("architecture") else "")
                     + f", power limit {_fmt(g.get('power_limit_w'), '.0f')} W, energy counter "
                     + ("present" if g.get("energy_counter") else "absent") + "; "
                     + ("hardware runs of this kit on this GPU model were already on record"
                        if g.get("hardware_runs_on_record_for_this_model") else
                        "no hardware run of this kit on this GPU model was on record when this code was released"))
        if not seen:
            L.append("- no NVIDIA GPU that NVML can read" + (" (as expected for a mock run on a machine without one)" if mock else ""))
        tc, nv = doc.get("torch") or {}, doc.get("nvml") or {}
        L.append(f"- PyTorch {tc.get('version') if tc.get('installed') else 'not installed'}"
                 + (f", CUDA {'available' if tc.get('cuda') else 'not available'}" if tc.get("installed") else "")
                 + f"; NVML driver {nv.get('driver') if nv.get('nvml') else 'not available'}"
                 + f"; root: {'yes' if (doc.get('system') or {}).get('root') else 'no'}")
    hs = _json_in(_step_output(out, results, "hw-selftest"))
    if hs:
        L += ["", "## Energy tracks verified work (hw-selftest)", "",
              f"- pass = {hs.get('pass')}: r2 {_fmt(hs.get('r2'))} (needs > 0.9), idle {_fmt(hs.get('idle_power_w'), '.1f')} W"
              + ("" if hs.get("work_ratio_25_to_100") is None and "levels_distinct" not in hs else
                 f", work at 25% load / work at 100% load = {_fmt(hs.get('work_ratio_25_to_100'), '.2f')} (needs < 0.8)")]
        u = hs.get("unit") or {}
        if u.get("unit_s") is not None:
            L.append(f"- unit of work: {u.get('dim')}x{u.get('dim')} {u.get('dtype')} GEMM + {u.get('mem_elems')}-element "
                     f"pass, {1e3 * u['unit_s']:.1f} ms against a {1e3 * u.get('slot_s', 0.1):.0f} ms slot")
        if hs.get("diagnosis"):
            L.append(f"- diagnosis: {hs['diagnosis']}")
    pr = _read(out / "probe.json")
    if pr:
        L += ["", "## Probe (H1.6 slack, H1.7 floor)", "",
              f"- s_max = {_fmt(pr.get('s_max'))} (stack {_fmt(pr.get('s_stack'))}, operand {_fmt(pr.get('s_operand'))}); "
              f"allowed stack variants {pr.get('n_allowed_variants')}, operand variants {pr.get('n_operand_variants')}"
              + (f"; null twin s_null = {_fmt(pr['s_null'])}, the bound a setting with no effect gets in "
                 f"{(pr.get('settings') or {}).get('repeats')} rounds (not counted)" if pr.get("s_null") is not None else ""),
              f"- e_floor = {_fmt(pr.get('e_floor_j_per_flop'), '.3g')} J/FLOP at "
              f"{(pr.get('e_floor_at') or {}).get('variant')}; band/floor = {_fmt(pr.get('band_over_floor'), '.3g')}",
              f"- probe.json sha256 {pr.get('sha256')}"]
        L += [f"- note: {n}" for n in pr.get("notes", [])]
    st = _json_in(_step_output(out, results, "hw-state"))
    if st:
        L += ["", "## Device-memory residency (T2 pilot)", "",
              f"- pass = {st.get('pass')}: honest false alarm {_fmt(st.get('honest_false_alarm'))}, parked-block detection "
              f"{_fmt(st.get('parked_detection'))} (block {st.get('block_mb')} MB, k = {st.get('k')}, judged by "
              f"{st.get('statistic', 'total time')})"]
        ch, one, tt = st.get("challenges") or {}, st.get("touching_one_parked_block") or {}, st.get("total_time") or {}
        if ch:
            L.append(f"- {ch.get('honest')} honest and {ch.get('parked')} parked-prover challenges, judged against a "
                     f"threshold from {ch.get('calibration')} more honest ones ({ch.get('order')}); challenges that "
                     f"touched exactly one parked block: {one.get('detected')}/{one.get('n')} caught; digests "
                     f"recomputed by the verifier: {st.get('digests_verified')}, wrong: {st.get('digests_wrong')}")
        if tt:
            L.append(f"- by total time, the statistic until 0.8.0: false alarm {_fmt(tt.get('honest_false_alarm'))}, "
                     f"detection {_fmt(tt.get('parked_detection'))}; slowest block {_fmt(1e3 * st['honest_median_slowest_block_s'], '.1f')} "
                     f"ms honest against {_fmt(1e3 * st['parked_median_slowest_block_s'], '.1f')} ms parked (medians)")
    res = _read(out / trial / "results.json")
    pre = _read(out / trial / "prereg.json") or {}
    stop = None if res else _interrupted(out / trial)
    if stop:
        b = stop.get("blocks") or {}
        L += ["", f"## {trial[3:].capitalize()} trial (T1)", "",
              f"- stopped before its data were complete ({stop.get('reason')}): {b.get('ref', 0)} reference and "
              f"{b.get('aud', 0)} audit blocks finished. They are kept in `{trial}/raw_partial.npz`, with the schedule "
              "revealed, and not analysed: stopping early is not part of the pre-registered design."]
    if res:
        fp = (res.get("false_positive") or {}).get("combined") or {}
        sl = res.get("slack") or {}
        smoke = trial == trial_dir("smoke")
        L += ["", f"## {trial[3:].capitalize()} trial (T1)", "",
              f"- status: {res.get('status')}",
              f"- false positives {fp.get('k')}/{fp.get('n')} (95% upper {_fmt(fp.get('cp95_upper'))})",
              f"- closure gap {_fmt(res.get('closure_gap_fraction'))} of capacity energy; slack-inflated gap "
              f"{_fmt(sl.get('slack_inflated_gap_fraction'))}",
              "- the smoke profile checks the pipeline; the registered numbers come from the Tier 1 run (`hw-full`)"
              if smoke else
              f"- the {trial[3:]} profile reads the registered decision rules at shakedown scale (below); the registered "
              "numbers come from the Tier 1 run (`hw-full`)"]
        wl = (pre.get("cfg") or {}).get("workload") or {}
        lk = res.get("link") or {}
        if lk:
            L.append(f"- analysis: link (a calibrated curve for each channel, one conformal threshold) over "
                     f"{lk.get('reference_blocks')} reference blocks; block residual SD {_fmt(lk['block_residual_sd']['energy'], '.1f')} J "
                     f"and {_fmt(lk['block_residual_sd']['busy'], '.3f')} s; partial-load slack "
                     f"{_fmt(lk.get('partial_load_slack'), '.3f')}")
        sco = res.get("scores") or {}
        if sco.get("reference") and (res.get("blocks") or {}).get("kind"):
            ref_top = sorted(sco["reference"]["combined"], reverse=True)[:3]
            kinds, hf = res["blocks"]["kind"], res["blocks"].get("hidden_fraction") or []
            null = [s_ for s_, k in zip(sco["audit"]["combined"], kinds) if k == "none"]
            big = [s_ for s_, k, f in zip(sco["audit"]["combined"], kinds, hf) if k not in ("none", "slack") and f >= 0.05 * (1 - 1e-6)]
            L.append(f"- scores (reported only; in spreads of the reference blocks): threshold {_fmt(sco.get('threshold'), '.2f')}; "
                     f"highest reference scores {', '.join(_fmt(x, '.2f') for x in ref_top)}"
                     + (f"; highest null audit score {_fmt(max(null), '.2f')}" if null else "")
                     + (f"; lowest score of a hidden block at 5% or more {_fmt(min(big), '.2f')}" if big else ""))
        solo = wl.get("hidden_solo") or {}
        if solo.get("duty"):
            L.append("- hidden load alone, before the trial (its labels are read off this): "
                     + ", ".join(f"duty {d:.2f}: {w:.1f} W" for d, w in zip(solo["duty"], solo["watts_per_gpu"]))
                     + ("" if solo.get("used") else " (not used: no power above idle)"))
        camp = (pre.get("cfg") or {}).get("campaign")
        if camp:
            L.append(f"- trial {camp['index']} of {camp['size']} in campaign `{camp['id']}`: read them together with "
                     "`closure pool`")
        if wl:
            L.append(f"- SM clocks: {'locked at ' + str(wl['locked_sm_mhz']) + ' MHz' if wl.get('locked_sm_mhz') else 'not locked'}"
                     + (f" ({wl['clock_lock_note']})" if wl.get("clock_lock_note") else ""))
        try:
            from .drift import report, summary_lines
            L += ["", "## Calibration drift (assumption A2; a diagnostic, not a criterion)", ""]
            L += summary_lines(report(out / trial))
        except (OSError, KeyError, ValueError) as e:
            L.append(f"- drift report unavailable ({type(e).__name__}: {e})")
        try:
            from .criteria import evaluate, summary_lines as rule_lines
            L += ["", "## Pre-registered T1 decision rules, read at this run's scale", ""]
            L += rule_lines(evaluate(res, float((pre.get("cfg") or {}).get("alpha", 0.01))))
        except (KeyError, TypeError, ValueError) as e:
            L.append(f"- decision rules unavailable ({type(e).__name__}: {e})")
        comp = _read(out / trial / f"results_comparison_{COMPARISON}.json")
        if comp:
            try:
                L += ["", f"## Declared comparison: the `{COMPARISON}` analysis (amendment v0.7 (c); decides nothing)", "",
                      "- the registered analysis with one more verified feature: the seconds of each window for which "
                      "the verifier asked for the GPU flat out. Declared before the run; read beside the rules above."]
                L += [ln for ln in rule_lines(evaluate(comp, float((pre.get("cfg") or {}).get("alpha", 0.01))))
                      if not ln.startswith("- scope")]
            except (KeyError, TypeError, ValueError) as e:
                L.append(f"- comparison unavailable ({type(e).__name__}: {e})")
        if pr:
            try:                                    # amendment v0.8: declared before the data; it decides nothing
                from .slack_left import reading, summary_lines as left_lines
                rep = reading(pr, res.get("closure_gap_fraction"), sl.get("mean_predicted_fraction_of_capacity"))
                L += ["", "## Efficiency slack left under each rule a regime could adopt (amendment v0.8; decides "
                      "nothing)", ""]
                L += ["- " + ln.strip() for ln in left_lines(rep)[1:]]
            except (KeyError, TypeError, ValueError) as e:
                L.append(f"- not available ({type(e).__name__}: {e})")
        try:
            from .physics import report as physics_report, summary_lines as physics_lines
            L += ["", "## What the GPU did, by requested load level (a diagnostic, not a criterion)", ""]
            L += physics_lines(physics_report(out / trial))
        except (OSError, KeyError, ValueError) as e:
            L.append(f"- not available ({type(e).__name__}: {e})")
    ver = _json_in(_step_output(out, results, "verify"))
    if ver:
        L += ["", "## Verification", "", "- " + ", ".join(f"{k}: {v}" for k, v in ver.items())]
    L += ["", "## What to send back", "",
          f"- `{BUNDLE}`: everything in this folder except `{PRIVATE_KEY}`.",
          f"- Keep `{trial}/{PRIVATE_KEY}` private or delete it: anyone holding it can forge this run's signature. "
          f"The public key is in `{trial}/signature.json`.",
          "- If an independent power meter logged during the trial, export it as `timestamp_s,power_w` and run "
          f"`closure dcbus-analyze --run {out / trial} --csv bus.csv`, then send `results_dcbus.json` as well."]
    return "\n".join(L) + "\n"


def unpack(tgz, dest, sha256: str = None) -> Path:
    """Extract a bundle someone sent back into dest (new or empty) and return the run folder inside it. A bundle is
    data from another machine: it is refused if its hash is not the one given, or if any member is not a plain file
    or folder under the bundle's one top folder (no links, devices, absolute paths or '..'); nothing in it is run."""
    import shutil
    tgz, dest = Path(tgz), Path(dest)
    if sha256 and hashlib.sha256(tgz.read_bytes()).hexdigest() != str(sha256).lower():
        raise ValueError(f"{tgz} is not the bundle with sha256 {sha256}")
    dest.mkdir(parents=True, exist_ok=True)
    if any(dest.iterdir()):
        raise ValueError(f"{dest} is not empty")
    with tarfile.open(tgz) as tf:
        members = tf.getmembers()
        tops = {Path(m.name).parts[0] for m in members if Path(m.name).parts}
        for m in members:
            parts = Path(m.name).parts
            if (len(tops) != 1 or not parts or not (m.isfile() or m.isdir()) or Path(m.name).is_absolute()
                    or ".." in parts or "\\" in m.name):
                raise ValueError(f"{tgz}: refusing member '{m.name}': a bundle holds plain files under one folder")
        for m in members:
            target = dest.joinpath(*Path(m.name).parts)
            if m.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with tf.extractfile(m) as src, open(target, "wb") as fh:
                shutil.copyfileobj(src, fh)
    return dest / tops.pop()


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
