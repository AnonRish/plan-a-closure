"""tests/test_verdict.py -- Phase 2/16/28."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from cuda_guard.ledger import TamperEvidentLedger
from cuda_guard.verdict import VerdictEngine, VerdictStatus
from cuda_guard.evidence import EvidenceLayer

L1_OK = {"status": "SUCCESS", "evidence_class": "SOFTWARE_SELF_AUDIT", "trust_root": "GOVERNED_PROCESS_SELF"}
L2_OK = {"status": "SUCCESS", "evidence_class": "HARDWARE_ATTESTATION", "trust_root": "NVIDIA_SIGNING_INFRASTRUCTURE"}
L2_FAILED = {"status": "FAILED", "evidence_class": "HARDWARE_ATTESTATION", "trust_root": "NVIDIA_SIGNING_INFRASTRUCTURE"}
L3_OK = {"status": "SUCCESS", "evidence_class": "REGISTRY_AUTHORIZATION", "trust_root": "REGISTRY_OPERATOR"}


def test_no_evidence():
    v = VerdictEngine(TamperEvidentLedger()).assess({}, {})
    assert v.overall_status == VerdictStatus.NO_EVIDENCE


def test_never_reduces_to_pass_fail():
    v = VerdictEngine(TamperEvidentLedger()).assess({}, {EvidenceLayer.L1_SELF_AUDIT: [L1_OK]})
    assert v.overall_status.value not in ("PASS", "FAIL")


def test_single_layer_is_limited_not_supported():
    v = VerdictEngine(TamperEvidentLedger()).assess({}, {EvidenceLayer.L1_SELF_AUDIT: [L1_OK]})
    assert v.overall_status == VerdictStatus.SUPPORTED_WITH_LIMITATIONS


def test_three_independent_layers_supported():
    v = VerdictEngine(TamperEvidentLedger()).assess({}, {
        EvidenceLayer.L1_SELF_AUDIT: [L1_OK], EvidenceLayer.L2_HARDWARE_ROOTED_TRUST: [L2_OK],
        EvidenceLayer.L3_VERIFIER_AUTHORIZATION: [L3_OK]})
    assert v.overall_status == VerdictStatus.VERIFICATION_SUPPORTED


def test_failed_attestation_not_absorbed_by_other_layers():
    v = VerdictEngine(TamperEvidentLedger()).assess({}, {
        EvidenceLayer.L1_SELF_AUDIT: [L1_OK], EvidenceLayer.L2_HARDWARE_ROOTED_TRUST: [L2_FAILED],
        EvidenceLayer.L3_VERIFIER_AUTHORIZATION: [L3_OK]})
    assert v.overall_status == VerdictStatus.HARDWARE_ATTESTATION_FAILED


def test_tampered_ledger_produces_evidence_conflict():
    ledger = TamperEvidentLedger()
    ledger.record("event_a", {"x": 1})
    ledger._records[0].payload["x"] = 999
    v = VerdictEngine(ledger).assess({}, {EvidenceLayer.L1_SELF_AUDIT: [L1_OK]})
    assert v.overall_status == VerdictStatus.EVIDENCE_CONFLICT


def test_unsupported_claims_always_present():
    v = VerdictEngine(TamperEvidentLedger()).assess({}, {})
    assert len(v.unsupported_claims) >= 10
