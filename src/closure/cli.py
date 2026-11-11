from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, fields
from pathlib import Path

import numpy as np

from . import __version__
from .evidence import Chain, Signer, canonical, clean, verify_sig
from .sim import SimConfig, SimSource
from .trial import TrialConfig, analyze_any, calibrate, run_trial
from .energy import EnergyFloor

CLASSES = ("constant", "idle_gap", "duty", "dilute")
# Every hardware profile since amendment v0.6: reference blocks interleaved with the audit, a balanced schedule, the
# link analysis (link.py) and warm-up blocks. One regime, because studentised scores do the regimes' job.
V06 = dict(n_regimes=1, alpha=0.01, classes=CLASSES, schedule="balanced", calibration="interleaved", analysis="link")
PROFILES = {
    # the simulator's own study (docs/SIM_STUDY.md): the straight-line analysis on a simulator that is a straight line
    "sim": dict(),
    "quick": dict(L=120, n_ref_blocks=240, n_audit_blocks=240, alpha=0.01),
    # Tier 0's pipeline check, one hour: 100 reference blocks (a conformal threshold at alpha = 0.01 needs 99), 40
    # null and 5 for each class at 5% and 20%. Until 0.8.0: 60 + 60 blocks of 30 s, calibrated before the audit.
    "smoke": dict(L=20, n_ref_blocks=100, n_audit_blocks=80, intensities=(0.05, 0.2), n_per_cell=5, warmup_blocks=3,
                  **V06),
    # CPU rehearsal against a fake NVML (tests/fakegpu): exercises the hardware code path in about a minute; refused on a GPU
    "rehearsal": dict(dt=0.5, L=2, n_ref_blocks=40, n_audit_blocks=12, intensities=(0.2,), n_per_cell=3,
                      warmup_blocks=2, **{**V06, "classes": ("constant", "idle_gap")}),
    # Tier 0 where a session cannot be trusted for 12 hours (free Colab): under 4 hours, and still 204 null blocks, so
    # H1.2 can be decided; 150 reference blocks; 6 blocks of 30 s for every class x intensity (18 per class at 5% or
    # more, so H1.3 primary is decided per class). Blocks half the long profile's, so it resolves about 1.4 times less.
    "medium": dict(L=30, n_ref_blocks=150, n_audit_blocks=300, intensities=(0.02, 0.05, 0.10, 0.20), n_per_cell=6,
                   warmup_blocks=5, **V06),
    # Tier 1 (registered). Since v0.6 interleaved, balanced and analysed with the link model like the shakedowns.
    "hw-short": dict(L=120, n_ref_blocks=180, n_audit_blocks=180, intensities=(0.01, 0.02, 0.05, 0.10, 0.20),
                     n_per_cell=4, warmup_blocks=5, **V06),
    "hw-full": dict(L=120, n_ref_blocks=360, n_audit_blocks=720, n_per_cell=15, warmup_blocks=5, **V06),
    # Tier 0 where a session ends at 12 hours (Kaggle, Colab): about 9 hours, the registered analysis and decision
    # rules at the largest scale that fits (amendments v0.5 and v0.6). 204 null blocks, so H1.2 can be decided; 12
    # blocks for every class x intensity; 144 reference blocks; 5 warm-up blocks.
    "long": dict(L=60, n_ref_blocks=144, n_audit_blocks=396, intensities=(0.02, 0.05, 0.10, 0.20), n_per_cell=12,
                 warmup_blocks=5, **V06),
}


def _cfg(profile: str, seed: int, status: str) -> TrialConfig:
    return TrialConfig(status=status, seed=seed, **PROFILES[profile])


def _signer(out: Path, announce: bool = True) -> Signer:
    kp = out / "signing_key.bin"
    if kp.exists():
        return Signer.load(kp)
    s = Signer()
    out.mkdir(parents=True, exist_ok=True)
    s.save(kp)
    if announce:                                   # no path in the message: nothing local to paste by accident
        print("note: signing_key.bin in the run directory is the PRIVATE signing key: never publish it "
              "(.gitignore excludes it; a hand-made zip would not)", file=sys.stderr)
    return s


def _apply_probe(cfg, path, out: Path, hardware: bool, rehearsal: bool = False) -> None:
    """Bind a sealed probe.json (closure hw-probe) into the trial config: energy floor, slack and the file's hash."""
    from .hw import probe as P
    pr = json.loads(Path(path).read_text())
    if not P.verify_seal(pr):
        raise SystemExit(f"refusing: {path} fails its own sha256 seal (do not edit probe.json; re-run closure hw-probe)")
    if hardware and str(pr.get("status", "")).startswith("MOCK"):
        raise SystemExit(f"refusing: {path} comes from `hw-probe --mock`; run `closure hw-probe --confirm-hardware` first")
    if hardware and not rehearsal and str(pr.get("status", "")).startswith("REHEARSAL"):
        raise SystemExit(f"refusing: {path} comes from a CPU rehearsal; run `closure hw-probe --confirm-hardware` on the GPU")
    src = f"measured by hw-probe ({pr['status']}), sha256 {pr['sha256'][:16]}"
    if pr.get("e_floor_j_per_flop"):
        cfg.e_floor_j_per_flop, cfg.e_floor_source = float(pr["e_floor_j_per_flop"]), src
    if pr.get("s_max") is not None:
        cfg.slack_s_max, cfg.slack_source = float(pr["s_max"]), src
    cfg.probe_sha256 = pr["sha256"]
    out.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, out / "probe.json")


def _print_headline(res: dict):
    fp = res["false_positive"]["combined"]
    print(f"status={res['status']}  FPR={fp['k']}/{fp['n']} (95% upper {fp['cp95_upper']:.4f})  "
          f"closure_gap={res['closure_gap_fraction']}  coverage={res['bound']['coverage_nonslack']}")
    s = res.get("slack") or {}
    if s.get("slack_inflated_gap_fraction") is not None:
        print(f"slack_inflated_gap={s['slack_inflated_gap_fraction']:.4f}  (s_max={s['s_max']:.4f}; {s['source']})")


def cmd_sim_trial(a) -> int:
    out = Path(a.out)
    cfg = _cfg(a.profile, a.seed, "SIMULATED")
    if getattr(a, "probe", None):
        _apply_probe(cfg, a.probe, out, hardware=False)
    res = run_trial(SimSource(SimConfig(), seed=a.seed), cfg, out, _signer(out))
    _print_headline(res)
    print(f"wrote {out}/results.md results.json chain.jsonl signature.json prereg.json raw.npz")
    return 0


def verify_checks(out: Path) -> dict:
    """A run directory's evidence, checked: hash chain, signature, schedule commitment, prereg and results hashes."""
    from .evidence import sha256_hex, verify_commit
    out = Path(out)
    ok, n, head = Chain.verify(out / "chain.jsonl")
    recs = [json.loads(l)["record"] for l in open(out / "chain.jsonl", encoding="utf-8")]
    by = {r.get("phase"): r for r in recs}
    sig = json.loads((out / "signature.json").read_text()) if (out / "signature.json").exists() else None
    sig_ok = bool(sig and sig["chain_head"] == head and verify_sig(sig["public_key"], sig["signature"], head.encode()))
    pre = json.loads((out / "prereg.json").read_text())
    rev = json.loads((out / "schedule_reveal.json").read_text())
    res = json.loads((out / "results.json").read_text())
    checks = {"chain_ok": ok, "entries": n, "signature_ok": sig_ok,
              "schedule_commitment_ok": verify_commit(rev["schedule"], pre["schedule_commitment"], rev["nonce"]),
              **({"order_commitment_ok": bool("order" in rev and "order_nonce" in rev and verify_commit(
                  rev["order"], pre["order_commitment"], rev["order_nonce"]))} if "order_commitment" in pre else {}),
              "prereg_hash_ok": sha256_hex(canonical(pre)) == by.get("prereg", {}).get("prereg_sha256"),
              "results_hash_ok": sha256_hex(canonical(res)) == by.get("results", {}).get("results_sha256")}
    if pre["cfg"].get("probe_sha256"):
        from .hw.probe import verify_seal
        pf = out / "probe.json"
        pr = json.loads(pf.read_text()) if pf.exists() else None
        checks["probe_hash_ok"] = bool(pr and verify_seal(pr) and pr.get("sha256") == pre["cfg"]["probe_sha256"])
    return checks


def _verified(checks: dict) -> bool:
    return all(v for k, v in checks.items() if k != "entries")


def cmd_verify(a) -> int:
    """Re-verify a run directory: hash chain, signature, schedule commitment, prereg and results hashes."""
    checks = verify_checks(Path(a.run))
    print(json.dumps(checks))
    return 0 if _verified(checks) else 1


def cmd_selftest(a) -> int:
    with tempfile.TemporaryDirectory() as d:
        out = Path(d)
        cfg = _cfg("quick", 5, "SIMULATED")
        res = run_trial(SimSource(SimConfig(), seed=5), cfg, out, _signer(out, announce=False))     # throwaway key
        checks = {
            "chain+signature+commitment verify": cmd_verify(argparse.Namespace(run=str(out))) == 0,
            "FPR 95% upper bound < 10%": res["false_positive"]["combined"]["cp95_upper"] < 0.10,
            "constant 20% hidden load detected >= 90%":
                (res["detection_combined"]["constant"]["0.2"]["rate"] or 0) >= 0.9,
            "hidden-energy bound covers >= 90% (non-slack)": (res["bound"]["coverage_nonslack"] or 0) >= 0.9,
        }
    for k, v in checks.items():
        print(("PASS  " if v else "FAIL  ") + k)
    return 0 if all(checks.values()) else 1


