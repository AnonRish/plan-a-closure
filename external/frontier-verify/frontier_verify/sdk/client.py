"""VerifierClient: a thin HTTP client for the Frontier Verify verifier API.

Matches the usage shape from the source specification (section 16):

    from frontier_verify import VerifierClient
    client = VerifierClient(endpoint="https://verifier.example.com")
    ...

MATURITY: EXPERIMENTAL. Covers the Phase 1 endpoint surface only -- see
docs/api-design.md. No retries, no auth, no idempotency keys yet; those are
explicitly deferred, not silently missing (see docs/protocol-roadmap.md).
"""
from __future__ import annotations

import httpx

from frontier_verify.evidence.models import Evidence, HardwareEvidence
from frontier_verify.policies.models import Policy
from frontier_verify.receipts.models import Receipt
from frontier_verify.receipts.signing import public_key_from_hex, verify_receipt


class VerifierClient:
    def __init__(self, endpoint: str, policy: str | None = None, timeout: float = 10.0):
        self.endpoint = endpoint.rstrip("/")
        self.policy = policy
        self._http = httpx.Client(base_url=self.endpoint, timeout=timeout)

    def attest(self, evidence: HardwareEvidence) -> dict:
        r = self._http.post("/v1/attestations", json=evidence.model_dump(mode="json"))
        r.raise_for_status()
        return r.json()

    def submit_evidence(self, evidence: Evidence) -> dict:
        r = self._http.post("/v1/evidence", json=evidence.model_dump(mode="json"))
        r.raise_for_status()
        return r.json()

    def validate_policy(self, policy: Policy) -> dict:
        r = self._http.post("/v1/policies/validate", json=policy.model_dump(mode="json"))
        r.raise_for_status()
        return r.json()

    def verify_inference(self, evidence_id: str, policy_id: str) -> dict:
        r = self._http.post(
            "/v1/inferences/verify",
            json={"evidence_id": evidence_id, "policy_id": policy_id},
        )
        r.raise_for_status()
        return r.json()

    def get_receipt(self, verification_id: str) -> Receipt | None:
        r = self._http.get(f"/v1/verifications/{verification_id}")
        r.raise_for_status()
        data = r.json()
        if not data.get("receipt"):
            return None
        return Receipt.model_validate(data["receipt"])

    def verify_receipt(self, receipt: Receipt, verifier_public_key_hex: str | None = None) -> bool:
        """If a public key is supplied, this verifies the signature
        LOCALLY -- no network call at all. That's the actual point of a
        receipt (see docs/receipt-specification.md). If no key is supplied,
        this falls back to asking the server's /v1/receipts/verify endpoint,
        which is weaker: you are trusting the server to tell the truth
        about its own receipt.

        Returns only signature_valid (VALID_AT_ISSUANCE) -- a receipt
        signed by a key that has since been REVOKED still returns True
        here. This is deliberate, not an oversight: the offline path
        (verifier_public_key_hex supplied) has no way to know about
        revocation by construction -- it's a pure crypto check, nothing
        more, same as tools/standalone-verifier/. Use check_trust() when
        you need revocation-awareness, which requires the online path and
        therefore reintroduces trust in the server -- see
        docs/protocol/key-management.md."""
        if verifier_public_key_hex:
            pk = public_key_from_hex(verifier_public_key_hex)
            return verify_receipt(receipt, pk)
        r = self._http.post(
            "/v1/receipts/verify",
            json={"receipt": receipt.model_dump(mode="json")},
        )
        r.raise_for_status()
        return r.json()["signature_valid"]

    def check_trust(self, receipt: Receipt) -> dict:
        """Revocation-aware check -- ALWAYS calls the server (there is no
        offline equivalent; see verify_receipt()'s docstring for why).
        Returns {signature_valid, key_status, currently_trusted}.
        `currently_trusted` is what a real decision should gate on, not
        signature_valid alone -- see docs/protocol/key-management.md."""
        r = self._http.post(
            "/v1/receipts/verify",
            json={"receipt": receipt.model_dump(mode="json")},
        )
        r.raise_for_status()
        return r.json()

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> VerifierClient:
        return self

    def __exit__(self, *exc) -> None:
        self.close()
