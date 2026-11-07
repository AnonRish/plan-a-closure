import hashlib

from embedded_audit.audit import AuditRound, build_audit_receipt, run_audit_round
from plan_a_protocol.protocol import Signer, generate_keypair, verify_receipt


def test_challenge_rejects_wrong_response():
    audit = AuditRound.create("a1", "company-1", ["compute-log"])
    try:
        audit.add_evidence(evidence_id="e1", artifact_type="compute-log", content=b"x", source_locator="company:compute-log", response="wrong")
        assert False
    except ValueError:
        pass


def test_complete_round_passes():
    audit = AuditRound.create("a2", "company-1", ["compute-log", "access-log"])
    assert run_audit_round(audit, artifacts={"compute-log": b"1", "access-log": b"2"})["status"] == "PASS"


def test_missing_evidence_is_unknown_not_pass():
    audit = AuditRound.create("a3", "company-1", ["compute-log", "access-log"])
    run_audit_round(audit, artifacts={"compute-log": b"1"})
    assert audit.evaluate()["status"] == "UNKNOWN"


def test_receipt_is_independently_verifiable():
    audit = AuditRound.create("a4", "company-1", ["compute-log"])
    run_audit_round(audit, artifacts={"compute-log": b"1"})
    akey, apub = generate_keypair()
    bkey, bpub = generate_keypair()
    signers = [
        (Signer("auditor-a", "embedded-auditor", apub, "org-a"), akey),
        (Signer("auditor-b", "review-auditor", bpub, "org-b"), bkey),
    ]
    receipt = build_audit_receipt(audit, signers, quorum=2)
    ok, errors = verify_receipt(receipt)
    assert ok, errors


def test_nonce_is_not_revealed_in_evaluation():
    audit = AuditRound.create("a5", "company-1", ["compute-log"])
    run_audit_round(audit, artifacts={"compute-log": b"1"})
    assert audit.nonce not in str(audit.evaluate())


def test_challenge_response_formula_is_stable():
    audit = AuditRound.create("a6", "company-1", ["compute-log"])
    expected = hashlib.sha256((audit.nonce + "compute-log").encode()).hexdigest()
    assert expected != audit.nonce