def preflight_checks(mock: bool = False, gpu: int = 0) -> list:
    from .hw import gpu as G
    R = []

    def add(name, status, detail=""):
        R.append({"check": name, "status": status, "detail": detail})

    add("python", "PASS" if sys.version_info >= (3, 9) else "FAIL", platform.python_version())
    for mod in ("numpy", "cryptography"):
        try:
            __import__(mod)
            add(f"import {mod}", "PASS")
        except Exception as e:
            add(f"import {mod}", "FAIL", str(e))
    if mock:
        for n in ("pynvml/NVML init", "GPU count>0", "energy counter readable", "torch.cuda available",
                  "NTP synchronised", "capture interface up"):
            add(n, "PASS", "mock")
        return R
    N, target = None, None
    try:
        import pynvml as N
        N.nvmlInit()
        n = N.nvmlDeviceGetCount()
        add("pynvml/NVML init", "PASS", f"driver {G._text(N.nvmlSystemGetDriverVersion())}")
        add("GPU count>0", "PASS" if n else "FAIL", str(n))
    except Exception as e:
        add("pynvml/NVML init", "FAIL", f"{type(e).__name__}: {e}")
        N = None
    try:
        import torch
        if torch.cuda.is_available():
            add("torch.cuda available", "PASS", torch.__version__)
        elif G.rehearsal_requested():
            add("torch.cuda available", "WARN", f"{torch.__version__}: REHEARSAL on CPU, nothing measured means anything")
        else:
            add("torch.cuda available", "FAIL", f"{torch.__version__}: install a CUDA build of torch on the GPU node")
    except Exception as e:
        add("torch.cuda available", "SKIP", f"torch not importable: {e}")
    if N is not None:
        try:                                         # the GPU every later step touches, matched across CUDA and NVML
            target = G.resolve(gpu, N=N)
            add(f"GPU identity (--gpu {gpu})", "WARN" if target.rehearsal else "PASS", target.describe())
        except Exception as e:
            add(f"GPU identity (--gpu {gpu})", "FAIL", f"{type(e).__name__}: {e}")
        if target is not None:
            try:
                e0 = N.nvmlDeviceGetTotalEnergyConsumption(N.nvmlDeviceGetHandleByIndex(target.nvml_index))
                add("energy counter readable", "PASS", f"{e0} mJ")
            except Exception as e:
                add("energy counter readable", "FAIL", f"{e} (use power sampling instead)")
    try:
        r = subprocess.run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"], capture_output=True, text=True, timeout=5)
        add("NTP synchronised", "PASS" if r.stdout.strip() == "yes" else "WARN", r.stdout.strip() or r.stderr.strip())
    except Exception as e:
        add("NTP synchronised", "SKIP", str(e))
    _gpu_readiness(add, target)
    add("tcpdump present", "PASS" if shutil.which("tcpdump") else "WARN", shutil.which("tcpdump") or "install for TAP capture")
    iface = os.environ.get("CLOSURE_IFACE")
    if iface:
        p = Path(f"/sys/class/net/{iface}/operstate")
        add(f"capture interface {iface} up", "PASS" if p.exists() and p.read_text().strip() == "up" else "FAIL")
    else:
        add("capture interface", "SKIP", "set CLOSURE_IFACE=<tap-nic> to check")
    return R


def _gpu_readiness(add, target=None) -> None:
    """Checks that do not stop a run but decide whether hw-probe and the trial can do their job on this node (WARN, never
    FAIL): root for clock and power control, MIG, persistence, the clock and power-limit ranges, other processes on the GPU,
    the GPU model, int8 and fp8 GEMM support, and free memory. `target` (hw.gpu.GpuTarget) says which GPU; default 0."""
    euid = getattr(os, "geteuid", lambda: -1)()
    add("running as root", "PASS" if euid == 0 else "WARN",
        "" if euid == 0 else "without root hw-probe cannot lock clocks or set power limits: those variants are dropped")
    gi, ti = (target.nvml_index, target.index) if target is not None else (0, 0)
    try:
        import pynvml as N
        N.nvmlInit()
        h = N.nvmlDeviceGetHandleByIndex(gi)
        checks = (
            ("MIG disabled", lambda: N.nvmlDeviceGetMigMode(h)[0] == 0,
             "MIG is on: the energy counter and clock control cover the whole GPU, not one slice"),
            ("persistence mode on", lambda: bool(N.nvmlDeviceGetPersistenceMode(h)), "run `nvidia-smi -pm 1` as root"),
            (f"no other compute processes on GPU {ti}", lambda: not N.nvmlDeviceGetComputeRunningProcesses(h),
             "another process is using the GPU: ask for an exclusive allocation"))
        for name, ok, hint in checks:
            try:
                good = ok()
                add(name, "PASS" if good else "WARN", "" if good else hint)
            except Exception as e:                    # not supported on this GPU or driver
                add(name, "SKIP", f"{type(e).__name__}: {e}")
        try:
            mem = max(N.nvmlDeviceGetSupportedMemoryClocks(h))
            cl = [int(c) for c in N.nvmlDeviceGetSupportedGraphicsClocks(h, mem)]
            add("supported SM clocks listed", "PASS" if len(cl) >= 3 else "WARN", f"{len(cl)} clocks, {min(cl)}-{max(cl)} MHz")
        except Exception as e:
            add("supported SM clocks listed", "WARN", f"{type(e).__name__}: hw-probe falls back to a fixed clock list")
        try:
            lo, hi = N.nvmlDeviceGetPowerManagementLimitConstraints(h)
            add("power-limit range", "PASS", f"{lo / 1000:.0f}-{hi / 1000:.0f} W")
        except Exception as e:
            add("power-limit range", "WARN", f"{type(e).__name__}: power-cap variants may be dropped")
    except Exception as e:
        add("GPU readiness (NVML)", "SKIP", f"{type(e).__name__}: {e}")
    try:
        import torch
        if torch.cuda.is_available() and not (target is not None and target.rehearsal):
            cap = tuple(torch.cuda.get_device_capability(ti))
            add("GPU model", "PASS", f"{torch.cuda.get_device_name(ti)}, compute capability {cap[0]}.{cap[1]}")
            i8 = hasattr(torch, "_int_mm")
            add("int8 GEMM (torch._int_mm)", "PASS" if i8 else "WARN", "" if i8 else "the int8 floor variant will be dropped")
            f8 = hasattr(torch, "_scaled_mm") and hasattr(torch, "float8_e4m3fn") and cap >= (8, 9)
            add("fp8 GEMM (torch._scaled_mm, compute capability 8.9+)", "PASS" if f8 else "WARN",
                "" if f8 else "the fp8 floor variant will be dropped")
            free, total = torch.cuda.mem_get_info(ti)
            add("free GPU memory >= 8 GB", "PASS" if free >= 8e9 else "WARN", f"{free / 1e9:.1f} of {total / 1e9:.1f} GB free")
    except Exception as e:
        add("GPU readiness (torch)", "SKIP", f"{type(e).__name__}: {e}")


def cmd_preflight(a) -> int:
    R = preflight_checks(mock=a.mock or os.environ.get("CLOSURE_MOCK") == "1", gpu=a.gpu)
    if a.json:
        print(json.dumps(R, indent=2))
    else:
        for r in R:
            print(f"{r['status']:5} {r['check']}  {r['detail']}")
    return 1 if any(r["status"] == "FAIL" for r in R) else 0


REHEARSAL_STATUS = "REHEARSAL-CPU (fake devices; no physical meaning)"


def _lock_clocks(targets, mhz) -> tuple:
    """Lock the SM clocks of these GPUs at mhz (`nvidia-smi -lgc mhz,mhz`) so a trial calibrates and audits at one
    clock (assumption A2; docs/DEVIATIONS.md section 3). (locked MHz or None, note). A refusal is recorded, not fatal."""
    if not mhz:
        return None, None
    from .hw import gpu as G
    for t in targets:
        ok, msg = G.smi(t.uuid, "-lgc", f"{int(mhz)},{int(mhz)}")
        if not ok:
            _unlock_clocks(targets)
            print(f"WARNING: could not lock SM clocks at {int(mhz)} MHz ({msg}); running with clocks unlocked",
                  file=sys.stderr, flush=True)
            return None, f"lock at {int(mhz)} MHz refused: {msg}"
    return int(mhz), None


def _unlock_clocks(targets) -> None:
    from .hw import gpu as G
    for t in targets:
        G.smi(t.uuid, "-rgc")


