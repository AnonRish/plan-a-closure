"""Simulated enrolled cluster. It validates the *estimators* (error rates, bounds, power curves),
NOT GPU physics: every physical claim is hardware-gated and decided on real hardware."""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

FEATURES = ["duration_s", "prefill_units", "decode_units", "steps"]
LEVELS = (0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0)


@dataclass
class SimConfig:
    n_gpu: int = 8
    p_idle_w: float = 120.0
    p_max_w: float = 700.0
    dt: float = 1.0
    prefill_j: float = 0.04
    decode_j: float = 0.25
    step_j: float = 0.54
    prefill_rate: float = 40000.0
    decode_rate: float = 10000.0
    step_rate: float = 1000.0
    noise_rel: float = 0.02
    idle_noise_w: float = 6.0
    drift_sd_w: float = 12.0
    drift_tau_s: float = 900.0
    meter_rel: float = 0.003
    busy_rel: float = 0.05
    busy_abs: float = 0.02

    @property
    def cap_w(self) -> float:
        return self.n_gpu * self.p_max_w

    @property
    def idle_cluster_w(self) -> float:
        return self.n_gpu * self.p_idle_w

    @property
    def dyn_max_w(self) -> float:
        return self.n_gpu * (self.p_max_w - self.p_idle_w)


@dataclass
class HiddenSpec:
    kind: str            # constant | idle_gap | duty | dilute | slack
    frac: float          # active hidden power / cluster cap (slack: fraction of verified dynamic energy)
    period_s: float = 20.0
    duty: float = 0.5

    def to_dict(self) -> dict:
        return {"kind": self.kind, "frac": self.frac, "period_s": self.period_s, "duty": self.duty}

    @staticmethod
    def from_dict(d):
        return None if d is None else HiddenSpec(d["kind"], float(d["frac"]),
                                                  float(d.get("period_s", 20.0)), float(d.get("duty", 0.5)))


def apply_hidden(cfg: SimConfig, spec, u, E, busy, dyn, t):
    n = len(u)
    if spec is None:
        return E, busy, np.zeros(n)
    if spec.kind in ("constant", "dilute"):
        active = np.ones(n, bool)
    elif spec.kind == "idle_gap":
        active = u < 0.2
    elif spec.kind == "duty":
        active = (t % spec.period_s) < spec.duty * spec.period_s
    elif spec.kind == "slack":
        # energy-neutral: efficiency gains are spent on hidden work, so observed energy is unchanged
        return E, busy, spec.frac * dyn
    else:
        raise ValueError(f"unknown hidden kind {spec.kind}")
    head = np.maximum(0.0, cfg.cap_w - E / cfg.dt)
    hw = np.where(active, np.minimum(spec.frac * cfg.cap_w, head), 0.0)
    hid = hw * cfg.dt
    return E + hid, busy + hid / cfg.dyn_max_w, hid


class SimSource:
    def __init__(self, cfg: SimConfig = None, seed: int = 0):
        self.cfg = cfg or SimConfig()
        self.rng = np.random.default_rng(seed)
        self.drift = self.cfg.drift_sd_w * self.rng.standard_normal()
        self.level, self.hold, self.clock = 0.5, 0, 0.0

    def _load(self, n):
        u = np.empty(n)
        i = 0
        while i < n:
            if self.hold <= 0:
                self.level = float(self.rng.choice(LEVELS))
                self.hold = int(self.rng.integers(30, 181))
            take = min(self.hold, n - i)
            u[i:i + take] = self.level
            self.hold -= take
            i += take
        return u

    def run_block(self, L: int, spec=None) -> dict:
        c, rng = self.cfg, self.rng
        u = self._load(L)
        a = math.exp(-c.dt / c.drift_tau_s)
        eps = rng.standard_normal(L) * c.drift_sd_w * math.sqrt(1 - a * a)
        d = np.empty(L)
        prev = self.drift
        for k in range(L):
            prev = a * prev + eps[k]
            d[k] = prev
        self.drift = prev
        pre = rng.poisson(c.prefill_rate * u * c.dt).astype(float)
        dec = rng.poisson(c.decode_rate * u * c.dt).astype(float)
        stp = rng.poisson(c.step_rate * u * c.dt).astype(float)
        X = np.column_stack([np.full(L, c.dt), pre, dec, stp])
        dyn = (pre * c.prefill_j + dec * c.decode_j + stp * c.step_j) * (1 + c.noise_rel * rng.standard_normal(L))
        E = c.idle_cluster_w * c.dt + dyn + d * c.dt + c.idle_noise_w * c.dt * rng.standard_normal(L)
        E = E * (1 + c.meter_rel * rng.standard_normal(L))
        busy = np.clip(u * c.dt * (1 + c.busy_rel * rng.standard_normal(L))
                       + c.busy_abs * c.dt * rng.standard_normal(L), 0, None)
        t = self.clock + np.arange(L) * c.dt
        self.clock += L * c.dt
        clean_busy = busy
        E, busy, hid = apply_hidden(c, spec, u, E, busy, dyn, t)
        # ground truth for the analysis to be checked against, never an input to it: the load level, and the busy
        # seconds the hidden load added
        return {"X": X, "E": E, "busy": busy, "hidden_j": hid, "t0": t, "u": u, "level": u, "hidden_s": busy - clean_busy}
