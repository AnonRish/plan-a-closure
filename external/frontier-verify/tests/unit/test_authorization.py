"""Confirms role-based authorization actually RESTRICTS access, not just
that it exists. Every test here uses a deliberately narrow, single-role
key -- if any of these pass when they shouldn't, the authorization model
is decorative, exactly what section 8 of the Phase 3 brief warns against.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from frontier_verify.api.auth import AuthConfigError, parse_api_keys
from frontier_verify.api.main import app
from frontier_verify.attestations.mock_provider import MockAttestationProvider
from frontier_verify.evidence.models import Evidence, ModelIdentity, RuntimeIdentity
from frontier_verify.policies.models import Policy

client = TestClient(app)

PROVER_KEY = "test-prover-only-key"
POLICY_AUTHORITY_KEY = "test-policy-authority-only-key"
ADMINISTRATOR_KEY = "test-administrator-only-key"
AUDITOR_KEY = "test-auditor-only-key"

NARROW_KEYS = (
    f"{PROVER_KEY}:PROVER,"
    f"{POLICY_AUTHORITY_KEY}:POLICY_AUTHORITY,"
    f"{ADMINISTRATOR_KEY}:ADMINISTRATOR,"
    f"{AUDITOR_KEY}:AUDITOR"
)


@pytest.fixture
def narrow_roles(monkeypatch):
    """Temporarily swap FV_API_KEYS for a set of deliberately single-role
    keys, restoring the shared multi-role test key afterward so other
    test files (which assume TEST_API_KEY has every role) aren't
    affected."""
    from tests.conftest import TEST_API_KEY

    monkeypatch.setenv("FV_API_KEYS", NARROW_KEYS + f",{TEST_API_KEY}:PROVER|POLICY_AUTHORITY|ADMINISTRATOR|AUDITOR")
    yield


def _h(key: str) -> dict[str, str]:
    return {"X-Api-Key": key}


def test_prover_can_submit_evidence(narrow_roles):
    hw = MockAttestationProvider().get_platform_evidence()
    ev = Evidence(
        evidence_id=str(uuid.uuid4()),
        model_identity=ModelIdentity(model_digest="d"),
        runtime_identity=RuntimeIdentity(serving_engine="e"),
        hardware_evidence=hw,
    )
    r = client.post("/v1/evidence", json=ev.model_dump(mode="json"), headers=_h(PROVER_KEY))
    assert r.status_code == 200


def test_prover_cannot_define_a_policy(narrow_roles):
    """The one role separation that maps to an actual attack: a prover
    that could define its own policy could write one that always
    passes."""
    policy = Policy(policy_id="attempted-by-prover", version="0.1.0", allow_mock_hardware=True)
    r = client.post("/v1/policies/validate", json=policy.model_dump(mode="json"), headers=_h(PROVER_KEY))
    assert r.status_code == 403


def test_prover_cannot_rotate_keys(narrow_roles):
    r = client.post("/v1/verifier/rotate-key", headers=_h(PROVER_KEY))
    assert r.status_code == 403


def test_policy_authority_can_define_policy(narrow_roles):
    policy = Policy(policy_id="by-policy-authority-" + str(uuid.uuid4()), version="0.1.0")
    r = client.post("/v1/policies/validate", json=policy.model_dump(mode="json"), headers=_h(POLICY_AUTHORITY_KEY))
    assert r.status_code == 200


def test_policy_authority_cannot_submit_evidence(narrow_roles):
    hw = MockAttestationProvider().get_platform_evidence()
    ev = Evidence(
        evidence_id=str(uuid.uuid4()),
        model_identity=ModelIdentity(model_digest="d"),
        runtime_identity=RuntimeIdentity(serving_engine="e"),
        hardware_evidence=hw,
    )
    r = client.post("/v1/evidence", json=ev.model_dump(mode="json"), headers=_h(POLICY_AUTHORITY_KEY))
    assert r.status_code == 403


def test_policy_authority_cannot_rotate_or_revoke_keys(narrow_roles):
    r = client.post("/v1/verifier/rotate-key", headers=_h(POLICY_AUTHORITY_KEY))
    assert r.status_code == 403
    r = client.post(
        "/v1/verifier/revoke-key",
        json={"key_id": "whatever", "reason": "test"},
        headers=_h(POLICY_AUTHORITY_KEY),
    )
    assert r.status_code == 403


def test_administrator_can_rotate_keys(narrow_roles):
    r = client.post("/v1/verifier/rotate-key", headers=_h(ADMINISTRATOR_KEY))
    assert r.status_code == 200


def test_administrator_cannot_submit_evidence_or_define_policy(narrow_roles):
    hw = MockAttestationProvider().get_platform_evidence()
    ev = Evidence(
        evidence_id=str(uuid.uuid4()),
        model_identity=ModelIdentity(model_digest="d"),
        runtime_identity=RuntimeIdentity(serving_engine="e"),
        hardware_evidence=hw,
    )
    assert client.post("/v1/evidence", json=ev.model_dump(mode="json"), headers=_h(ADMINISTRATOR_KEY)).status_code == 403
    policy = Policy(policy_id="attempted-by-admin", version="0.1.0")
    assert (
        client.post(
            "/v1/policies/validate", json=policy.model_dump(mode="json"), headers=_h(ADMINISTRATOR_KEY)
        ).status_code
        == 403
    )


def test_auditor_can_read_but_not_write(narrow_roles):
    r = client.get("/v1/verifier/keys/some-key/status", headers=_h(AUDITOR_KEY))
    assert r.status_code in (200, 404)  # key may not exist, but auth itself must not be what fails
    assert r.status_code != 403

    r = client.post("/v1/verifier/rotate-key", headers=_h(AUDITOR_KEY))
    assert r.status_code == 403

    hw = MockAttestationProvider().get_platform_evidence()
    ev = Evidence(
        evidence_id=str(uuid.uuid4()),
        model_identity=ModelIdentity(model_digest="d"),
        runtime_identity=RuntimeIdentity(serving_engine="e"),
        hardware_evidence=hw,
    )
    r = client.post("/v1/evidence", json=ev.model_dump(mode="json"), headers=_h(AUDITOR_KEY))
    assert r.status_code == 403


def test_valid_key_wrong_role_gets_403_not_401(narrow_roles):
    """A key that EXISTS but lacks the needed role is an authorization
    failure, not an authentication failure -- these are different facts
    and the status code must reflect which one occurred, or debugging a
    real misconfiguration becomes guesswork."""
    r = client.post("/v1/verifier/rotate-key", headers=_h(PROVER_KEY))
    assert r.status_code == 403  # NOT 401 -- the key is valid, just wrong role


def test_bare_key_with_no_role_suffix_is_rejected(monkeypatch):
    monkeypatch.setenv("FV_API_KEYS", "some-bare-key-no-role")
    with pytest.raises(AuthConfigError):
        parse_api_keys()

    r = client.post("/v1/verifier/rotate-key", headers=_h("some-bare-key-no-role"))
    assert r.status_code == 500  # loud failure, not silent full access


def test_unknown_role_name_in_config_is_rejected(monkeypatch):
    monkeypatch.setenv("FV_API_KEYS", "bad-key:SUPER_ADMIN_ROLE_THAT_DOES_NOT_EXIST")
    with pytest.raises(AuthConfigError):
        parse_api_keys()
