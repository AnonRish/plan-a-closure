"""A Narrow Path's mock training runs (p. 32): regulators test whether a compute provider can cut off a run that exceeds
its permitted compute, and confirm that the model's weights start from scratch. This drill does both, at small scale,
on a CPU or one GPU.

The job is a declared training run: a stack of bias-free linear layers trained with SGD. Its matrix-multiply FLOP per
step is exactly 2 B d^2 (3 L - 1) for batch B, width d and L layers (forward 2Bd^2 per layer, weight gradients 2Bd^2
per layer, input gradients for every layer but the first), the "6ND" rule made exact; element-wise work adds well under
1%. It logs its cumulative FLOP after every step and, before training, its seed and a hash of its initial weights.

The provider is a separate process that sees only an energy meter. With the device's energy floor e (the fewest
joules a FLOP can cost, measured by `closure hw-probe`), FLOP <= energy / e, so stopping the job when energy / e
reaches the budget can never let it exceed the budget, whatever the job reports, provided e is a true floor. A floor
set too high lets the job run past its budget (the drill shows this too). The record holds the budget, the energy and
the provider's bound at the stop, the FLOP the job did (from its own log, to within the step in flight), how long the
stop took, and whether the logged initial weights are the ones its seed produces. That last check means something
only together with inspector code access (Scher and Thiergart): a job can log a false hash.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def step_flop(dim: int, layers: int, batch: int) -> int:
    return 2 * int(batch) * int(dim) ** 2 * (3 * int(layers) - 1)


def _model(torch, dim, layers, seed):
    torch.manual_seed(int(seed))
    return torch.nn.Sequential(*[torch.nn.Linear(int(dim), int(dim), bias=False) for _ in range(int(layers))])


def weights_sha256(model) -> str:
    """sha256 over the float32 bytes of every weight, in order."""
    h = hashlib.sha256()
    for p in model.parameters():
        h.update(p.detach().float().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def job(out: str, dim: int, layers: int, batch: int, seed: int, device: str, max_steps: int,
        not_from_scratch: bool = False) -> int:
    """The declared training run (`closure treaty mock-job`). not_from_scratch perturbs the weights before training,
    as loading a pretrained checkpoint would, and logs the true initial hash."""
    import torch
    model = _model(torch, dim, layers, seed)
    if not_from_scratch:
        with torch.no_grad():
            for p in model.parameters():
                p.add_(0.01)
    init = weights_sha256(model)
    model = model.to(device)
    opt = torch.optim.SGD(model.parameters(), lr=1e-4)
    g = torch.Generator(device="cpu").manual_seed(int(seed) + 1)
    x = torch.randn(int(batch), int(dim), generator=g).to(device)
    fps = step_flop(dim, layers, batch)
    with open(out, "w", encoding="utf-8") as f:
        f.write(json.dumps({"event": "start", "seed": int(seed), "dim": int(dim), "layers": int(layers),
                            "batch": int(batch), "flop_per_step": fps, "init_sha256": init, "t": time.time()}) + "\n")
        f.flush()
        for s in range(int(max_steps)):
            loss = model(x).pow(2).mean()
            opt.zero_grad(set_to_none=True)
            loss.backward()
            opt.step()
            if str(device).startswith("cuda"):
                torch.cuda.synchronize(device)
            f.write(json.dumps({"event": "step", "step": s + 1, "flop": (s + 1) * fps, "t": time.time()}) + "\n")
            f.flush()
    return 0


class ProcCpuMeter:
    """A modelled meter for CPU rehearsals: watts_per_core x the job's CPU-seconds (from /proc, Linux). It stands in
    for the provider's own power meter; it measures nothing physical."""
    kind = "MODEL: watts per core x CPU-seconds of the job (/proc), a rehearsal"

    def __init__(self, watts_per_core: float = 10.0):
        self.w, self.tick, self.pid, self.last = float(watts_per_core), os.sysconf("SC_CLK_TCK"), None, float("nan")

    def attach(self, pid: int):
        self.pid, self.last = int(pid), float("nan")

    def energy_j(self) -> float:
        """The latest reading; after the job has exited, the last one taken while it ran."""
        try:
            with open(f"/proc/{self.pid}/stat", encoding="ascii") as f:
                parts = f.read().rsplit(")", 1)[1].split()
            self.last = self.w * (int(parts[11]) + int(parts[12])) / self.tick    # utime + stime
        except (OSError, IndexError, ValueError):
            pass
        return self.last


class NvmlMeter:
    """The GPU's NVML energy counter (spoofable by the prover's own driver stack: assumption A6)."""
    kind = "NVML energy counter"

    def __init__(self, nvml_index: int = 0):
        from ..hw.nvml import NvmlReader
        self.r = NvmlReader([int(nvml_index)])

    def attach(self, pid: int):
        pass

    def energy_j(self) -> float:
        return float(self.r.energy_j())


