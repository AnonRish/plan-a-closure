"""SDK-level test for the revocation-aware check_trust() method, driven
against a REAL running server (background thread), not an ASGI transport
shortcut -- httpx.ASGITransport only supports httpx.AsyncClient, and the
SDK deliberately uses a synchronous httpx.Client (see sdk/client.py), so
the transport-shortcut approach doesn't apply here. This is the same
real-server pattern already proven out manually in earlier phases.
"""
from __future__ import annotations

import threading
import time
import uuid

import pytest
import uvicorn

from frontier_verify.api.main import app
from frontier_verify.attestations.mock_provider import MockAttestationProvider
from frontier_verify.evidence.models import Evidence, ModelIdentity, RuntimeIdentity
from frontier_verify.policies.models import Policy
from frontier_verify.receipts.models import Receipt
from frontier_verify.sdk.client import VerifierClient

TEST_PORT = 8899


@pytest.fixture
def live_server():
    config = uvicorn.Config(app, host="127.0.0.1", port=TEST_PORT, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.monotonic() + 5.0
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.05)
    assert server.started, "uvicorn server did not start in time"

    yield f"http://127.0.0.1:{TEST_PORT}"

    server.should_exit = True
    thread.join(timeout=5.0)


def test_check_trust_reports_full_status_and_flips_after_revocation(live_server, auth_headers):
    sdk_client = VerifierClient(endpoint=live_server)
    sdk_client._http.headers.update(auth_headers)

    hw = MockAttestationProvider().get_platform_evidence()
    evidence = Evidence(
        evidence_id=str(uuid.uuid4()),
        model_identity=ModelIdentity(model_digest="sdk-trust-test"),
        runtime_identity=RuntimeIdentity(serving_engine="e"),
        hardware_evidence=hw,
    )
    sdk_client.submit_evidence(evidence)
    policy = Policy(policy_id="sdk-trust-" + evidence.evidence_id, version="0.1.0", allow_mock_hardware=True)
    sdk_client.validate_policy(policy)
    result = sdk_client.verify_inference(evidence.evidence_id, policy.policy_id)
    receipt = Receipt.model_validate(result["receipt"])

    trust_before = sdk_client.check_trust(receipt)
    assert trust_before["signature_valid"] is True
    assert trust_before["currently_trusted"] is True
    assert trust_before["key_status"] == "ACTIVE"

    r = sdk_client._http.post(
        "/v1/verifier/revoke-key",
        json={"key_id": receipt.verifier_key_id, "reason": "sdk test"},
    )
    r.raise_for_status()

    trust_after = sdk_client.check_trust(receipt)
    assert trust_after["signature_valid"] is True  # unchanged -- still genuinely signed
    assert trust_after["currently_trusted"] is False  # but no longer trusted
    assert trust_after["key_status"] == "REVOKED"

    sdk_client.close()
