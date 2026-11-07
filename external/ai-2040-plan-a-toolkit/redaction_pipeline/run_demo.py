from redactor import redact, PatternRule, WatchlistRule, StubKeywordSemanticFlagger

EMAIL_RULE = PatternRule("email", r"[\w.+-]+@[\w-]+\.[\w.-]+", "email_address")
ID_RULE = PatternRule("employee_id", r"\bEMP-\d{4,6}\b", "internal_identifier")

REPORT = """Quarterly compliance summary, cluster 7.

Audit conducted by EMP-4821 (contact: auditor7@example.org) over the reporting period.
No compute-cap violations were found across the sampled workloads.

<<SENSITIVE:exploit_detail>>During testing, the recomputation server's attestation
check could be bypassed by replaying a stale challenge nonce -- full reproduction
steps and affected firmware versions are in the internal ticket.<<END>>

The finding above has been reported to the vendor under responsible disclosure and
is not yet patched.

Reviewed and approved by Jordan Alvarez.

Unrelated administrative note: the office banana supply needs restocking.
"""

if __name__ == "__main__":
    flagger = StubKeywordSemanticFlagger(trigger_terms=["banana"], category="stub_flagged_administrivia")
    result = redact(
        REPORT,
        patterns=[EMAIL_RULE, ID_RULE],
        watchlist=WatchlistRule(names=("Jordan Alvarez",)),
        semantic_flagger=flagger,
    )

    print("=== REDACTED (public-facing) ===")
    print(result.redacted_text)
    print("\n=== PUBLIC MANIFEST (safe to publish alongside the report) ===")
    for entry in result.public_manifest:
        print(f"  {entry['entry_id']:6s} {entry['category']:28s} via {entry['rule_type']:20s} hash={entry['original_text_hash'][:12]}...")
    print(f"\n  category counts: {result.public_summary()}")
    print("\n=== CONFIDENTIAL MANIFEST entries (internal reviewers only -- never publish this) ===")
    for entry in result.confidential_manifest:
        print(f"  {entry.entry_id}: [{entry.category}] {entry.original_text!r}")
