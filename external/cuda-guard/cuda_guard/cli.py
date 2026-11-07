"""
cuda_guard.cli
=================
Phase 34 (spec Sec. 34). Every command states whether evidence is REAL,
SIMULATED, UNAVAILABLE, FAILED, or UNVERIFIED in its own output -- not
buried in debug logs.
"""

from __future__ import annotations

import argparse
import json
import sys

from .capability_registry import readable_report, to_json, verify
from .diagnostics import capability_summary, gather_environment, print_report
from .external_evidence import ApplicationMemoryWiper
from .hardware import DeviceDiscovery, DeviceRegistry, ModelIdentity, run_attestation
from .ledger import TamperEvidentLedger


def _shared_ledger() -> TamperEvidentLedger:
    return TamperEvidentLedger()


def cmd_status(args) -> int:
    env = gather_environment()
    print_report(env)
    return 0


def cmd_hardware_inspect(args) -> int:
    ledger = _shared_ledger()
    disc = DeviceDiscovery()
    devices = disc.query()
    ev = disc.as_evidence(devices)
    print(f"evidence_status: {ev.status.value}")
    for d in devices:
        print(f"  {d.uuid}  {d.name}  cc={d.compute_capability}  emulated={d.is_emulated}")
    return 0


def cmd_attestation_run(args) -> int:
    ledger = _shared_ledger()
    env = gather_environment()
    cc_suspected = env.get("gpu_compute_capability", "sm_0").startswith(("sm_9", "sm_1"))
    ev = run_attestation(ledger, cc_capable_gpu_suspected=cc_suspected, device_uuid=None)
    print(f"evidence_status: {ev.status.value}")
    print(f"establishes: {ev.establishes}")
    print(f"does_not_establish: {ev.does_not_establish}")
    print(json.dumps(ev.detail, indent=2, default=str))
    return 0


def cmd_registry_check(args) -> int:
    reg = DeviceRegistry()
    result = reg.check(args.device_uuid)
    print(f"registry_label: {result.registry_label}")
    print(f"status: {result.status.value}")
    return 0


def cmd_model_hash(args) -> int:
    import torch
    ledger = _shared_ledger()
    mi = ModelIdentity(ledger)
    sd = torch.load(args.state_dict_path, map_location="cpu") if args.state_dict_path else None
    if sd is None:
        print("evidence_status: FAILED -- no --state-dict-path provided")
        return 1
    h = mi.hash_state_dict(sd)
    print(f"model_hash: {h}")
    return 0


def cmd_ledger_verify(args) -> int:
    ledger = _shared_ledger()
    result = ledger.verify_chain()
    print(f"evidence_status: {'REAL' if result.valid else 'FAILED'}")
    print(f"valid: {result.valid}  records_checked: {result.records_checked}")
    if not result.valid:
        print(f"break_at: {result.first_break_at}  reason: {result.break_reason}")
    return 0 if result.valid else 1


def cmd_capabilities_show(args) -> int:
    entries = verify()
    if args.json:
        print(to_json(entries))
    else:
        print(readable_report(entries))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cuda-guard", description="AI 2040 compute-verification CLI")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="environment self-diagnostics (spec Sec. 33)").set_defaults(func=cmd_status)
    sub.add_parser("hardware-inspect", help="real/emulated device discovery").set_defaults(func=cmd_hardware_inspect)
    sub.add_parser("attestation-run", help="attempt real NVIDIA attestation").set_defaults(func=cmd_attestation_run)

    reg_p = sub.add_parser("registry-check", help="check device against the LOCAL_DEMO_REGISTRY")
    reg_p.add_argument("device_uuid")
    reg_p.set_defaults(func=cmd_registry_check)

    hash_p = sub.add_parser("model-hash", help="compute SHA-256 identity of a saved state_dict")
    hash_p.add_argument("--state-dict-path", required=False)
    hash_p.set_defaults(func=cmd_model_hash)

    sub.add_parser("ledger-verify", help="verify the tamper-evident chain").set_defaults(func=cmd_ledger_verify)

    cap_p = sub.add_parser("capabilities-show", help="print the capability matrix")
    cap_p.add_argument("--json", action="store_true")
    cap_p.set_defaults(func=cmd_capabilities_show)

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
