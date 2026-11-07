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
from .sim import FEATURES, SimConfig, SimSource
from .trial import TrialConfig, analyze, fit_channels, run_trial
from .energy import EnergyFloor

PROFILES = {
    "sim": dict(),
    "quick": dict(L=120, n_ref_blocks=240, n_audit_blocks=240, alpha=0.01),
    "smoke": dict(L=30, n_ref_blocks=60, n_audit_blocks=60, n_regimes=1, alpha=0.01,
                  classes=("constant", "idle_gap", "duty", "dilute"), intensities=(0.05, 0.2)),
    "hw-short": dict(L=120, n_ref_blocks=180, n_audit_blocks=180, n_regimes=2, alpha=0.01,
                     classes=("constant", "idle_gap", "duty", "dilute"), intensities=(0.01, 0.02, 0.05, 0.10, 0.20)),
    "hw-full": dict(L=120, n_ref_blocks=360, n_audit_blocks=720, n_regimes=3, alpha=0.01,
                    classes=("constant", "idle_gap", "duty", "dilute")),
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


def _apply_probe(cfg, path, out: Path, hardware: bool) -> None:
    """Bind a sealed probe.json (closure hw-probe) into the trial config: energy floor, slack and the file's hash."""
    from .hw import probe as P
    pr = json.loads(Path(path).read_text())
    if not P.verify_seal(pr):
        raise SystemExit(f"refusing: {path} fails its own sha256 seal (do not edit probe.json; re-run closure hw-probe)")
    if hardware and str(pr.get("status", "")).startswith("MOCK"):
        raise SystemExit(f"refusing: {path} comes from `hw-probe --mock`; run `closure hw-probe --confirm-hardware` first")
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


def cmd_verify(a) -> int:
    """Re-verify a run directory: hash chain, signature, schedule commitment, prereg and results hashes."""
    from .evidence import sha256_hex, verify_commit
    out = Path(a.run)
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
              "prereg_hash_ok": sha256_hex(canonical(pre)) == by.get("prereg", {}).get("prereg_sha256"),
              "results_hash_ok": sha256_hex(canonical(res)) == by.get("results", {}).get("results_sha256")}
    if pre["cfg"].get("probe_sha256"):
        from .hw.probe import verify_seal
        pf = out / "probe.json"
        pr = json.loads(pf.read_text()) if pf.exists() else None
        checks["probe_hash_ok"] = bool(pr and verify_seal(pr) and pr.get("sha256") == pre["cfg"]["probe_sha256"])
    print(json.dumps(checks))
    return 0 if all(v for k, v in checks.items() if k != "entries") else 1


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


def preflight_checks(mock: bool = False) -> list:
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
    try:
        import pynvml as N
        N.nvmlInit()
        n = N.nvmlDeviceGetCount()
        add("pynvml/NVML init", "PASS", f"driver {N.nvmlSystemGetDriverVersion()}")
        add("GPU count>0", "PASS" if n else "FAIL", str(n))
        if n:
            h = N.nvmlDeviceGetHandleByIndex(0)
            try:
                e0 = N.nvmlDeviceGetTotalEnergyConsumption(h)
                add("energy counter readable", "PASS", f"{e0} mJ")
            except Exception as e:
                add("energy counter readable", "FAIL", f"{e} (use power sampling instead)")
    except Exception as e:
        add("pynvml/NVML init", "FAIL", f"{type(e).__name__}: {e}")
    try:
        import torch
        add("torch.cuda available", "PASS" if torch.cuda.is_available() else "FAIL", torch.__version__)
    except Exception as e:
        add("torch.cuda available", "SKIP", f"torch not importable: {e}")
    try:
        r = subprocess.run(["timedatectl", "show", "-p", "NTPSynchronized", "--value"], capture_output=True, text=True, timeout=5)
        add("NTP synchronised", "PASS" if r.stdout.strip() == "yes" else "WARN", r.stdout.strip() or r.stderr.strip())
    except Exception as e:
        add("NTP synchronised", "SKIP", str(e))
    _gpu_readiness(add)
    add("tcpdump present", "PASS" if shutil.which("tcpdump") else "WARN", shutil.which("tcpdump") or "install for TAP capture")
    iface = os.environ.get("CLOSURE_IFACE")
    if iface:
        p = Path(f"/sys/class/net/{iface}/operstate")
        add(f"capture interface {iface} up", "PASS" if p.exists() and p.read_text().strip() == "up" else "FAIL")
    else:
        add("capture interface", "SKIP", "set CLOSURE_IFACE=<tap-nic> to check")
    return R


