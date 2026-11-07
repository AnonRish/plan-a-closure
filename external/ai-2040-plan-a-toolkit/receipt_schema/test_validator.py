import json
import copy
import pytest

from .validator import validate, schema_errors, quorum_errors, is_consummated
from .examples import (
    VALID_RECEIPT, broken_missing_quorum, broken_duplicate_signer,
    broken_single_signer_high_threshold, broken_missing_governance_binding,
)


def test_valid_receipt_is_consummated():
    ok, consummated, errs = validate(VALID_RECEIPT)
    assert ok is True
    assert consummated is True
    assert errs == []


def test_missing_quorum_is_well_formed_but_not_consummated():
    ok, consummated, errs = validate(broken_missing_quorum())
    assert ok is True
    assert consummated is False
    assert any("required_quorum" in e for e in errs)


def test_duplicate_signer_is_caught():
    ok, consummated, errs = validate(broken_duplicate_signer())
    assert ok is True
    assert consummated is False
    assert any("duplicate signer_id" in e for e in errs)


def test_single_signer_high_threshold_is_flagged():
    ok, consummated, errs = validate(broken_single_signer_high_threshold())
    assert ok is True
    assert consummated is False
    assert any("min_attack=1" in e for e in errs)


def test_missing_governance_binding_is_malformed():
    ok, consummated, errs = validate(broken_missing_governance_binding())
    assert ok is False
    assert consummated is False
    assert any("governance_binding" in e for e in errs)


def test_missing_evidence_chain_is_malformed():
    r = copy.deepcopy(VALID_RECEIPT)
    del r["evidence_chain"]
    ok, _, errs = validate(r)
    assert ok is False


def test_bad_hash_format_is_malformed():
    r = copy.deepcopy(VALID_RECEIPT)
    r["evidence_chain"]["hash"] = "not-a-valid-hex-hash"
    ok, _, _ = validate(r)
    assert ok is False


def test_confidence_out_of_range_is_malformed():
    r = copy.deepcopy(VALID_RECEIPT)
    r["claim"]["confidence"] = 1.5
    ok, _, _ = validate(r)
    assert ok is False


def test_unknown_receipt_type_is_malformed():
    r = copy.deepcopy(VALID_RECEIPT)
    r["receipt_type"] = "not_a_real_type"
    ok, _, _ = validate(r)
    assert ok is False


def test_is_consummated_shortcut_matches_validate():
    assert is_consummated(VALID_RECEIPT) is True
    assert is_consummated(broken_missing_quorum()) is False


def test_extra_top_level_field_rejected():
    """additionalProperties: false at the root -- receipts shouldn't grow undocumented fields."""
    r = copy.deepcopy(VALID_RECEIPT)
    r["mystery_field"] = "surprise"
    ok, _, _ = validate(r)
    assert ok is False
