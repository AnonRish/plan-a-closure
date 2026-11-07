"""tests/test_ledger.py -- Phase 3 tamper-evidence tests.

Every test here actually mutates a constructed ledger and checks the real
verify_chain()/check_and_register_nonce() result. None of these are
asserted from design intent (spec Sec. 9/31: "must actually be
demonstrated").
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from cuda_guard.ledger import TamperEvidentLedger, LedgerRecord
from cuda_guard.evidence import EvidenceLayer


def _fresh_ledger() -> TamperEvidentLedger:
    l = TamperEvidentLedger()
    l.record("event_a", {"x": 1})
    l.record("VIOLATION", {"layer": EvidenceLayer.L1_SELF_AUDIT, "reason": "backward blocked"})
    l.record("event_b", {"y": 2})
    l.record("VIOLATION", {"layer": EvidenceLayer.L2_HARDWARE_ROOTED_TRUST, "reason": "attest failed"})
    return l


def test_untouched_chain_is_valid():
    result = _fresh_ledger().verify_chain()
    assert result.valid
    assert result.records_checked == 4


def test_violations_by_layer_partitions_correctly():
    l = _fresh_ledger()
    assert len(l.violations()) == 2
    assert len(l.violations_by_layer(EvidenceLayer.L1_SELF_AUDIT)) == 1
    assert len(l.violations_by_layer(EvidenceLayer.L2_HARDWARE_ROOTED_TRUST)) == 1


def test_modification_detected():
    l = _fresh_ledger()
    l._records[1].payload["reason"] = "TAMPERED"
    result = l.verify_chain()
    assert not result.valid
    assert result.first_break_at == 1


def test_timestamp_alteration_detected():
    l = _fresh_ledger()
    l._records[2].timestamp = "1999-01-01T00:00:00+00:00"
    result = l.verify_chain()
    assert not result.valid
    assert result.first_break_at == 2


def test_deletion_detected():
    l = _fresh_ledger()
    del l._records[1]
    result = l.verify_chain()
    assert not result.valid


def test_insertion_detected():
    l = _fresh_ledger()
    fake = LedgerRecord(sequence_number=99, previous_hash=l._records[0].record_hash,
                         timestamp="2020-01-01T00:00:00+00:00", event_type="fabricated",
                         payload={"p": 1}, source="attacker", nonce="fakefake")
    fake.record_hash = fake.compute_hash()
    l._records.insert(1, fake)
    result = l.verify_chain()
    assert not result.valid


def test_reordering_detected():
    l = _fresh_ledger()
    l._records[1], l._records[2] = l._records[2], l._records[1]
    result = l.verify_chain()
    assert not result.valid


def test_duplicate_content_flagged_but_chain_still_valid():
    l = TamperEvidentLedger()
    l.record("event_a", {"x": 1})
    l.record("event_a", {"x": 1})
    result = l.verify_chain()
    assert result.valid  # duplicate content is not a chain-integrity break
    assert result.duplicate_content_pairs == [(0, 1)]


def test_nonce_replay_detected():
    l = TamperEvidentLedger()
    nonce = "reused-nonce-123"
    assert l.check_and_register_nonce(nonce) is True
    assert l.check_and_register_nonce(nonce) is False


def test_known_limitation_wholesale_replacement_not_detected_by_design():
    """Documents, via a real test, the limitation stated in ledger.py's
    module docstring: an attacker who rebuilds a ledger from scratch with a
    fully self-consistent alternate chain is NOT detected by verify_chain()
    alone -- that requires an external anchor, out of scope here. This test
    exists so the limitation is verified true, not just claimed."""
    forged = TamperEvidentLedger()
    forged.record("event_a", {"x": "an attacker's fabricated version"})
    forged.record("VIOLATION", {"layer": EvidenceLayer.L1_SELF_AUDIT, "reason": "fabricated"})
    result = forged.verify_chain()
    assert result.valid  # correctly "valid" -- internally self-consistent, NOT independently anchored
