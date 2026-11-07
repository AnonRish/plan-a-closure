## What changed

<!-- Describe the evidence, code, or documentation change in concrete terms. -->

### Evidence / provenance
- [ ] I identified the exact source URL or retained artifact.
- [ ] I recorded the observation/capture date where applicable.
- [ ] I preserved the raw publisher value and separated any normalized value.
- [ ] I did not convert a missing public record into an absence claim.
- [ ] I kept unlike MW measurements separate.

### Track 3 state
- [ ] I used the canonical Track 3 schema in data/track3_evidence_schema.json.
- [ ] I preserved the distinction between discovery lead, evidence, derived observation, and unknown.
- [ ] For physical evidence, I included scene/record identifiers, source URL, date, method, and quality metadata.
- [ ] For a correction, I identified the prior evidence record and explain the superseding evidence.

### Reproducibility
- [ ] I added or updated the appropriate manifest.
- [ ] I added/updated self-tests or validation where the code path changed.
- [ ] Generated artifacts were produced from a documented command/workflow.
- [ ] I did not commit secrets, private contact information, or unsupported conclusions.

### Canonical research handoff
For evidence/research contributions, use data/track3/research_submission_schema.json and include:
- task_id, result_status, site_name, epoch_id, target
- source_name, source_url, source_kind, record_id_or_locator
- publication_date, accessed_date, site_specificity, evidence_summary
- field_or_domain, normalized_value, raw_value, units, temporal_scope, confidence, notes

### Checks run
<!-- Replace this line with exact commands and results. -->
- python validate_track3_ledger.py
- python validate_physical_provenance.py

### Reviewer notes
<!-- Explain any intentional limitations, unresolved ambiguity, or non-additive accounting. -->