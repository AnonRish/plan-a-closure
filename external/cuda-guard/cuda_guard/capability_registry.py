"""
cuda_guard.capability_registry
=================================
Phase 32 (spec Sec. 32). Each entry is declared once here, then
cross-checked against REAL introspection (can the module actually be
imported, does the named symbol actually exist) at generation time -- so a
capability whose implementation silently broke would show up as a
discrepancy rather than being trusted from the static declaration alone.
"""

from __future__ import annotations

import importlib
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class CapabilityEntry:
    capability: str
    implementation: str          # "module.ClassOrFunction"
    status: str                   # CapabilityStatus value
    evidence_strength: str
    hardware_requirement: str
    trust_root: str
    independence: str
    bypassability: str
    known_limitations: list[str]
    test_coverage: str
    import_verified: Optional[bool] = None   # filled in by verify()


REGISTRY: list[CapabilityEntry] = [
    CapabilityEntry("Typed evidence model", "cuda_guard.evidence.EvidenceRecord", "REAL_AND_TESTABLE",
                     "N/A (foundational)", "none", "N/A", "N/A", "N/A -- not an observation mechanism",
                     [], "tests/test_evidence.py"),
    CapabilityEntry("Tamper-evident audit ledger", "cuda_guard.ledger.TamperEvidentLedger", "REAL_AND_TESTABLE",
                     "STRONG for retained-history tampering", "none", "N/A (self-referential)", "partial",
                     "detects modification/deletion/insertion/reordering; does not survive wholesale replacement",
                     ["No external anchor -- see LIMITATIONS.md"], "tests/test_ledger.py (9 tamper/replay scenarios)"),
    CapabilityEntry("Backward/optimizer-step interception", "cuda_guard.self_audit.InferenceOnlyGovernor",
                     "REAL_AND_TESTABLE", "WEAK alone (self-audit)", "none", "GOVERNED_PROCESS_SELF",
                     "none (governed party controls it)", "high -- see bypass test results",
                     ["torch.autograd.grad() is a real, currently-unhooked entry point",
                      "full restoration of both patched surfaces is an undetected bypass"],
                     "tests/test_self_audit_bypass.py (7 real bypass scenarios)"),
    CapabilityEntry("NCCL size-threshold auditor", "cuda_guard.self_audit.NCCLAuditor", "REAL_AND_TESTABLE",
                     "WEAK (heuristic)", "none", "GOVERNED_PROCESS_SELF", "none", "high -- size/pattern only",
                     ["cannot distinguish authorized vs. unauthorized traffic by content"], "existing prototype tests"),
    CapabilityEntry("Observed FLOP ledger", "cuda_guard.self_audit.ObservedFlopLedger", "REAL_AND_TESTABLE",
                     "WEAK (lower bound only)", "none", "GOVERNED_PROCESS_SELF", "none", "moderate",
                     ["only F.linear/torch.matmul hooked -- other ops invisible"], "verified against hand-computed FLOPs"),
    CapabilityEntry("LD_PRELOAD driver interceptor", "cuda_guard.driver_interceptor.DriverInterceptor",
                     "REAL_AND_TESTABLE", "MODERATE (proven mechanism)", "gcc required", "GOVERNED_PROCESS_SELF",
                     "none", "high -- no-preload/static-link bypasses both demonstrated",
                     ["scoped to processes launched WITH LD_PRELOAD set"], "real subprocess+harness tests"),
    CapabilityEntry("Device discovery (NVML)", "cuda_guard.hardware.DeviceDiscovery", "REAL_BUT_HARDWARE_DEPENDENT",
                     "STRONG when real NVML present", "NVIDIA driver + pynvml", "GOVERNED_PROCESS_SELF",
                     "N/A (inventory only)", "N/A", ["emulated fallback when no driver present"], "tests/test_hardware.py"),
    CapabilityEntry("Real NVIDIA attestation (NRAS/local verifier)", "cuda_guard.hardware.NRASAttestationAdapter",
                     "REAL_BUT_HARDWARE_DEPENDENT", "STRONG when hardware present", "Hopper+ CC-enabled GPU",
                     "NVIDIA_SIGNING_INFRASTRUCTURE", "vendor-rooted, not independent", "N/A (cryptographic)",
                     ["proves firmware integrity only, never workload/location/authorization",
                      "Python SDK flagged deprecated by NVIDIA, migration path unverified here"],
                     "tests/test_hardware.py (skip-path verified fast; real-hardware path untestable here)"),
    CapabilityEntry("Device authorization registry", "cuda_guard.hardware.DeviceRegistry", "SIMULATED_FOR_DEVELOPMENT",
                     "WEAK (LOCAL_DEMO_REGISTRY)", "none", "REGISTRY_OPERATOR", "depends on operator",
                     "trivial -- entries are locally editable", ["not a real signed remote registry"],
                     "tests/test_hardware.py"),
    CapabilityEntry("Attestation+authorization composition", "cuda_guard.hardware.compose_device_authorization",
                     "REAL_AND_TESTABLE", "depends on inputs", "none", "N/A (logic only)", "N/A", "N/A",
                     [], "tests/test_hardware.py (4 branches)"),
    CapabilityEntry("Model identity (SHA-256 hash)", "cuda_guard.hardware.ModelIdentity", "REAL_AND_TESTABLE",
                     "MODERATE (point-in-time only)", "none", "GOVERNED_PROCESS_SELF", "none",
                     "trivial after a verified checkpoint -- see ModelContinuity",
                     ["proves identity at measurement time only, not continuously"],
                     "7-case matrix, tests/test_hardware.py"),
    CapabilityEntry("Model-state continuity", "cuda_guard.hardware.ModelContinuity", "REAL_AND_TESTABLE",
                     "WEAK (checkpoint instants only)", "none", "GOVERNED_PROCESS_SELF", "none",
                     "undetected between checkpoints", ["not continuous -- explicit checkpoint calls only"],
                     "exercised in integration test"),
    CapabilityEntry("PCAP network evidence", "cuda_guard.network_evidence.PcapEvidenceSource", "REAL_AND_TESTABLE",
                     "MODERATE (replayed, not live)", "none", "GOVERNED_PROCESS_SELF (file source)", "N/A",
                     "moderate", ["REPLAYED_NETWORK_EVIDENCE only -- not live capture"],
                     "tests/test_network_evidence.py, validated against system file(1)"),
    CapabilityEntry("Live network interface capture", "cuda_guard.network_evidence.LiveInterfaceSource",
                     "REAL_BUT_HARDWARE_DEPENDENT", "N/A (not exercised)", "CAP_NET_RAW/root", "GOVERNED_PROCESS_SELF",
                     "N/A", "N/A", ["not testable in this sandboxed environment"], "interface only, not exercised"),
    CapabilityEntry("External tap feed (IOVT-class)", "cuda_guard.network_evidence.ExternalTapFeedSource",
                     "REAL_BUT_HARDWARE_DEPENDENT", "N/A", "physical tap hardware", "INDEPENDENT_EXTERNAL_VERIFIER",
                     "independent by design", "N/A", ["no such feed exists in this environment"], "interface only"),
    CapabilityEntry("Deterministic-mode reproducibility check", "cuda_guard.reproducibility.check_reproducibility",
                     "REAL_AND_TESTABLE", "MODERATE (one model/input/seed at a time)", "none",
                     "GOVERNED_PROCESS_SELF", "none", "N/A", ["not a universal determinism guarantee"],
                     "verified deterministic AND correctly flags injected nondeterminism"),
    CapabilityEntry("Sampled recomputation verifier", "cuda_guard.reproducibility.RecomputationVerifier",
                     "PROTOTYPE_RESEARCH", "WEAK-MODERATE, sample-size-dependent", "none", "GOVERNED_PROCESS_SELF",
                     "none", "N/A", ["toy-model scale only; not demonstrated on frontier-model-scale workloads"],
                     "verified detects deliberately-corrupted captured output"),
    CapabilityEntry("External power/PDU evidence ingestion", "cuda_guard.external_evidence.ingest_external_evidence",
                     "SIMULATED_FOR_DEVELOPMENT", "N/A until real feed connected", "physical PDU/meter",
                     "INDEPENDENT_PHYSICAL_INFRASTRUCTURE", "independent by design", "N/A",
                     ["no real PDU connected in this environment -- interface only"], "tested with a manual fixture"),
    CapabilityEntry("Power-FLOP plausibility correlation", "cuda_guard.external_evidence.correlate_power_with_compute",
                     "REAL_AND_TESTABLE", "WEAK (coarse plausibility only)", "none", "N/A (logic)", "N/A", "N/A",
                     ["never infers exact FLOPs from watts"], "unit-tested"),
    CapabilityEntry("Application memory wipe", "cuda_guard.external_evidence.ApplicationMemoryWiper",
                     "REAL_AND_TESTABLE", "MODERATE (application buffer only)", "none", "GOVERNED_PROCESS_SELF",
                     "none", "N/A", ["never proves physical VRAM erasure"], "verified: non-zero->wipe->re-read-zero"),
    CapabilityEntry("Hardware-backed erasure proof", "cuda_guard.external_evidence.HardwareBackedErasureAdapter",
                     "NOT_IMPLEMENTED", "N/A", "unknown -- no confirmed public API", "NVIDIA_SIGNING_INFRASTRUCTURE",
                     "N/A", "N/A", ["no NVIDIA API for this confirmed to exist"], "interface only, not exercised"),
    CapabilityEntry("Governance verdict engine", "cuda_guard.verdict.VerdictEngine", "REAL_AND_TESTABLE",
                     "depends entirely on input evidence", "none", "N/A (aggregation logic)", "N/A", "N/A",
                     ["only as strong as the evidence layers actually fed into it"],
                     "tests/test_verdict.py (5 scenarios incl. tamper propagation)"),
    CapabilityEntry("GMMU read-only weight-page enforcement", "N/A", "NOT_TECHNICALLY_PROVABLE_BY_THIS_LAYER",
                     "N/A", "unconfirmed CUDA driver API", "would be NVIDIA_SIGNING_INFRASTRUCTURE", "N/A", "N/A",
                     ["no public CUDA API for arbitrary device-allocation write protection confirmed to exist"],
                     "not implemented -- research task, not a stub"),
    CapabilityEntry("PTX/SASS optimizer-kernel fingerprinting", "N/A", "PROTOTYPE_RESEARCH", "WEAK by design",
                     "none", "GOVERNED_PROCESS_SELF", "none", "high -- adversarially weak by construction",
                     ["evasion-cost-raising heuristic only, not a hard guarantee"], "not implemented this pass"),
]


