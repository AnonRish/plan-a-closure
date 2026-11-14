"""`closure doctor`: what this kit can and cannot do on the machine it is run on. Ten seconds, changes nothing.

Before anyone gives a GPU two to ten hours, they can see which steps of the pilot will run on it, which will run in a
reduced form, and why. The report reads the machine and promises nothing about results: it says a step can run, not
what it will show. Send `doctor.json` back even if the pilot is never run; it is a record of a GPU model this kit has
met.

What each step needs, and where that comes from:

  the energy channel     NVML's total-energy counter (nvmlDeviceGetTotalEnergyConsumption; Volta and later)
  the time channel       NVML's utilisation counter
  verified work          a CUDA build of PyTorch that can see the GPU
  the probe's variants   fp16 and TF32 anywhere; FP8 needs compute capability 8.9 or higher (Ada, Hopper, Blackwell);
                         clock and power-limit variants need root and a machine that lets root change them
  the trial's clock lock root, and `nvidia-smi -lgc` accepted (bare metal and most VMs; refused in many containers)
  an independent meter   not on the GPU at all: a DC-bus instrument, or the rack's own metering (`closure dcbus-analyze`)

GPUs from other makers are listed from the kernel's own files (/sys/class/drm): which of them report power or energy
there. The pilot's readers are NVML's; on a GPU without NVML the analysis still runs on any power log
(`closure dcbus-analyze` takes a CSV), and the load generator runs wherever PyTorch has a device, but the device-side
readers for those GPUs are not written. The report says so instead of guessing.
"""
from __future__ import annotations

import json
import os
import platform
import shutil
from pathlib import Path

# CUDA compute capability to architecture (developer.nvidia.com/cuda/gpus). Named so a reader knows what was met.
ARCHITECTURES = {(7, 0): "Volta", (7, 5): "Turing", (8, 0): "Ampere", (8, 6): "Ampere", (8, 7): "Ampere (Jetson)",
                 (8, 9): "Ada Lovelace", (9, 0): "Hopper", (10, 0): "Blackwell", (10, 3): "Blackwell Ultra",
                 (11, 0): "Blackwell (Jetson)", (12, 0): "Blackwell (RTX)", (12, 1): "Blackwell (DGX Spark)"}
FP8_FROM = (8, 9)                # torch._scaled_mm, the probe's fp8 variant
ON_RECORD = "Tesla T4"           # the only GPU model with hardware runs published under results/
VENDORS = {"0x10de": "NVIDIA", "0x1002": "AMD", "0x8086": "Intel"}


def _text(x) -> str:
    return x.decode() if isinstance(x, bytes) else str(x)


def _try(f, *a):
    """(value, None) or (None, why)."""
    try:
        return f(*a), None
    except Exception as e:                      # NVML raises its own types; a missing call is an AttributeError
        return None, f"{type(e).__name__}: {e}".strip().rstrip(":")


def system_facts() -> dict:
    from . import __version__
    from .trial import _code_version
    code = _code_version()
    return {"closure": __version__, "git_commit": code.get("git_commit"), "python": platform.python_version(),
            "os": platform.platform(), "machine": platform.machine(),
            "root": bool(hasattr(os, "geteuid") and os.geteuid() == 0),
            # found or not, never where: a path can carry a user name, and this record travels in the bundle
            "nvidia_smi": shutil.which("nvidia-smi") is not None, "ots": shutil.which("ots") is not None}


def torch_facts(torch=None) -> dict:
    """What PyTorch sees. `torch` can be passed in (tests; False stands for "not installed"); otherwise it is imported
    if it is installed."""
    if torch is False:
        return {"installed": False, "why": "not installed", "devices": []}
    if torch is None:
        try:
            import torch
        except Exception as e:
            return {"installed": False, "why": f"{type(e).__name__}: {e}", "devices": []}
    out = {"installed": True, "version": getattr(torch, "__version__", "?"), "cuda": False, "devices": []}
    ok, why = _try(lambda: bool(torch.cuda.is_available()))
    out["cuda"] = bool(ok)
    if why:
        out["why"] = why
    if ok:
        for i in range(int(torch.cuda.device_count())):
            cap, _ = _try(torch.cuda.get_device_capability, i)
            name, _ = _try(torch.cuda.get_device_name, i)
            out["devices"].append({"index": i, "name": name, "capability": list(cap) if cap else None})
    return out


