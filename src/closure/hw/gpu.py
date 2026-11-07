"""Which physical GPU a hardware command touches, and putting it back the way it was found.

`--gpu N` names the N-th GPU this process sees through CUDA, so CUDA_VISIBLE_DEVICES applies. NVML and nvidia-smi
ignore CUDA_VISIBLE_DEVICES and number GPUs in PCI order. On a scheduler that hands a job physical GPU 3 as "cuda:0",
using index 0 for NVML would read another GPU's energy counter, and `nvidia-smi -i 0` would lock another GPU's clocks.
So the GPU is resolved once, by UUID (or PCI address), and NVML and nvidia-smi are always given that identity.

Stopping: `install_stop_handlers` turns the first SIGTERM, SIGINT or SIGHUP into SystemExit, so `finally` blocks run
and clocks and power limits are restored (a Slurm time limit sends SIGTERM); later signals are ignored so they cannot
interrupt the restore. SIGKILL cannot be caught: `closure hw-restore --gpu N` puts clocks and the power limit back.

Rehearsal: with CLOSURE_REHEARSAL_CPU=1 and no CUDA device, a command runs the real hardware code on CPU torch against
whatever NVML and nvidia-smi it finds. The tests use it with a fake NVML library and a fake nvidia-smi
(tests/fakegpu/) to run `closure tier0 --confirm-hardware` end to end. Its outputs are labelled REHEARSAL and mean
nothing physically.
"""
from __future__ import annotations

import contextlib
import os
import re
import signal
import subprocess
import sys
from dataclasses import dataclass

REHEARSAL_ENV = "CLOSURE_REHEARSAL_CPU"
STOP_SIGNALS = tuple(getattr(signal, n) for n in ("SIGTERM", "SIGINT", "SIGHUP") if hasattr(signal, n))


@dataclass(frozen=True)
class GpuTarget:
    index: int                 # position among the GPUs CUDA shows this process
    torch_device: str          # "cuda:<index>", or "cpu" in a rehearsal
    nvml_index: int            # NVML's index of the same physical GPU (PCI order)
    uuid: str                  # NVML's UUID ("GPU-..."): what nvidia-smi -i is given
    how: str                   # how the two were matched
    rehearsal: bool = False

    def describe(self) -> str:
        return (f"{self.torch_device} = NVML index {self.nvml_index} ({self.uuid}), matched by {self.how}"
                + (" [REHEARSAL: CPU torch, no physical meaning]" if self.rehearsal else ""))


def rehearsal_requested(env=None) -> bool:
    return (env if env is not None else os.environ).get(REHEARSAL_ENV) == "1"


def prefer_pci_order(env=None) -> None:
    """Number CUDA devices in PCI order, as NVML and nvidia-smi do, unless the environment already chose an order.
    Must run before CUDA is initialised; it changes nothing when CUDA_VISIBLE_DEVICES holds UUIDs."""
    (env if env is not None else os.environ).setdefault("CUDA_DEVICE_ORDER", "PCI_BUS_ID")


def _text(x) -> str:
    return x.decode() if isinstance(x, bytes) else str(x)


def _hex(s) -> str:
    s = _text(s).strip().lower()
    for p in ("gpu-", "mig-"):
        if s.startswith(p):
            s = s[len(p):]
    return re.sub(r"[^0-9a-f]", "", s)


def nvml_devices(N) -> list:
    """Every GPU NVML lets this process open: index, UUID and PCI (domain, bus, device)."""
    out = []
    for k in range(int(N.nvmlDeviceGetCount())):
        try:
            h = N.nvmlDeviceGetHandleByIndex(k)
            uuid = _text(N.nvmlDeviceGetUUID(h))
        except Exception:                      # a GPU this process may not open (cgroups, permissions)
            continue
        try:
            p = N.nvmlDeviceGetPciInfo(h)
            pci = (int(p.domain), int(p.bus), int(p.device))
        except Exception:
            pci = None
        out.append({"index": k, "uuid": uuid, "pci": pci})
    return out


def _torch():
    try:
        import torch
        return torch
    except Exception:
        return None


