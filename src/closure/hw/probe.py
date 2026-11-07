"""Efficiency-slack and energy-floor probe (pre-registered H1.6 and H1.7).

Closure bounds hidden work by *unexplained* energy. Two measured quantities keep that bound honest:

* efficiency slack ``s_max`` (assumption A4). An allowed software stack, a clock or power cap, or a numerics choice may
  do the *same verified work at the same rate* for less energy. So may the *data*: the same GEMMs on cheaper activations
  (zeros, sparse or low-entropy values) draw less power. An operator who uses either can run hidden work for free, so
  the bound has to be inflated by ``s_max`` (``trial.analyze`` then reports the slack-inflated gap). ``s_max`` is the
  larger of the stack slack ``s_stack`` and the operand slack ``s_operand``; both are reported.
* the energy floor ``e_floor``: the lowest *dynamic* (above-idle) joules per FLOP reached over everything swept,
  including int8 and fp8 GEMMs where the device runs them (integer operations count as FLOPs).
  Hidden FLOPs <= hidden joules / e_floor.

Kimpson, Baker and Graham (arXiv 2610.07476) bound hidden compute from power analytically and show why both matter: on an
A100 a "matched-energy" attack runs the declared work on cheap operands and spends the saved energy on covert int8 work.
In their notation declared work costs between r_lo and r_hi joules per operation and covert work at least r_lo^cov. This
probe reports the measured band (``declared_band_j_per_flop``), the floor, and ``band_over_floor`` = (hi - lo) / e_floor,
the first term of their Eq. 18 per unit of declared utilisation.

Method. Each variant is run in duty-cycled windows at fixed work rates ("levels", a fraction of the reference stack's
measured capacity), the way the trial's own synthetic load runs: ``n`` units of work per 100 ms slot, then idle. Energy
comes from the NVML hardware counter over the whole window. A stack variant counts only if it keeps up with the work rate
(feasible) and its numerics are at least as accurate as the reference's, within ``rel_tol``. An operand variant keeps the
reference stack and changes only the activation operand (the weights stay Gaussian, as a whitelisted model's would): it is
exempt from the numerics check, because its outputs differ by construction, but must keep up with the work rate. Operand
variants probe how cheap *declared* work can be made, so they never set the energy floor. The saving at a level is
``1 - P_variant / P_reference`` (mean power at the same work rate); level 0 captures idle-power slack. ``s_max`` is the
largest one-sided 95% *upper* confidence saving over counted variants and levels, so noise inflates the bound rather
than shrinking it. The reference is measured at the start and end of every round, so drift shows up in it.

Everything is written to ``probe.json`` with a sha256 seal. ``closure hw-trial --probe probe.json`` binds that hash into
the pre-registration and the report.

HARDWARE-GATED. ``TorchRig`` has not been run on a GPU by its author: ``FakeProbeRig`` and the tests exercise the logic
and the control flow only. A measured floor is an empirical floor over the swept space (clocks, caps, dtypes, kernel
library), not a proof of a physical limit: widen the sweep before relying on it. Subclass ``TorchRig`` (or any object
with ``prepare``, ``measure``, ``reset``, ``info``) to probe a served-model stack for T1b.
"""
from __future__ import annotations

import math
import random
import subprocess
import sys
import time
from dataclasses import dataclass

import numpy as np

from ..conformal import t_upper
from ..evidence import canonical, clean, sha256_hex

MIN_VARIANTS = 3                    # H1.6: at least three allowed stack variants
MIN_LOAD_FRACTION = 0.10            # a cell counts toward the floor only if dynamic energy is >= 10% of its total
DEFAULT_LEVELS = (0.0, 0.25, 0.5, 0.9)
DEFAULT_PRECISIONS = ("tf32", "fp16", "int8", "fp8")      # int8 and fp8 lower the floor; their numerics keep them out of s_max
DEFAULT_OPERANDS = ("sparse90", "lowent", "zeros")        # activation patterns: 90% zeros, values in {-1, 0, 1}, all zeros
LOWP = ("int8", "fp8")                                    # precisions that need their own matmul (TorchRig)
FALLBACK_CLOCKS = (1755, 1500, 1275, 1005, 780, 510)       # used when the device cannot list its supported clocks