def _hw_parts(a):
    """(reader, load, clock, n_gpu, to_stop, targets). On hardware every --gpus index (default: every GPU CUDA shows) is
    resolved to its physical GPU by UUID, so NVML reads the energy of the GPUs torch actually loads (hw/gpu.py)."""
    if a.mock:
        from .hw.source import FakeHardware
        fh = FakeHardware(seed=a.seed)
        return fh, fh, dict(time_fn=fh.now, sleep_fn=fh.sleep), 8, None, []
    import pynvml as N
    from .hw import gpu as G
    from .hw.nvml import NvmlReader
    from .hw.workloads import TorchLoad, measure_idle_w
    N.nvmlInit()
    if a.gpus:
        idx = [int(x) for x in a.gpus.split(",")]
    else:
        torch = G._torch()
        idx = list(range(torch.cuda.device_count())) if torch is not None and torch.cuda.is_available() else [0]
    targets = [G.resolve(i, N=N) for i in idx]
    for t in targets:
        print("GPU:", t.describe(), file=sys.stderr, flush=True)
    G.install_stop_handlers()                       # a SIGTERM (e.g. a scheduler time limit) stops the load cleanly
    reader = NvmlReader([t.nvml_index for t in targets])
    rehearsal = any(t.rehearsal for t in targets)
    p_max = float(reader.power_limit_w())          # this GPU's limit (a T4: 70 W), not an H100's 700 W
    locked, lock_note = _lock_clocks(targets, getattr(a, "lock_clock_mhz", None))   # before sizing and idle
    kw = dict(dim=128, mem_elems=1 << 16, device="cpu") if rehearsal else {}
    if getattr(a, "dim", None):                     # given (tier0 passes hw-selftest's size on): used as is
        kw.update(dim=int(a.dim), auto_size=False)
    if getattr(a, "mem_elems", None):
        kw.update(mem_elems=int(a.mem_elems))
    load = TorchLoad([t.index for t in targets], p_max_w=p_max, **kw)
    idle = measure_idle_w(reader, len(targets), seconds=0.5 if rehearsal else 3.0, settle_s=0.2 if rehearsal else 2.0)
    load.p_idle = min(max(idle, 0.0), 0.9 * p_max)
    load.locked_mhz, load.lock_note = locked, lock_note
    u = load.describe()
    print(f"unit of work: {u['dim']}x{u['dim']} {u['dtype']} GEMM + {u['mem_elems']}-element pass, "
          f"{1e3 * u['unit_s']:.1f} ms against a {1e3 * u['slot_s']:.0f} ms slot"
          f"{'' if u['auto_sized'] else ' (size given)'}; power limit {p_max:.0f} W, idle {idle:.1f} W per GPU"
          + (f"; SM clocks locked at {locked} MHz" if locked else ""), file=sys.stderr, flush=True)
    if not u["fits_slot"]:
        print(f"WARNING: a unit takes longer than {1e3 * u['budget_s']:.0f} ms, so low load levels will run more work "
              "than they ask for; hw-selftest checks whether the levels still differ", file=sys.stderr, flush=True)
    return reader, load, {}, len(targets), load, targets


def _pause_hook(path, sha):
    print(f"\nPRE-REGISTRATION WRITTEN: {path}\n  sha256(canonical) = {sha}\n"
          f"  Timestamp it now (e.g. `ots stamp {path}`), then press Enter to start the blind audit.")
    input()


def _stamp_hook(path, sha):
    """Non-interactive alternative to --pause-after-prereg (used by `closure tier0`): stamp prereg.json with OpenTimestamps
    if the `ots` client is installed, and print its hash either way, before any audit data exist."""
    print(f"PRE-REGISTRATION WRITTEN: {path}\n  sha256(canonical) = {sha}", flush=True)
    ots = shutil.which("ots")
    if not ots:
        print("  `ots` not found: prereg.json was not externally timestamped (its hash is in the chain and in this log)",
              flush=True)
        return
    try:
        r = subprocess.run([ots, "stamp", str(path)], capture_output=True, text=True, timeout=120)
        print("  ots stamp: " + ("ok" if r.returncode == 0 else f"failed: {(r.stderr or r.stdout).strip()[:300]}"), flush=True)
    except Exception as e:                            # a stamp failure must not block the run; it is logged instead
        print(f"  ots stamp: failed: {e}", flush=True)


def _campaign(text: str) -> dict:
    """'NAME:i/N' -> {"id": NAME, "index": i, "size": N}: trial i of the N declared together as campaign NAME."""
    name, _, part = str(text).rpartition(":")
    i, _, n = part.partition("/")
    if not name or not i.isdigit() or not n.isdigit() or not 1 <= int(i) <= int(n):
        raise SystemExit(f"--campaign wants NAME:i/N with 1 <= i <= N, not '{text}'")
    return {"id": name, "index": int(i), "size": int(n)}


def cmd_hw_trial(a) -> int:
    if not (a.mock or a.confirm_hardware):
        print("refusing: pass --confirm-hardware (this runs sustained GPU load and hidden-load injections)")
        return 2
    from .hw.source import HwSource
    if a.profile == "rehearsal" and not a.mock and not os.environ.get("CLOSURE_REHEARSAL_CPU") == "1":
        print("refusing: the rehearsal profile is for CPU rehearsals against a fake NVML; use smoke, hw-short or hw-full")
        return 2
    reader, load, clock, n_gpu, to_stop, targets = _hw_parts(a)
    rehearsal = any(t.rehearsal for t in targets)
    if a.profile == "rehearsal" and not a.mock and not rehearsal:
        to_stop.stop()
        print("refusing: the rehearsal profile is for CPU rehearsals; this process sees a real GPU")
        return 2
    try:
        cfg = _cfg(a.profile, a.seed, "HARDWARE-MOCK" if a.mock else REHEARSAL_STATUS if rehearsal
                   else "HARDWARE (NVML energy counter; spoofable)")
        out = Path(a.out)
        if getattr(a, "probe", None):
            _apply_probe(cfg, a.probe, out, hardware=not a.mock, rehearsal=rehearsal)
        cfg.n_gpu = n_gpu
        if hasattr(load, "describe"):              # real load generator: capacity is this GPU's power limit, and the
            cfg.p_max_w = float(load.p_max)         # unit of verified work is recorded with it in the pre-registration
            cfg.workload = {k: v for k, v in load.describe().items() if k != "tried"}
            cfg.workload["idle_w_measured"] = float(load.p_idle)
            cfg.workload["locked_sm_mhz"] = getattr(load, "locked_mhz", None)
            if getattr(load, "lock_note", None):
                cfg.workload["clock_lock_note"] = load.lock_note
            # the hidden load on its own, so that "x% of capacity" is its measured power and not an estimate
            from .hw.workloads import characterise_hidden
            quick = dict(on_s=0.4, idle_s=0.2, settle_s=0.1, duties=(0.1, 0.4, 0.8)) if rehearsal else {}
            solo = characterise_hidden(load, reader, n_gpu, **quick)
            if solo["watts_per_gpu"][-1] > 0:
                load.hidden_table = list(zip(solo["duty"], solo["watts_per_gpu"]))
            cfg.workload["hidden_solo"] = {**solo, "used": bool(load.hidden_table)}
            print("hidden load alone: " + ", ".join(f"duty {d:.2f} -> {w:.1f} W" for d, w in
                                                    zip(solo["duty"], solo["watts_per_gpu"]))
                  + ("" if load.hidden_table else " (no power above idle measured: labels fall back to the estimate)"),
                  file=sys.stderr, flush=True)
        if getattr(a, "campaign", None):
            cfg.campaign = _campaign(a.campaign)
        src = HwSource(reader, load, dt=cfg.dt, n_gpu=n_gpu, p_max_w=cfg.p_max_w, seed=a.seed, **clock)
        hook = _pause_hook if a.pause_after_prereg else (_stamp_hook if getattr(a, "stamp_prereg", False) else None)
        res = run_trial(src, cfg, out, _signer(out), pause_hook=hook)
    finally:
        if to_stop is not None:
            to_stop.stop()
        if getattr(load, "locked_mhz", None):
            _unlock_clocks(targets)
    _print_headline(res)
    return 0


def cmd_hw_selftest(a) -> int:
    """First thing to run on the cluster: is the evidence chain sane before any hidden-load trial? (hw/selftest.py)"""
    from .hw.selftest import LEVELS, report
    from .hw.source import HwSource
    reader, load, clock, n_gpu, to_stop, targets = _hw_parts(a)
    src = HwSource(reader, load, dt=1.0, n_gpu=n_gpu, p_max_w=float(getattr(load, "p_max", 700.0)), seed=a.seed,
                   **clock)
    rows = []
    try:
        for level in LEVELS:
            src.force_level = level
            for _ in range(a.windows):
                b = src.run_block(1, None)
                rows.append((level, b["X"][0], b["E"][0]))
    finally:
        if to_stop is not None:
            to_stop.stop()
        if getattr(load, "locked_mhz", None):
            _unlock_clocks(targets)
    unit = load.describe() if hasattr(load, "describe") else None
    out = report(rows, unit)
    out["gpus"] = [t.describe() for t in targets]
    if unit is not None:                            # tier0 passes this size on to hw-probe and hw-trial
        out["unit"] = unit
        out["power_limit_w"], out["idle_w_measured_at_start"] = float(load.p_max), float(load.p_idle)
        out["locked_sm_mhz"] = getattr(load, "locked_mhz", None)
    if getattr(load, "errors", None):
        out["load_errors"] = list(load.errors)
    if any(t.rehearsal for t in targets):
        out["status"] = REHEARSAL_STATUS
    print(json.dumps(clean(out), indent=2))
    return 0 if out["pass"] else 1


def cmd_state_sim(a) -> int:
    from . import state as S
    v = S.Verifier(n_blocks=a.blocks)
    tier = S.TierModel(bw_slow=a.slow_bw)
    ht = []
    p = S.Prover(tier)
    S.fill(v, p)
    for _ in range(300):
        ht.append(S.run_challenge(v, p, a.k, 1e9)["elapsed_s"])
    thr = S.calibrate_time_threshold(ht, 0.001)
    out = {"time_threshold_s": thr}
    for name, pr in (("honest", S.Prover(tier)), ("drop_5pct", S.DropProver(0.05, tier=tier)),
                     ("slow_tier_20pct", S.SlowTierProver(0.2, tier=tier))):
        S.fill(v, pr)
        r = [S.run_challenge(v, pr, a.k, thr)["passed"] for _ in range(200)]
        out[name] = {"pass_rate": float(np.mean(r))}
    print(json.dumps(out, indent=2))
    return 0


STATE_ALPHA = 0.005          # hw-state's threshold quantile: half the registered 1% false-alarm allowance
STATE_MIX = (4, 2, 1)        # calibration : honest : parked challenges, in one randomly interleaved pass


