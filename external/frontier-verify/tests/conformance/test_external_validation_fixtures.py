"""Pins examples/external-validation/'s fixture files as a real
regression test -- if a future change to canonicalization or signing
ever made these pre-generated example files stop behaving as documented,
this test catches it. The external validation package is only honest if
it stays correct as the codebase evolves.
"""
from __future__ import annotations

import json
from pathlib import Path

from frontier_verify.receipts.models import Receipt
from frontier_verify.receipts.signing import public_key_from_hex, verify_receipt

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "examples" / "external-validation"


def _load(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text())


def _pubkey_hex() -> str:
    return (FIXTURE_DIR / "verifier_public_key.txt").read_text().strip()


def _wrong_pubkey_hex() -> str:
    return (FIXTURE_DIR / "wrong_public_key.txt").read_text().strip()


def test_valid_receipt_fixture_verifies():
    receipt = Receipt.model_validate(_load("01_valid_receipt.json"))
    assert verify_receipt(receipt, public_key_from_hex(_pubkey_hex())) is True


def test_tampered_result_fixture_fails():
    receipt = Receipt.model_validate(_load("02_tampered_result.json"))
    assert verify_receipt(receipt, public_key_from_hex(_pubkey_hex())) is False


def test_tampered_assurance_level_fixture_fails():
    receipt = Receipt.model_validate(_load("03_tampered_assurance_level.json"))
    assert verify_receipt(receipt, public_key_from_hex(_pubkey_hex())) is False


def test_corrupted_signature_fixture_fails():
    receipt = Receipt.model_validate(_load("04_corrupted_signature.json"))
    assert verify_receipt(receipt, public_key_from_hex(_pubkey_hex())) is False


def test_valid_receipt_against_wrong_key_fails():
    receipt = Receipt.model_validate(_load("01_valid_receipt.json"))
    assert verify_receipt(receipt, public_key_from_hex(_wrong_pubkey_hex())) is False