def verify(registry: list[CapabilityEntry] = REGISTRY) -> list[CapabilityEntry]:
    """Cross-checks each entry's `implementation` string against real
    import machinery. A capability claiming REAL_AND_TESTABLE whose
    implementation string doesn't actually import is a genuine discrepancy,
    surfaced here rather than trusted from the static table alone."""
    for entry in registry:
        if entry.implementation == "N/A":
            entry.import_verified = None
            continue
        module_path, _, symbol = entry.implementation.rpartition(".")
        try:
            mod = importlib.import_module(module_path)
            entry.import_verified = hasattr(mod, symbol)
        except Exception:
            entry.import_verified = False
    return registry


def to_json(registry: list[CapabilityEntry] = REGISTRY) -> str:
    return json.dumps({
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "capabilities": [asdict(e) for e in registry],
    }, indent=2)


def readable_report(registry: list[CapabilityEntry] = REGISTRY) -> str:
    lines = ["# Capability Matrix", "", "Generated from cuda_guard.capability_registry, cross-checked against "
             "real import introspection (see `import_verified` per entry).", ""]
    by_status: dict[str, list[CapabilityEntry]] = {}
    for e in registry:
        by_status.setdefault(e.status, []).append(e)
    for status in ("REAL_AND_TESTABLE", "REAL_BUT_HARDWARE_DEPENDENT", "SIMULATED_FOR_DEVELOPMENT",
                   "PROTOTYPE_RESEARCH", "NOT_IMPLEMENTED", "NOT_TECHNICALLY_PROVABLE_BY_THIS_LAYER"):
        entries = by_status.get(status, [])
        if not entries:
            continue
        lines.append(f"## {status} ({len(entries)})")
        for e in entries:
            verified_tag = {"True": "\u2713 import-verified", "False": "\u2717 IMPORT FAILED",
                             "None": ""}[str(e.import_verified)]
            lines.append(f"- **{e.capability}** ({e.implementation}) {verified_tag}")
            lines.append(f"  - Evidence strength: {e.evidence_strength}; Trust root: {e.trust_root}")
            lines.append(f"  - Test coverage: {e.test_coverage}")
            if e.known_limitations:
                lines.append(f"  - Known limitations: {'; '.join(e.known_limitations)}")
        lines.append("")
    return "\n".join(lines)
