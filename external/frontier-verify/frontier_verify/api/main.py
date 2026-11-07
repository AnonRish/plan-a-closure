"""Frontier Verify verifier API.

Phase 2 changes from Phase 1: real API-key auth (auth.py) on mutating and
sensitive-read endpoints; a LocalFileKeyProvider instead of one hardcoded
in-memory keypair, so keys can rotate and OLD receipts stay verifiable
(receipts are looked up by their own verifier_key_id, not "whatever's
current"); evidence-id collision detection (409, not a silent overwrite).

See docs/api-design.md for the full endpoint table.
"""
from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from frontier_verify.api.auth import Role, require_role
from frontier_verify.api.store import EvidenceConflict, store
from frontier_verify.audit.log import AuditLog
from frontier_verify.evidence.models import Evidence, HardwareEvidence
from frontier_verify.keys.local_provider import LocalFileKeyProvider
from frontier_verify.keys.provider import KeyStatus
from frontier_verify.policies.evaluator import evaluate
from frontier_verify.api.recomputation import create_router as create_recomputation_router
from frontier_verify.policies.models import Policy
from frontier_verify.receipts.models import Receipt
from frontier_verify.receipts.signing import (
    public_key_from_hex,
    public_key_to_hex,
    sign_receipt,
    verify_receipt,
)

app = FastAPI(title="Frontier Verify API", version="0.2.0")


def _default_key_dir() -> Path:
    env = os.environ.get("FV_KEY_DIR")
    if env:
        return Path(env)
    return Path(tempfile.mkdtemp(prefix="frontier-verify-keys-"))


# Phase 2: a real KeyProvider, not one hardcoded keypair. Defaults to a
# fresh temp dir per process -- set FV_KEY_DIR for real persistence across
# restarts. See docs/protocol/key-management.md.
key_provider = LocalFileKeyProvider(_default_key_dir())

# Phase 4: real audit logging for administrative actions -- see
# frontier_verify/audit/log.py for why this exists.
audit_log = AuditLog()

# Experimental Track 2 software path. The legacy /v1/recomputation endpoints remain 501.
app.include_router(create_recomputation_router(store=store, key_provider=key_provider))


def get_demo_verifier_public_key():
    """Convenience for tests/examples: the CURRENT verifier public key.
    Not the mechanism a real relying party should rely on -- that's
    fetching by key_id via GET /v1/verifier/public-key/{key_id} or an
    out-of-band channel, precisely so a compromised/offline verifier can't
    just lie about its own current key. See
    docs/protocol/key-management.md."""
    key_id = key_provider.current_key_id()
    return key_provider.get_public_key(key_id)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    return {"status": "ready"}


@app.get("/v1/verifier/public-key")
def verifier_public_key():
    key_id = key_provider.current_key_id()
    return {"key_id": key_id, "public_key_hex": public_key_to_hex(key_provider.get_public_key(key_id))}


@app.get("/v1/verifier/public-key/{key_id}")
def verifier_public_key_by_id(key_id: str):
    """Fetch a SPECIFIC (possibly rotated-out) key -- needed to verify
    old receipts after rotation. See docs/protocol/key-management.md."""
    try:
        pk = key_provider.get_public_key(key_id)
    except KeyError:
        raise HTTPException(404, f"unknown key_id {key_id!r}")
    return {"key_id": key_id, "public_key_hex": public_key_to_hex(pk)}


@app.post("/v1/verifier/rotate-key")
def rotate_key(api_key: str = Depends(require_role(Role.ADMINISTRATOR))):
    new_key_id = key_provider.rotate()
    audit_log.record("rotate-key", actor_key_prefix=api_key, details={"new_key_id": new_key_id})
    return {"key_id": new_key_id, "public_key_hex": public_key_to_hex(key_provider.get_public_key(new_key_id))}


class RevokeKeyRequest(BaseModel):
    key_id: str
    reason: str


