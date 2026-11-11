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


HIDDEN_DUTIES = (0.02, 0.05, 0.10, 0.20, 0.40, 0.80)


def duty_for_watts(table, watts: float) -> float:
    """The hidden duty whose solo power is `watts` per GPU: piecewise linear through the measured (duty, watts) points
    from (0, 0), extended along the last segment, never above 1."""
    pts = [(0.0, 0.0)] + [(float(d), float(w)) for d, w in table]
    if watts <= 0:
        return 0.0
    for (d0, w0), (d1, w1) in zip(pts[:-1], pts[1:]):
        if watts <= w1:
            return d0 + (d1 - d0) * (watts - w0) / max(w1 - w0, 1e-12)
    (d0, w0), (d1, w1) = pts[-2], pts[-1]
    return float(min(1.0, d1 + (d1 - d0) * (watts - w1) / max(w1 - w0, 1e-12)))


def characterise_hidden(load, reader, n_gpu: int, duties=HIDDEN_DUTIES, on_s: float = 20.0, idle_s: float = 8.0,
                        settle_s: float = 2.0, sleep=time.sleep, now=time.perf_counter) -> dict:
    """The hidden load run alone ("solo"), before the trial: its power above idle at each duty, per GPU.

    The trial labels a hidden load by its power as a fraction of capacity. Until 0.8.0 the duty for a label was
    computed from the power limit less idle power, and each slot ran whole GEMMs until that time was used up. Both
    missed: with clocks locked high a T4's bursts drew 73 W per unit of duty against the 41 W assumed (run 4), and
    whole GEMMs overshot each slot by up to one GEMM, which doubled the smallest load (run 5). In those two runs the
    hidden load ran at 1.1 to 2.2 times its label (docs/DEVIATIONS.md sections 4 and 5). Here each duty is measured
    between two idle readings, one before it and one after, so a slow change in idle power cancels, and the trial
    then picks duties from this table, so a label means what it says. About three and a half minutes with the
    defaults. Returns {"duty": [...], "watts_per_gpu": [...], "idle_w_per_gpu": [...]} with watts made monotone."""
    was = load.state
    rest = {"level": 0.0, "hid_duty": 0.0, "hid_gpus": frozenset()}
    out = {"duty": [], "watts_per_gpu": [], "idle_w_per_gpu": []}
    try:
        load.state = rest
        idle, on = [measure_idle_w(reader, n_gpu, seconds=idle_s, settle_s=settle_s, sleep=sleep, now=now)], []
        for d in duties:
            load.state = {"level": 0.0, "hid_duty": float(d), "hid_gpus": frozenset(load.gpus)}
            on.append(measure_idle_w(reader, n_gpu, seconds=on_s, settle_s=settle_s, sleep=sleep, now=now))
            load.state = rest
            idle.append(measure_idle_w(reader, n_gpu, seconds=idle_s, settle_s=settle_s, sleep=sleep, now=now))
        best = 0.0
        for i, d in enumerate(duties):
            base = 0.5 * (idle[i] + idle[i + 1])
            best = max(best, on[i] - base)
            out["duty"].append(float(d)); out["watts_per_gpu"].append(float(best)); out["idle_w_per_gpu"].append(float(base))
    finally:
        load.state = was
    return out


class TorchLoad:
    """Synthetic *verified* inference load plus controllable *hidden* load, duty-cycled per 100 ms slot.

    One unit of work = one compute-bound GEMM ('prefill unit') + one memory-bound pass ('decode unit'), in the device's
    native half precision. The unit is sized to fit the slot (size_unit) unless auto_size=False, and units are counted
    as they finish. Verified work runs first in each slot; hidden work then takes its share of wall-clock time, so the
    two never overlap on a GPU, and when both do not fit in a slot it is the verified work that gives way. A
    hidden-load fraction becomes a duty cycle through hidden_table, the load's own power measured before the trial
    (characterise_hidden); without one, through the old estimate from p_max_w and p_idle_w (pass this GPU's own
    numbers: cli._hw_parts reads the power limit from NVML and measures idle). The seconds the hidden work ran are
    counted (pop_hidden_s). HARDWARE-GATED: run `closure hw-selftest` first."""

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
        self.hidden_table = None                        # (duty, solo watts per GPU) from characterise_hidden
        self.hid_s = 0.0                                # seconds the hidden load really ran since the last pop
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
        """hidden_frac: the hidden load's power as a fraction of capacity, on as few GPUs as can carry it. With a solo
        characterisation (hidden_table) the duty is read off the measured curve; without one it is the old estimate
        from the power limit."""
        cap = len(self.gpus) * self.p_max
        hw = hidden_frac * cap
        if self.hidden_table and hw > 0:
            full = max(self.hidden_table[-1][1] / max(self.hidden_table[-1][0], 1e-9), 1e-9)   # watts at duty 1, about
            n_h = min(len(self.gpus), max(1, int(np.ceil(hw / full))))
            duty = duty_for_watts(self.hidden_table, hw / n_h)
        else:
            dyn = max(self.p_max - self.p_idle, 0.05 * self.p_max)
            n_h = min(len(self.gpus), max(1, int(np.ceil(hw / dyn)))) if hw > 0 else 0
            duty = min(1.0, hw / (n_h * dyn)) if n_h else 0.0
        self.state = {"level": float(level), "hid_duty": duty, "hid_gpus": frozenset(self.gpus[:n_h])}

    def pop_units(self):
        with self.lock:
            c, self.counts = self.counts.copy(), np.zeros(3)
        return float(c[0]), float(c[1]), float(c[2])

    def pop_hidden_s(self) -> float:
        """Seconds the hidden load ran since the last call, as a mean over the GPUs: ground truth, counted as it runs,
        in the busy channel's own units (mean utilisation over the GPUs times seconds)."""
        with self.lock:
            h, self.hid_s = self.hid_s, 0.0
        return float(h) / max(1, len(self.gpus))

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
            credit = 0.0                                # hidden seconds owed; negative after a GEMM ran ahead of it
            last = time.perf_counter()                  # when the credit was last topped up
            while not self.stop_flag:
                t0, st = time.perf_counter(), self.state
                lvl = st["level"]
                hid = st["hid_duty"] if g in st["hid_gpus"] else 0.0
                end = t0 + lvl * self.slot
                while time.perf_counter() < end:
                    self._unit(A, B, big, dev)
                    with self.lock:                     # counted as it finishes: a window holds the units it ran
                        self.counts += 1.0
                # Hidden work: whole GEMMs paid for from a running credit of `hid` seconds for every second of wall
                # time, so the hidden load takes the share of the GPU's time it was asked to take, whatever the
                # verified load is doing and even when that share is a fraction of one GEMM per slot. (Until 0.8.0
                # each slot ran whole GEMMs until its hidden time was used up, so every slot overshot by up to one
                # GEMM and the smallest loads ran at about twice their duty.)
                # At full verified load the two do not fit in a slot; the slot then runs long and it is the verified
                # work that gives way, as it would on an operator's GPU.
                now = time.perf_counter()
                credit = min(credit + hid * (now - last), self.slot) if hid > 0 else 0.0
                last = now
                while credit > 0 and not self.stop_flag:
                    t1 = time.perf_counter()
                    torch.matmul(A, B)
                    self._sync(dev)
                    d = time.perf_counter() - t1
                    credit -= d
                    with self.lock:
                        self.hid_s += d
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
