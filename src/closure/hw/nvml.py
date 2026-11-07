from __future__ import annotations

import numpy as np


def _s(x):
    return x.decode() if isinstance(x, bytes) else str(x)


class NvmlReader:
    """Reads the *hardware energy counter* (no sampling aliasing), utilisation and power via NVML.
    NVML is reported by the prover's own driver stack: treat it as spoofable (see README, A6)."""

    def __init__(self, gpus=None):
        import pynvml as N
        N.nvmlInit()
        self.N = N
        n = N.nvmlDeviceGetCount()
        self.idx = list(range(n)) if gpus is None else list(gpus)
        self.h = [N.nvmlDeviceGetHandleByIndex(i) for i in self.idx]

    def energy_j(self) -> float:
        return sum(self.N.nvmlDeviceGetTotalEnergyConsumption(h) for h in self.h) / 1000.0

    def util(self) -> float:
        return float(np.mean([self.N.nvmlDeviceGetUtilizationRates(h).gpu for h in self.h])) / 100.0

    def power_w(self) -> float:
        return sum(self.N.nvmlDeviceGetPowerUsage(h) for h in self.h) / 1000.0

    def power_limit_w(self) -> float:
        return float(self.N.nvmlDeviceGetPowerManagementLimit(self.h[0])) / 1000.0

    def sm_clock_mhz(self) -> float:
        return float(np.median([self.N.nvmlDeviceGetClockInfo(h, self.N.NVML_CLOCK_SM) for h in self.h]))

    def supported_sm_clocks(self) -> list:
        """Graphics clocks the first GPU supports at its highest memory clock, high to low ([] if NVML cannot say)."""
        N, h = self.N, self.h[0]
        try:
            mem = max(N.nvmlDeviceGetSupportedMemoryClocks(h))
            return sorted({int(c) for c in N.nvmlDeviceGetSupportedGraphicsClocks(h, mem)}, reverse=True)
        except Exception:
            return []

    def power_limit_range_w(self):
        """(min, max) settable power limit of the first GPU in watts, or None."""
        try:
            lo, hi = self.N.nvmlDeviceGetPowerManagementLimitConstraints(self.h[0])
            return float(lo) / 1000.0, float(hi) / 1000.0
        except Exception:
            return None

    def info(self) -> dict:
        N = self.N
        return {"driver": _s(N.nvmlSystemGetDriverVersion()),
                "gpus": [{"index": i, "name": _s(N.nvmlDeviceGetName(h)),
                          "power_limit_w": N.nvmlDeviceGetPowerManagementLimit(h) / 1000.0,
                          "sm_clock_mhz": N.nvmlDeviceGetClockInfo(h, N.NVML_CLOCK_SM),
                          "temp_c": N.nvmlDeviceGetTemperature(h, N.NVML_TEMPERATURE_GPU)}
                         for i, h in zip(self.idx, self.h)]}

    def close(self):
        self.N.nvmlShutdown()
