"""Cross-implementation conformance: the standalone verifier
(tools/standalone-verifier/verify_receipt.py, which deliberately does NOT
import from frontier_verify) must agree with the main package's
frontier_verify.receipts.signing.verify_receipt() on every input tested
here. Disagreement would mean the standalone file's re-implemented
canonicalization has silently drifted from the reference implementation's
-- exactly the interoperability bug a second implementation exists to
catch. See tools/standalone-verifier/README.md.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from frontier_verify.receipts.models import Receipt
from frontier_verify.receipts.signing import (
    generate_keypair,
    public_key_to_hex,
    sign_receipt,
)

STANDALONE_PATH = (
    Path(__file__).resolve().parents[2] / "tools" / "standalone-verifier" / "verify_receipt.py"
)


def _load_standalone_module():
    spec = importlib.util.spec_from_file_location("standalone_verify_receipt", STANDALONE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


standalone = _load_standalone_module()


def _signed_receipt(**overrides) -> tuple[Receipt, str]:
    sk, pk = generate_keypair()
    defaults = {
        "verification_id": "conformance-v1",
        "verifier_key_id": "conformance-k1",
        "model_identity_digest": "m1",
        "runtime_identity_digest": "r1",
        "hardware_evidence_digest": "h1",
        "policy_id": "p1",
        "policy_version": "0.1.0",
        "assurance_level": "L1",
        "result": True,
        "limitations": ["example limitation one", "example limitation two"],
    }
    defaults.update(overrides)
    receipt = sign_receipt(Receipt(**defaults), sk)
    return receipt, public_key_to_hex(pk)


def test_standalone_verifier_accepts_a_genuinely_valid_receipt():
    receipt, pk_hex = _signed_receipt()
    assert standalone.verify_receipt(receipt.model_dump(mode="json"), pk_hex) is True


def test_standalone_verifier_rejects_tampered_receipt():
    receipt, pk_hex = _signed_receipt()
    tampered = receipt.model_dump(mode="json")
    tampered["result"] = False
    assert standalone.verify_receipt(tampered, pk_hex) is False


def test_standalone_verifier_rejects_wrong_key():
    receipt, _correct_pk_hex = _signed_receipt()
    _, wrong_pk = generate_keypair()
    wrong_pk_hex = public_key_to_hex(wrong_pk)
    assert standalone.verify_receipt(receipt.model_dump(mode="json"), wrong_pk_hex) is False


def test_two_implementations_agree_across_a_battery_of_receipts():
    """The real cross-check: generate several structurally different
    receipts and confirm both implementations reach the same verdict on
    each, both for genuine and for tampered copies."""
    from frontier_verify.receipts.signing import verify_receipt as reference_verify

    cases = [
        {"result": True, "assurance_level": "L0"},
        {"result": False, "assurance_level": "L1", "limitations": []},
        {"policy_id": "unicode-\u00e9\u00e8-policy"},
        {"limitations": ["one", "two", "three", "four"]},
    ]
    for overrides in cases:
        receipt, pk_hex = _signed_receipt(**overrides)

        standalone_result = standalone.verify_receipt(receipt.model_dump(mode="json"), pk_hex)
        from frontier_verify.receipts.signing import public_key_from_hex

        reference_result = reference_verify(receipt, public_key_from_hex(pk_hex))
        assert standalone_result is True
        assert reference_result is True
        assert standalone_result == reference_result

        tampered = receipt.model_copy(update={"result": not receipt.result})
        standalone_tampered = standalone.verify_receipt(tampered.model_dump(mode="json"), pk_hex)
        reference_tampered = reference_verify(tampered, public_key_from_hex(pk_hex))
        assert standalone_tampered is False
        assert reference_tampered is False
        assert standalone_tampered == reference_tampered