def nvidia_facts(N=None) -> dict:
    """What NVML reports, per GPU. `N` is the pynvml module (the fake one in tests); imported if not given."""
    if N is None:
        try:
            import pynvml as N
        except Exception as e:
            return {"nvml": False, "why": f"pynvml not importable ({type(e).__name__}: {e}); pip install nvidia-ml-py",
                    "gpus": []}
    _, why = _try(N.nvmlInit)
    if why:
        return {"nvml": False, "why": why, "gpus": []}
    driver, _ = _try(N.nvmlSystemGetDriverVersion)
    count, why = _try(N.nvmlDeviceGetCount)
    out = {"nvml": True, "driver": _text(driver) if driver is not None else None, "gpus": []}
    for i in range(int(count or 0)):
        h, why = _try(N.nvmlDeviceGetHandleByIndex, i)
        if why:
            out["gpus"].append({"index": i, "error": why})
            continue
        name, _ = _try(N.nvmlDeviceGetName, h)
        uuid, _ = _try(N.nvmlDeviceGetUUID, h)
        energy, e_why = _try(N.nvmlDeviceGetTotalEnergyConsumption, h)
        util, u_why = _try(N.nvmlDeviceGetUtilizationRates, h)
        limit, _ = _try(N.nvmlDeviceGetPowerManagementLimit, h)
        default, _ = _try(N.nvmlDeviceGetPowerManagementDefaultLimit, h)
        rng, _ = _try(N.nvmlDeviceGetPowerManagementLimitConstraints, h)
        mem, _ = _try(lambda: N.nvmlDeviceGetMemoryInfo(h).total)
        clock, _ = _try(N.nvmlDeviceGetClockInfo, h, getattr(N, "NVML_CLOCK_SM", 1))
        mig, _ = _try(lambda: N.nvmlDeviceGetMigMode(h)[0])
        out["gpus"].append({
            "index": i, "name": _text(name) if name is not None else None,
            "uuid": _text(uuid) if uuid is not None else None,
            "energy_counter": energy is not None, "energy_counter_why_not": e_why,
            "utilisation_counter": util is not None, "utilisation_counter_why_not": u_why,
            "power_limit_w": None if limit is None else limit / 1000.0,
            "default_power_limit_w": None if default is None else default / 1000.0,
            "power_limit_range_w": None if not rng else [rng[0] / 1000.0, rng[1] / 1000.0],
            "memory_gb": None if mem is None else round(mem / 2 ** 30, 1), "sm_clock_mhz": clock,
            "mig_enabled": bool(mig) if mig is not None else None})
    _try(N.nvmlShutdown)
    return out


def sysfs_gpus(root="/sys") -> list:
    """Every graphics device the kernel lists, with the power and energy files its driver exposes (Linux only)."""
    out = []
    base = Path(root) / "class" / "drm"
    if not base.is_dir():
        return out
    for card in sorted(base.glob("card[0-9]*")):
        if "-" in card.name:                    # card0-DP-1 and the like are connectors, not devices
            continue
        dev = card / "device"
        vid, _ = _try(lambda: (dev / "vendor").read_text().strip().lower())
        if vid is None:
            continue
        files = sorted(p.name for hw in (dev / "hwmon").glob("hwmon*") for p in hw.iterdir()
                       if p.name.startswith(("power", "energy")) and p.name.endswith(("_average", "_input")))
        out.append({"card": card.name, "vendor_id": vid, "vendor": VENDORS.get(vid, "other"),
                    "power_or_energy_files": files, "busy_percent_file": (dev / "gpu_busy_percent").exists()})
    return out