def cmd_hw_state(a) -> int:
    """Residency test on real device memory: honest GPU-resident prover vs a prover that parks part of the
    stream in host DRAM. Reports whether tier timing separates beyond jitter at this block size.

    Two things can let a parked block through: a challenge that samples no parked block (pure combinatorics, fixed by
    the number of blocks per challenge) and a challenge that touches one but is not slow enough (the physics). The
    challenge size is chosen so the first stays under 0.1%; the old default of 8 blocks could not reach the
    registered 99% (docs/DEVIATIONS.md section 3). For the second, since amendment v0.6:

      - each block of a challenge is timed on its own and the challenge is judged by its slowest block, so one
        swapped-in block stands against one block's time and not against the jitter of all of them (the total-time
        result is still reported);
      - all challenges run back to back in one pass, in random order: for every parked-prover challenge (--trials),
        two honest ones that are judged and four honest ones that set the threshold. The device is then in one
        steady state throughout, and the threshold's honest challenges are exchangeable with the judged honest ones
        by design, so the conformal threshold holds its false-alarm level whatever the timing distribution. Until
        0.8.0 the three kinds ran one after another with the verifier's two-second recomputation between challenges,
        so every challenge started on an idle GPU;
      - the verifier recomputes the digest itself afterwards, on every --verify-every-th challenge: on 64 MB blocks
        that recomputation is most of the cost and says nothing about timing (the prover computes every digest).

    H2.1 asks for 1,000 honest challenges; the default gives 2,000. The threshold is the conformal quantile at
    --threshold-alpha (0.005, half the registered 1% allowance) of the threshold-setting challenges. A run with far
    fewer challenges than the default cannot hold a 1% rule to two decimal places: the mock and rehearsal runs, which
    check the pipeline and not the statistics, pass a much smaller value."""
    import random
    from . import state as S
    bb = a.block_mb << 20
    a.k_given = bool(a.k)
    a.k = a.k if a.k else S.challenge_size(a.blocks, a.park_frac, a.sampling_assurance)
    v = S.Verifier(n_blocks=a.blocks, block_bytes=bb)
    if a.mock:
        tier = S.TierModel(bw_slow=a.mock_slow_bw)
        honest, parked = S.Prover(tier, block_bytes=bb, seed=1), S.SlowTierProver(a.park_frac, tier=tier, block_bytes=bb, seed=2)
    else:
        honest = S.TorchProver(a.device, bb)
        parked = S.TorchProver(a.device, bb, park_frac=a.park_frac, seed=2)
    S.fill(v, honest)
    S.fill(v, parked)
    n = int(a.trials)
    kinds = [kind for kind, x in zip(("calibration", "honest", "parked"), STATE_MIX) for _ in range(x * n)]
    random.SystemRandom().shuffle(kinds)
    for _ in range(max(2, min(20, n // 10))):         # warm-up, not recorded: kernels chosen, clocks and allocator settled
        S.timed_challenge(v, honest, a.k)
        S.timed_challenge(v, parked, a.k)
    recs = {"calibration": [], "honest": [], "parked": []}
    import gc
    gc.collect()
    gc.disable()                                      # no collector pause inside a timed block
    try:
        for kind in kinds:
            recs[kind].append(S.timed_challenge(v, parked if kind == "parked" else honest, a.k))
    finally:
        gc.enable()
    cal, h, p = recs["calibration"], recs["honest"], recs["parked"]
    alpha = float(a.threshold_alpha)
    thr_block = S.calibrate_time_threshold([r["slowest_block_s"] for r in cal], alpha)
    thr_total = S.calibrate_time_threshold([r["elapsed_s"] for r in cal], alpha)
    every = max(1, int(a.verify_every))
    checked = {kind: [S.digest_matches(v, r) for r in rs[::every]] for kind, rs in recs.items()}
    wrong = sum(not ok for oks in checked.values() for ok in oks)

    def slow(r):
        return r["slowest_block_s"] > thr_block

    fa, det = float(np.mean([slow(r) for r in h])), float(np.mean([slow(r) for r in p]))
    parked_set = parked.parked()
    hits = [sum(i in parked_set for i in r["idx"]) for r in p]
    touched = [r for r, m in zip(p, hits) if m > 0]
    single = [r for r, m in zip(p, hits) if m == 1]
    out = {"status": "MOCK" if a.mock else "HARDWARE", "device": a.device, "block_mb": a.block_mb, "k": a.k,
           "k_chosen": "given" if a.k_given else f"for {a.sampling_assurance:.1%} sampling detection",
           "blocks": a.blocks, "trials": n, "park_frac": a.park_frac, "parked_blocks": len(parked_set),
           "challenges": {"calibration": len(cal), "honest": len(h), "parked": len(p),
                          "order": "one pass, interleaved at random, back to back"},
           "sampling_limit": S.sampling_limit(a.blocks, len(parked_set), a.k),
           "statistic": "slowest block of each challenge", "threshold_alpha": alpha,
           "block_time_threshold_s": thr_block,
           "honest_median_slowest_block_s": float(np.median([r["slowest_block_s"] for r in h])),
           "parked_median_slowest_block_s": float(np.median([r["slowest_block_s"] for r in p])),
           "honest_false_alarm": fa, "parked_detection": det,
           "challenges_touching_parked": len(touched),
           "detected_when_touching_parked": (float(np.mean([slow(r) for r in touched])) if touched else None),
           "touching_one_parked_block": {"n": len(single), "detected": int(sum(slow(r) for r in single))},
           "total_time": {"threshold_s": thr_total,
                          "honest_median_s": float(np.median([r["elapsed_s"] for r in h])),
                          "parked_median_s": float(np.median([r["elapsed_s"] for r in p])),
                          "honest_false_alarm": float(np.mean([r["elapsed_s"] > thr_total for r in h])),
                          "parked_detection": float(np.mean([r["elapsed_s"] > thr_total for r in p]))},
           "digests_verified": sum(len(oks) for oks in checked.values()), "digests_wrong": wrong,
           "digest_ok_honest": all(checked["calibration"] + checked["honest"]),
           "pass": fa <= 0.01 and det >= 0.99 and wrong == 0}
    print(json.dumps(clean(out), indent=2))
    return 0 if out["pass"] else 1


def cmd_drift(a) -> int:
    """Calibration against audit in a finished trial folder: a check on assumption A2 (drift.py)."""
    from .drift import report
    print(json.dumps(clean(report(a.run)), indent=2))
    return 0


def cmd_criteria(a) -> int:
    """The pre-registered T1 decision rules read off a finished trial folder (criteria.py)."""
    from .criteria import evaluate, summary_lines
    run = Path(a.run)
    res = json.loads((run / "results.json").read_text())
    alpha = float(json.loads((run / "prereg.json").read_text())["cfg"]["alpha"])
    ev = evaluate(res, alpha)
    print(json.dumps(clean(ev), indent=2) if a.json else "\n".join(summary_lines(ev)))
    return 0


def cmd_physics(a) -> int:
    """What the GPU did in a finished trial, by requested load level, and what each hidden load did to it (physics.py)."""
    from .physics import report, summary_lines
    try:
        rep = report(a.run)
    except (OSError, KeyError, ValueError) as e:
        print(f"refusing: {e}")
        return 2
    print(json.dumps(clean(rep), indent=2) if a.json else "\n".join(summary_lines(rep)))
    return 0


def cmd_reanalyze(a) -> int:
    """Apply an analysis to a finished trial's raw data. With the analysis the trial pre-registered, this reproduces
    results.json. With another it is a post hoc reading: labelled as one, written beside the signed results and never
    over them, and deciding nothing (the analysis was chosen after the data were seen)."""
    from dataclasses import replace
    from .criteria import evaluate, summary_lines
    run = Path(a.run)
    cfg, ref, aud, sched = _load_run(run)
    analysis = a.analysis or cfg.analysis
    post_hoc = analysis != cfg.analysis
    cfg2 = replace(cfg, analysis=analysis)
    if post_hoc:
        cfg2.status = (f"{cfg.status} | POST HOC: the '{analysis}' analysis, applied after the data were seen "
                       f"(pre-registered: '{cfg.analysis}')")
    res = analyze_any(cfg2, calibrate(ref, cfg2), aud, sched, EnergyFloor(cfg.e_floor_j_per_flop, cfg.e_floor_source))
    res["reanalysis"] = {"pre_registered_analysis": cfg.analysis, "analysis": analysis, "post_hoc": post_hoc,
                         "package": __version__}
    out = Path(a.out) if a.out else run / (f"results_posthoc_{analysis}.json" if post_hoc else "results_reanalysis.json")
    out.write_text(json.dumps(clean(res), indent=2, sort_keys=True))
    print(f"{'POST HOC reading' if post_hoc else 'reanalysis'} ({analysis}) written to {out}")
    print("\n".join(summary_lines(evaluate(res, cfg.alpha))))
    return 0


def cmd_pool(a) -> int:
    """Read several trials of one design as one: block counts are pooled, every trial keeps its own calibration,
    schedule, commitments and chain. A campaign declared beforehand (`hw-trial --campaign NAME:i/N`) must be pooled
    whole; anything else is labelled a post hoc pooling."""
    from dataclasses import replace
    from .criteria import evaluate, summary_lines
    from .trial import summarise
    loaded, seen = [], {}
    for r in map(Path, a.runs):
        try:                                    # a pooled reading rests on every trial's evidence: check it first
            checks = verify_checks(r)
        except (OSError, ValueError, KeyError) as e:
            print(f"refusing: {r} is not a complete trial folder ({type(e).__name__}: {e})")
            return 2
        if not _verified(checks):
            print(f"refusing: {r} fails `closure verify` ({', '.join(k for k, v in checks.items() if not v)})")
            return 2
        pre = json.loads((r / "prereg.json").read_text())
        if pre["schedule_commitment"] in seen:  # the same trial twice would count its blocks twice
            print(f"refusing: {r} and {seen[pre['schedule_commitment']]} are the same trial (one schedule commitment)")
            return 2
        seen[pre["schedule_commitment"]] = r
        res = json.loads((r / a.results).read_text())
        if "blocks" not in res:
            print(f"refusing: {r / a.results} has no block table (results from before 0.8.0). `closure reanalyze --run "
                  f"{r}` writes one; pass its file name with --results")
            return 2
        loaded.append((r, _load_cfg(r), res))
    cfgs = [c for _, c, _ in loaded]
    design = {(c.L, c.dt, c.n_ref_blocks, c.n_audit_blocks, c.alpha, tuple(c.classes), tuple(c.intensities),
               c.schedule, c.n_per_cell, c.calibration, c.n_gpu, r.get("analysis", "linear"))
              for (_, c, r) in loaded}
    if len(design) != 1:
        print("refusing: these trials do not share one design (block length, block counts, alpha, classes, intensities, "
              "schedule, calibration, analysis)")
        return 2
    camp = [c.campaign for c in cfgs]
    declared = (all(camp) and len({(x["id"], x["size"]) for x in camp}) == 1
                and len({x["index"] for x in camp}) == len(camp))
    complete = bool(declared and len(camp) == camp[0]["size"])
    if declared and not complete and not a.allow_partial:
        print(f"refusing: campaign '{camp[0]['id']}' declared {camp[0]['size']} trials and {len(camp)} were given. Pool "
              "them all, or pass --allow-partial (the reading is then labelled post hoc)")
        return 2
    keys = [k for k in loaded[0][2]["blocks"] if all(k in r["blocks"] for _, _, r in loaded)]
    table = {k: [x for _, _, r in loaded for x in r["blocks"][k]] for k in keys}
    slacks = [c.slack_s_max for c in cfgs]
    label = (f"POOLED (campaign '{camp[0]['id']}', {len(camp)} of {camp[0]['size']} trials)" if complete else
             f"POOLED POST HOC ({len(loaded)} trials not declared together beforehand, or not all of them)")
    cfg = replace(cfgs[0], status=f"{label}: {loaded[0][2].get('status', cfgs[0].status)}",
                  slack_s_max=None if any(x is None for x in slacks) else max(slacks),
                  slack_source="the largest s_max among the pooled trials' probes")
    floor = min(cfgs, key=lambda c: c.e_floor_j_per_flop)
    res = summarise(cfg, table, EnergyFloor(floor.e_floor_j_per_flop, floor.e_floor_source))
    res.update({"analysis": loaded[0][2].get("analysis", "linear"), "blocks": table,
                "normality_p": {ch: [p for _, _, r in loaded for p in r["normality_p"][ch]] for ch in ("energy", "busy")},
                "calibration_n_eff": {ch: [n for _, _, r in loaded for n in r["calibration_n_eff"][ch]]
                                      for ch in ("energy", "busy")},
                "methods_used": {k: sorted({m for _, _, r in loaded for m in r["methods_used"].get(k, [])})
                                 for k in ("energy", "busy", "combined")},
                "pooling": {"declared_beforehand": bool(declared), "complete": complete, "trials": [
                    {"run": str(r), "campaign": c.campaign, "seed": c.seed,
                     "schedule_commitment": json.loads((r / "prereg.json").read_text())["schedule_commitment"],
                     "results_file": a.results, "false_alarms": x["false_positive"]["combined"],
                     "outcome": evaluate(x, c.alpha)["outcome"]} for r, c, x in loaded]}})
    Path(a.out).write_text(json.dumps(clean(res), indent=2, sort_keys=True))
    print(f"{label}; written to {a.out}")
    print("\n".join(summary_lines(evaluate(res, cfg.alpha))))
    return 0


def cmd_claims(a) -> int:
    from . import claims
    cs = claims.check_all()
    for c in cs:
        if a.all or c.status != "OK":
            print(f"{c.status:12} {c.id:16} expected={c.expected:<12.5g} computed={c.computed:<12.5g} {c.claim}"
                  + (f"  [{c.note}]" if c.note else ""))
    s = claims.summary(cs)
    print(f"\n{s['total']} claims re-derived from the pasted plan: {s['OK']} OK, {s['WORDING']} WORDING "
          f"(true only under a stated reading), {s['INCONSISTENT']} INCONSISTENT")
    return 1 if (a.strict and (s["WORDING"] or s["INCONSISTENT"])) else 0


def cmd_coverage(a) -> int:
    from . import coverage
    errs = coverage.validate()
    s = coverage.summary()
    print(json.dumps(s))
    if a.write:
        Path(a.write).parent.mkdir(parents=True, exist_ok=True)
        Path(a.write).write_text(coverage.to_markdown(), encoding="utf-8")
        print(f"wrote {a.write}")
    for e in errs:
        print("ERROR", e)
    return 1 if errs else 0


def cmd_retrofit(a) -> int:
    from . import retrofit as R
    us_on_cn = R.schedule(a.cn_racks, a.us_taps, a.taps_per_month, a.months)
    cn_on_us = R.schedule(a.us_racks, a.cn_taps, a.taps_per_month, a.months)
    prop = R.proportional(cn_on_us, us_on_cn)
    print("month  US-verifies-China  China-verifies-US  proportional")
    for (m, _, f1), (_, _, f2), (_, fp) in zip(us_on_cn, cn_on_us, prop):
        print(f"{m:>5}  {f1:>17.0%}  {f2:>17.0%}  {fp:>12.0%}")
    return 0


def cmd_assurance(a) -> int:
    from . import assurance as A
    print(f"assurance curve at N_ver={a.n_ver:g}:")
    for c, conf in A.assurance_curve(a.n_ver):
        print(f"  coverage {c:>8.4%}  confidence {conf:.6f}  ({A.nines(conf):.2f} nines)")
    print("hours to catch a sustained rogue deployment at 99% (1% budget):")
    for yr, p in A.GRANULARITY_H100E.items():
        print(f"  {yr}: packets of {p:g} H100e-h: " + ", ".join(
            f"{d:,.0f} H100e -> {A.detection_time_hours(0.01, p, d):.1f} h" for d in (1_000, 10_000, 100_000)))
    return 0


def cmd_repro(a) -> int:
    from . import repro
    if a.mock:
        out = {}
        for k in ("variant", "invariant"):
            r = repro.measure_reproducibility(repro.ToyLM(kernel=k), n_requests=a.n)
            out[k] = {x: r[x] for x in ("bitwise_equal_rate", "max_abs_diff", "p99_abs_diff")}
        print(json.dumps(out, indent=2))
        return 0
    r = repro.torch_repro_check(a.device, n=a.n, deterministic=not a.nondeterministic)
    print(json.dumps(r, indent=2))
    return 0 if r["bitwise_equal_rate"] == 1.0 else 1


def cmd_traffic_check(a) -> int:
    from . import traffic as T
    st = T.PcapStats()
    pk = T.iter_pcap(a.pcap, st)                      # streamed: constant memory
    ver = {}
    for k, v in json.loads(Path(a.verified).read_text()).items():
        proto, a_, b_ = k.split("|")
        ep = tuple(sorted([tuple([a_.rsplit(":", 1)[0], int(a_.rsplit(":", 1)[1])]),
                           tuple([b_.rsplit(":", 1)[0], int(b_.rsplit(":", 1)[1])])]))
        ver[(int(proto), ep)] = int(v)
    r = T.traffic_closure(pk, ver, stats=st, unparsed_tol_bytes=a.unparsed_tol_bytes)
    print(json.dumps(clean(r), indent=2))
    return 0 if r["pass"] else 1


def _floats(s) -> list:
    return [float(x) for x in str(s).split(",") if x.strip()]


def _strs(s) -> list:
    return [x.strip() for x in str(s).split(",") if x.strip()]


def cmd_hw_probe(a) -> int:
    """Measure the efficiency slack (H1.6) and the energy floor (H1.7) before the trial; see hw/probe.py."""
    from .hw import probe as P
    if not (a.mock or a.confirm_hardware):
        print("refusing: pass --confirm-hardware (this locks clocks, changes the power limit and runs sustained GPU load; "
              "it needs root, and clocks and limit are restored afterwards)")
        return 2
    if a.mock:
        rig, status = P.FakeProbeRig(seed=a.seed, window_s=a.window_s), "MOCK"
    else:
        from .hw import gpu as G
        target = G.resolve(a.gpu)                    # the physical GPU by UUID: nvidia-smi and NVML touch only it
        print("GPU:", target.describe(), file=sys.stderr, flush=True)
        G.install_stop_handlers()                    # SIGTERM/SIGINT/SIGHUP: restore clocks and power limit, then exit
        rig = P.TorchRig(target=target, dim=a.dim or 8192, mem_elems=a.mem_elems or (1 << 29), window_s=a.window_s,
                         auto_size=a.dim is None)   # no --dim: halve from 8192 until a unit fits the slot
        status = REHEARSAL_STATUS if target.rehearsal else "HARDWARE-PROBE (NVML energy counter; spoofable)"
    if a.clocks == "auto":                       # clocks this device supports, so no variant is wasted on an invalid clock
        clocks = P.pick_clocks(rig.supported_clocks())
        clock_src = "picked from the device's supported clocks" if clocks else "fixed fallback: the device did not list its clocks"
        clocks = clocks or list(P.FALLBACK_CLOCKS)
    else:
        clocks, clock_src = _floats(a.clocks), "given"
    if a.power_caps == "auto":
        caps, cap_src = P.pick_power_caps(rig.default_pl_w, rig.power_limits()), "0.7 and 0.5, raised to the device minimum"
    else:
        caps, cap_src = _floats(a.power_caps), "given"
    variants = P.default_variants(clocks, caps, _strs(a.precisions), _strs(a.kernels), _strs(a.operands))
    res = P.run_probe(rig, variants, levels=_floats(a.levels), repeats=a.repeats, rel_tol=a.rel_tol, seed=a.seed,
                      log=lambda s: print(s, file=sys.stderr))
    res["settings"].update({"clocks_mhz": [float(c) for c in clocks], "clock_source": clock_src,
                            "power_caps": [float(c) for c in caps], "power_cap_source": cap_src})
    res = P.seal(res, status, rig.info())
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=2, sort_keys=True))
    s, e = res["s_max"], res["e_floor_j_per_flop"]

    def f(x, spec=".4f"):
        return "n/a" if x is None else format(x, spec)
    print(f"status={res['status']}  allowed variants={res['n_allowed_variants']} (H1.6 needs >= {P.MIN_VARIANTS})  "
          f"s_max={f(s)} (stack {f(res['s_stack'])}, operand {f(res['s_operand'])})  e_floor={f(e, '.3g')} J/FLOP  "
          f"band/floor={f(res['band_over_floor'], '.3g')}")
    for n in res["notes"]:
        print("NOTE:", n)
    print(f"wrote {a.out} (sha256 {res['sha256']})")
    return 0 if (res["h1_6_variants_ok"] and e) else 1


def cmd_cadence_check(a) -> int:
    """Defence in depth (hardwired pause 3.3.3): is there a training cadence in this power trace? Exit 1 if flagged."""
    from . import cadence, dcbus
    kw = dict(min_period_s=a.min_period_s, max_period_s=a.max_period_s)
    t, p = dcbus.load_csv(a.csv, scale=a.scale, ts_unit=a.ts_unit)
    out = {"trace": cadence.statistic(t, p, **kw)}
    if a.null:
        cal = cadence.calibrate([dcbus.load_csv(f, scale=a.scale, ts_unit=a.ts_unit) for f in _strs(a.null)], a.alpha, **kw)
        s = out["trace"]["stat"]
        out["calibration"] = cal
        out["flagged"] = bool(s is not None and np.isfinite(cal["threshold"]) and s > cal["threshold"])
    else:
        out["note"] = "no --null traces: the statistic is uncalibrated, so no decision is made"
    print(json.dumps(clean(out), indent=2))
    return 1 if out.get("flagged") else 0


def cmd_tap_commit(a) -> int:
    """Hashing tap: commit to a capture's payload bytes in fixed-size groups (digests plus a Merkle root per direction)."""
    from . import taphash as H
    c = H.commit_pcap(a.pcap, a.group_bytes)
    out = {"group_bytes": a.group_bytes, "bandwidth_reduction": H.bandwidth_reduction(a.group_bytes),
           "flows": {k: {"root": v["root"].hex(), "n_groups": len(v["digests"]), "payload_bytes": v["payload_bytes"],
                         "declared_bytes": v["declared_bytes"], "digests": [d.hex() for d in v["digests"]]}
                     for k, v in c.items()}}
    cut = [k for k, v in c.items() if v["declared_bytes"] > v["payload_bytes"]]
    if cut:
        out["warning"] = f"{len(cut)} flow direction(s) lost payload bytes to the snaplen: capture with `tcpdump -s 0`"
        print("WARNING:", out["warning"])
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, indent=2))
    print(f"wrote {a.out}: {len(c)} flow directions, {sum(len(v['digests']) for v in c.values())} groups, "
          f"output {H.bandwidth_reduction(a.group_bytes):.0f}x smaller than a full copy")
    return 0


