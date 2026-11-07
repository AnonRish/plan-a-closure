from fides.ledger import AuditLedger, GENESIS_HASH
from fides.attestation import AuditResult


def test_first_entry_chains_to_genesis():
    ledger = AuditLedger()
    entry = ledger.append("gpu-1", AuditResult(0, True, "ok"))
    assert entry.prev_hash == GENESIS_HASH


def test_entries_chain_to_previous_hash():
    ledger = AuditLedger()
    e0 = ledger.append("gpu-1", AuditResult(0, True, "ok"))
    e1 = ledger.append("gpu-1", AuditResult(1, True, "ok"))
    e2 = ledger.append("gpu-1", AuditResult(2, False, "declared INFERENCE but revealed event 4 is 'backward_matmul'"))
    assert e1.prev_hash == e0.entry_hash
    assert e2.prev_hash == e1.entry_hash


def test_untampered_chain_verifies():
    ledger = AuditLedger()
    for i in range(10):
        ledger.append("gpu-1", AuditResult(i, i != 7, "ok" if i != 7 else "violation"))
    assert ledger.verify_chain()


def test_tampering_with_a_past_entry_breaks_the_chain():
    ledger = AuditLedger()
    ledger.append("gpu-1", AuditResult(0, True, "ok"))
    ledger.append("gpu-1", AuditResult(1, True, "ok"))
    ledger.append("gpu-1", AuditResult(2, False, "declared INFERENCE but revealed event 4 is 'backward_matmul'"))
    assert ledger.verify_chain()

    ledger.tamper(2, "ok")  # attacker tries to erase the violation after the fact
    assert not ledger.verify_chain()


def test_tampering_with_an_early_entry_is_still_detected_even_if_later_entries_are_untouched():
    ledger = AuditLedger()
    for i in range(5):
        ledger.append("gpu-1", AuditResult(i, True, "ok"))
    ledger.tamper(0, "rewritten")
    assert not ledger.verify_chain()


def test_empty_ledger_verifies_trivially():
    assert AuditLedger().verify_chain()