def cpu_energy_floor(watts_per_core: float = 10.0, n: int = 1024, seconds: float = 1.0) -> float:
    """J/FLOP of a large float32 matmul under the CPU meter model: the best this CPU does, so a floor for the drill."""
    import resource

    import torch
    a, b = torch.randn(n, n), torch.randn(n, n)
    a @ b
    r0, t0, k = resource.getrusage(resource.RUSAGE_SELF), time.perf_counter(), 0
    while time.perf_counter() - t0 < seconds:
        a @ b
        k += 1
    r1 = resource.getrusage(resource.RUSAGE_SELF)
    cpu = (r1.ru_utime - r0.ru_utime) + (r1.ru_stime - r0.ru_stime)
    return watts_per_core * cpu / (k * 2.0 * n ** 3)


def run_drill(budget_flop: float, e_floor_j_per_flop: float, meter, out_dir, dim: int = 256, layers: int = 4,
              batch: int = 64, seed: int = 1, device: str = "cpu", max_steps: int = None, poll_s: float = 0.01,
              floor_source: str = "given", not_from_scratch: bool = False, count_from: str = "spawn") -> dict:
    """Start the job, watch the meter, stop the job when energy / floor reaches the budget, and report.

    count_from="spawn" (the default) charges everything from process start, imports included, as a provider metering
    an allocation would; "start" charges from the job's start line, which a small drill needs when start-up energy
    would use up most of its budget (a job could hide work before that line, so only for drills)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    log = out / "job.jsonl"
    fps = step_flop(dim, layers, batch)
    if max_steps is None:
        max_steps = int(3 * budget_flop / fps) + 1                  # enough to overrun the budget if not stopped
    argv = [sys.executable, "-m", "closure.cli", "treaty", "mock-job", "--out", str(log), "--dim", str(dim),
            "--layers", str(layers), "--batch", str(batch), "--seed", str(seed), "--device", device,
            "--max-steps", str(max_steps)] + (["--not-from-scratch"] if not_from_scratch else [])
    if count_from not in ("spawn", "start"):
        raise ValueError("count_from is 'spawn' or 'start'")
    t_start = time.time()
    errf = open(out / "job.stderr", "w", encoding="utf-8")
    p = subprocess.Popen(argv, stdout=subprocess.DEVNULL, stderr=errf)
    meter.attach(p.pid)
    e0 = meter.energy_j()
    e0 = 0.0 if e0 != e0 else e0                                      # NaN: process not readable yet, count from 0
    if count_from == "start":
        while p.poll() is None and not (log.exists() and log.read_text(encoding="utf-8").strip()):
            time.sleep(poll_s)
        e1 = meter.energy_j()
        e0 = e1 if e1 == e1 else e0
    stopped, t_stop, e_stop = False, None, None
    while p.poll() is None:
        e = meter.energy_j() - e0
        if e == e and e / e_floor_j_per_flop >= budget_flop:
            p.kill()
            stopped, t_stop, e_stop = True, time.time(), e
            break
        time.sleep(poll_s)
    p.wait()
    t_exit = time.time()
    if e_stop is None:
        e_last = meter.energy_j()
        e_stop = (e_last - e0) if e_last == e_last else None
    errf.close()
    err = (out / "job.stderr").read_text(encoding="utf-8", errors="replace")[-2000:]
    lines = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x.strip()] if log.exists() else []
    start = next((x for x in lines if x["event"] == "start"), None)
    steps = [x for x in lines if x["event"] == "step"]
    done = steps[-1]["flop"] if steps else 0
    at_most = done + (fps if stopped else 0)                           # the step in flight when killed
    match = None
    if start is not None:
        import torch
        match = weights_sha256(_model(torch, dim, layers, seed)) == start["init_sha256"]
    rec = {"budget_flop": float(budget_flop), "e_floor_j_per_flop": float(e_floor_j_per_flop),
           "floor_source": floor_source, "meter": meter.kind, "device": device, "counted_from": count_from,
           "job": {"dim": dim, "layers": layers, "batch": batch, "seed": seed, "flop_per_step": fps,
                   "max_steps": max_steps},
           "stopped_by_provider": stopped, "job_started_training": start is not None, "energy_at_stop_j": e_stop,
           "provider_bound_flop": (e_stop / e_floor_j_per_flop) if e_stop is not None else None,
           "job_steps_logged": len(steps), "job_flop_logged": done, "job_flop_at_most": at_most,
           "budget_used": done / float(budget_flop), "compliant": bool(at_most <= budget_flop),
           "stop_to_exit_s": (t_exit - t_stop) if t_stop else None, "wall_s": t_exit - t_start,
           "init_weights_match_seed": match, "job_stderr_tail": err if (not steps and err) else ""}
    (out / "drill.json").write_text(json.dumps(rec, indent=2), encoding="utf-8")
    return rec