def cmd_tap_compare(a) -> int:
    """Compare a tap's commitment with the prover's recomputed one; exit 1 on any mismatched group or missing flow."""
    from . import taphash as H
    tap, prov = json.loads(Path(a.tap).read_text()), json.loads(Path(a.prover).read_text())
    if tap["group_bytes"] != prov["group_bytes"]:
        print(f"refusing: group sizes differ ({tap['group_bytes']} vs {prov['group_bytes']})")
        return 2
    bad = {}
    for k in sorted(set(tap["flows"]) | set(prov["flows"])):
        td = [bytes.fromhex(x) for x in tap["flows"].get(k, {}).get("digests", [])]
        pd = [bytes.fromhex(x) for x in prov["flows"].get(k, {}).get("digests", [])]
        mm = H.mismatched_groups(td, pd)
        if mm or k not in tap["flows"] or k not in prov["flows"]:
            bad[k] = {"n_mismatched": len(mm), "first_mismatched_groups": mm[:20],
                      "only_in": "tap" if k not in prov["flows"] else ("prover" if k not in tap["flows"] else None)}
    out = {"flows": len(set(tap["flows"]) | set(prov["flows"])), "flows_with_mismatch": len(bad), "detail": bad,
           "pass": not bad}
    print(json.dumps(out, indent=2))
    return 0 if out["pass"] else 1


