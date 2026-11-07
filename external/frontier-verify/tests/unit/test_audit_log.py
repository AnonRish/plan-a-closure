"""Tests the audit log fix for the gap found in
docs/reviews/external-review.md finding #1: which credential performed a
given administrative action must now be recorded, not lost.
"""
from __future__ import annotations

from frontier_verify.audit.log import AuditLog


def test_recorded_entry_captures_actor_and_action(tmp_path):
    log = AuditLog(path=tmp_path / "audit.jsonl")
    log.record("rotate-key", actor_key_prefix="fv_abc12345xyz", details={"new_key_id": "k1"})

    entries = log.read_all()
    assert len(entries) == 1
    assert entries[0]["action"] == "rotate-key"
    assert entries[0]["details"]["new_key_id"] == "k1"
    assert "timestamp" in entries[0]


def test_full_key_never_appears_in_the_log_file(tmp_path):
    """The whole key must never land in a log file that may be less
    carefully protected than the key store itself."""
    log = AuditLog(path=tmp_path / "audit.jsonl")
    full_key = "fv_" + "x" * 64
    log.record("revoke-key", actor_key_prefix=full_key, details={})

    raw_content = tmp_path.joinpath("audit.jsonl").read_text()
    assert full_key not in raw_content


def test_keys_sharing_a_human_chosen_naming_convention_are_still_distinguishable(tmp_path):
    """Regression test for the actual bug this module was rewritten to
    fix: a first version truncated to an 8-character literal prefix,
    which THIS EXACT test case caught as broken -- 'fv_admin1_secret' and
    'fv_admin2_secret' both truncate to 'fv_admin' and were
    indistinguishable. A hash-based fingerprint must not have this
    problem. This is the real scenario finding #1 in
    docs/reviews/external-review.md describes: two different
    ADMINISTRATOR-role keys, and it must be possible to tell their
    actions apart afterward."""
    log = AuditLog(path=tmp_path / "audit.jsonl")
    log.record("revoke-key", actor_key_prefix="fv_admin1_secret", details={"key_id": "k1"})
    log.record("rotate-key", actor_key_prefix="fv_admin2_secret", details={"new_key_id": "k2"})

    entries = log.read_all()
    fingerprints = {e["actor_fingerprint"] for e in entries}
    assert len(fingerprints) == 2, "two different administrators' actions were not distinguishable"


def test_same_key_always_produces_the_same_fingerprint(tmp_path):
    """Necessary for the fingerprint to be useful at all -- an auditor
    reviewing the log needs to recognize repeated actions by the SAME
    actor, not just distinguish different actors from each other."""
    log = AuditLog(path=tmp_path / "audit.jsonl")
    log.record("rotate-key", actor_key_prefix="fv_same_key_both_times", details={})
    log.record("rotate-key", actor_key_prefix="fv_same_key_both_times", details={})

    entries = log.read_all()
    assert entries[0]["actor_fingerprint"] == entries[1]["actor_fingerprint"]


def test_empty_log_reads_as_empty_list_not_an_error(tmp_path):
    log = AuditLog(path=tmp_path / "never_written.jsonl")
    assert log.read_all() == []
