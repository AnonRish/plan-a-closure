"""Full local flow: mock attestation -> evidence -> policy -> verify ->
signed receipt -> INDEPENDENT offline signature verification.

'Independent' means: the final check uses only the verifier's raw public
key and the receipt bytes, calling verify_receipt() directly rather than
going back through the API. That's the property a receipt is supposed to
have -- see docs/receipt-specification.md.
"""
import uuid

from fastapi.testclient import TestClient

from frontier_verify.api.main import app, get_demo_verifier_public_key, key_provider
from frontier_verify.attestations.mock_provider import MockAttestationProvider
from frontier_verify.evidence.models import Evidence, ModelIdentity, RuntimeIdentity
from frontier_verify.policies.models import Policy
from frontier_verify.receipts.models import Receipt
from frontier_verify.receipts.signing import verify_receipt

client = TestClient(app)


def _submit_and_verify(auth_headers, model_digest="sha256:" + "cd" * 32):
    hw = MockAttestationProvider().get_platform_evidence()
    evidence = Evidence(
        evidence_id=str(uuid.uuid4()),
        model_identity=ModelIdentity(model_digest=model_digest),
        runtime_identity=RuntimeIdentity(serving_engine="pytest-demo"),
        hardware_evidence=hw,
    )
    r = client.post("/v1/evidence", json=evidence.model_dump(mode="json"), headers=auth_headers)
    assert r.status_code == 200

    policy = Policy(policy_id="demo-" + evidence.evidence_id, version="0.1.0", allow_mock_hardware=True)
    r = client.post("/v1/policies/validate", json=policy.model_dump(mode="json"), headers=auth_headers)
    assert r.status_code == 200

    r = client.post(
        "/v1/inferences/verify",
        json={"evidence_id": evidence.evidence_id, "policy_id": policy.policy_id},
        headers=auth_headers,
    )
    assert r.status_code == 200
    return r.json()


def test_end_to_end_flow_and_independent_receipt_verification(auth_headers):
    body = _submit_and_verify(auth_headers)
    assert body["passed"] is True
    assert body["assurance_level_achieved"] == "L1"
    assert body["receipt"] is not None

    receipt = Receipt.model_validate(body["receipt"])

    # Independent, offline check -- does not go through the API.
    assert verify_receipt(receipt, get_demo_verifier_public_key()) is True

    # And through the API's own convenience endpoint (unauthenticated by
    # design -- see docs/receipt-specification.md).
    r = client.post("/v1/receipts/verify", json={"receipt": receipt.model_dump(mode="json")})
    assert r.status_code == 200
    assert r.json()["signature_valid"] is True


def test_verification_result_is_retrievable_by_id(auth_headers):
    evidence_id_marker = str(uuid.uuid4())
    hw = MockAttestationProvider().get_platform_evidence()
    evidence = Evidence(
        evidence_id=evidence_id_marker,
        model_identity=ModelIdentity(model_digest="d"),
        runtime_identity=RuntimeIdentity(serving_engine="e"),
        hardware_evidence=hw,
    )
    client.post("/v1/evidence", json=evidence.model_dump(mode="json"), headers=auth_headers).raise_for_status()
    policy = Policy(policy_id="retr-" + evidence.evidence_id, version="0.1.0", allow_mock_hardware=True)
    client.post("/v1/policies/validate", json=policy.model_dump(mode="json"), headers=auth_headers).raise_for_status()

    r = client.post(
        "/v1/inferences/verify",
        json={"evidence_id": evidence.evidence_id, "policy_id": policy.policy_id},
        headers=auth_headers,
    )
    verification_id = r.json()["verification_id"]

    r2 = client.get(f"/v1/verifications/{verification_id}", headers=auth_headers)
    assert r2.status_code == 200
    assert r2.json()["receipt"] is not None

    # Same lookup without credentials must fail, not silently succeed.
    r3 = client.get(f"/v1/verifications/{verification_id}")
    assert r3.status_code == 401