def cmd_redteam(a) -> int:
    """Gateway sampling plus recomputation against substituted models and tampered outputs (toy model)."""
    from . import gateway as G
    r = G.red_team(n_requests=a.n, frac_bad=a.frac_bad, epsilon=a.epsilon, alpha=a.alpha, seed=a.seed)
    print(json.dumps(clean(r), indent=2))
    ok = r["results"]["honest"]["flagged"] == 0 and all(v["log_ok"] and v["sample_ok"] for v in r["results"].values())
    return 0 if ok else 1


def cmd_metrics(a) -> int:
    """The Verification Plan's six evaluation metrics, scored for this repository's mechanisms (judgments, with a basis)."""
    from . import metrics as M
    errs = [e for c in M.CARDS for e in M.validate(c)]
    print(json.dumps(clean(M.as_dicts()), indent=2) if a.json else M.table())
    for e in errs:
        print("ERROR", e)
    return 1 if errs else 0


def cmd_external(a) -> int:
    """The AnonRish repositories vendored under external/: list the manifest, check the trees, run their own tests."""
    from . import external as E
    root = E.find_root(a.root)
    if a.action == "list":
        print(E.table(E.load_manifest(root)))
        return 0
    if a.action == "check":
        errs = E.check(root)
        for e in errs:
            print("ERROR", e)
        print("external: every vendored tree matches external/MANIFEST.json and every cited test passed in the recorded run"
              if not errs else f"external: {len(errs)} problem(s)")
        return 1 if errs else 0
    names = a.repos or E.repos(root)
    unknown = sorted(set(names) - set(E.repos(root)))
    if unknown:
        print("unknown repositories:", ", ".join(unknown), file=sys.stderr)
        return 2
    cited, log_dir = E.cited_tests(), Path(a.log_dir) if Path(a.log_dir).is_absolute() else root / a.log_dir
    results = []
    for n in names:
        if a.install:
            ok, msg = E.install(root / "external" / n, a.python)
            if not ok:
                print(f"{n}: editable install failed: {msg}", file=sys.stderr)
        r = E.run_suite(root / "external" / n, a.timeout, a.python, log_dir, cited.get(n, ()))
        results.append(r)
        bad = [t for t, o in r["cited"].items() if o != "passed"]
        print(f"{n:28s} {r['status']:8s} {r['passed']:4d} passed {r['skipped']:3d} skipped {r['failures'] + r['errors']:3d} failed"
              f"  {r['seconds']:7.1f} s" + (f"  cited tests not passed: {bad}" if bad else "")
              + ("  (the tests wrote into the vendored tree)" if r["tests_wrote_into_tree"] else ""), flush=True)
    if a.json:
        print(json.dumps(results, indent=2))
    if a.record:
        print("recorded in", E.record(results, root))
    return 0 if all(r["status"] == "pass" and all(o == "passed" for o in r["cited"].values()) for r in results) else 1


def cmd_tier0(a) -> int:
    """Run the Tier 0 pilot end to end without keyboard input; see tier0.py and docs/OPERATOR_TIER0.md."""
    from . import tier0
    if not (a.mock or a.confirm_hardware):
        print("refusing: pass --confirm-hardware (about 2 h on one GPU, about 5 h with --trial-profile medium, about "
              "10.5 h with long: clock locking, power-limit changes, sustained load and hidden-load injection; clocks "
              "and limit are restored afterwards) or --mock to rehearse without a GPU")
        return 2
    return tier0.run(Path(a.out), gpu=a.gpu, mock=a.mock, run_tests=not a.skip_tests, profile=a.trial_profile,
                     campaign=a.campaign, seed=a.seed)


def cmd_unpack(a) -> int:
    """Extract a returned tier0 bundle safely (tier0.unpack) and say where its trial is, for verify and reanalyze."""
    from . import tier0
    try:
        root = tier0.unpack(a.bundle, a.out, a.sha256)
    except (ValueError, OSError) as e:
        print(f"refusing: {e}")
        return 2
    print(f"unpacked to {root}")
    for t in sorted(root.glob("T1-*")):
        print(f"trial folder: {t}   (closure verify {t}; closure criteria --run {t}; closure reanalyze --run {t})")
    return 0


