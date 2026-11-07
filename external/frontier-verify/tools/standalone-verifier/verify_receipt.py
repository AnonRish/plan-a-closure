#!/usr/bin/env python3
"""Standalone Frontier Verify receipt verifier.

Verifies a receipt's signature using ONLY the Python standard library plus
`cryptography` (pip install cryptography). It does NOT import anything
from the frontier_verify package -- that is the entire point of this file.
A relying party can copy these ~90 lines, never install Frontier Verify,
and still get a trustworthy answer about whether a receipt is genuine.

This is the concrete version of the claim in section 6 of the Phase 2
brief: "a third party can validate the receipt without installing the
Frontier Verify server." A doc making that claim is easy to write and easy
to leave unverified; this file is the same claim made falsifiable --
tests/conformance/test_standalone_verifier_agrees.py cross-checks this
file's verify_receipt() against frontier_verify.receipts.signing's
independently, on every test run. If the two ever disagree on the same
input, that test fails loudly, because it would mean this file's canonical
encoding has silently drifted from the reference implementation's -- an
interoperability bug, not a style issue.

Usage:
    python3 verify_receipt.py receipt.json <verifier_public_key_hex>

Exit code 0 if the signature is valid, 1 otherwise.
"""
from __future__ import annotations

import base64
import json
import sys


def canonicalize(obj: object) -> bytes:
    """Deliberately RE-IMPLEMENTED here, not imported from
    frontier_verify.core.canonical -- see this file's module docstring for
    why that duplication is the point, not an oversight."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def verify_receipt(receipt: dict, public_key_hex: str) -> bool:
    """Returns True iff `receipt["signature"]` is a valid Ed25519
    signature, by the key `public_key_hex`, over every other field of
    `receipt` in canonical encoding. Never raises on malformed input --
    always resolves to True/False, matching
    frontier_verify.receipts.signing.verify_receipt's contract."""
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError:
        print("Missing dependency: pip install cryptography", file=sys.stderr)
        raise

    signature_b64 = receipt.get("signature")
    if not signature_b64:
        return False

    payload = {k: v for k, v in receipt.items() if k != "signature"}
    message = canonicalize(payload)

    try:
        signature = base64.b64decode(signature_b64)
        public_key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
        public_key.verify(signature, message)
        return True
    except (InvalidSignature, ValueError, TypeError):
        return False


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    receipt_path, public_key_hex = sys.argv[1], sys.argv[2]
    with open(receipt_path) as f:
        receipt = json.load(f)

    ok = verify_receipt(receipt, public_key_hex)
    print(f"signature_valid={ok}")
    if ok:
        print(f"verifier_key_id={receipt.get('verifier_key_id')}")
        print(f"assurance_level={receipt.get('assurance_level')}")
        print(f"result={receipt.get('result')}")
        for limitation in receipt.get("limitations", []):
            print(f"  limitation: {limitation}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