@app.post("/v1/verifier/revoke-key")
def revoke_key(req: RevokeKeyRequest, api_key: str = Depends(require_role(Role.ADMINISTRATOR))):
    """Revocation is distinct from rotation -- see
    docs/protocol/key-management.md. Revoking does NOT automatically
    rotate; if key_id is the current signing key, it is now unusable for
    NEW signatures (get_signing_key() refuses) until someone explicitly
    calls rotate-key too. That two-step requirement is deliberate: an
    automatic rotate-on-revoke would silently paper over the fact that a
    compromise just happened.

    Phase 4: now audit-logged, closing a gap found in this project's own
    self-critique (docs/reviews/external-review.md, finding #1) -- with
    multiple credentials able to hold ADMINISTRATOR, nothing previously
    recorded WHICH one revoked a given key."""
    try:
        key_provider.revoke(req.key_id, req.reason)
    except KeyError:
        raise HTTPException(404, f"unknown key_id {req.key_id!r}")
    audit_log.record(
        "revoke-key", actor_key_prefix=api_key, details={"key_id": req.key_id, "reason": req.reason}
    )
    return {"key_id": req.key_id, "status": key_provider.key_status(req.key_id)}


@app.get("/v1/verifier/keys/{key_id}/status", dependencies=[Depends(require_role(Role.ADMINISTRATOR, Role.AUDITOR))])
def get_key_status(key_id: str):
    try:
        status = key_provider.key_status(key_id)
    except KeyError:
        raise HTTPException(404, f"unknown key_id {key_id!r}")
    return {
        "key_id": key_id,
        "status": status,
        "revocation_reason": key_provider.revocation_reason(key_id),
    }


@app.post("/v1/attestations", dependencies=[Depends(require_role(Role.PROVER))])
def submit_attestation(evidence: HardwareEvidence):
    attestation_id = str(uuid.uuid4())
    digest = store.put_attestation(attestation_id, evidence)
    return {"attestation_id": attestation_id, "digest": digest}


class AttestationVerifyRequest(BaseModel):
    attestation_id: str


@app.post("/v1/attestations/verify", dependencies=[Depends(require_role(Role.PROVER, Role.AUDITOR))])
def verify_attestation(req: AttestationVerifyRequest):
    ev = store.get_attestation(req.attestation_id)
    if ev is None:
        raise HTTPException(404, "attestation not found")
    return {
        "attestation_id": req.attestation_id,
        "structurally_valid": True,
        "mock": ev.mock,
        "maturity": ev.maturity,
        "note": (
            "Phase 1/2 check schema validity only; neither validates a "
            "real hardware signature chain. See docs/ai2040-coverage-matrix.md."
        ),
    }


@app.post("/v1/evidence", dependencies=[Depends(require_role(Role.PROVER))])
def submit_evidence(evidence: Evidence):
    try:
        digest = store.put_evidence(evidence)
    except EvidenceConflict as e:
        raise HTTPException(409, str(e))
    return {"evidence_id": evidence.evidence_id, "digest": digest}


class EvidenceVerifyRequest(BaseModel):
    evidence_id: str


@app.post("/v1/evidence/verify", dependencies=[Depends(require_role(Role.PROVER, Role.AUDITOR))])
def verify_evidence(req: EvidenceVerifyRequest):
    ev = store.get_evidence(req.evidence_id)
    if ev is None:
        raise HTTPException(404, "evidence not found")
    return {"evidence_id": req.evidence_id, "digest": ev.digest(), "structurally_valid": True}


@app.post("/v1/policies/validate", dependencies=[Depends(require_role(Role.POLICY_AUTHORITY))])
def validate_policy(policy: Policy):
    store.policies[policy.policy_id] = policy
    return {"policy_id": policy.policy_id, "valid": True}


@app.get("/v1/policies/{policy_id}", dependencies=[Depends(require_role(Role.PROVER, Role.POLICY_AUTHORITY, Role.AUDITOR, Role.ADMINISTRATOR))])
def get_policy(policy_id: str):
    p = store.policies.get(policy_id)
    if p is None:
        raise HTTPException(404, "policy not found")
    return p


class InferenceVerifyRequest(BaseModel):
    evidence_id: str
    policy_id: str