def cmd_hw_restore(a) -> int:
    """Unlock the SM clocks and set the power limit back on one GPU: what hw-probe does on exit, for when a run was
    killed with SIGKILL (or the node lost power) before it could. Needs root, like hw-probe.

    --same-user (tier0 passes it): every step that could have changed this GPU ran as this user. If this user may not
    change clocks or power limits, none of those steps did either, so there is nothing to restore and that is not a
    failure. On its own the command cannot know who ran the probe, so a refusal asks for root instead."""
    import pynvml as N
    from .hw import gpu as G
    N.nvmlInit()
    target = G.resolve(a.gpu, N=N)
    print("GPU:", target.describe())
    w = a.power_limit_w if a.power_limit_w is not None else G.default_power_limit_w(N, target.nvml_index)
    print(f"power limit -> {w:.0f} W ({'given' if a.power_limit_w is not None else 'the GPU default'})" if w else
          "power limit: NVML gave no default; pass --power-limit-w to set it")
    rows = G.restore(target, w, N=N)
    failed = [msg for _, ok, msg in rows if not ok]
    refused = bool(failed) and all(G.not_permitted(m) for m in failed)
    if refused and getattr(a, "same_user", False):
        print(f"nothing to restore: this user may not lock clocks or set power limits ({failed[0]}), so no step of "
              "this run changed them")
        return 0
    for cmd, ok, msg in rows:
        print(("ok    " if ok else "FAIL  ") + cmd + ("" if ok else f"  ({msg})"))
    if refused:
        print(f'not permitted: run it as root, e.g. sudo -E env PATH="$PATH" closure hw-restore --gpu {a.gpu}')
    return 0 if rows and all(ok for _, ok, _ in rows) else 1


def cmd_dcbus_decimate(a) -> int:
    from . import dcbus
    r = dcbus.decimate_csv(a.src, a.dst, a.window_ms / 1000.0, scale=a.scale, ts_unit=a.ts_unit)
    print(json.dumps(clean(r), indent=2))
    return 0


def _load_cfg(run: Path) -> TrialConfig:
    cfgd = json.loads((run / "prereg.json").read_text())["cfg"]
    for k in ("intensities", "classes"):
        cfgd[k] = tuple(cfgd[k])
    return TrialConfig(**{f.name: cfgd[f.name] for f in fields(TrialConfig) if f.name in cfgd})


def _load_run(run: Path):
    """(cfg, reference windows, audit windows, schedule) of a finished trial folder, as the trial itself had them."""
    z = np.load(run / "raw.npz")
    cfg = _load_cfg(run)
    keys = ("X", "E", "B", "t0", "hid", "lev", "hs")
    ref = {k: z[f"ref_{k}"] for k in keys if f"ref_{k}" in z.files}
    aud = {k: z[f"aud_{k}"] for k in keys if f"aud_{k}" in z.files}
    return cfg, ref, aud, json.loads((run / "schedule_reveal.json").read_text())["schedule"]


def cmd_dcbus(a) -> int:
    from . import dcbus
    run = Path(a.run)
    cfg, ref, aud, sched = _load_run(run)
    z = {"ref_E": ref["E"].copy(), "ref_t0": ref["t0"]}
    t, p = dcbus.load_csv(a.csv, scale=a.scale, ts_unit=a.ts_unit)
    nvml_mean_w = float(np.sum(z["ref_E"]) / (len(z["ref_E"]) * cfg.dt))
    meter = dcbus.check_absolute_power(t, p, ref_mean_w=nvml_mean_w)
    for w in meter["warnings"]:
        print("METER CHECK:", w)
    if not meter["ok"] and not a.force_meter:
        print("refusing: this trace is not an absolute-power channel. Closure needs calibrated, DC-coupled power; an AC-coupled "
              "probe cannot give joules. --force-meter labels the report METER UNVERIFIED instead.")
        return 2
    offs = a.offset
    if offs is None:
        offs = dcbus.align_offset(z["ref_t0"], z["ref_E"], t, p, dt=cfg.dt)
    print(f"clock offset applied: {offs:.3f} s")
    ref["E"] = dcbus.window_energy(t, p, ref["t0"] + offs, cfg.dt)
    aud["E"] = dcbus.window_energy(t, p, aud["t0"] + offs, cfg.dt)
    ref["X"][:, 0] = cfg.dt
    aud["X"][:, 0] = cfg.dt
    cal = calibrate(ref, cfg)
    ratio = float(np.sum(ref["E"]) / np.sum(z["ref_E"]))
    if not 0.5 <= ratio <= 2.0:
        meter["warnings"].append(f"bus energy is {ratio:.2f} x the NVML energy over the reference run: check units (--scale), the "
                                 "measurement point and which rails the meter covers")
        print("METER CHECK:", meter["warnings"][-1])
    cfg.status = ("HARDWARE+DCBUS (independent meter)" if meter["ok"]
                  else "HARDWARE+DCBUS (METER UNVERIFIED: not an absolute-power channel)")
    res = analyze_any(cfg, cal, aud, sched, EnergyFloor(cfg.e_floor_j_per_flop, cfg.e_floor_source))
    res["meter_check"] = {**meter, "bus_to_nvml_energy_ratio": ratio}
    (run / "results_dcbus.json").write_text(json.dumps(clean(res), indent=2, sort_keys=True))
    _print_headline(res)
    return 0


