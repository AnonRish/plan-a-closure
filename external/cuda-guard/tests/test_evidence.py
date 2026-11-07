"""tests/test_evidence.py -- Phase 1 evidence-model tests."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
from cuda_guard.evidence import (
    EvidenceRecord, EvidenceClass, EvidenceSource, EvidenceStatus, TrustRoot,
    EpistemicClass, UNSUPPORTED_CLAIMS,
)


def test_success_maps_to_evidence_of_success():
    r = EvidenceRecord(EvidenceClass.HARDWARE_ATTESTATION, EvidenceSource.NRAS_LOCAL_VERIFIER,
                        EvidenceStatus.SUCCESS, TrustRoot.NVIDIA_SIGNING_INFRASTRUCTURE,
                        establishes=["firmware genuine"], does_not_establish=["location"])
    assert r.epistemic_class == EpistemicClass.EVIDENCE_OF_SUCCESS


def test_unavailable_is_absence_not_failure():
    """The specific distinction spec Sec. 2 calls out by name: UNAVAILABLE
    must never be classified as EVIDENCE_OF_FAILURE."""
    r = EvidenceRecord(EvidenceClass.HARDWARE_ATTESTATION, EvidenceSource.NRAS_LOCAL_VERIFIER,
                        EvidenceStatus.UNAVAILABLE, TrustRoot.NVIDIA_SIGNING_INFRASTRUCTURE,
                        establishes=[], does_not_establish=["anything -- no hardware"])
    assert r.epistemic_class == EpistemicClass.ABSENCE_OF_EVIDENCE


def test_failed_is_evidence_of_failure_not_absence():
    r = EvidenceRecord(EvidenceClass.HARDWARE_ATTESTATION, EvidenceSource.NRAS_LOCAL_VERIFIER,
                        EvidenceStatus.FAILED, TrustRoot.NVIDIA_SIGNING_INFRASTRUCTURE,
                        establishes=["attestation was attempted and rejected"], does_not_establish=[])
    assert r.epistemic_class == EpistemicClass.EVIDENCE_OF_FAILURE


def test_simulated_is_absence_of_evidence():
    """A SIMULATED status must never read as EVIDENCE_OF_SUCCESS -- this is
    the load-bearing check for 'never fabricate evidence' (spec Sec. 3)."""
    r = EvidenceRecord(EvidenceClass.HARDWARE_ATTESTATION, EvidenceSource.MANUAL_TEST_FIXTURE,
                        EvidenceStatus.SIMULATED, TrustRoot.LOCAL_DEVELOPMENT_FIXTURE,
                        establishes=[], does_not_establish=["anything -- this is a dev mock"])
    assert r.epistemic_class == EpistemicClass.ABSENCE_OF_EVIDENCE
    assert r.is_simulated is True


def test_to_dict_json_round_trips():
    r = EvidenceRecord(EvidenceClass.DEVICE_IDENTITY, EvidenceSource.NVML, EvidenceStatus.SUCCESS,
                        TrustRoot.GOVERNED_PROCESS_SELF, establishes=["a"], does_not_establish=["b"])
    parsed = json.loads(json.dumps(r.to_dict()))
    assert parsed["status"] == "SUCCESS"
    assert parsed["epistemic_class"] == "EVIDENCE_OF_SUCCESS"


def test_content_hash_changes_with_content():
    r = EvidenceRecord(EvidenceClass.DEVICE_IDENTITY, EvidenceSource.NVML, EvidenceStatus.SUCCESS,
                        TrustRoot.GOVERNED_PROCESS_SELF, establishes=[], does_not_establish=[])
    h1 = r.content_hash()
    r.detail["x"] = 1
    assert r.content_hash() != h1


def test_unsupported_claims_registry_nonempty():
    assert len(UNSUPPORTED_CLAIMS) >= 10
    assert all(c.claim and c.why_wrong and c.correct_framing for c in UNSUPPORTED_CLAIMS)
