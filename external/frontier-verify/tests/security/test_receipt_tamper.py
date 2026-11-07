"""Attack the receipt. Every field-level tamper attempted here must flip
verify_receipt() to False -- if any of these ever pass, the signing scheme
is broken and nothing downstream (docs/receipt-specification.md's
"independently verifiable" claim) is true anymore."""
from frontier_verify.receipts.models import Receipt
from frontier_verify.receipts.signing import generate_keypair, sign_receipt, verify_receipt


def _signed_receipt(sk):
    unsigned = Receipt(
        verification_id="v1",
        verifier_key_id="k1",
        model_identity_digest="m1",
        runtime_identity_digest="r1",
        hardware_evidence_digest="h1",
        policy_id="p1",
        policy_version="0.1.0",
        assurance_level="L1",
        result=True,
    )
    return sign_receipt(unsigned, sk)


def test_tampered_result_field_fails_verification():
    sk, pk = generate_keypair()
    receipt = _signed_receipt(sk)
    tampered = receipt.model_copy(update={"result": False})
    assert verify_receipt(tampered, pk) is False


def test_tampered_assurance_level_fails_verification():
    sk, pk = generate_keypair()
    receipt = _signed_receipt(sk)
    tampered = receipt.model_copy(update={"assurance_level": "L5"})
    assert verify_receipt(tampered, pk) is False


def test_tampered_policy_id_fails_verification():
    sk, pk = generate_keypair()
    receipt = _signed_receipt(sk)
    tampered = receipt.model_copy(update={"policy_id": "different-policy"})
    assert verify_receipt(tampered, pk) is False


def test_wrong_public_key_fails_verification():
    sk1, _ = generate_keypair()
    _, pk2 = generate_keypair()
    receipt = _signed_receipt(sk1)
    assert verify_receipt(receipt, pk2) is False


def test_corrupted_signature_fails_verification():
    sk, pk = generate_keypair()
    receipt = _signed_receipt(sk)
    tampered = receipt.model_copy(update={"signature": "not-valid-base64!!"})
    assert verify_receipt(tampered, pk) is False
