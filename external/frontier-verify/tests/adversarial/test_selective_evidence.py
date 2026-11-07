"""These do NOT prove the system is secure against a sophisticated dishonest
prover -- see docs/threat-model.md, question A. They prove the specific,
narrow claims in each test name: unknown evidence is rejected, no receipt
is ever issued for evidence the policy says fails, and resubmitting an
evidence_id with different content is rejected rather than silently
accepted (see docs/adversarial-results.md, attack #6)."""
import uuid

from fastapi.testclient import TestClient

from frontier_verify.api.main import app
from frontier_verify.attestations.mock_provider import MockAttestationProvider
from frontier_verify.evidence.models import Evidence, ModelIdentity, RuntimeIdentity
from frontier_verify.policies.models import Policy

client = TestClient(app)


def test_protected_endpoint_without_api_key_is_rejected():
    r = client.post(
        "/v1/inferences/verify",
        json={"evidence_id": "does-not-exist", "policy_id": "also-does-not-exist"},
    )
    assert r.status_code == 401


def test_verification_of_unknown_evidence_id_returns_404(auth_headers):
    r = client.post(
        "/v1/inferences/verify",
        json={"evidence_id": "does-not-exist", "policy_id": "also-does-not-exist"},
        headers=auth_headers,
    )
    assert r.status_code == 404


def test_no_receipt_issued_when_policy_rejects_evidence(auth_headers):
    hw = MockAttestationProvider().get_platform_evidence()
    evidence = Evidence(
        evidence_id=str(uuid.uuid4()),
        model_identity=ModelIdentity(model_digest="d"),
        runtime_identity=RuntimeIdentity(serving_engine="e"),
        hardware_evidence=hw,
    )
    client.post("/v1/evidence", json=evidence.model_dump(mode="json"), headers=auth_headers).raise_for_status()

    strict_policy = Policy(
        policy_id="strict-" + evidence.evidence_id,
        version="0.1.0",
        allow_mock_hardware=False,  # the point of this test
    )
    client.post(
        "/v1/policies/validate", json=strict_policy.model_dump(mode="json"), headers=auth_headers
    ).raise_for_status()

    r = client.post(
        "/v1/inferences/verify",
        json={"evidence_id": evidence.evidence_id, "policy_id": strict_policy.policy_id},
        headers=auth_headers,
    )
    body = r.json()
    assert body["passed"] is False
    assert body["receipt"] is None


def test_evidence_id_resubmitted_with_different_content_is_rejected(auth_headers):
    evidence_id = str(uuid.uuid4())
    hw = MockAttestationProvider().get_platform_evidence()

    first = Evidence(
        evidence_id=evidence_id,
        model_identity=ModelIdentity(model_digest="original-model"),
        runtime_identity=RuntimeIdentity(serving_engine="e"),
        hardware_evidence=hw,
    )
    r1 = client.post("/v1/evidence", json=first.model_dump(mode="json"), headers=auth_headers)
    assert r1.status_code == 200

    conflicting = Evidence(
        evidence_id=evidence_id,  # SAME id
        model_identity=ModelIdentity(model_digest="swapped-in-model"),  # DIFFERENT content
        runtime_identity=RuntimeIdentity(serving_engine="e"),
        hardware_evidence=hw,
    )
    r2 = client.post("/v1/evidence", json=conflicting.model_dump(mode="json"), headers=auth_headers)
    assert r2.status_code == 409

    # And the original is still what's on record -- the conflicting write
    # did not partially apply.
    r3 = client.post(
        "/v1/evidence/verify", json={"evidence_id": evidence_id}, headers=auth_headers
    )
    assert r3.json()["digest"] == first.digest()


def test_identical_resubmission_of_same_evidence_id_is_idempotent(auth_headers):
    evidence_id = str(uuid.uuid4())
    hw = MockAttestationProvider().get_platform_evidence()
    evidence = Evidence(
        evidence_id=evidence_id,
        model_identity=ModelIdentity(model_digest="d"),
        runtime_identity=RuntimeIdentity(serving_engine="e"),
        hardware_evidence=hw,
    )
    r1 = client.post("/v1/evidence", json=evidence.model_dump(mode="json"), headers=auth_headers)
    r2 = client.post("/v1/evidence", json=evidence.model_dump(mode="json"), headers=auth_headers)
    assert r1.status_code == 200
    assert r2.status_code == 200  # same content, same id -- not a conflict


def test_recomputation_endpoints_are_honest_501_not_silent_success():
    # Deliberately unauthenticated: these are permanently-off endpoints
    # returning a fixed 501 regardless of who asks, so there's nothing
    # sensitive to gate.
    r = client.post("/v1/recomputation", json={})
    assert r.status_code == 501
    r = client.post("/v1/recomputation/check", json={})
    assert r.status_code == 501
