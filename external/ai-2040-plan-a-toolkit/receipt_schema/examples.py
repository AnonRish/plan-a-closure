"""
examples.py

One valid receipt shaped exactly like what Arbiter's license_finalize event
now produces (3-of-5 quorum, real field correspondence), and four broken
ones -- each violating exactly one thing, so it's clear which check caught it.
"""

from .validator import validate

import hashlib

VALID_RECEIPT = {
    "schema_version": "1.0",
    "receipt_id": "rcpt-unit-seed-1-seq-1",
    "receipt_type": "license_grant",
    "issued_at": "2026-08-03T12:00:00Z",
    "subject": {
        "subject_id": "unit-seed-1",
        "subject_type": "compute_unit",
        "display_name": "Halcyon Cloud",
    },
    "claim": {
        "statement": "Compute unit unit-seed-1 is licensed to operate, sequence #1, expiring 2026-09-02.",
        "confidence": 1.0,
        "basis": "k-of-n signature quorum (ECDSA P-256, 3 of 5)",
    },
    "evidence_chain": {
        "hash": hashlib.sha256(b"unit-seed-1|seq-1|content").hexdigest(),
        "prev_hash": "0" * 64,
        "hash_algorithm": "sha256",
    },
    "attestation": {
        "scheme": "ecdsa-p256-k-of-n",
        "required_quorum": 3,
        "total_signers": 5,
        "signatures": [
            {"signer_id": "signer-lab", "signer_role": "Operating Lab", "signature": "MEUCIQD...base64...", "public_key_fingerprint": "a1b2 c3d4 e5f6 0102"},
            {"signer_id": "signer-auditor", "signer_role": "Independent Auditor", "signature": "MEQCIH...base64...", "public_key_fingerprint": "b2c3 d4e5 f601 0203"},
            {"signer_id": "signer-secretariat", "signer_role": "Treaty Secretariat", "signature": "MEUCIQC...base64...", "public_key_fingerprint": "c3d4 e5f6 0102 0304"},
        ],
    },
    "governance_binding": {
        "instrument_ref": "AI-2040-Plan-A-Verification-Annex-3 (illustrative)",
        "retention_until": "2033-08-03T00:00:00Z",
        "dispute_process": "Treaty Secretariat review board, ref VER-DISPUTE-01",
        "supersedes": None,
    },
    "producer_note": "Issued by Arbiter (demonstration system); simulated clock, not wall-clock time.",
}


def broken_missing_quorum():
    r = json_deepcopy(VALID_RECEIPT)
    r["receipt_id"] = "rcpt-broken-quorum"
    r["attestation"]["signatures"] = r["attestation"]["signatures"][:2]  # only 2 of required 3
    return r


def broken_duplicate_signer():
    r = json_deepcopy(VALID_RECEIPT)
    r["receipt_id"] = "rcpt-broken-duplicate"
    r["attestation"]["signatures"] = [r["attestation"]["signatures"][0]] * 3  # same signer 3x
    return r


def broken_single_signer_high_threshold():
    r = json_deepcopy(VALID_RECEIPT)
    r["receipt_id"] = "rcpt-broken-scheme"
    r["attestation"]["scheme"] = "single-signer"
    return r


def broken_missing_governance_binding():
    r = json_deepcopy(VALID_RECEIPT)
    r["receipt_id"] = "rcpt-broken-no-governance"
    del r["governance_binding"]
    return r


def json_deepcopy(d):
    import json
    return json.loads(json.dumps(d))


if __name__ == "__main__":
    cases = [
        ("VALID (Arbiter-shaped, 3-of-5 quorum met)", VALID_RECEIPT),
        ("BROKEN: only 2 of required 3 signatures", broken_missing_quorum()),
        ("BROKEN: 3 signatures, same signer 3x", broken_duplicate_signer()),
        ("BROKEN: single-signer scheme claiming a 3-of-5 threshold", broken_single_signer_high_threshold()),
        ("BROKEN: no governance_binding at all", broken_missing_governance_binding()),
    ]
    for label, receipt in cases:
        well_formed, consummated, errors = validate(receipt)
        status = "CONSUMMATED" if consummated else ("WELL-FORMED, NOT CONSUMMATED" if well_formed else "MALFORMED")
        print(f"\n{label}\n  -> {status}")
        for e in errors:
            print(f"     - {e}")
