from plan_a_protocol.protocol import EvidenceRecord, Signer, compute_evidence_hash, compute_receipt_digest, generate_keypair, issue_receipt, verify_receipt


def test_evidence_chain_is_order_sensitive():
    a = EvidenceRecord("e1", "network", "site-1", "tap-1", "2026-01-01T00:00:00Z", {"n": 1})
    b = EvidenceRecord("e2", "power", "site-1", "meter-1", "2026-01-01T00:01:00Z", {"mw": 10}, a.digest())
    assert compute_evidence_hash([a, b]) == b.digest()


def test_broken_chain_is_rejected():
    a = EvidenceRecord("e1", "network", "site-1", "tap-1", "2026-01-01T00:00:00Z", {})
    b = EvidenceRecord("e2", "power", "site-1", "meter-1", "2026-01-01T00:01:00Z", {}, "f" * 64)
    try:
        compute_evidence_hash([a, b])
        assert False
    except ValueError:
        pass


def test_threshold_receipt_verifies():
    signers = []
    for signer_id, role, group in [("s1", "auditor", "org-a"), ("s2", "inspector", "org-b"), ("s3", "secretariat", "org-c")]:
        key, pub = generate_keypair()
        signers.append((Signer(signer_id, role, pub, group), key))
    receipt = issue_receipt(
        receipt_id="r1",
        track="TRACK_1",
        subject={"id": "company-1"},
        claim={"statement": "audit checks satisfied", "basis": "embedded audit v1"},
        evidence_chain={"root_hash": "a" * 64, "evidence_ids": ["e1"]},
        verification={"status": "PASS", "procedure_id": "T1-AUDIT-1"},
        governance_binding={"instrument_ref": "LOCAL-AGREEMENT-1", "retention_days": 365},
        signers=signers,
        quorum=2,
    )
    ok, errors = verify_receipt(receipt)
    assert ok, errors
    assert compute_receipt_digest(receipt) == receipt.digest()


def test_one_trust_root_cannot_fake_two_independent_roots():
    key, pub = generate_keypair()
    signer = Signer("s1", "auditor", pub, "same-root")
    receipt = issue_receipt(
        receipt_id="r2",
        track="TRACK_1",
        subject={"id": "company-1"},
        claim={"statement": "x", "basis": "y"},
        evidence_chain={"root_hash": "b" * 64, "evidence_ids": []},
        verification={"status": "PASS"},
        governance_binding={"instrument_ref": "demo"},
        signers=[(signer, key), (signer, key)],
        quorum=2,
    )
    ok, errors = verify_receipt(receipt)
    assert not ok
    assert any("same independence group" in e or "quorum" in e for e in errors)