def plan_for(gpu: dict, cap, cuda: bool, root: bool, nvidia_smi: bool, torch_installed: bool = True) -> list:
    """Which pilot steps run on one NVIDIA GPU: [{step, runs: "yes" | "reduced" | "no" | "not read", note}].
    Without PyTorch in this environment nothing can be said about CUDA, so the steps that need it read "not read"
    instead of "no": the GPU has not been found wanting, it has not been asked."""
    def row(step, runs, note):
        return {"step": step, "runs": runs, "note": note}
    e, u = gpu.get("energy_counter"), gpu.get("utilisation_counter")
    rows = []
    if not torch_installed:
        if gpu.get("mig_enabled"):
            rows.append(row("everything", "no", "MIG is on: the energy counter covers the whole GPU, not one slice of "
                                                "it. Turn MIG off for the run"))
        need = "PyTorch is not installed in this environment, so what CUDA can do on this GPU was not read"
        rows.append(row("preflight", "not read" if e else "no",
                        need if e else f"no NVML energy counter ({gpu.get('energy_counter_why_not')})"))
        for step in ("hw-selftest", "hw-probe", "hw-state", "hw-trial"):
            rows.append(row(step, "not read" if e or step == "hw-state" else "no", need))
        rows.append(row("independent meter", "no", "not part of any GPU: bring a DC-bus log and run `closure "
                                                   "dcbus-analyze`. Without one every result is labelled NVML-only "
                                                   "and spoofable"))
        return rows
    if gpu.get("mig_enabled"):
        rows.append(row("everything", "no", "MIG is on: the energy counter covers the whole GPU, not one slice of it. "
                                            "Turn MIG off for the run"))
    rows.append(row("preflight", "yes" if e and cuda else "no",
                    "NVML energy counter and CUDA torch both present" if e and cuda else
                    "; ".join(x for x in ("" if e else f"no NVML energy counter ({gpu.get('energy_counter_why_not')})",
                                          "" if cuda else "PyTorch cannot see a CUDA device") if x)))
    why_not = "" if e and cuda else " (not until preflight passes: see its row)"
    rows.append(row("hw-selftest", "yes" if e and cuda else "no", "energy against verified work at four load levels" + why_not))
    fp8 = cap is not None and tuple(cap) >= FP8_FROM
    control = root and nvidia_smi
    notes = ["fp16 and TF32 variants", "FP8 variant" if fp8 else
             "no FP8 variant (compute capability under 8.9)" if cap is not None else "FP8 variant unknown (no capability read)",
             "clock and power-limit variants will be tried (root); a container may still refuse them" if control else
             "no clock or power-limit variants (not root, or no nvidia-smi): the slack measured is then a lower bound"]
    rows.append(row("hw-probe", ("yes" if control else "reduced") if e and cuda else "no", "; ".join(notes) + why_not))
    rows.append(row("hw-state", "yes" if cuda else "no", "device-memory residency challenges; needs no meter"
                    + ("" if cuda else " (needs a CUDA device)")))
    rows.append(row("hw-trial", ("yes" if u else "reduced") if e and cuda else "no",
                    ("both channels; " if u else "energy channel only (no utilisation counter): the time bound and the "
                                                 "time channel are not available; ")
                    + ("the clock lock will be tried" if control else "clocks not locked (not root): the trial runs with "
                                                                    "the GPU's own governor, as on Kaggle") + why_not))
    rows.append(row("independent meter", "no", "not part of any GPU: bring a DC-bus log and run `closure dcbus-analyze`. "
                                               "Without one every result is labelled NVML-only and spoofable"))
    return rows


def report(N=None, torch=None, sysfs_root="/sys", system: dict = None) -> dict:
    sysf = system or system_facts()
    nv, tc = nvidia_facts(N), torch_facts(torch)
    # NVML's order and CUDA's can differ, so a capability is given to a GPU only when every CUDA device has the same one
    distinct = {tuple(d["capability"]) for d in tc.get("devices", []) if d.get("capability")}
    shared = list(next(iter(distinct))) if len(distinct) == 1 else None
    gpus = []
    for g in nv["gpus"]:
        if "error" in g:
            gpus.append(g)
            continue
        cap = shared
        arch = ARCHITECTURES.get(tuple(cap)) if cap else None
        gpus.append({**g, "compute_capability": cap, "architecture": arch,
                     "hardware_runs_on_record_for_this_model": bool(g.get("name") and ON_RECORD in g["name"]),
                     "plan": plan_for(g, cap, tc.get("cuda", False), sysf["root"], bool(sysf["nvidia_smi"]),
                                      torch_installed=bool(tc.get("installed")))})
    others = [c for c in sysfs_gpus(sysfs_root) if c["vendor"] != "NVIDIA"]
    for c in others:
        c["note"] = ("the kernel reports power or energy for this device, so its draw can be logged to a CSV and read "
                     "with `closure dcbus-analyze`; " if c["power_or_energy_files"] else
                     "the kernel reports no power or energy for this device; ") + \
                    "this kit's device-side readers are NVML's and none is written for this maker"
    def trial(g):
        return next((r["runs"] for r in g.get("plan", []) if r["step"] == "hw-trial"), "no")
    can = [g for g in gpus if trial(g) in ("yes", "reduced") and not g.get("mig_enabled")]
    unread = [g for g in gpus if trial(g) == "not read" and not g.get("mig_enabled")]
    if can:
        verdict = (f"the pilot can run on {len(can)} GPU{'s' if len(can) != 1 else ''} here: `bash "
                   f"scripts/run_anywhere.sh --hardware --gpu {can[0]['index']}` installs what is missing, runs it and "
                   f"bundles the result (about 2 h 20 min; with `--profile medium` about 5 h 40 min, with `--profile long` "
                   f"about 11 h). The command underneath is `closure tier0 --confirm-hardware`")
    elif unread:
        verdict = (f"NVML reads {len(unread)} GPU{'s' if len(unread) != 1 else ''} with an energy counter here, and "
                   f"PyTorch is not installed in this environment, so what CUDA can do on "
                   f"{'them' if len(unread) != 1 else 'it'} was not read: `bash scripts/run_anywhere.sh --hardware` "
                   f"installs PyTorch and runs the pilot, and `pip install -e \".[hw]\"` then `closure doctor` "
                   f"completes this report without running anything")
    elif any(g.get("energy_counter") and not g.get("mig_enabled") for g in gpus):
        n = sum(1 for g in gpus if g.get("energy_counter") and not g.get("mig_enabled"))
        verdict = (f"NVML reads {n} GPU{'s' if n != 1 else ''} with an energy counter here, and the PyTorch in this "
                   f"environment cannot use CUDA (a CPU-only build, or one that does not match the driver), so the "
                   f"pilot cannot run yet: install a CUDA build of PyTorch (on Linux, `pip install torch` gets one) "
                   f"and run `closure doctor` again. Meanwhile `closure tier0 --mock` runs the whole pilot on a "
                   f"simulated GPU")
    else:
        verdict = ("no NVIDIA GPU that NVML can read was found: `closure tier0 --mock` runs the whole pilot on a "
                   "simulated GPU, and `closure selftest` and the test suite need no GPU")
        if any(g.get("mig_enabled") for g in gpus):
            verdict = ("the NVIDIA GPUs here have MIG on, and the energy counter covers a whole GPU, not one slice of "
                       "it: turn MIG off for a run. " + verdict[0].upper() + verdict[1:]).replace(
                           "No NVIDIA GPU that NVML can read was found: ", "Meanwhile ")
    return {"what": "what plan-a-closure can do on this machine; read from the machine, nothing was run on the GPU",
            "system": sysf, "torch": {k: v for k, v in tc.items() if k != "devices"}, "nvml": {k: v for k, v in nv.items() if k != "gpus"},
            "nvidia_gpus": gpus, "other_gpus": others, "verdict": verdict}


