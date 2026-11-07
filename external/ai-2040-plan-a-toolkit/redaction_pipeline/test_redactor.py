import re
import pytest

from .redactor import redact, PatternRule, WatchlistRule, StubKeywordSemanticFlagger

EMAIL_RULE = PatternRule("email", r"[\w.+-]+@[\w-]+\.[\w.-]+", "email_address")
ID_RULE = PatternRule("employee_id", r"\bEMP-\d{4,6}\b", "internal_identifier")


def test_author_marker_is_redacted_and_removed_from_output():
    text = "Findings were normal. <<SENSITIVE:exploit_detail>>Buffer overflow at offset 0x1F in the parser.<<END>> No further action needed."
    result = redact(text)
    assert "Buffer overflow" not in result.redacted_text
    assert "[REDACTED: exploit_detail" in result.redacted_text
    assert "Findings were normal." in result.redacted_text
    assert "No further action needed." in result.redacted_text


def test_pattern_rule_redacts_all_matches():
    text = "Contact reviewer1@example.org or reviewer2@example.org for questions."
    result = redact(text, patterns=[EMAIL_RULE])
    assert "reviewer1@example.org" not in result.redacted_text
    assert "reviewer2@example.org" not in result.redacted_text
    assert result.redacted_text.count("[REDACTED: email_address") == 2


def test_watchlist_redacts_case_insensitively():
    text = "The run was approved by Jordan Alvarez and reviewed by jordan alvarez again."
    result = redact(text, watchlist=WatchlistRule(names=("Jordan Alvarez",)))
    assert "Jordan Alvarez" not in result.redacted_text
    assert "jordan alvarez" not in result.redacted_text.lower()
    assert result.redacted_text.count("[REDACTED: watchlisted_individual") == 2


def test_multiple_rule_types_together_and_offsets_stay_correct():
    text = "Auditor EMP-4821 flagged reviewer1@example.org. <<SENSITIVE:capability>>Model achieved X on eval Y.<<END>> End of report."
    result = redact(text, patterns=[EMAIL_RULE, ID_RULE])
    assert "EMP-4821" not in result.redacted_text
    assert "reviewer1@example.org" not in result.redacted_text
    assert "Model achieved X" not in result.redacted_text
    assert result.redacted_text.startswith("Auditor [REDACTED:")
    assert result.redacted_text.strip().endswith("End of report.")


def test_overlapping_spans_merge_and_prefer_earliest_found_category():
    # the marker fully contains an email that a pattern rule would also match
    text = "<<SENSITIVE:contact_info>>Reach out at reviewer1@example.org directly.<<END>>"
    result = redact(text, patterns=[EMAIL_RULE])
    assert len(result.confidential_manifest) == 1
    assert result.confidential_manifest[0].category == "contact_info"  # marker wins, not email_address
    assert "reviewer1@example.org" not in result.redacted_text


def test_public_manifest_never_contains_original_text():
    text = "<<SENSITIVE:secret>>the actual sensitive payload<<END>>"
    result = redact(text)
    dumped = str(result.public_manifest)
    assert "the actual sensitive payload" not in dumped
    assert "original_text" not in result.public_manifest[0]


def test_confidential_manifest_hash_matches_original_span():
    import hashlib
    text = "<<SENSITIVE:secret>>exact payload<<END>>"
    result = redact(text)
    entry = result.confidential_manifest[0]
    assert entry.original_text == "exact payload"
    assert entry.original_text_hash == hashlib.sha256(b"exact payload").hexdigest()


def test_public_summary_counts_by_category():
    text = "<<SENSITIVE:a>>x<<END>> <<SENSITIVE:a>>y<<END>> <<SENSITIVE:b>>z<<END>>"
    result = redact(text)
    assert result.public_summary() == {"a": 2, "b": 1}


def test_semantic_flagger_only_runs_on_uncovered_paragraphs():
    text = (
        "Paragraph one is unremarkable.\n\n"
        "<<SENSITIVE:known>>Paragraph two is already marked by the author.<<END>>\n\n"
        "Paragraph three mentions the trigger word banana."
    )
    flagger = StubKeywordSemanticFlagger(trigger_terms=["banana"], category="stub_flagged")
    result = redact(text, semantic_flagger=flagger)
    categories = [e.category for e in result.confidential_manifest]
    assert "known" in categories
    assert "stub_flagged" in categories
    assert "Paragraph one is unremarkable." in result.redacted_text  # untouched
    assert "banana" not in result.redacted_text


def test_semantic_flagger_finding_nothing_leaves_text_unchanged():
    text = "Nothing sensitive here at all, just routine numbers and dates."
    flagger = StubKeywordSemanticFlagger(trigger_terms=["banana"])
    result = redact(text, semantic_flagger=flagger)
    assert result.redacted_text == text
    assert result.confidential_manifest == []


def test_no_rules_and_no_flagger_is_a_no_op():
    text = "Plain report, nothing configured to catch."
    result = redact(text)
    assert result.redacted_text == text
    assert result.public_manifest == []


def test_entry_ids_are_unique_and_referenced_correctly_in_output():
    text = "<<SENSITIVE:a>>first<<END>> and <<SENSITIVE:b>>second<<END>>"
    result = redact(text, id_prefix="rep42")
    ids = [e.entry_id for e in result.confidential_manifest]
    assert len(ids) == len(set(ids))
    for entry_id in ids:
        assert f"#{entry_id}" in result.redacted_text