def test_receipt_survives_key_rotation(auth_headers):
    """The whole point of key-id-based lookup (Phase 2's fix to Phase 1's
    hardcoded single key) is that OLD receipts stay verifiable after the
    verifier rotates to a new key. This test would fail under Phase 1's
    design, where /v1/receipts/verify defaulted to 'whatever key is
    current' instead of looking up the receipt's own verifier_key_id."""
    body_before_rotation = _submit_and_verify(auth_headers, model_digest="pre-rotation-model")
    old_receipt = Receipt.model_validate(body_before_rotation["receipt"])
    old_key_id = old_receipt.verifier_key_id

    r = client.post("/v1/verifier/rotate-key", headers=auth_headers)
    assert r.status_code == 200
    new_key_id = r.json()["key_id"]
    assert new_key_id != old_key_id

    # New verifications now use the new key.
    body_after_rotation = _submit_and_verify(auth_headers, model_digest="post-rotation-model")
    new_receipt = Receipt.model_validate(body_after_rotation["receipt"])
    assert new_receipt.verifier_key_id == new_key_id

    # Both the OLD and NEW receipts still verify, each against the API's
    # own key lookup by verifier_key_id -- no explicit key needed from the
    # caller for either.
    r_old = client.post("/v1/receipts/verify", json={"receipt": old_receipt.model_dump(mode="json")})
    r_new = client.post("/v1/receipts/verify", json={"receipt": new_receipt.model_dump(mode="json")})
    assert r_old.json()["signature_valid"] is True
    assert r_new.json()["signature_valid"] is True

    # And directly against key_provider, bypassing the API entirely.
    assert verify_receipt(old_receipt, key_provider.get_public_key(old_key_id)) is True
    assert verify_receipt(new_receipt, key_provider.get_public_key(new_key_id)) is True


def test_revoked_key_receipt_stays_cryptographically_valid_but_becomes_untrusted(auth_headers):
    """Phase 3's central semantic addition, made concrete: revoking a key
    does NOT retroactively change whether a receipt it signed was
    genuinely signed (signature_valid / VALID_AT_ISSUANCE never changes --
    it's a mathematical fact about the past). It DOES change whether that
    receipt should be trusted TODAY (currently_trusted /
    CURRENTLY_TRUSTED). These must diverge after revocation, or the
    distinction docs/protocol/key-management.md describes isn't real."""
    body = _submit_and_verify(auth_headers, model_digest="pre-revocation-model")
    receipt = Receipt.model_validate(body["receipt"])
    key_id = receipt.verifier_key_id

    # Before revocation: both true.
    r_before = client.post("/v1/receipts/verify", json={"receipt": receipt.model_dump(mode="json")})
    assert r_before.json()["signature_valid"] is True
    assert r_before.json()["currently_trusted"] is True
    assert r_before.json()["key_status"] == "ACTIVE"

    r_revoke = client.post(
        "/v1/verifier/revoke-key",
        json={"key_id": key_id, "reason": "test: simulated compromise"},
        headers=auth_headers,
    )
    assert r_revoke.status_code == 200

    # After revocation: signature_valid is STILL True (nothing about the
    # cryptographic fact changed) -- but currently_trusted flips to False.
    r_after = client.post("/v1/receipts/verify", json={"receipt": receipt.model_dump(mode="json")})
    assert r_after.json()["signature_valid"] is True
    assert r_after.json()["currently_trusted"] is False
    assert r_after.json()["key_status"] == "REVOKED"

    # And the revoked key can no longer be used to sign anything new --
    # rotating (without which submitting new evidence would be signed
    # with a known-compromised key) is required, and confirmed to work.
    r_verify_fails_to_issue = client.post(
        "/v1/inferences/verify",
        json={"evidence_id": "nonexistent-for-this-test", "policy_id": "nonexistent"},
        headers=auth_headers,
    )
    assert r_verify_fails_to_issue.status_code == 404  # unrelated 404, not the revocation issue --
    # the REAL check that the revoked key can't sign is at the KeyProvider
    # level, already covered by tests/unit/test_key_revocation.py; this
    # just confirms the API path doesn't crash around a revoked key either.

    r_rotate = client.post("/v1/verifier/rotate-key", headers=auth_headers)
    assert r_rotate.status_code == 200
    new_key_id = r_rotate.json()["key_id"]
    assert new_key_id != key_id

    body_after_recovery = _submit_and_verify(auth_headers, model_digest="post-recovery-model")
    recovered_receipt = Receipt.model_validate(body_after_recovery["receipt"])
    assert recovered_receipt.verifier_key_id == new_key_id
    r_recovered = client.post("/v1/receipts/verify", json={"receipt": recovered_receipt.model_dump(mode="json")})
    assert r_recovered.json()["currently_trusted"] is True
