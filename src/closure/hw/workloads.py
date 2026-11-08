from __future__ import annotations

import threading
import time

import numpy as np

UNIT_BUDGET_FRAC = 0.2       # one unit of work may take at most this share of a slot (see size_unit)
MIN_DIM = 64


def native_half(torch, device) -> object:
    """The half precision this device runs on tensor cores: bf16 from compute capability 8.0 (A100, L4, H100, ...) and
    on CPU; fp16 before that (V100, T4), where a bf16 matmul falls back to a path several times slower."""
    dev = str(device)
    if not dev.startswith("cuda"):
        return torch.bfloat16
    major, _minor = torch.cuda.get_device_capability(dev)
    return torch.bfloat16 if int(major) >= 8 else torch.float16


def size_unit(time_unit, dim: int, mem_elems: int, budget_s: float, min_dim: int = MIN_DIM):
    """Halve (dim, mem_elems) from the requested size until one unit of work takes at most budget_s seconds.

    A unit longer than the slot breaks load control: every level above zero then runs at least one whole unit per
    slot, so 25% load and 100% load do the same work. That is what the first run on a T4 showed (docs/DEVIATIONS.md):
    an 8192 x 8192 bf16 unit took about half a second against a 100 ms slot. time_unit(dim, mem_elems) measures one unit
    in seconds. Returns (dim, mem_elems, seconds, tried), where tried lists every size measured."""
    tried = []
    while True:
        t = float(time_unit(dim, mem_elems))
        tried.append({"dim": int(dim), "mem_elems": int(mem_elems), "unit_s": t})
        if t <= budget_s or dim // 2 < min_dim:
            return int(dim), int(mem_elems), t, tried
        dim, mem_elems = dim // 2, max(1 << 12, mem_elems // 2)


def measure_idle_w(reader, n_gpu: int, seconds: float = 3.0, settle_s: float = 2.0, sleep=time.sleep,
                   now=time.perf_counter) -> float:
    """Mean power per GPU, from the energy counter, while the load generator sits at level 0."""
    sleep(settle_s)
    e0, t0 = reader.energy_j(), now()
    sleep(seconds)
    e1, t1 = reader.energy_j(), now()
    return (e1 - e0) / max(t1 - t0, 1e-9) / max(1, int(n_gpu))


