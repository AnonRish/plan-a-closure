"""A fake NVML (the `pynvml` module of nvidia-ml-py) for rehearsing the hardware code path on CPU. Not a model of a GPU.

Put this folder first on PYTHONPATH and nvidia_smi.py on PATH as `nvidia-smi` (tests/test_hw_rehearsal.py does both).
The two share the JSON file named by FAKEGPU_STATE: per GPU, the locked SM clock and the power limit. The energy counter
integrates a power that follows this process's CPU use, so it tracks the work torch does on CPU.

Environment: FAKEGPU_STATE (required), FAKEGPU_COUNT (GPUs, default 2), FAKEGPU_OTHER_PROCS=1 (report a process on
every GPU).
"""
import json
import os
import time

NVML_CLOCK_SM = 1
NVML_TEMPERATURE_GPU = 0
F_MAX = 1980
CLOCKS = list(range(1980, 344, -15))
# FAKEGPU_LIMITS_W="default,min,max" and FAKEGPU_POWER_W="idle,dynamic" model a smaller GPU (a T4: "70,60,70", "30,45")
DEFAULT_W, MIN_W, MAX_W = (float(x) for x in os.environ.get("FAKEGPU_LIMITS_W", "700,200,700").split(","))
P_IDLE, P_DYN = (float(x) for x in os.environ.get("FAKEGPU_POWER_W", "90,450").split(","))


class NVMLError(Exception):
    pass


def _count() -> int:
    return int(os.environ.get("FAKEGPU_COUNT", "2"))


def uuid_of(i: int) -> str:
    return f"GPU-fa4e0000-0000-4000-8000-{i:012d}"


def _state() -> dict:
    p = os.environ.get("FAKEGPU_STATE")
    if p and os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _gpu(i: int) -> dict:
    g = _state().get(str(i), {})
    return {"clock": g.get("clock"), "limit_w": float(g.get("limit_w", DEFAULT_W))}


class _Handle:
    def __init__(self, i):
        self.i = i

    def __repr__(self):
        return f"<fake GPU {self.i}>"


class _Pci:
    def __init__(self, i):
        self.domain, self.bus, self.device = 0, 0x18 + i, 0
        self.busId = f"00000000:{self.bus:02X}:00.0"


class _Util:
    def __init__(self, g):
        self.gpu, self.memory = g, g // 2


_acc = {}                                    # per GPU: (last wall time, last process CPU time, energy mJ)


def _advance(i: int) -> float:
    """Advance GPU i's energy counter to now; return the power over the step (W)."""
    now_w, now_c = time.time(), time.process_time()
    last = _acc.get(i)
    if last is None:
        _acc[i] = (now_w, now_c, now_w * 1000.0 * P_IDLE)          # an arbitrary start, as on a real counter
        return P_IDLE
    w0, c0, e = last
    dw = max(now_w - w0, 1e-9)
    busy = min(1.0, max(0.0, (now_c - c0) / (dw * (os.cpu_count() or 1))))
    g = _gpu(i)
    f = (g["clock"] or F_MAX) / F_MAX
    p = min(P_IDLE * (0.8 + 0.2 * f) + P_DYN * busy * f * f, g["limit_w"])
    _acc[i] = (now_w, now_c, e + p * dw * 1000.0)
    return p


def nvmlInit():
    if not os.environ.get("FAKEGPU_STATE"):
        raise NVMLError("fake NVML: FAKEGPU_STATE is not set")


def nvmlShutdown():
    pass


def nvmlSystemGetDriverVersion():
    return "999.99 (fake)"


def nvmlDeviceGetCount():
    return _count()


def nvmlDeviceGetHandleByIndex(i):
    i = int(i)
    if not 0 <= i < _count():
        raise NVMLError("Invalid Argument")
    return _Handle(i)


def nvmlDeviceGetUUID(h):
    return uuid_of(h.i)


def nvmlDeviceGetPciInfo(h):
    return _Pci(h.i)


def nvmlDeviceGetName(h):
    return "Fake H100 (rehearsal)"


def nvmlDeviceGetTemperature(h, sensor):
    return 40


def nvmlDeviceGetMigMode(h):
    return (0, 0)


def nvmlDeviceGetPersistenceMode(h):
    return 1


def nvmlDeviceGetComputeRunningProcesses(h):
    return [object()] if os.environ.get("FAKEGPU_OTHER_PROCS") == "1" else []


def nvmlDeviceGetSupportedMemoryClocks(h):
    return [2619, 1593]


def nvmlDeviceGetSupportedGraphicsClocks(h, mem):
    return list(CLOCKS)


def nvmlDeviceGetPowerManagementLimitConstraints(h):
    return (int(MIN_W * 1000), int(MAX_W * 1000))


def nvmlDeviceGetPowerManagementDefaultLimit(h):
    return int(DEFAULT_W * 1000)


def nvmlDeviceGetPowerManagementLimit(h):
    return int(_gpu(h.i)["limit_w"] * 1000)


def nvmlDeviceGetClockInfo(h, kind):
    return int(_gpu(h.i)["clock"] or F_MAX)


def nvmlDeviceGetTotalEnergyConsumption(h):
    _advance(h.i)
    return int(_acc[h.i][2])


def nvmlDeviceGetPowerUsage(h):
    return int(_advance(h.i) * 1000)


def nvmlDeviceGetUtilizationRates(h):
    p = _advance(h.i)
    return _Util(int(round(100 * max(0.0, min(1.0, (p - P_IDLE) / P_DYN)))))