def pick_clocks(supported, n: int = 6, low_frac: float = 0.25) -> list:
    """n SM clocks the device actually supports, spread from just below its maximum down to about low_frac of it. Locking
    at the maximum is skipped (it is the reference); an empty list means the device did not say (use FALLBACK_CLOCKS)."""
    s = sorted({int(c) for c in supported if c and c > 0}, reverse=True)
    if len(s) < 2:
        return []
    cand = [c for c in s[1:] if c >= low_frac * s[0]] or s[1:]
    if len(cand) <= n:
        return cand
    idx = np.unique(np.linspace(0, len(cand) - 1, n).round().astype(int))
    return [cand[i] for i in idx]


def pick_power_caps(default_w: float, limits, fracs=(0.7, 0.5)) -> list:
    """Power-limit fractions of the default limit, each raised to the device's settable minimum when it lies below it.
    A cap above 95% of the default is no cap, so it is dropped."""
    if not limits or not default_w:
        return list(fracs)
    lo = float(limits[0]) / float(default_w)
    out = sorted({round(max(float(f), lo + 0.01), 3) for f in fracs}, reverse=True)
    return [f for f in out if f <= 0.95]


class Unavailable(RuntimeError):
    """A variant cannot be applied on this machine (unsupported clock, library missing, ...): it is dropped and noted."""


@dataclass(frozen=True)
class Variant:
    name: str
    kind: str            # reference | clock_cap | power_cap | precision | kernel | operand
    value: object = None  # MHz, fraction of the default power limit, dtype name, BLAS library name, operand pattern

    def to_dict(self) -> dict:
        return {"name": self.name, "kind": self.kind, "value": self.value}


def default_variants(clocks=(1755, 1500, 1275, 1005, 780, 510), power_caps=(0.7, 0.5),
                     precisions=("tf32", "fp16"), kernels=("cublaslt",), operands=()) -> list:
    """The CLI passes DEFAULT_PRECISIONS and DEFAULT_OPERANDS; the narrower defaults here keep library callers unchanged."""
    vs = [Variant("reference", "reference")]
    vs += [Variant(f"clock-{int(c)}MHz", "clock_cap", float(c)) for c in clocks]
    vs += [Variant(f"powercap-{int(round(100 * f))}pct", "power_cap", float(f)) for f in power_caps]
    vs += [Variant(f"precision-{p}", "precision", p) for p in precisions]
    vs += [Variant(f"kernel-{k}", "kernel", k) for k in kernels]
    vs += [Variant(f"operand-{o}", "operand", o) for o in operands]
    return vs


def _mean_se(x):
    x = np.asarray(x, float)
    n = int(len(x))
    return float(x.mean()), (float(x.std(ddof=1) / math.sqrt(n)) if n > 1 else 0.0), n


