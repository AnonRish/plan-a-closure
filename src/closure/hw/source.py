from __future__ import annotations

import time

import numpy as np

from ..sim import LEVELS, SimConfig


class FakeHardware:
    """Virtual-clock stand-in for NVML + workload. Exercises the orchestration end to end; it says
    nothing about physics. Acts as reader (energy_j/util), load (set_state/pop_units) and clock."""

    def __init__(self, cfg: SimConfig = None, seed: int = 0):
        self.cfg, self.rng = cfg or SimConfig(), np.random.default_rng(seed)
        self.t, self.E, self.level, self.hid_w, self.drift = 1_700_000_000.0, 0.0, 0.0, 0.0, 0.0
        self.units, self.hid_s = np.zeros(3), 0.0

    def now(self):
        return self.t

    def _shares(self):
        """(verified level actually run, hidden busy share): hidden work takes the time it takes, and when the two do
        not fit in the second the verified work is what gives way, as on the real GPUs (docs/DEVIATIONS.md section 5)."""
        hb = min(1.0, self.hid_w / self.cfg.dyn_max_w)
        return min(self.level, 1.0 - hb), hb

    SENSOR_FULL = 0.95                  # what the utilisation counter reads when the GPU never rests; under 1, so its
                                        # noise is not clipped away at the top (a real counter reads about 0.99)

    def sleep(self, s):
        c, r = self.cfg, self.rng
        level, hb = self._shares()
        pre, dec, stp = (c.prefill_rate * level * s, c.decode_rate * level * s, c.step_rate * level * s)
        a = np.exp(-s / c.drift_tau_s)
        self.drift = a * self.drift + c.drift_sd_w * np.sqrt(1 - a * a) * r.standard_normal()
        dyn = (pre * c.prefill_j + dec * c.decode_j + stp * c.step_j) * (1 + c.noise_rel * r.standard_normal())
        e = c.idle_cluster_w * s + dyn + self.drift * s + self.hid_w * s
        self.E += max(0.0, e) * (1 + c.meter_rel * r.standard_normal())
        self.units += np.array([pre, dec, stp]) * (1 + 0.01 * r.standard_normal())
        self.hid_s += self.SENSOR_FULL * hb * s          # in the counter's own units, like the busy channel
        self.t += s

    def energy_j(self):
        return self.E

    def util(self):
        level, hb = self._shares()
        # relative noise: an idle GPU reads exactly 0, as a real counter does, so nothing is clipped away at either end
        return float(np.clip(self.SENSOR_FULL * (level + hb) * (1 + self.cfg.busy_abs * self.rng.standard_normal()), 0, 1))

    def set_state(self, level, hidden_frac=0.0, spec=None):
        self.level, self.hid_w = float(level), hidden_frac * self.cfg.cap_w

    def pop_units(self):
        u, self.units = self.units.copy(), np.zeros(3)
        return float(u[0]), float(u[1]), float(u[2])

    def pop_hidden_s(self):
        h, self.hid_s = self.hid_s, 0.0
        return float(h)


class HwSource:
    """Runs verified + hidden load on real (or fake) hardware and reports per-window evidence."""

    def __init__(self, reader, load, dt: float = 1.0, sub: float = 0.1, n_gpu: int = 8,
                 p_max_w: float = 700.0, seed: int = 0, time_fn=time.time, sleep_fn=time.sleep):
        self.reader, self.load, self.dt, self.sub = reader, load, dt, sub
        self.n_gpu, self.p_max, self.rng = n_gpu, p_max_w, np.random.default_rng(seed)
        self.time, self.sleep = time_fn, sleep_fn
        self.level, self.hold, self.wcount = 0.5, 0, 0
        self.force_level = None          # set by hw-selftest to hold a fixed load level

    def _active(self, spec, level, k):
        if spec is None:
            return False
        if spec.kind in ("constant", "dilute"):
            return True
        if spec.kind == "idle_gap":
            return level < 0.2
        if spec.kind == "duty":
            return ((k * self.dt) % spec.period_s) < spec.duty * spec.period_s
        raise NotImplementedError(f"hidden class '{spec.kind}' cannot be run on hardware "
                                  "(use the efficiency-slack probe instead)")

    def run_block(self, L: int, spec=None) -> dict:
        X, E, busy, hid, t0 = np.zeros((L, 4)), np.zeros(L), np.zeros(L), np.zeros(L), np.zeros(L)
        lev, hs, counts_hidden = np.zeros(L), np.zeros(L), hasattr(self.load, "pop_hidden_s")
        cap = self.n_gpu * self.p_max
        for w in range(L):
            if self.force_level is not None:
                level = self.force_level
            else:
                if self.hold <= 0:
                    self.level, self.hold = float(self.rng.choice(LEVELS)), int(self.rng.integers(30, 181))
                self.hold -= 1
                level = self.level
            self.wcount += 1
            hf = spec.frac if (spec is not None and self._active(spec, level, self.wcount)) else 0.0
            self.load.set_state(level, hf, spec)
            ts, e0, utils = self.time(), self.reader.energy_j(), []
            while True:
                rem = ts + self.dt - self.time()
                if rem <= 1e-9:
                    break
                self.sleep(min(self.sub, rem))
                utils.append(self.reader.util())
            te, e1 = self.time(), self.reader.energy_j()
            pre, dec, stp = self.load.pop_units()
            dur = te - ts
            X[w] = [dur, pre, dec, stp]
            E[w], busy[w], hid[w], t0[w] = e1 - e0, float(np.mean(utils)) * dur, hf * cap * dur, ts
            lev[w] = level
            if counts_hidden:
                hs[w] = self.load.pop_hidden_s()
        out = {"X": X, "E": E, "busy": busy, "hidden_j": hid, "t0": t0, "level": lev}
        if counts_hidden:               # ground truth: the seconds the hidden load really ran, in the busy channel's
            out["hidden_s"] = hs        # units (a mean over the GPUs)
        return out