def resolve(index: int = 0, N=None, torch=None, env=None) -> GpuTarget:
    """The physical GPU behind `--gpu index`, found in NVML by UUID or PCI address. Raises RuntimeError rather than guess."""
    env = env if env is not None else os.environ
    index = int(index)
    if N is None:
        import pynvml as N
        N.nvmlInit()
    devs = nvml_devices(N)
    if not devs:
        raise RuntimeError("NVML lists no GPU this process can open")
    torch = torch if torch is not None else _torch()
    cuda = bool(torch is not None and torch.cuda.is_available())
    if not cuda:
        if not rehearsal_requested(env):
            raise RuntimeError("torch sees no CUDA GPU (a CPU-only torch build, or no driver in this environment); "
                               "install a CUDA build of torch on the GPU node")
        hit = [d for d in devs if d["index"] == index]
        if not hit:
            raise RuntimeError(f"rehearsal: NVML has no GPU with index {index}")
        return GpuTarget(index, "cpu", index, hit[0]["uuid"], "index (rehearsal without CUDA)", True)
    count = int(torch.cuda.device_count())
    if not 0 <= index < count:
        raise RuntimeError(f"--gpu {index}: this process sees {count} GPU(s) through CUDA "
                           f"(CUDA_VISIBLE_DEVICES={env.get('CUDA_VISIBLE_DEVICES')!r})")
    props = torch.cuda.get_device_properties(index)
    uuid = getattr(props, "uuid", None)
    if uuid is not None and _hex(uuid):
        if "mig" in _text(uuid).lower():
            raise RuntimeError("this CUDA device is a MIG slice: the energy counter and clock control cover the whole GPU")
        hit = [d for d in devs if _hex(d["uuid"]) == _hex(uuid)]
        if hit:
            return GpuTarget(index, f"cuda:{index}", hit[0]["index"], hit[0]["uuid"], "uuid")
    pci = tuple(getattr(props, a, None) for a in ("pci_domain_id", "pci_bus_id", "pci_device_id"))
    if None not in pci:
        hit = [d for d in devs if d["pci"] == tuple(int(x) for x in pci)]
        if hit:
            return GpuTarget(index, f"cuda:{index}", hit[0]["index"], hit[0]["uuid"], "PCI address")
    if uuid is not None or None not in pci:
        raise RuntimeError(f"cuda:{index} is not among the GPUs NVML can open ({len(devs)} listed); refusing to guess")
    # an old torch that exposes neither: only safe when CUDA and NVML provably use the same numbering
    cvd = env.get("CUDA_VISIBLE_DEVICES")
    if cvd is None and env.get("CUDA_DEVICE_ORDER") == "PCI_BUS_ID":
        hit = [d for d in devs if d["index"] == index]
        if hit:
            return GpuTarget(index, f"cuda:{index}", index, hit[0]["uuid"], "PCI order (no CUDA_VISIBLE_DEVICES)")
    raise RuntimeError("this torch exposes neither device UUIDs nor PCI addresses, so cuda:N cannot be matched to an NVML "
                       "GPU safely; upgrade torch, or unset CUDA_VISIBLE_DEVICES and set CUDA_DEVICE_ORDER=PCI_BUS_ID")


def install_stop_handlers() -> None:
    """The first SIGTERM/SIGINT/SIGHUP raises SystemExit(128 + signal) so cleanup runs; later ones are ignored."""
    state = {"stopping": False}

    def handler(signum, frame):
        if state["stopping"]:
            return
        state["stopping"] = True
        print(f"\nreceived signal {signum}: stopping and restoring the GPU", file=sys.stderr, flush=True)
        raise SystemExit(128 + int(signum))

    for s in STOP_SIGNALS:
        try:
            signal.signal(s, handler)
        except (ValueError, OSError):           # not the main thread, or not allowed here
            pass


@contextlib.contextmanager
def signals_held():
    """Ignore stop signals while the device is being restored, so a second signal cannot abort the restore."""
    old = {}
    for s in STOP_SIGNALS:
        try:
            old[s] = signal.signal(s, signal.SIG_IGN)
        except (ValueError, OSError):
            pass
    try:
        yield
    finally:
        for s, h in old.items():
            try:
                signal.signal(s, h)
            except (ValueError, OSError):
                pass


def smi(gpu_id: str, *args, timeout: float = 60.0) -> tuple:
    """Run `nvidia-smi -i <gpu_id> args...`; (ok, message)."""
    try:
        r = subprocess.run(["nvidia-smi", "-i", str(gpu_id), *map(str, args)], capture_output=True, text=True,
                           timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, f"{type(e).__name__}: {e}"
    return r.returncode == 0, (r.stdout + r.stderr).strip()


def default_power_limit_w(N, nvml_index: int):
    try:
        h = N.nvmlDeviceGetHandleByIndex(int(nvml_index))
        return float(N.nvmlDeviceGetPowerManagementDefaultLimit(h)) / 1000.0
    except Exception:
        return None


def current_power_limit_w(N, nvml_index: int):
    try:
        h = N.nvmlDeviceGetHandleByIndex(int(nvml_index))
        return float(N.nvmlDeviceGetPowerManagementLimit(h)) / 1000.0
    except Exception:
        return None


def restore(target: GpuTarget, power_limit_w=None, N=None) -> list:
    """Unlock the SM clocks and set the power limit back (to power_limit_w, else the GPU's default). [(command, ok, msg)]"""
    if N is None:
        import pynvml as N
        N.nvmlInit()
    w = power_limit_w if power_limit_w is not None else default_power_limit_w(N, target.nvml_index)
    steps = [("-rgc",)] + ([("-pl", int(round(float(w))))] if w else [])
    out = []
    with signals_held():
        for args in steps:
            ok, msg = smi(target.uuid, *args)
            out.append(("nvidia-smi -i " + target.uuid + " " + " ".join(map(str, args)), ok, msg))
    return out
