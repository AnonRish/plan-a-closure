"""Model-in-the-loop reproduction of the Colab T4 `closure hw-selftest` result.

Runs plan-a-closure's real TorchLoad (worker thread, 100 ms slots, unit counting), real HwSource windowing and the real
`cmd_hw_selftest` fit. Only the GPU is replaced, by a timing and power model:
  * one n x n matmul takes tau * (n / 8192)**3 seconds; tau depends on the dtype (bf16 on Turing has no tensor cores);
  * the GPU draws BUSY watts while a unit runs and IDLE watts otherwise (a 70 W-capped T4 at full load ~ 68 W).
The meter is exact and the physics exactly linear in work, so any shortfall in r2 comes from the harness itself.
"""
import argparse
import contextlib
import io
import json
import sys
import threading
import time
from types import SimpleNamespace

ap = argparse.ArgumentParser()
ap.add_argument("--src", required=True, help="plan-a-closure src/ directory to run")
ap.add_argument("--tau-bf16", type=float, default=0.54, help="seconds per 8192^3 bf16 unit (Turing slow path)")
ap.add_argument("--tau-fp16", type=float, default=0.05, help="seconds per 8192^3 fp16 unit (tensor cores, 70 W cap)")
ap.add_argument("--idle", type=float, default=30.0)
ap.add_argument("--busy", type=float, default=68.0)
ap.add_argument("--windows", type=int, default=30)
ap.add_argument("--tau-jitter", type=float, default=0.0, help="lognormal relative SD of each unit's time (DVFS)")
ap.add_argument("--busy-sd", type=float, default=0.0, help="SD of the power drawn during one unit, W (cap ripple)")
ap.add_argument("--seed", type=int, default=0)
ap.add_argument("--turing", action="store_true", help="make the new code see a compute-capability 7.5 GPU (fp16)")
a = ap.parse_args()
sys.path.insert(0, a.src)

import torch  # noqa: E402

import closure.cli as C  # noqa: E402
import closure.hw.workloads as W  # noqa: E402


class Meter:
    """Exact energy counter for the power model: IDLE always, plus (P - IDLE) while a unit drawing P runs."""

    def __init__(self, idle, busy):
        self.idle, self.busy, self.lock = idle, busy, threading.Lock()
        self.t0, self.since, self.p, self.extra, self.n = time.perf_counter(), None, busy, 0.0, 0

    def begin(self, p=None):
        with self.lock:
            if self.n == 0:
                self.since, self.p = time.perf_counter(), (self.busy if p is None else p)
            self.n += 1

    def end(self):
        with self.lock:
            self.n -= 1
            if self.n == 0:
                self.extra += (self.p - self.idle) * (time.perf_counter() - self.since)
                self.since = None

    def energy_j(self):
        with self.lock:
            now = time.perf_counter()
            cur = (self.p - self.idle) * (now - self.since) if self.since is not None else 0.0
            return self.idle * (now - self.t0) + self.extra + cur

    def util(self):
        return 1.0 if self.n else 0.0

    def power_limit_w(self):
        return 70.0


meter = Meter(a.idle, a.busy)
import random  # noqa: E402
rng = random.Random(a.seed)


def fake_matmul(A, B):
    n = int(A.shape[0])
    tau = a.tau_bf16 if A.dtype == torch.bfloat16 else a.tau_fp16
    jit = rng.lognormvariate(0.0, a.tau_jitter) if a.tau_jitter else 1.0
    meter.begin(rng.gauss(a.busy, a.busy_sd) if a.busy_sd else None)
    time.sleep(tau * jit * (n / 8192.0) ** 3)
    meter.end()
    return A


torch.matmul = fake_matmul
kw = dict(dim=8192, mem_elems=1 << 12, device="cpu")
if a.turing:
    if not hasattr(W, "native_half"):
        sys.exit("--turing needs the patched code (closure.hw.workloads.native_half)")
    W.native_half = lambda torch_, device: torch_.float16
load = W.TorchLoad([0], **kw)
C._hw_parts = lambda args: (meter, load, {}, 1, load, [])
args = SimpleNamespace(windows=a.windows, seed=1, mock=False, gpus="0", out="run", profile="hw-short",
                       confirm_hardware=True, pause_after_prereg=False, dim=None, mem_elems=None)
buf = io.StringIO()
t0 = time.time()
with contextlib.redirect_stdout(buf):
    rc = C.cmd_hw_selftest(args)
out = json.loads(buf.getvalue()[buf.getvalue().find("{"):])
out["exit"], out["wall_s"] = rc, round(time.time() - t0, 1)
out["model"] = {"tau_bf16_s": a.tau_bf16, "tau_fp16_s": a.tau_fp16, "idle_w": a.idle, "busy_w": a.busy,
                "turing_dtype": a.turing, "tau_jitter": a.tau_jitter, "busy_sd_w": a.busy_sd}
print(json.dumps(out, indent=2))