def summarize(variants, levels, samples, rel_tol: float, alpha: float = 0.05, dropped=None) -> dict:
    """samples[(variant_name, level)] = list of measurement dicts. Pure function of the data: unit-tested."""
    ref = next(v for v in variants if v.kind == "reference")
    notes = [f"variant {k} dropped: {why}" for k, why in (dropped or {}).items()]

    def power(ms):
        return [m["energy_j"] / m["time_s"] for m in ms]

    ref_err = max(m["rel_err"] for l in levels for m in samples[(ref.name, l)])
    ref_ok = {l: all(m["feasible"] for m in samples[(ref.name, l)]) for l in levels}
    for l in levels:
        if not ref_ok[l]:
            notes.append(f"the reference could not sustain level {l}: no savings are computed at that level")
    rows, cands, band = [], [], []
    for v in variants:
        err = max(m["rel_err"] for l in levels for m in samples[(v.name, l)])
        cls = "reference" if v.kind == "reference" else ("operand" if v.kind == "operand" else "stack")
        # an operand variant keeps the reference stack and numerics; its outputs differ by construction: no accuracy gate
        allowed = cls in ("reference", "operand") or err <= ref_err + rel_tol
        idle_p = float(np.mean(power(samples[(v.name, 0.0)])))
        row = {**v.to_dict(), "class": cls, "rel_err": err, "allowed": bool(allowed), "idle_power_w": idle_p, "levels": []}
        for l in levels:
            ms = samples[(v.name, l)]
            feas = all(m["feasible"] for m in ms)
            pm, pse, n = _mean_se(power(ms))
            cell = {"level": l, "n": n, "feasible": bool(feas), "power_w_mean": pm, "power_w_se": pse,
                    "busy_frac": float(np.mean([m["busy_frac"] for m in ms])),
                    "sm_mhz": float(np.median([m["sm_mhz"] for m in ms]))}
            if v.kind != "reference" and feas and ref_ok[l]:
                rp, rse, rn = _mean_se(power(samples[(ref.name, l)]))
                tc = t_upper(alpha, max(1.0, min(n, rn) - 1.0))
                cell["saving_point"] = 1.0 - pm / rp
                cell["saving_upper95"] = 1.0 - (pm - tc * pse) / (rp + tc * rse)
            if l > 0:                                    # dynamic J/FLOP; feasibility is irrelevant to a floor
                jpf = [(m["energy_j"] - idle_p * m["time_s"]) / m["flop"] for m in ms
                       if m["flop"] > 0 and m["energy_j"] > idle_p * m["time_s"]
                       and (m["energy_j"] - idle_p * m["time_s"]) / m["energy_j"] >= MIN_LOAD_FRACTION]
                if jpf:
                    cell["dynamic_j_per_flop"] = float(np.mean(jpf))
                    if cls != "operand":                  # operand patterns probe declared work, not covert work
                        cands.append((cell["dynamic_j_per_flop"], v.name, l))
                    if allowed and feas:                  # work an operator could declare at this rate
                        band.append((cell["dynamic_j_per_flop"], v.name, l))
            row["levels"].append(cell)
        rows.append(row)

    def best_of(c):
        s = [(cell["saving_upper95"], r["name"], cell["level"], cell["saving_point"], r["class"]) for r in rows
             if r["class"] == c and r["allowed"] for cell in r["levels"] if "saving_upper95" in cell]
        return max(s) if s else None

    def measurable(c):
        return sum(1 for r in rows if r["class"] == c and r["allowed"]
                   and any("saving_upper95" in cell for cell in r["levels"] if cell["level"] > 0))

    b_stack, b_op = best_of("stack"), best_of("operand")
    n_allowed, n_operand = measurable("stack"), measurable("operand")
    if n_allowed < MIN_VARIANTS:
        notes.append(f"only {n_allowed} allowed variants were measurable above idle; H1.6 needs at least {MIN_VARIANTS}")
    if n_operand == 0:
        notes.append("operand slack was not measured: s_max covers stack choices only, but a matched-energy attack runs "
                     "the declared work on cheap operands (pass --operands)")
    best = max([b for b in (b_stack, b_op) if b is not None], default=None)
    floor = min(cands) if cands else None
    if floor is None:
        notes.append("no cell had dynamic energy above 10% of its total: the energy floor is not measured")
    lo, hi = (min(band), max(band)) if band else (None, None)
    return {"reference": ref.name, "levels": [float(l) for l in levels], "rel_tol": rel_tol, "alpha_one_sided": alpha,
            "variants": rows, "n_allowed_variants": int(n_allowed), "h1_6_variants_ok": bool(n_allowed >= MIN_VARIANTS),
            "n_operand_variants": int(n_operand),
            "s_max": (max(0.0, best[0]) if best else None),
            "s_max_at": ({"variant": best[1], "level": best[2], "saving_point": best[3], "class": best[4]}
                         if best else None),
            "s_stack": (max(0.0, b_stack[0]) if b_stack else None),
            "s_operand": (max(0.0, b_op[0]) if b_op else None),
            "e_floor_j_per_flop": (floor[0] if floor else None),
            "e_floor_at": ({"variant": floor[1], "level": floor[2]} if floor else None),
            "declared_band_j_per_flop": ({"lo": lo[0], "lo_at": {"variant": lo[1], "level": lo[2]},
                                          "hi": hi[0], "hi_at": {"variant": hi[1], "level": hi[2]}} if band else None),
            "band_over_floor": ((hi[0] - lo[0]) / floor[0] if (band and floor) else None),
            "notes": notes}