@app.post("/v1/inferences/verify", dependencies=[Depends(require_role(Role.PROVER))])
def verify_inference(req: InferenceVerifyRequest):
    ev = store.get_evidence(req.evidence_id)
    if ev is None:
        raise HTTPException(404, "evidence not found")
    policy = store.policies.get(req.policy_id)
    if policy is None:
        raise HTTPException(404, "policy not found")

    result = evaluate(ev, policy)
    verification_id = str(uuid.uuid4())

    receipt: Receipt | None = None
    if result.passed:
        key_id, signing_key = key_provider.get_signing_key()
        unsigned = Receipt(
            verification_id=verification_id,
            verifier_key_id=key_id,
            model_identity_digest=ev.model_identity.digest(),
            runtime_identity_digest=ev.runtime_identity.digest(),
            hardware_evidence_digest=ev.hardware_evidence.digest(),
            policy_id=policy.policy_id,
            policy_version=policy.version,
            assurance_level=result.assurance_level_achieved,
            result=True,
            limitations=[
                "Phase 1/2: no independent recomputation was performed",
                "Phase 1/2: no network evidence was collected",
                (
                    "Phase 1/2: hardware evidence is MOCK unless a real "
                    "AttestationProvider produced it (none exists yet)"
                ),
                (
                    "this receipt attests that the evidence satisfied the "
                    "named policy's checks -- it does not attest that the "
                    "evidence was truthful when submitted"
                ),
            ],
        )
        receipt = sign_receipt(unsigned, signing_key)
        store.receipts[verification_id] = receipt

    store.verifications[verification_id] = {
        "evidence_id": req.evidence_id,
        "policy_id": req.policy_id,
        "result": result.model_dump(),
        "receipt": receipt.model_dump(mode="json") if receipt else None,
    }

    return {
        "verification_id": verification_id,
        "passed": result.passed,
        "reasons": result.reasons,
        "assurance_level_achieved": result.assurance_level_achieved,
        "receipt": receipt,
    }


@app.get("/v1/verifications/{verification_id}", dependencies=[Depends(require_role(Role.PROVER, Role.AUDITOR))])
def get_verification(verification_id: str):
    v = store.verifications.get(verification_id)
    if v is None:
        raise HTTPException(404, "verification not found")
    return v


class ReceiptVerifyRequest(BaseModel):
    receipt: Receipt
    verifier_public_key_hex: str | None = None


@app.post("/v1/receipts/verify")
def verify_receipt_endpoint(req: ReceiptVerifyRequest):
    """Deliberately NOT behind auth: the entire point of a receipt is that
    anyone can check it, not just credentialed API callers -- gating this
    would contradict docs/receipt-specification.md.

    Phase 3: the response now distinguishes two genuinely different
    questions, per docs/protocol/key-management.md --

      signature_valid   -- VALID_AT_ISSUANCE. A pure cryptographic fact
                            that never changes: was this receipt actually
                            signed by the claimed key. Unaffected by
                            revocation.
      key_status         -- ACTIVE / ROTATED / REVOKED / UNKNOWN right now.
      currently_trusted  -- CURRENTLY_TRUSTED. signature_valid AND the key
                            has not been revoked. THIS is the field a
                            relying party should actually gate decisions
                            on, not signature_valid alone.
    """
    key_status = None
    if req.verifier_public_key_hex:
        # Caller supplied their own key out of band -- we have no key_id
        # to look up a revocation status against, so we honestly report
        # none rather than guessing.
        pk = public_key_from_hex(req.verifier_public_key_hex)
    else:
        try:
            pk = key_provider.get_public_key(req.receipt.verifier_key_id)
            key_status = key_provider.key_status(req.receipt.verifier_key_id)
        except KeyError:
            return {
                "signature_valid": False,
                "key_status": "UNKNOWN",
                "currently_trusted": False,
                "note": f"unknown verifier_key_id {req.receipt.verifier_key_id!r}",
            }

    signature_valid = verify_receipt(req.receipt, pk)
    currently_trusted = signature_valid and key_status != KeyStatus.REVOKED
    return {
        "signature_valid": signature_valid,
        "key_status": key_status,
        "currently_trusted": currently_trusted,
    }


@app.get("/v1/verifier/audit-log", dependencies=[Depends(require_role(Role.ADMINISTRATOR, Role.AUDITOR))])
def get_audit_log():
    return {"entries": audit_log.read_all()}


@app.post("/v1/recomputation")
def recomputation_not_implemented():
    raise HTTPException(501, "recomputation is Phase 6 -- see docs/protocol-roadmap.md")


@app.post("/v1/recomputation/check")
def recomputation_check_not_implemented():
    raise HTTPException(501, "recomputation is Phase 6 -- see docs/protocol-roadmap.md")
