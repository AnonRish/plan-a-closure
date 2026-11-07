"""End-to-end local demo: mock attestation -> evidence -> policy -> verify ->
signed receipt -> INDEPENDENT offline receipt verification -> tamper check
-> key rotation -> old receipt still verifiable.

"Independent" here specifically means: the final check uses only the
verifier's raw public key and the receipt bytes, calling verify_receipt()
directly rather than going back through the API. That is the property a
receipt is supposed to have; see docs/receipt-specification.md.

Run from the repo root after `pip install -e .`:
    python3 examples/local-demo/run_demo.py
"""
from __future__ import annotations

import os
import uuid

# This is a standalone process, not run under pytest, so it has no
# conftest.py setting FV_API_KEYS for it -- set it here, before importing
# the app, exactly like a real deployment would via its environment.
# Phase 3: FV_API_KEYS now requires a role suffix (see
# frontier_verify/api/auth.py) -- the demo grants itself every role so it
# can walk through the whole flow (prover actions, policy registration,
# key rotation/revocation as administrator) in one script, which a real
# deployment should NOT do; see docs/trust-model.md for why these should
# be separate credentials in practice.
os.environ.setdefault("FV_API_KEYS", "local-demo-key:PROVER|POLICY_AUTHORITY|ADMINISTRATOR|AUDITOR")
AUTH = {"X-Api-Key": "local-demo-key"}

from fastapi.testclient import TestClient

from frontier_verify.api.main import app, get_demo_verifier_public_key
from frontier_verify.attestations.mock_provider import MockAttestationProvider
from frontier_verify.evidence.models import Evidence, ModelIdentity, RuntimeIdentity
from frontier_verify.policies.models import Policy
from frontier_verify.receipts.models import Receipt
from frontier_verify.receipts.signing import verify_receipt


def main() -> None:
    client = TestClient(app)

    print("1. Producing MOCK hardware attestation (Phase 1/2 have no real GPU here)...")
    hw = MockAttestationProvider().get_platform_evidence()
    print(f"   provider={hw.provider_name} mock={hw.mock} maturity={hw.maturity}")

    print("2. Building and submitting an evidence bundle...")
    evidence = Evidence(
        evidence_id=str(uuid.uuid4()),
        model_identity=ModelIdentity(model_digest="sha256:" + "ab" * 32),
        runtime_identity=RuntimeIdentity(serving_engine="demo-engine"),
        hardware_evidence=hw,
    )
    r = client.post("/v1/evidence", json=evidence.model_dump(mode="json"), headers=AUTH)
    r.raise_for_status()
    print(f"   evidence_id={r.json()['evidence_id']}")

    print("3. Registering a policy that allows mock hardware (demo only)...")
    policy = Policy(policy_id="demo-policy", version="0.1.0", allow_mock_hardware=True)
    client.post("/v1/policies/validate", json=policy.model_dump(mode="json"), headers=AUTH).raise_for_status()

    print("4. Requesting verification...")
    r = client.post(
        "/v1/inferences/verify",
        json={"evidence_id": evidence.evidence_id, "policy_id": policy.policy_id},
        headers=AUTH,
    )
    r.raise_for_status()
    result = r.json()
    print(f"   passed={result['passed']} assurance={result['assurance_level_achieved']}")
    for reason in result["reasons"]:
        print(f"     - {reason}")

    receipt = Receipt.model_validate(result["receipt"])
    old_key_id = receipt.verifier_key_id

    print("5. Independently verifying the receipt signature OFFLINE, using only")
    print("   the verifier's public key (NOT trusting the server that issued it)...")
    ok = verify_receipt(receipt, get_demo_verifier_public_key())
    print(f"   signature_valid={ok}")

    print("6. Tampering with the receipt and re-checking (this must fail)...")
    tampered = receipt.model_copy(update={"result": False})
    ok_tampered = verify_receipt(tampered, get_demo_verifier_public_key())
    print(f"   signature_valid after tampering={ok_tampered} (expected False)")

    print("7. Rotating the verifier's signing key...")
    r = client.post("/v1/verifier/rotate-key", headers=AUTH)
    r.raise_for_status()
    new_key_id = r.json()["key_id"]
    print(f"   old_key_id={old_key_id}")
    print(f"   new_key_id={new_key_id}")

    print("8. Confirming the OLD receipt (signed before rotation) still verifies,")
    print("   looked up by ITS OWN verifier_key_id, not 'whatever's current'...")
    r = client.post("/v1/receipts/verify", json={"receipt": receipt.model_dump(mode="json")})
    still_valid = r.json()["signature_valid"]
    print(f"   signature_valid={still_valid}")

    assert ok is True
    assert ok_tampered is False
    assert still_valid is True
    assert new_key_id != old_key_id

    print("\nDemo complete. This proves receipt tamper-evidence and rotation")
    print("safety, nothing about hardware truthfulness. See")
    print("docs/ai2040-coverage-matrix.md for what's covered vs deferred.")


if __name__ == "__main__":
    main()