def run_probe(rig, variants, levels=DEFAULT_LEVELS, repeats: int = 3, rel_tol: float = 5e-3, seed: int = 0,
              log=None) -> dict:
    levels = tuple(float(x) for x in levels)
    if 0.0 not in levels or not any(l > 0 for l in levels):
        raise ValueError("levels must include 0 (idle) and at least one positive work rate")
    refs = [v for v in variants if v.kind == "reference"]
    if len(refs) != 1:
        raise ValueError("exactly one reference variant is required")
    ref = refs[0]
    others = [v for v in variants if v is not ref]
    if hasattr(rig, "prepare"):
        rig.prepare(ref)
    rng = random.Random(seed)
    samples = {(v.name, l): [] for v in variants for l in levels}
    dropped = {}
    try:
        for r in range(int(repeats)):
            for v in [ref] + rng.sample(others, len(others)) + [ref]:     # the reference brackets every round
                if v.name in dropped:
                    continue
                try:
                    got = [rig.measure(v, l) for l in levels]
                except Unavailable as e:
                    dropped[v.name] = str(e)
                    for l in levels:
                        samples[(v.name, l)] = []
                    if log:
                        log(f"dropped {v.name}: {e}")
                    continue
                for l, m in zip(levels, got):
                    samples[(v.name, l)].append(m)
                if log:
                    log(f"round {r + 1}/{repeats}  {v.name}")
    finally:
        if hasattr(rig, "reset"):
            rig.reset()
    kept = [v for v in variants if v.name not in dropped]
    res = summarize(kept, levels, samples, rel_tol, dropped=dropped)
    res["settings"] = {"repeats": int(repeats), "seed": int(seed)}
    return res