def _gpu_readiness(add) -> None:
    """Checks that do not stop a run but decide whether hw-probe and the trial can do their job on this node (WARN, never
    FAIL): root for clock and power control, MIG, persistence, the clock and power-limit ranges, other processes on the GPU,
    the GPU model, int8 and fp8 GEMM support, and free memory."""
    euid = getattr(os, "geteuid", lambda: -1)()
    add("running as root", "PASS" if euid == 0 else "WARN", "" if euid == 0 else "hw-probe needs root to lock clocks and set power limits")
    try:
        import pynvml as N
        N.nvmlInit()
        h = N.nvmlDeviceGetHandleByIndex(0)
        checks = (
            ("MIG disabled", lambda: N.nvmlDeviceGetMigMode(h)[0] == 0,
             "MIG is on: the energy counter and clock control cover the whole GPU, not one slice"),
            ("persistence mode on", lambda: bool(N.nvmlDeviceGetPersistenceMode(h)), "run `nvidia-smi -pm 1` as root"),
            ("no other compute processes on GPU 0", lambda: not N.nvmlDeviceGetComputeRunningProcesses(h),
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
        if torch.cuda.is_available():
            cap = tuple(torch.cuda.get_device_capability(0))
            add("GPU model", "PASS", f"{torch.cuda.get_device_name(0)}, compute capability {cap[0]}.{cap[1]}")
            i8 = hasattr(torch, "_int_mm")
            add("int8 GEMM (torch._int_mm)", "PASS" if i8 else "WARN", "" if i8 else "the int8 floor variant will be dropped")
            f8 = hasattr(torch, "_scaled_mm") and hasattr(torch, "float8_e4m3fn") and cap >= (8, 9)
            add("fp8 GEMM (torch._scaled_mm, compute capability 8.9+)", "PASS" if f8 else "WARN",
                "" if f8 else "the fp8 floor variant will be dropped")
            free, total = torch.cuda.mem_get_info(0)
            add("free GPU memory >= 8 GB", "PASS" if free >= 8e9 else "WARN", f"{free / 1e9:.1f} of {total / 1e9:.1f} GB free")
    except Exception as e:
        add("GPU readiness (torch)", "SKIP", f"{type(e).__name__}: {e}")


def cmd_preflight(a) -> int:
    R = preflight_checks(mock=a.mock or os.environ.get("CLOSURE_MOCK") == "1")
    if a.json:
        print(json.dumps(R, indent=2))
    else:
        for r in R:
            print(f"{r['status']:5} {r['check']}  {r['detail']}")
    return 1 if any(r["status"] == "FAIL" for r in R) else 0


def _hw_parts(a):
    if a.mock:
        from .hw.source import FakeHardware
        fh = FakeHardware(seed=a.seed)
        return fh, fh, dict(time_fn=fh.now, sleep_fn=fh.sleep), 8, None
    from .hw.nvml import NvmlReader
    from .hw.workloads import TorchLoad
    gpus = [int(x) for x in a.gpus.split(",")] if a.gpus else None
    reader = NvmlReader(gpus)
    load = TorchLoad(reader.idx)
    return reader, load, {}, len(reader.idx), load


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


def cmd_hw_trial(a) -> int:
    if not (a.mock or a.confirm_hardware):
        print("refusing: pass --confirm-hardware (this runs sustained GPU load and hidden-load injections)")
        return 2
    from .hw.source import HwSource
    cfg = _cfg(a.profile, a.seed, "HARDWARE-MOCK" if a.mock else "HARDWARE (NVML energy counter; spoofable)")
    out = Path(a.out)
    if getattr(a, "probe", None):
        _apply_probe(cfg, a.probe, out, hardware=not a.mock)
    reader, load, clock, n_gpu, to_stop = _hw_parts(a)
    cfg.n_gpu = n_gpu
    src = HwSource(reader, load, dt=cfg.dt, n_gpu=n_gpu, seed=a.seed, **clock)
    hook = _pause_hook if a.pause_after_prereg else (_stamp_hook if getattr(a, "stamp_prereg", False) else None)
    try:
        res = run_trial(src, cfg, out, _signer(out), pause_hook=hook)
    finally:
        if to_stop is not None:
            to_stop.stop()
    _print_headline(res)
    return 0


def cmd_hw_selftest(a) -> int:
    """First thing to run on the cluster: is the evidence chain sane before any hidden-load trial?"""
    from .hw.source import HwSource
    from .residual import nnls
    reader, load, clock, n_gpu, to_stop = _hw_parts(a)
    src = HwSource(reader, load, dt=1.0, n_gpu=n_gpu, seed=a.seed, **clock)
    rows = []
    try:
        for level in (0.0, 0.25, 0.5, 0.75, 1.0):
            src.force_level = level
            for _ in range(a.windows):
                b = src.run_block(1, None)
                rows.append((level, b["X"][0], b["E"][0], b["busy"][0]))
    finally:
        if to_stop is not None:
            to_stop.stop()
    X, y = np.array([r[1] for r in rows]), np.array([r[2] for r in rows])
    th = nnls(X, y)
    res = y - X @ th
    r2 = 1 - float(np.sum(res ** 2) / np.sum((y - y.mean()) ** 2))
    idle_w = float(np.mean([r[2] / r[1][0] for r in rows if r[0] == 0.0]))
    out = {"windows": len(rows), "r2": r2, "residual_sd_j": float(res.std()), "idle_power_w": idle_w,
           "theta": dict(zip(FEATURES, th.tolist())), "pass": r2 > 0.9 and idle_w > 0}
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


def cmd_hw_state(a) -> int:
    """Residency test on real device memory: honest GPU-resident prover vs a prover that parks part of the
    stream in host DRAM. Reports whether tier timing separates beyond jitter at this block size."""
    from . import state as S
    bb = a.block_mb << 20
    v = S.Verifier(n_blocks=a.blocks, block_bytes=bb)
    if a.mock:
        tier = S.TierModel(bw_slow=a.mock_slow_bw)
        honest, parked = S.Prover(tier, block_bytes=bb, seed=1), S.SlowTierProver(a.park_frac, tier=tier, block_bytes=bb, seed=2)
    else:
        honest = S.TorchProver(a.device, bb)
        parked = S.TorchProver(a.device, bb, park_frac=a.park_frac, seed=2)
    S.fill(v, honest)
    S.fill(v, parked)
    cal = [S.run_challenge(v, honest, a.k, 1e9)["elapsed_s"] for _ in range(a.trials)]
    thr = S.calibrate_time_threshold(cal, 0.001)
    h = [S.run_challenge(v, honest, a.k, thr) for _ in range(a.trials)]
    p = [S.run_challenge(v, parked, a.k, thr) for _ in range(a.trials)]
    fa = float(np.mean([not r["passed"] for r in h]))
    det = float(np.mean([not r["passed"] for r in p]))
    out = {"status": "MOCK" if a.mock else "HARDWARE", "device": a.device, "block_mb": a.block_mb, "k": a.k,
           "trials": a.trials, "park_frac": a.park_frac, "time_threshold_s": thr,
           "honest_median_s": float(np.median([r["elapsed_s"] for r in h])),
           "parked_median_s": float(np.median([r["elapsed_s"] for r in p])),
           "honest_false_alarm": fa, "parked_detection": det, "digest_ok_honest": all(r["digest_ok"] for r in h),
           "pass": fa <= 0.01 and det >= 0.99}
    print(json.dumps(clean(out), indent=2))
    return 0 if out["pass"] else 1


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
    rig = P.FakeProbeRig(seed=a.seed, window_s=a.window_s) if a.mock else P.TorchRig(a.gpu, a.dim, window_s=a.window_s)
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
    res = P.seal(res, "MOCK" if a.mock else "HARDWARE-PROBE (NVML energy counter; spoofable)", rig.info())
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
        print("refusing: pass --confirm-hardware (about 2 h on one GPU: clock locking, power-limit changes, sustained load and "
              "hidden-load injection; clocks and limit are restored afterwards) or --mock to rehearse without a GPU")
        return 2
    return tier0.run(Path(a.out), gpu=a.gpu, mock=a.mock, run_tests=not a.skip_tests)


def cmd_dcbus_decimate(a) -> int:
    from . import dcbus
    r = dcbus.decimate_csv(a.src, a.dst, a.window_ms / 1000.0, scale=a.scale, ts_unit=a.ts_unit)
    print(json.dumps(clean(r), indent=2))
    return 0


def cmd_dcbus(a) -> int:
    from . import dcbus
    run = Path(a.run)
    z = np.load(run / "raw.npz")
    pre = json.loads((run / "prereg.json").read_text())
    cfgd = pre["cfg"]
    for k in ("intensities", "classes"):
        cfgd[k] = tuple(cfgd[k])
    cfg = TrialConfig(**{f.name: cfgd[f.name] for f in fields(TrialConfig) if f.name in cfgd})
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
    ref = {k: z[f"ref_{k}"] for k in ("X", "E", "B", "t0", "hid")}
    aud = {k: z[f"aud_{k}"] for k in ("X", "E", "B", "t0", "hid")}
    ref["E"] = dcbus.window_energy(t, p, ref["t0"] + offs, cfg.dt)
    aud["E"] = dcbus.window_energy(t, p, aud["t0"] + offs, cfg.dt)
    ref["X"][:, 0] = cfg.dt
    aud["X"][:, 0] = cfg.dt
    calE, calB = fit_channels(ref, cfg)
    sched = json.loads((run / "schedule_reveal.json").read_text())["schedule"]
    ratio = float(np.sum(ref["E"]) / np.sum(z["ref_E"]))
    if not 0.5 <= ratio <= 2.0:
        meter["warnings"].append(f"bus energy is {ratio:.2f} x the NVML energy over the reference run: check units (--scale), the "
                                 "measurement point and which rails the meter covers")
        print("METER CHECK:", meter["warnings"][-1])
    cfg.status = ("HARDWARE+DCBUS (independent meter)" if meter["ok"]
                  else "HARDWARE+DCBUS (METER UNVERIFIED: not an absolute-power channel)")
    res = analyze(cfg, calE, calB, aud, sched, EnergyFloor(cfg.e_floor_j_per_flop, cfg.e_floor_source))
    res["meter_check"] = {**meter, "bus_to_nvml_energy_ratio": ratio}
    (run / "results_dcbus.json").write_text(json.dumps(clean(res), indent=2, sort_keys=True))
    _print_headline(res)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="closure", description=f"plan-a-closure {__version__}")
    sp = ap.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("selftest"); s.set_defaults(f=cmd_selftest)
    s = sp.add_parser("verify"); s.add_argument("run"); s.set_defaults(f=cmd_verify)
    s = sp.add_parser("preflight"); s.add_argument("--mock", action="store_true"); s.add_argument("--json", action="store_true"); s.set_defaults(f=cmd_preflight)
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
        if name == "hw-trial":
            s.add_argument("--probe", default=None, help="sealed probe.json from `closure hw-probe` (energy floor + slack)")
            s.add_argument("--stamp-prereg", action="store_true",
                           help="non-interactive: `ots stamp` prereg.json if available and log its hash, then continue")
        s.set_defaults(f=fn)
    s = sp.add_parser("hw-probe"); s.add_argument("--out", default="probe.json"); s.add_argument("--gpu", type=int, default=0)
    s.add_argument("--dim", type=int, default=8192); s.add_argument("--window-s", type=float, default=8.0)
    s.add_argument("--clocks", default="auto", help="'auto' picks six of the device's supported SM clocks, or a list in MHz")
    s.add_argument("--power-caps", default="auto", help="'auto' uses 0.7,0.5 of the default limit, raised to the device minimum")
    s.add_argument("--precisions", default="tf32,fp16,int8,fp8"); s.add_argument("--kernels", default="cublaslt")
    s.add_argument("--operands", default="sparse90,lowent,zeros",
                   help="activation patterns run on the reference stack (operand slack); empty string to skip")
    s.add_argument("--levels", default="0,0.25,0.5,0.9"); s.add_argument("--repeats", type=int, default=3)
    s.add_argument("--rel-tol", type=float, default=5e-3); s.add_argument("--seed", type=int, default=1)
    s.add_argument("--mock", action="store_true"); s.add_argument("--confirm-hardware", action="store_true")
    s.set_defaults(f=cmd_hw_probe)
    s = sp.add_parser("hw-state"); s.add_argument("--device", default="cuda:0"); s.add_argument("--blocks", type=int, default=32)
    s.add_argument("--block-mb", type=int, default=64); s.add_argument("--k", type=int, default=8)
    s.add_argument("--trials", type=int, default=200); s.add_argument("--park-frac", type=float, default=0.25)
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
    s = sp.add_parser("tier0", help="the whole Tier 0 pilot on one GPU (about 2 h), unattended, bundled for sending back")
    s.add_argument("--out", default="runs/tier0"); s.add_argument("--gpu", type=int, default=0)
    s.add_argument("--mock", action="store_true"); s.add_argument("--confirm-hardware", action="store_true")
    s.add_argument("--skip-tests", action="store_true", help="skip the unit tests at the start")
    s.set_defaults(f=cmd_tier0)
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