def main(argv=None) -> int:
    from .hw.gpu import prefer_pci_order
    prefer_pci_order()                    # number CUDA devices as NVML and nvidia-smi do, before CUDA is initialised
    ap = argparse.ArgumentParser(prog="closure", description=f"plan-a-closure {__version__}")
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("selftest"); s.set_defaults(f=cmd_selftest)
    s = sp.add_parser("verify"); s.add_argument("run"); s.set_defaults(f=cmd_verify)
    s = sp.add_parser("preflight"); s.add_argument("--mock", action="store_true"); s.add_argument("--json", action="store_true")
    s.add_argument("--gpu", type=int, default=0, help="index among the GPUs CUDA shows this process"); s.set_defaults(f=cmd_preflight)
    s = sp.add_parser("sim-trial"); s.add_argument("--out", required=True); s.add_argument("--seed", type=int, default=1)
    s.add_argument("--profile", choices=list(PROFILES), default="sim"); s.add_argument("--probe", default=None)
    s.set_defaults(f=cmd_sim_trial)
    for name, fn in (("hw-trial", cmd_hw_trial), ("hw-selftest", cmd_hw_selftest)):
        s = sp.add_parser(name)
        s.add_argument("--out", default="run"); s.add_argument("--seed", type=int, default=1)
        s.add_argument("--profile", choices=[k for k in PROFILES if k != "sim"], default="hw-short")
        s.add_argument("--gpus", default=None); s.add_argument("--mock", action="store_true")
        s.add_argument("--confirm-hardware", action="store_true"); s.add_argument("--windows", type=int, default=30)
        s.add_argument("--pause-after-prereg", action="store_true")
        s.add_argument("--dim", type=int, default=None,
                       help="GEMM size of one unit of work; default: halve from 8192 until a unit fits the 100 ms slot")
        s.add_argument("--mem-elems", type=int, default=None, help="elements in the memory-bound pass of one unit")
        s.add_argument("--lock-clock-mhz", type=int, default=None,
                       help="lock SM clocks at this MHz for the run and unlock after (tier0 picks it from probe.json)")
        if name == "hw-trial":
            s.add_argument("--probe", default=None, help="sealed probe.json from `closure hw-probe` (energy floor + slack)")
            s.add_argument("--stamp-prereg", action="store_true",
                           help="non-interactive: `ots stamp` prereg.json if available and log its hash, then continue")
            s.add_argument("--campaign", default=None, metavar="NAME:i/N",
                           help="this trial is number i of the N trials declared together as campaign NAME "
                                "(`closure pool` reads them as one)")
        s.set_defaults(f=fn)
    s = sp.add_parser("hw-probe"); s.add_argument("--out", default="probe.json"); s.add_argument("--gpu", type=int, default=0)
    s.add_argument("--dim", type=int, default=None,
                   help="GEMM size of one unit; default: halve from 8192 until a unit fits the 100 ms slot")
    s.add_argument("--mem-elems", type=int, default=None); s.add_argument("--window-s", type=float, default=8.0)
    s.add_argument("--clocks", default="auto", help="'auto' picks six of the device's supported SM clocks, or a list in MHz")
    s.add_argument("--power-caps", default="auto", help="'auto' uses 0.7,0.5 of the default limit, raised to the device minimum")
    s.add_argument("--precisions", default="tf32,fp16,int8,fp8"); s.add_argument("--kernels", default="cublaslt")
    s.add_argument("--operands", default="sparse90,lowent,zeros",
                   help="activation patterns run on the reference stack (operand slack); empty string to skip")
    s.add_argument("--levels", default="0,0.25,0.5,0.9"); s.add_argument("--repeats", type=int, default=3)
    s.add_argument("--rel-tol", type=float, default=5e-3); s.add_argument("--seed", type=int, default=1)
    s.add_argument("--mock", action="store_true"); s.add_argument("--confirm-hardware", action="store_true")
    s.set_defaults(f=cmd_hw_probe)
    s = sp.add_parser("drift", help="did the energy model drift between calibration and audit? (a trial folder)")
    s.add_argument("--run", required=True); s.set_defaults(f=cmd_drift)
    s = sp.add_parser("criteria", help="the pre-registered T1 decision rules (H1.1 to H1.4) read off a trial folder")
    s.add_argument("--run", required=True); s.add_argument("--json", action="store_true"); s.set_defaults(f=cmd_criteria)
    s = sp.add_parser("physics", help="what the GPU did in a finished trial, by load level, and what hidden load did to it")
    s.add_argument("--run", required=True); s.add_argument("--json", action="store_true"); s.set_defaults(f=cmd_physics)
    s = sp.add_parser("reanalyze", help="apply an analysis to a finished trial's raw data; another analysis than the "
                                        "pre-registered one gives a labelled post hoc reading")
    s.add_argument("--run", required=True); s.add_argument("--analysis", choices=("linear", "link"), default=None)
    s.add_argument("--out", default=None); s.set_defaults(f=cmd_reanalyze)
    s = sp.add_parser("pool", help="read several trials of one design as one (a campaign declared with --campaign)")
    s.add_argument("--runs", nargs="+", required=True); s.add_argument("--out", default="pooled.json")
    s.add_argument("--results", default="results.json", help="the results file to pool in each trial folder")
    s.add_argument("--allow-partial", action="store_true"); s.set_defaults(f=cmd_pool)
    s = sp.add_parser("hw-state"); s.add_argument("--device", default="cuda:0"); s.add_argument("--blocks", type=int, default=32)
    s.add_argument("--block-mb", type=int, default=64)
    s.add_argument("--k", type=int, default=None, help="blocks per challenge; default: enough that sampling alone "
                   "touches a parked block with probability --sampling-assurance (17 of 32 at 25%% parked)")
    s.add_argument("--sampling-assurance", type=float, default=0.999)
    s.add_argument("--trials", type=int, default=1000,
                   help="challenges to the parked prover; with them, interleaved at random, twice as many honest ones "
                        "that are judged (H2.1 asks for 1,000) and four times as many that set the threshold")
    s.add_argument("--park-frac", type=float, default=0.25)
    s.add_argument("--threshold-alpha", type=float, default=STATE_ALPHA,
                   help="quantile of the threshold-setting challenges used as the threshold (default 0.005: half the "
                        "registered 1%% false-alarm allowance)")
    s.add_argument("--verify-every", type=int, default=50,
                   help="afterwards the verifier recomputes the digest itself for every n-th challenge of each kind "
                        "(the prover computes all of them)")
    s.add_argument("--mock", action="store_true"); s.add_argument("--mock-slow-bw", type=float, default=2e9)
    s.set_defaults(f=cmd_hw_state)
    s = sp.add_parser("cadence-check", help="defence in depth: is there a training cadence in a power trace?")
    s.add_argument("--csv", required=True, help="timestamp_s,power_w at 2 Hz or faster")
    s.add_argument("--null", default=None, help="comma-separated declared-inference traces that calibrate the threshold")
    s.add_argument("--alpha", type=float, default=0.05); s.add_argument("--min-period-s", type=float, default=1.0)
    s.add_argument("--max-period-s", type=float, default=120.0); s.add_argument("--scale", type=float, default=1.0)
    s.add_argument("--ts-unit", choices=["s", "ms", "us", "ns"], default="s")
    s.set_defaults(f=cmd_cadence_check)
    s = sp.add_parser("tap-commit", help="hashing tap: commit to a capture's payload bytes in fixed-size groups")
    s.add_argument("pcap"); s.add_argument("--group-bytes", type=int, default=65536); s.add_argument("--out", required=True)
    s.set_defaults(f=cmd_tap_commit)
    s = sp.add_parser("tap-compare", help="compare the tap's commitment with the prover's recomputed one")
    s.add_argument("tap"); s.add_argument("prover"); s.set_defaults(f=cmd_tap_compare)
    s = sp.add_parser("redteam", help="gateway sampling and recomputation against substituted models (toy model)")
    s.add_argument("--n", type=int, default=400); s.add_argument("--frac-bad", type=float, default=0.25)
    s.add_argument("--epsilon", type=float, default=0.1); s.add_argument("--alpha", type=float, default=0.01)
    s.add_argument("--seed", type=int, default=0); s.set_defaults(f=cmd_redteam)
    s = sp.add_parser("metrics", help="the Verification Plan's six evaluation metrics, scored per mechanism")
    s.add_argument("--json", action="store_true"); s.set_defaults(f=cmd_metrics)
    s = sp.add_parser("external", help="the AnonRish repositories vendored under external/: list, check, run their tests")
    s.add_argument("action", choices=["list", "check", "test"])
    s.add_argument("repos", nargs="*", help="limit `test` to these repositories (default: all)")
    s.add_argument("--install", action="store_true", help="pip install --no-deps -e each repository before testing it")
    s.add_argument("--record", action="store_true", help="write the results and tree hashes into external/MANIFEST.json")
    s.add_argument("--timeout", type=int, default=1800, help="seconds per repository")
    s.add_argument("--python", default=None, help="interpreter to run the suites with (default: this one)")
    s.add_argument("--log-dir", default="runs/external"); s.add_argument("--root", default=None)
    s.add_argument("--json", action="store_true"); s.set_defaults(f=cmd_external)
    s = sp.add_parser("hw-restore", help="unlock the clocks and restore the power limit of one GPU (after a killed run)")
    s.add_argument("--gpu", type=int, default=0, help="index among the GPUs CUDA shows this process")
    s.add_argument("--power-limit-w", type=float, default=None, help="limit to set back (default: the GPU's default)")
    s.add_argument("--same-user", action="store_true",
                   help="every step that could have changed this GPU ran as this user (tier0 passes this): if this "
                        "user may not change clocks or power limits, there is nothing to restore")
    s.set_defaults(f=cmd_hw_restore)
    s = sp.add_parser("tier0", help="the whole Tier 0 pilot on one GPU (about 2 h), unattended, bundled for sending back")
    s.add_argument("--out", default="runs/tier0"); s.add_argument("--gpu", type=int, default=0)
    s.add_argument("--mock", action="store_true"); s.add_argument("--confirm-hardware", action="store_true")
    s.add_argument("--skip-tests", action="store_true", help="skip the unit tests at the start")
    s.add_argument("--trial-profile", choices=("smoke", "medium", "long"), default="smoke",
                   help="smoke: a 1 h trial that checks the pipeline (the default); medium: under 4 h, the smallest "
                        "that can decide the registered rules H1.1 to H1.4 (a free Colab session); long: about 9 h, "
                        "the same rules with blocks twice as long (a 12-hour Kaggle session)")
    s.add_argument("--campaign", default=None, metavar="NAME:i/N",
                   help="this run's trial is number i of N declared together (two GPUs of one session, say); "
                        "`closure pool` then reads them as one")
    s.add_argument("--seed", type=int, default=None,
                   help="trial seed (load sequence and schedule); default: drawn fresh on hardware, 1 with --mock")
    s.set_defaults(f=cmd_tier0)
    s = sp.add_parser("unpack", help="extract a returned tier0 bundle safely, to verify or re-analyse it")
    s.add_argument("bundle"); s.add_argument("--out", required=True, help="a new or empty folder")
    s.add_argument("--sha256", default=None, help="refuse the bundle unless its SHA-256 is this")
    s.set_defaults(f=cmd_unpack)
    s = sp.add_parser("claims"); s.add_argument("--all", action="store_true"); s.add_argument("--strict", action="store_true"); s.set_defaults(f=cmd_claims)
    s = sp.add_parser("coverage"); s.add_argument("--write", default=None); s.set_defaults(f=cmd_coverage)
    s = sp.add_parser("retrofit"); s.add_argument("--us-racks", type=int, default=200_000); s.add_argument("--cn-racks", type=int, default=100_000)
    s.add_argument("--us-taps", type=int, default=10_000); s.add_argument("--cn-taps", type=int, default=20_000)
    s.add_argument("--taps-per-month", type=int, default=10_000); s.add_argument("--months", type=int, default=6); s.set_defaults(f=cmd_retrofit)
    s = sp.add_parser("assurance"); s.add_argument("--n-ver", type=float, default=10_000.0); s.set_defaults(f=cmd_assurance)
    s = sp.add_parser("repro-check"); s.add_argument("--mock", action="store_true"); s.add_argument("--device", default="cuda:0")
    s.add_argument("--n", type=int, default=100); s.add_argument("--nondeterministic", action="store_true"); s.set_defaults(f=cmd_repro)
    s = sp.add_parser("state-sim"); s.add_argument("--blocks", type=int, default=64); s.add_argument("--k", type=int, default=16)
    s.add_argument("--slow-bw", type=float, default=2e9); s.set_defaults(f=cmd_state_sim)
    s = sp.add_parser("traffic-check"); s.add_argument("pcap"); s.add_argument("verified")
    s.add_argument("--unparsed-tol-bytes", type=int, default=0, help="wire bytes of non-TCP/UDP or unparsed frames to accept")
    s.set_defaults(f=cmd_traffic_check)
    s = sp.add_parser("dcbus-analyze"); s.add_argument("--run", required=True); s.add_argument("--csv", required=True)
    s.add_argument("--offset", type=float, default=None); s.add_argument("--scale", type=float, default=1.0)
    s.add_argument("--ts-unit", choices=["s", "ms", "us", "ns"], default="s"); s.add_argument("--force-meter", action="store_true")
    s.set_defaults(f=cmd_dcbus)
    s = sp.add_parser("dcbus-decimate"); s.add_argument("src"); s.add_argument("dst"); s.add_argument("--window-ms", type=float, default=1.0)
    s.add_argument("--scale", type=float, default=1.0); s.add_argument("--ts-unit", choices=["s", "ms", "us", "ns"], default="s")
    s.set_defaults(f=cmd_dcbus_decimate)
    from .pause.cli import register as _register_pause
    _register_pause(sp)
    from .treaty.cli import add_parser as _register_treaty
    _register_treaty(sp)
    a = ap.parse_args(argv)
    try:
        return a.f(a)
    except ModuleNotFoundError as e:
        if e.name in ("pynvml", "torch"):
            print(f"closure: the '{e.name}' package is not installed. Hardware commands need the hw extra:\n"
                  "    pip install -e \".[hw]\"      # for torch, install the CUDA build your node needs\n"
                  "`closure preflight` lists what is missing; `--mock` runs without hardware.", file=sys.stderr)
            return 2
        raise


if __name__ == "__main__":
    sys.exit(main())