def to_markdown(rep: dict) -> str:
    s = rep["system"]
    L = ["# closure doctor", "", f"- plan-a-closure {s['closure']}" + (f" (commit {s['git_commit'][:12]})" if s.get("git_commit") else ""),
         f"- {s['os']}; Python {s['python']}; root: {'yes' if s['root'] else 'no'}; nvidia-smi: "
         f"{'found' if s['nvidia_smi'] else 'not found'}",
         f"- PyTorch: " + (f"{rep['torch'].get('version')}, CUDA {'available' if rep['torch'].get('cuda') else 'not available'}"
                           if rep["torch"].get("installed") else "not installed"),
         f"- NVML: " + (f"driver {rep['nvml'].get('driver')}" if rep["nvml"].get("nvml") else f"not available ({rep['nvml'].get('why')})"),
         "", f"**{rep['verdict']}**"]
    for g in rep["nvidia_gpus"]:
        if "error" in g:
            L += ["", f"## GPU {g['index']}: not readable ({g['error']})"]
            continue
        cap = g.get("compute_capability")
        L += ["", f"## GPU {g['index']}: {g.get('name')}", "",
              f"- compute capability {'.'.join(map(str, cap)) if cap else 'not read'}"
              + (f" ({g['architecture']})" if g.get("architecture") else "")
              + f"; memory {g.get('memory_gb')} GB; power limit {g.get('power_limit_w')} W"
              + (f" (range {g['power_limit_range_w'][0]:.0f} to {g['power_limit_range_w'][1]:.0f} W)" if g.get("power_limit_range_w") else ""),
              f"- energy counter: {'yes' if g.get('energy_counter') else 'no'}; utilisation counter: "
              f"{'yes' if g.get('utilisation_counter') else 'no'}",
              "- hardware runs of this kit on this GPU model are published under results/" if g.get("hardware_runs_on_record_for_this_model")
              else "- no hardware run of this kit on this GPU model is on record yet: a run here would be the first",
              "", "| step | runs | note |", "| --- | --- | --- |"]
        L += [f"| {r['step']} | {r['runs']} | {r['note']} |" for r in g["plan"]]
    if rep["other_gpus"]:
        L += ["", "## Other graphics devices the kernel lists", ""]
        L += [f"- {c['card']}: {c['vendor']} ({c['vendor_id']}); power or energy files: "
              f"{', '.join(c['power_or_energy_files']) or 'none'}. {c['note']}" for c in rep["other_gpus"]]
    return "\n".join(L) + "\n"


def main(out_json=None, out_md=None, as_json: bool = False, echo=print) -> int:
    rep = report()
    if out_json:
        Path(out_json).write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")
    md = to_markdown(rep)
    if out_md:
        Path(out_md).write_text(md, encoding="utf-8")
    echo(json.dumps(rep, indent=2) if as_json else md)
    return 0
