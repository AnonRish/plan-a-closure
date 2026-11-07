from __future__ import annotations

import threading
import time

import numpy as np


class TorchLoad:
    """Synthetic *verified* inference load plus controllable *hidden* load, duty-cycled per 100 ms slot.

    One loop iteration = one compute-bound GEMM ('prefill unit') + one memory-bound pass ('decode unit').
    Verified work runs first in each slot, hidden work fills part of the remaining (spare) time, so the two
    never overlap on a GPU. HARDWARE-GATED: untested without GPUs; run `closure hw-selftest` first."""

    def __init__(self, gpus, dim: int = 8192, mem_elems: int = 1 << 29, slot_s: float = 0.1,
                 p_max_w: float = 700.0, p_idle_w: float = 120.0, device: str = None):
        import torch
        self.torch, self.gpus, self.dim, self.mem, self.slot = torch, list(gpus), dim, mem_elems, slot_s
        self.device = device                            # e.g. "cpu": the same loop without a GPU (tests, rehearsal)
        self.p_max, self.p_idle = p_max_w, p_idle_w
        self.state = {"level": 0.0, "hid_duty": 0.0, "hid_gpus": frozenset()}
        self.counts, self.lock, self.stop_flag = np.zeros(3), threading.Lock(), False
        self.threads = [threading.Thread(target=self._worker, args=(g,), daemon=True) for g in self.gpus]
        for t in self.threads:
            t.start()

    def set_state(self, level: float, hidden_frac: float = 0.0, spec=None):
        cap = len(self.gpus) * self.p_max
        hw = hidden_frac * cap
        dyn = self.p_max - self.p_idle
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

    def _worker(self, g):
        torch = self.torch
        dev = self.device or f"cuda:{g}"
        if dev.startswith("cuda"):
            torch.cuda.set_device(g)
        A = torch.randn(self.dim, self.dim, device=dev, dtype=torch.bfloat16)
        B = torch.randn(self.dim, self.dim, device=dev, dtype=torch.bfloat16)
        big = torch.zeros(self.mem, device=dev, dtype=torch.float16)
        while not self.stop_flag:
            t0, st = time.perf_counter(), self.state
            lvl = st["level"]
            hid = st["hid_duty"] if g in st["hid_gpus"] else 0.0
            n = 0
            end = t0 + lvl * self.slot
            while time.perf_counter() < end:
                torch.matmul(A, B)
                self._sync(dev)
                big.mul_(1.0001)
                self._sync(dev)
                n += 1
            end2 = time.perf_counter() + hid * self.slot
            while time.perf_counter() < end2:
                torch.matmul(A, B)
                self._sync(dev)
            with self.lock:
                self.counts += np.array([n, n, n], float)
            rest = t0 + self.slot - time.perf_counter()
            if rest > 0:
                time.sleep(rest)

    def stop(self):
        self.stop_flag = True
        for t in self.threads:
            t.join(timeout=2.0)