class TorchLoad:
    """Synthetic *verified* inference load plus controllable *hidden* load, duty-cycled per 100 ms slot.

    One unit of work = one compute-bound GEMM ('prefill unit') + one memory-bound pass ('decode unit'), in the device's
    native half precision. The unit is sized to fit the slot (size_unit) unless auto_size=False, and units are counted
    as they finish. Verified work runs first in each slot, hidden work fills part of the remaining (spare) time, so the
    two never overlap on a GPU. p_max_w and p_idle_w map a hidden-load fraction to a duty cycle: pass this GPU's own
    numbers (cli._hw_parts reads the power limit from NVML and measures idle). HARDWARE-GATED: run
    `closure hw-selftest` first."""

    def __init__(self, gpus, dim: int = 8192, mem_elems: int = 1 << 29, slot_s: float = 0.1,
                 p_max_w: float = 700.0, p_idle_w: float = 120.0, device: str = None, auto_size: bool = True,
                 budget_frac: float = UNIT_BUDGET_FRAC):
        import torch
        self.torch, self.gpus, self.slot = torch, list(gpus), slot_s
        self.device = device                            # e.g. "cpu": the same loop without a GPU (tests, rehearsal)
        self.p_max, self.p_idle = float(p_max_w), float(p_idle_w)
        dev0 = self.device or f"cuda:{self.gpus[0]}"
        self.dtype = native_half(torch, dev0)
        self.budget_s, self.auto_sized = float(budget_frac) * slot_s, bool(auto_size)
        if auto_size:
            self.dim, self.mem, self.unit_s, self.size_tried = size_unit(
                lambda d, m: self._time_unit(dev0, d, m), int(dim), int(mem_elems), self.budget_s)
        else:                                           # given (e.g. hw-selftest's size, passed on by tier0): kept
            self.dim, self.mem = int(dim), int(mem_elems)
            self.unit_s = self._time_unit(dev0, self.dim, self.mem)
            self.size_tried = [{"dim": self.dim, "mem_elems": self.mem, "unit_s": self.unit_s}]
        self.state = {"level": 0.0, "hid_duty": 0.0, "hid_gpus": frozenset()}
        self.counts, self.lock, self.stop_flag = np.zeros(3), threading.Lock(), False
        self.errors = []                                # a worker that died: reported, not mistaken for an idle GPU
        self.threads = [threading.Thread(target=self._worker, args=(g,), daemon=True) for g in self.gpus]
        for t in self.threads:
            t.start()

    def describe(self) -> dict:
        return {"dim": self.dim, "mem_elems": self.mem, "dtype": str(self.dtype).replace("torch.", ""),
                "unit_s": self.unit_s, "slot_s": self.slot, "budget_s": self.budget_s,
                "fits_slot": bool(self.unit_s <= self.budget_s), "auto_sized": self.auto_sized,
                "tried": list(self.size_tried)}

    def set_state(self, level: float, hidden_frac: float = 0.0, spec=None):
        cap = len(self.gpus) * self.p_max
        hw = hidden_frac * cap
        dyn = max(self.p_max - self.p_idle, 0.05 * self.p_max)
        n_h = min(len(self.gpus), max(1, int(np.ceil(hw / dyn)))) if hw > 0 else 0
        duty = min(1.0, hw / (n_h * dyn)) if n_h else 0.0
        self.state = {"level": float(level), "hid_duty": duty, "hid_gpus": frozenset(self.gpus[:n_h])}

    def pop_units(self):
        with self.lock:
            c, self.counts = self.counts.copy(), np.zeros(3)
        return float(c[0]), float(c[1]), float(c[2])

    def _sync(self, dev):
        if dev.startswith("cuda"):
            self.torch.cuda.synchronize(dev)

    def _tensors(self, dev, dim, mem):
        torch = self.torch
        A = torch.randn(dim, dim, device=dev, dtype=self.dtype)
        B = torch.randn(dim, dim, device=dev, dtype=self.dtype)
        return A, B, torch.zeros(mem, device=dev, dtype=torch.float16)

    def _unit(self, A, B, big, dev):
        self.torch.matmul(A, B)
        self._sync(dev)
        big.mul_(1.0001)
        self._sync(dev)

    def _time_unit(self, dev, dim, mem, warmup: int = 2, reps: int = 3) -> float:
        """Median seconds per unit at this size, after a warm-up (kernel selection, clocks)."""
        A, B, big = self._tensors(dev, dim, mem)
        try:
            for _ in range(warmup):
                self._unit(A, B, big, dev)
            ts = []
            for _ in range(reps):
                t0 = time.perf_counter()
                self._unit(A, B, big, dev)
                ts.append(time.perf_counter() - t0)
        finally:
            del A, B, big
            if dev.startswith("cuda"):
                self.torch.cuda.empty_cache()
        return float(np.median(ts))

    def _worker(self, g):
        torch = self.torch
        dev = self.device or f"cuda:{g}"
        try:
            if dev.startswith("cuda"):
                torch.cuda.set_device(g)
            A, B, big = self._tensors(dev, self.dim, self.mem)
            while not self.stop_flag:
                t0, st = time.perf_counter(), self.state
                lvl = st["level"]
                hid = st["hid_duty"] if g in st["hid_gpus"] else 0.0
                end = t0 + lvl * self.slot
                while time.perf_counter() < end:
                    self._unit(A, B, big, dev)
                    with self.lock:                     # counted as it finishes: a window holds the units it ran
                        self.counts += 1.0
                end2 = time.perf_counter() + hid * self.slot
                while time.perf_counter() < end2:
                    torch.matmul(A, B)
                    self._sync(dev)
                rest = t0 + self.slot - time.perf_counter()
                if rest > 0:
                    time.sleep(rest)
        except Exception as e:
            self.errors.append(f"GPU {g}: {type(e).__name__}: {e}")
            raise

    def stop(self):
        self.stop_flag = True
        for t in self.threads:
            t.join(timeout=2.0)