def seal(res: dict, status: str, info=None) -> dict:
    out = dict(res)
    out["status"] = status
    out["rig"] = info or {}
    out["created_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    out = clean(out)
    out["sha256"] = sha256_hex(canonical({k: v for k, v in out.items() if k != "sha256"}))
    return out


def verify_seal(res: dict) -> bool:
    return res.get("sha256") == sha256_hex(canonical({k: v for k, v in res.items() if k != "sha256"}))


class FakeProbeRig:
    """Deterministic, physics-flavoured stand-in with no GPU: dynamic power goes with the cube of the clock, so energy per
    unit of work falls at lower clocks until idle power dominates; locking a lower clock also lowers idle power. It exists
    to test the probe logic. It says nothing about any real chip."""
    F_MAX = 1980.0

    def __init__(self, seed: int = 0, p_idle: float = 120.0, p_max: float = 700.0, unit_flop: float = 2 * 8192 ** 3,
                 t_unit_s: float = 0.0016, noise: float = 0.004, window_s: float = 8.0):
        self.rng = np.random.default_rng(seed)
        self.p_idle, self.p_max, self.unit_flop, self.t_unit = p_idle, p_max, unit_flop, t_unit_s
        self.noise, self.window_s = noise, window_s
        self.default_pl_w = p_max

    def supported_clocks(self) -> list:
        return [1980, 1755, 1500, 1275, 1005, 780, 510, 345]

    def power_limits(self):
        return (200.0, self.p_max)

    def prepare(self, ref):
        return None

    def reset(self):
        return None

    def info(self) -> dict:
        return {"rig": "FakeProbeRig", "p_idle_w": self.p_idle, "p_max_w": self.p_max}

    def measure(self, v: Variant, level: float) -> dict:
        x, e_fac, err, idle_fac = 1.0, 1.0, 4e-3, 1.0
        if v.kind == "clock_cap":
            x = min(1.0, float(v.value) / self.F_MAX)
            idle_fac = 0.8 + 0.2 * x
        elif v.kind == "power_cap":
            cap_w = float(v.value) * self.p_max
            x = min(1.0, max(0.1, ((cap_w - self.p_idle) / (self.p_max - self.p_idle)) ** (1.0 / 3.0)))
        elif v.kind == "precision":
            e_fac, err = {"tf32": (1.12, 1e-3), "fp16": (0.99, 6e-4), "int8": (0.5, 2e-2),
                          "fp8": (0.6, 4e-2)}.get(v.value, (1.0, 4e-3))
        elif v.kind == "kernel":
            e_fac = 0.97
        elif v.kind == "operand":                     # cheaper activations: same work, less switching (invented factors)
            e_fac = {"zeros": 0.7, "sparse90": 0.8, "lowent": 0.9}.get(v.value, 1.0)
        t_unit = self.t_unit / x
        busy = level * t_unit / self.t_unit
        feasible = busy <= 1.0
        busy_eff = min(busy, 1.0)
        power = self.p_idle * idle_fac + busy_eff * (self.p_max - self.p_idle) * x ** 3 * e_fac
        T = self.window_s
        units = int(busy_eff * T / t_unit)
        return {"energy_j": power * T * (1.0 + self.noise * float(self.rng.standard_normal())), "time_s": T,
                "units": units, "flop": units * self.unit_flop, "level": level, "busy_frac": busy_eff,
                "feasible": feasible, "sm_mhz": self.F_MAX * x, "rel_err": err}


class TorchRig:
    """Real device. One GPU under test, NVML energy counter, ``nvidia-smi`` for clock and power-limit control (needs root).

    One unit of work = one dim x dim GEMM plus one memory-bound pass, the same unit ``TorchLoad`` uses. Numerics are
    judged by the relative Frobenius error of a seeded 1024 x 1024 product against a float64 truth (int8 after symmetric
    per-tensor quantisation). int8 runs through ``torch._int_mm`` and fp8 (e4m3) through ``torch._scaled_mm``; a GPU or
    torch build that cannot run them drops the variant with a note (fp8 needs compute capability 8.9 or newer).
    HARDWARE-GATED: not run on a GPU by the author; ``measure`` control flow is covered by a virtual-clock test."""
    SLOT_S = 0.1
    OVERRUN_TOL = 0.02       # share of slots allowed to overrun before a variant is called infeasible at a level
    SETTLE_S, WARMUP_S, CALIB_S = 2.0, 3.0, 2.0

    def __init__(self, gpu: int = 0, dim: int = 8192, mem_elems: int = 1 << 29, window_s: float = 8.0,
                 reader=None, time_fn=time.perf_counter, sleep_fn=time.sleep, device: str = None, control: bool = True):
        self.gpu, self.dim, self.mem, self.T = int(gpu), int(dim), int(mem_elems), float(window_s)
        self.time, self.sleep = time_fn, sleep_fn
        self.t_unit_ref = None
        self._err = {}
        self._mm = None                                # matmul for the current variant; None means torch.matmul
        self.control = bool(control)                   # False: no nvidia-smi; clock and power variants are dropped
        self.dev = device or f"cuda:{self.gpu}"        # "cpu" runs the same code without a GPU (tests, rehearsal)
        if reader is None or device is not None:
            import torch
            self.torch = torch
            if self.dev.startswith("cuda"):
                torch.cuda.set_device(self.gpu)
            self._tf32 = torch.backends.cuda.matmul.allow_tf32
            try:
                bl = getattr(torch.backends.cuda, "preferred_blas_library", None)
                self._blas = bl() if bl else None
            except Exception:                          # no CUDA context (CPU runs) or an older torch
                self._blas = None
        if reader is None:
            from .nvml import NvmlReader
            reader = NvmlReader([self.gpu])
        self.reader = reader
        self.default_pl_w = float(self.reader.power_limit_w())

    def _sync(self):
        if str(self.dev).startswith("cuda"):
            self.torch.cuda.synchronize(self.dev)

    def supported_clocks(self) -> list:
        f = getattr(self.reader, "supported_sm_clocks", None)
        return f() if f else []

    def power_limits(self):
        f = getattr(self.reader, "power_limit_range_w", None)
        return f() if f else None

    # ---- device control -------------------------------------------------------------------------------------
    def _smi(self, *args):
        if not self.control:
            raise Unavailable("device control is off: clock and power-limit variants are skipped")
        r = subprocess.run(["nvidia-smi", "-i", str(self.gpu), *map(str, args)], capture_output=True, text=True, timeout=60)
        if r.returncode != 0:
            msg = (r.stderr or r.stdout).strip()
            if any(s in msg.lower() for s in ("permission", "root", "administrator")):
                raise RuntimeError(f"`nvidia-smi {' '.join(map(str, args))}` needs root: {msg}")
            raise Unavailable(msg or f"nvidia-smi {' '.join(map(str, args))} failed")

    def _restore_numerics(self):
        self.torch.backends.cuda.matmul.allow_tf32 = self._tf32
        self._set_blas(self._blas)

    def _set_blas(self, lib):
        setter = getattr(self.torch.backends.cuda, "preferred_blas_library", None)
        if lib is None:
            return
        if setter is None:
            raise Unavailable("this torch has no preferred_blas_library")
        try:
            setter(lib)
        except Exception as e:                       # unknown library name or backend not built
            raise Unavailable(f"BLAS library {lib!r}: {e}")

    def reset(self):
        for args in ((("-rgc",), ("-pl", int(round(self.default_pl_w)))) if self.control else ()):
            try:
                self._smi(*args)
            except Exception as e:
                print(f"WARNING: could not undo `nvidia-smi {' '.join(map(str, args))}`: {e}", file=sys.stderr)
        self._restore_numerics()

    def apply(self, v: Variant):
        self.reset()
        if v.kind == "clock_cap":
            self._smi("-lgc", f"{int(v.value)},{int(v.value)}")
        elif v.kind == "power_cap":
            self._smi("-pl", int(round(float(v.value) * self.default_pl_w)))
        elif v.kind == "kernel":
            self._set_blas(v.value)

    # ---- work -----------------------------------------------------------------------------------------------
    def _dtype(self, v: Variant):
        t = self.torch
        t.backends.cuda.matmul.allow_tf32 = False
        if v.kind != "precision":
            return t.bfloat16
        if v.value == "tf32":
            t.backends.cuda.matmul.allow_tf32 = True
            return t.float32
        if v.value in ("fp16", "fp32"):
            return t.float16 if v.value == "fp16" else t.float32
        raise Unavailable(f"precision {v.value!r} is not supported by this rig")

    def _activations(self, pattern, dt):
        """The activation operand of an operand variant; the weight operand stays Gaussian."""
        t, n, dev = self.torch, self.dim, self.dev
        if pattern == "zeros":
            return t.zeros(n, n, device=dev, dtype=dt)
        if pattern == "sparse90":
            return t.randn(n, n, device=dev, dtype=dt) * (t.rand(n, n, device=dev) < 0.1).to(dt)
        if pattern == "lowent":
            return t.randint(-1, 2, (n, n), device=dev).to(dt)
        raise Unavailable(f"operand pattern {pattern!r} is not supported by this rig")

    def _lowp_mm(self, kind):
        """The matmul for an int8 or fp8 variant, or Unavailable if this torch has none."""
        t = self.torch
        if kind == "int8":
            if not hasattr(t, "_int_mm"):
                raise Unavailable("precision 'int8': this torch has no _int_mm")
            return lambda a, b: t._int_mm(a, b)
        if not (hasattr(t, "_scaled_mm") and hasattr(t, "float8_e4m3fn")):
            raise Unavailable("precision 'fp8': this torch has no _scaled_mm or float8_e4m3fn")
        one = t.ones((), device=self.dev, dtype=t.float32)

        def mm(a, b):
            r = t._scaled_mm(a, b, scale_a=one, scale_b=one, out_dtype=t.bfloat16)
            return r[0] if isinstance(r, tuple) else r          # older torch returned (out, amax)
        return mm

    def _to_lowp(self, kind, x, scale=1.0, colmajor=False):
        t = self.torch
        if kind == "int8":
            return (x / scale).round().clamp(-127, 127).to(t.int8)
        y = (x / scale).to(t.float8_e4m3fn)
        return y.t().contiguous().t() if colmajor else y           # _scaled_mm wants its second operand column-major

    def _run_lowp(self, kind, fn):
        try:
            out = fn()
            self._sync()
            return out
        except Unavailable:
            raise
        except Exception as e:                       # unsupported GPU (fp8 needs sm89+), shape rules, API changes
            raise Unavailable(f"precision {kind!r}: {type(e).__name__}: {e}")

    def _tensors(self, v: Variant):
        t, n = self.torch, self.dim
        self._mm = None
        if v.kind == "precision" and v.value in LOWP:
            mm = self._lowp_mm(v.value)

            def make():
                if v.value == "int8":
                    A = t.randint(-128, 128, (n, n), device=self.dev, dtype=t.int8)
                    B = t.randint(-128, 128, (n, n), device=self.dev, dtype=t.int8)
                else:
                    A = self._to_lowp("fp8", t.randn(n, n, device=self.dev, dtype=t.float32))
                    B = self._to_lowp("fp8", t.randn(n, n, device=self.dev, dtype=t.float32), colmajor=True)
                mm(A, B)                                   # fails here, not mid-window, if the device cannot run it
                return A, B
            A, B = self._run_lowp(v.value, make)
            self._mm = mm
        else:
            dt = self._dtype(v)
            A = self._activations(v.value, dt) if v.kind == "operand" else t.randn(n, n, device=self.dev, dtype=dt)
            B = t.randn(n, n, device=self.dev, dtype=dt)
        return A, B, t.zeros(self.mem, device=self.dev, dtype=t.float16)

    def _unit(self, A, B, big):
        (self._mm or self.torch.matmul)(A, B)
        self._sync()
        big.mul_(1.0001)
        self._sync()

    def _rel_err(self, v: Variant) -> float:
        key = (v.kind, v.value) if v.kind in ("precision", "kernel") else "base"
        if key not in self._err:
            t = self.torch
            t.manual_seed(0)
            a = t.randn(1024, 1024, device=self.dev, dtype=t.float32)
            b = t.randn(1024, 1024, device=self.dev, dtype=t.float32)
            truth = a.double() @ b.double()
            if v.kind == "precision" and v.value in LOWP:
                mm = self._lowp_mm(v.value)
                if v.value == "int8":                      # symmetric per-tensor quantisation
                    sa, sb = float(a.abs().max()) / 127.0, float(b.abs().max()) / 127.0
                    c = self._run_lowp("int8", lambda: mm(self._to_lowp("int8", a, sa),
                                                          self._to_lowp("int8", b, sb))).double() * (sa * sb)
                else:
                    c = self._run_lowp("fp8", lambda: mm(self._to_lowp("fp8", a),
                                                         self._to_lowp("fp8", b, colmajor=True))).double()
            else:
                dt = self._dtype(v)
                c = (a.to(dt) @ b.to(dt)).double()
            self._err[key] = float(t.linalg.norm(c - truth) / t.linalg.norm(truth))
        return self._err[key]

    def prepare(self, ref: Variant):
        self.apply(ref)
        A, B, big = self._tensors(ref)
        end = self.time() + self.WARMUP_S
        while self.time() < end:                      # warm up: clocks, caches, allocator
            self._unit(A, B, big)
        n, t0 = 0, self.time()
        while self.time() - t0 < self.CALIB_S:
            self._unit(A, B, big)
            n += 1
        self.t_unit_ref = (self.time() - t0) / n

    def measure(self, v: Variant, level: float) -> dict:
        if self.t_unit_ref is None:
            raise RuntimeError("call prepare(reference) first")
        self.apply(v)
        A, B, big = self._tensors(v)
        n_slot = int(level * self.SLOT_S / self.t_unit_ref)
        slots = max(1, int(self.T / self.SLOT_S))

        def window(k):
            over, busy_total = 0, 0.0
            for _ in range(k):
                s0 = self.time()
                for _ in range(n_slot):
                    self._unit(A, B, big)
                busy = self.time() - s0
                busy_total += busy
                if busy < self.SLOT_S:
                    self.sleep(self.SLOT_S - busy)
                else:
                    over += 1
            return over, busy_total

        window(max(1, int(self.SETTLE_S / self.SLOT_S)))   # settle clocks and temperature at this duty cycle
        e0, t0 = self.reader.energy_j(), self.time()
        over, busy_total = window(slots)
        e1, t1 = self.reader.energy_j(), self.time()
        return {"energy_j": e1 - e0, "time_s": t1 - t0, "units": slots * n_slot, "flop": slots * n_slot * 2 * self.dim ** 3,
                "level": level, "busy_frac": busy_total / (slots * self.SLOT_S), "feasible": over <= self.OVERRUN_TOL * slots,
                "sm_mhz": float(self.reader.sm_clock_mhz()), "rel_err": self._rel_err(v)}

    def info(self) -> dict:
        d = {"rig": "TorchRig", "gpu": self.gpu, "device": self.dev, "control": self.control, "dim": self.dim,
             "window_s": self.T, "default_power_limit_w": self.default_pl_w, "t_unit_ref_s": self.t_unit_ref}
        try:
            d["device"] = self.reader.info()
            d["torch"] = self.torch.__version__
        except Exception:
            pass
        return d
