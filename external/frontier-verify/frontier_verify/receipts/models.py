"""Signed verification receipts. See docs/receipt-specification.md.

A receipt is designed to be checked independently of the verifier that
issued it: anyone holding the verifier's public key can call
frontier_verify.receipts.signing.verify_receipt() directly, offline, with no
API call and no trust in the server that produced the receipt. That
property is only as good as the signature scheme and the key's provenance
-- see docs/receipt-specification.md for what Phase 1 does and does not
guarantee about the latter.
"""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class Receipt(BaseModel):
    receipt_version: str = "0.1.0"
    verification_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    verifier_key_id: str
    model_identity_digest: str
    runtime_identity_digest: str
    hardware_evidence_digest: str
    policy_id: str
    policy_version: str
    assurance_level: str
    result: bool
    limitations: list[str] = Field(default_factory=list)
    signature: str | None = None

    def unsigned_payload(self) -> dict:
        """The exact dict that gets canonicalized and signed/verified.
        Excludes `signature` itself -- used identically by sign_receipt and
        verify_receipt so both sides hash the same bytes."""
        return self.model_dump(exclude={"signature"}, mode="json")
