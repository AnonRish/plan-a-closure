"""Three independently-written implementations must agree on every
tested input: the Python reference (frontier_verify.receipts.signing),
the Python standalone verifier (tools/standalone-verifier/verify_receipt.py),
and the JavaScript standalone verifier
(tools/standalone-verifier/verify_receipt.js, using Node's native Ed25519,
zero shared dependencies with either Python implementation).

Skipped automatically if `node` isn't on PATH -- this environment has it,
but a CI runner or a contributor's machine might not, and failing loudly
because Node isn't installed would be a worse signal than skipping with a
clear reason.
"""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from frontier_verify.receipts.models import Receipt
from frontier_verify.receipts.signing import generate_keypair, public_key_to_hex, sign_receipt

REPO_ROOT = Path(__file__).resolve().parents[2]
JS_VERIFIER = REPO_ROOT / "tools" / "standalone-verifier" / "verify_receipt.js"
PY_STANDALONE = REPO_ROOT / "tools" / "standalone-verifier" / "verify_receipt.py"

pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not on PATH")


def _load_py_standalone():
    spec = importlib.util.spec_from_file_location("standalone_verify_receipt_xlang", PY_STANDALONE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


py_standalone = _load_py_standalone()


def _run_js_verifier(receipt_path: Path, public_key_hex: str) -> bool:
    result = subprocess.run(
        ["node", str(JS_VERIFIER), str(receipt_path), public_key_hex],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,  # exit code 1 (invalid signature) is an expected, meaningful
        # outcome this function's caller reads directly -- not an error to raise on.
    )
    # The JS verifier's own exit code IS the answer -- 0 for valid, 1 for
    # invalid -- not something this test infers from stdout text parsing.
    return result.returncode == 0


def _signed_receipt(**overrides) -> tuple[Receipt, str]:
    sk, pk = generate_keypair()
    defaults = {
        "verification_id": "xlang-v1",
        "verifier_key_id": "xlang-k1",
        "model_identity_digest": "m1",
        "runtime_identity_digest": "r1",
        "hardware_evidence_digest": "h1",
        "policy_id": "p1",
        "policy_version": "0.1.0",
        "assurance_level": "L1",
        "result": True,
        "limitations": ["ascii limitation", "unicode limitation: caf\u00e9, \u00fcber, \u65e5\u672c\u8a9e"],
    }
    defaults.update(overrides)
    receipt = sign_receipt(Receipt(**defaults), sk)
    return receipt, public_key_to_hex(pk)


def test_all_three_implementations_agree_on_a_valid_receipt(tmp_path):
    receipt, pk_hex = _signed_receipt()
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps(receipt.model_dump(mode="json")))

    from frontier_verify.receipts.signing import public_key_from_hex, verify_receipt

    reference_result = verify_receipt(receipt, public_key_from_hex(pk_hex))
    py_standalone_result = py_standalone.verify_receipt(receipt.model_dump(mode="json"), pk_hex)
    js_result = _run_js_verifier(receipt_path, pk_hex)

    assert reference_result is True
    assert py_standalone_result is True
    assert js_result is True


def test_all_three_implementations_agree_on_a_tampered_receipt(tmp_path):
    receipt, pk_hex = _signed_receipt()
    tampered = receipt.model_dump(mode="json")
    tampered["result"] = not tampered["result"]
    receipt_path = tmp_path / "tampered.json"
    receipt_path.write_text(json.dumps(tampered))

    from frontier_verify.receipts.models import Receipt as ReceiptModel
    from frontier_verify.receipts.signing import public_key_from_hex, verify_receipt

    reference_result = verify_receipt(ReceiptModel.model_validate(tampered), public_key_from_hex(pk_hex))
    py_standalone_result = py_standalone.verify_receipt(tampered, pk_hex)
    js_result = _run_js_verifier(receipt_path, pk_hex)

    assert reference_result is False
    assert py_standalone_result is False
    assert js_result is False


def test_all_three_agree_with_unicode_and_nested_list_content(tmp_path):
    """The case most likely to expose a genuine cross-language
    canonicalization bug: non-ASCII text and a multi-element list field.
    This is exactly the kind of input where 'looks fine in English-only
    testing' has historically hidden real interoperability bugs."""
    receipt, pk_hex = _signed_receipt(
        policy_id="policy-with-unicode-\u4e2d\u6587",
        limitations=["a", "b", "c with emoji: \U0001f512", "d"],
    )
    receipt_path = tmp_path / "unicode_receipt.json"
    receipt_path.write_text(json.dumps(receipt.model_dump(mode="json"), ensure_ascii=False), encoding="utf-8")

    from frontier_verify.receipts.signing import public_key_from_hex, verify_receipt

    reference_result = verify_receipt(receipt, public_key_from_hex(pk_hex))
    py_standalone_result = py_standalone.verify_receipt(receipt.model_dump(mode="json"), pk_hex)
    js_result = _run_js_verifier(receipt_path, pk_hex)

    assert reference_result is True
    assert py_standalone_result is True
    assert js_result is True
