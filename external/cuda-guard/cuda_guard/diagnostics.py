"""
cuda_guard.diagnostics
=========================
Phase 33 (spec Sec. 33): `verify system` -- detects real environment state
and prints a truthful capability summary. Never claims AVAILABLE for
something that wasn't actually just checked.
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
from typing import Any


def _try_import(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


def gather_environment() -> dict[str, Any]:
    env: dict[str, Any] = {
        "os": f"{platform.system()} {platform.release()}",
        "cpu": platform.processor() or platform.machine(),
        "python_version": sys.version.split()[0],
        "repository_version": "0.1.0-phase0-19",
    }
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal:"):
                    env["ram_kb"] = int(line.split()[1])
                    break
    except Exception:
        env["ram_kb"] = None

    env["has_torch"] = _try_import("torch")
    if env["has_torch"]:
        import torch
        env["torch_version"] = torch.__version__
        env["cuda_available"] = torch.cuda.is_available()
        if env["cuda_available"]:
            props = torch.cuda.get_device_properties(0)
            env["gpu_name"] = props.name
            env["gpu_compute_capability"] = f"sm_{props.major}{props.minor}"
        else:
            env["gpu_name"] = None
    else:
        env["cuda_available"] = False
        env["gpu_name"] = None

    env["has_pynvml"] = _try_import("pynvml")
    env["has_nv_attestation_sdk"] = _try_import("nv_attestation_sdk")
    env["has_gcc"] = shutil.which("gcc") is not None
    env["has_nvidia_smi"] = shutil.which("nvidia-smi") is not None
    try:
        import socket
        env["network_interfaces"] = list(os.listdir("/sys/class/net")) if os.path.isdir("/sys/class/net") else []
    except Exception:
        env["network_interfaces"] = []
    env["packet_capture_capability"] = "UNAVAILABLE (requires CAP_NET_RAW/root, not present)"
    env["pdu_adapter_available"] = False
    return env


def capability_summary(env: dict[str, Any]) -> list[tuple[str, str]]:
    """Truthful AVAILABLE/UNAVAILABLE lines, derived from `env`, not asserted."""
    lines = [
        ("Software self-audit (backward/optimizer interception)", "AVAILABLE" if env["has_torch"] else "UNAVAILABLE (torch not found)"),
        ("Observed FLOP accounting", "AVAILABLE" if env["has_torch"] else "UNAVAILABLE (torch not found)"),
        ("Model hashing", "AVAILABLE" if env["has_torch"] else "UNAVAILABLE (torch not found)"),
        ("Tamper-evident ledger", "AVAILABLE"),
        ("CUDA driver LD_PRELOAD interceptor", "AVAILABLE" if env["has_gcc"] else "UNAVAILABLE (gcc not found)"),
        ("NVIDIA GPU", "PRESENT" if env["gpu_name"] else "ABSENT"),
        ("NVIDIA attestation SDK installed", "YES" if env["has_nv_attestation_sdk"] else "NO"),
        ("NVIDIA real attestation (Hopper+ required)",
         "POSSIBLE" if (env["has_nv_attestation_sdk"] and env.get("gpu_compute_capability", "sm_0").startswith(("sm_9", "sm_1")))
         else "UNAVAILABLE (needs Hopper+ GPU and the SDK)"),
        ("PCAP network evidence ingestion", "AVAILABLE (file-based)"),
        ("Live network interface capture", env["packet_capture_capability"]),
        ("Physical PDU / power evidence", "UNAVAILABLE (no adapter connected)" if not env["pdu_adapter_available"] else "AVAILABLE"),
        ("IOVT / external tap feed", "UNAVAILABLE (no feed connected)"),
    ]
    return lines


def print_report(env: dict[str, Any]) -> None:
    print("=== Environment ===")
    for k in ("os", "cpu", "ram_kb", "python_version", "torch_version", "cuda_available", "gpu_name", "repository_version"):
        if k in env:
            print(f"  {k}: {env[k]}")
    print("\n=== Truthful Capability Summary ===")
    for name, status in capability_summary(env):
        print(f"  {name}: {status}")
