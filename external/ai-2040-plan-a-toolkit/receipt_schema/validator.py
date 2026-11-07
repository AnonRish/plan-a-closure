"""
validator.py

Validates a verification receipt against receipt_schema.json, plus two
cross-field checks JSON Schema can't express on its own:

1. QUORUM MET: len(signatures) >= attestation.required_quorum
2. DISTINCT SIGNERS: no signer_id appears twice (five signatures from the
   same key isn't a quorum, it's one signer with good penmanship)

A receipt can be schema-valid (right shape) but still fail these -- e.g. a
receipt honestly recording an in-progress proposal that hasn't reached
quorum yet. is_consummated() distinguishes "correctly shaped" from
"actually attests to anything."
"""

import json
from pathlib import Path
import jsonschema

SCHEMA_PATH = Path(__file__).parent / "receipt_schema.json"
_schema = json.loads(SCHEMA_PATH.read_text())
_validator = jsonschema.Draft202012Validator(_schema)


class ReceiptValidationError(Exception):
    def __init__(self, errors):
        self.errors = errors
        super().__init__("; ".join(errors))


def schema_errors(receipt: dict):
    """List of JSON-Schema-level structural errors (empty if well-formed)."""
    return [f"{'/'.join(str(p) for p in e.path) or '(root)'}: {e.message}" for e in _validator.iter_errors(receipt)]


def quorum_errors(receipt: dict):
    """Cross-field checks the schema can't express on its own."""
    errs = []
    att = receipt.get("attestation", {})
    sigs = att.get("signatures", [])
    required = att.get("required_quorum")
    signer_ids = [s.get("signer_id") for s in sigs]

    if required is not None and len(sigs) < required:
        errs.append(f"attestation: only {len(sigs)} signature(s) present, required_quorum is {required}")
    if len(signer_ids) != len(set(signer_ids)):
        dupes = {s for s in signer_ids if signer_ids.count(s) > 1}
        errs.append(f"attestation: duplicate signer_id(s) {sorted(dupes)} -- not {len(sigs)} independent signers")
    if att.get("scheme") == "single-signer" and required and required > 1:
        errs.append(
            "attestation: scheme is 'single-signer' but required_quorum > 1 -- per the trust-composition "
            "analysis, a single-signer scheme has min_attack=1 regardless of the claimed threshold"
        )
    return errs


def validate(receipt: dict, raise_on_error: bool = False):
    """Full validation. Returns (is_well_formed, is_consummated, errors)."""
    struct_errs = schema_errors(receipt)
    if struct_errs:
        if raise_on_error:
            raise ReceiptValidationError(struct_errs)
        return False, False, struct_errs

    q_errs = quorum_errors(receipt)
    if raise_on_error and q_errs:
        raise ReceiptValidationError(q_errs)
    return True, len(q_errs) == 0, q_errs


def is_consummated(receipt: dict) -> bool:
    ok, consummated, _ = validate(receipt)
    return ok and consummated
