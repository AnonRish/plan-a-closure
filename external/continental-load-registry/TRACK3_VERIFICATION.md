# Track 3 verification procedure

## Purpose

This repository uses a claim-level verification model rather than a single facility-wide score. A facility can pass one narrowly defined check and remain UNKNOWN or NOT TESTED on another.

## Status rules

- **PASS** — the evidence requirements for the exact claim are satisfied.
- **FAIL** — explicit evidence contradicts the exact claim.
- **UNKNOWN** — the test/search was attempted but the evidence is insufficient to resolve PASS vs FAIL.
- **NOT TESTED** — the test was not executed.
- **NOT APPLICABLE** — the claim does not apply and the reason is recorded.
- **UNASSESSED** — no verifier has yet assigned a result.

**No evidence → UNKNOWN when the claim was actually tested. No evidence is never a reason for PASS. An unrun test is NOT TESTED.**

## Reproducible run

From a clean checkout:

```
python build_track3_verification.py
python verify_track3.py
```

The builder reads the repository-hosted Epoch AI site registry, queue registry embedded in `index.html`, site-level evidence records, physical-verification state and site-level power observations. It emits:

- `data/track3/detection_universe.json`
- `data/track3/verification_protocol.json`
- `data/track3/verification_results.json`
- `data/track3/absence_testing.json`

The read-only verifier checks schema/status invariants, facility cardinality, and the rule that a PASS/FAIL result must carry an evidence reference.

## Track 3 detection

The current detection layer contains the 93-site Epoch research universe plus a broader surveillance population of queue/request records that have no conservative direct project-name match to Epoch.

Surveillance labels are deliberately weaker than verification claims:

- `KNOWN_AI_COMPUTE` means the retained Epoch record has a positive current H100-equivalent field. This is a publisher/derived-data classification, not independent physical confirmation.
- `PROBABLE_AI_COMPUTE` means the facility remains in the Epoch AI-data-center universe without a positive current H100-equivalent field.
- `AI_COMPUTE_CANDIDATE` means an outside-Epoch queue/request row contains an AI/compute/data-center signal. It is a surveillance candidate, not a claim that AI computation is operating there.
- `UNKNOWN_LARGE_COMPUTE` is retained when a large-load row has no strong classifier signal.
- `NON_AI_INDUSTRIAL_CONTROL_GROUP` is a false-positive control population based on a strong industrial/manufacturing signal without an AI/compute signal.

## Cross-checking

The source cross-check records Epoch membership, queue/site evidence, retained company/regulatory or permit references, DC Byte availability, and the current remote-sensing state.

DC Byte is treated as an external comparison source, not as silently imported data. The current repository records its coverage/methodology as a source to check, but does not represent a facility-level DC Byte match without an actual retained record.

Company disclosure and permit counts are conservative indicators derived from retained source URLs/text. They are not equivalent to successful verification.

Satellite availability is distinct from satellite ingestion. The current physical layer retains the source families, but no site-level optical/TIR/SAR numeric observations are promoted to a verification PASS until those observations are actually acquired and retained.

## Absence testing

A no-match statement must have a retained search record containing:

- the facility/request identifier;
- the source/database name;
- the source URL or record locator;
- the capture date;
- the search scope;
- the search result.

The absence ledger includes only explicit `NO_MATCH_FOUND` evidence records. A missing value in a table, an unmatched name, or an unqueried source is not converted into a no-found claim.

## Independent verification

`verify_track3.py` and `.github/workflows/track3_independent_verifier.yml` are read-only and do not modify data. This creates operational separation between the publication/build workflow and the integrity verifier. It is not a claim that the GitHub repository itself is an independent institution; an external verifier should run the same procedure against a fixed commit.

## Signed/auditable records

`.github/workflows/track3_verification.yml` packages the exact verification outputs into an audit bundle and uses GitHub Artifact Attestations. GitHub documents that public-repository attestations are Sigstore-backed, cryptographically signed provenance/integrity claims, and can be verified with the GitHub CLI. The workflow therefore provides a cryptographically verifiable bundle-level audit trail; it does not turn the underlying empirical claims into truth by itself.

## Disputes and corrections

Use the **Evidence correction / dispute** issue form. Corrections are append-only: the original record remains in Git history, a correction references the exact facility/evidence/verification ID, and the new record documents the supporting source and rationale.
