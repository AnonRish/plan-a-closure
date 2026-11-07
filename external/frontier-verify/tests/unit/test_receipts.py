from frontier_verify.receipts.models import Receipt
from frontier_verify.receipts.signing import (
    generate_keypair,
    private_key_from_hex,
    private_key_to_hex,
    public_key_from_hex,
    public_key_to_hex,
    sign_receipt,
    verify_receipt,
)


def _receipt(**overrides) -> Receipt:
    defaults = {
        "verification_id": "v1",
        "verifier_key_id": "k1",
        "model_identity_digest": "m1",
        "runtime_identity_digest": "r1",
        "hardware_evidence_digest": "h1",
        "policy_id": "p1",
        "policy_version": "0.1.0",
        "assurance_level": "L1",
        "result": True,
    }
    defaults.update(overrides)
    return Receipt(**defaults)


def test_valid_signature_verifies():
    sk, pk = generate_keypair()
    signed = sign_receipt(_receipt(), sk)
    assert signed.signature is not None
    assert verify_receipt(signed, pk) is True


def test_unsigned_receipt_fails_verification():
    _, pk = generate_keypair()
    assert verify_receipt(_receipt(), pk) is False


def test_key_hex_roundtrip():
    sk, pk = generate_keypair()
    sk2 = private_key_from_hex(private_key_to_hex(sk))
    pk2 = public_key_from_hex(public_key_to_hex(pk))
    signed = sign_receipt(_receipt(), sk2)
    assert verify_receipt(signed, pk2) is True
