# Track 3 Reviewer Checklist — 2026-09-28

This is the current repository-state checklist for reviewing the Continental Large-Load Interconnection & Telemetry Registry as a Track 3 research contribution.

## 1. Verification substance

### Priority reorder for reviewer value

**P0 — close cases before widening.** The dominant remaining test is whether the registry can move genuinely ambiguous public load records from queue entry to a defensible disposition. four closure-pilot cases are now published in `ambiguous-case-studies.html` and `data/track3/ambiguous_case_studies.json`; the separate five-case strict discovery queue is now terminally dispositioned in `data/track3/strict_discovery_case_dispositions_2026-09-28.json`.

**P1 — expand the 93-site Epoch layer only after the closure loop is demonstrated.** Epoch is a useful reference/cross-check universe, but those sites are already publicly identified; more breadth there should not displace closing ambiguous registry cases.

**P2 — strengthen provenance/CI after substantive findings exist.** Artifact hashing, broader experimental CI, and automated integrity checks are valuable, but they are secondary to producing additional closed evidence chains.

**P3 — maintenance surface.** CONTRIBUTING, CITATION, cross-links, and similar repository ergonomics remain useful maintenance work, but they do not demonstrate that the method works.

### Highest-value elements to preserve

- Phase 1 versus Track 3 boundary.
- Queue/interconnection versus satellite/physical-method comparison and explicit blind spots.
- Honest semantics of “100% field accounted”: every defined field has an accounting state; it does not mean every value is known or every facility is verified.
- Explicit distinction between missing public evidence and evidence of absence.
- Published closure pilot with terminal adjudications and unresolved items.


- [x] Reproducible, sourced large-load baseline across nine North American markets.
- [x] Ambiguous tier separates unresolved/undisclosed cases from confirmed identities without guessing.
- [x] Actual processed physical evidence exists: 575 retained derived remote-sensing observations across 92 of 93 Epoch sites, with scene IDs, STAC item URLs, dates, collections, and processing metadata.
- [ ] All 93 Epoch sites have site-specific remote-sensing observations. One site remains without a resolved physical target: OpenAI Stargate UAE. September 11, 2026 Reuters reporting now provides an attributed area-level lead near Al Dhafra Air Base, but no canonical parcel/coordinate has been established, so the site-specific observation gate remains open.
- [x] Four ambiguous-load closure cases are published: three bounded/public-identity outcomes and one intentionally inconclusive case; each locatable case has six derived multi-sensor observations.
- [x] Claim-level verification vocabulary exists: PASS / FAIL / UNKNOWN / NOT_TESTED.
- [x] Facility-level vocabulary is defined in the verifier as VERIFIED_PRESENT / VERIFIED_ABSENT / INCONCLUSIVE, with INCONCLUSIVE remaining the default until the facility-wide end-to-end gate is satisfied.
- [x] Phase 1 versus Track 3 boundary is stated in the main README and public Track 3/Plan A pages.
- [x] Queue-vs-satellite comparison is public and explicitly covers complementary blind spots between electrical intent and physical realization.
- [x] Evasion case is explicit: a project using existing capacity, behind-the-meter/private generation, or another route that avoids a new public interconnection can evade the grid signal.

### Track 3 domain-accounting closure

- [x] 1,395/1,395 defined site-domain cells are in terminal evidence-accounting states (93 sites × 15 domains).
- [x] 559 ASSESSMENT_COMPLETE records explicitly document the current public-evidence ceiling for cells without qualifying retained records.
- [x] ASSESSMENT_COMPLETE is explicitly not evidence of absence and can be reopened when new evidence arrives.

## 2. Provenance and trust

- [x] Core nine-source hashes, byte counts, capture metadata, and filter funnels are documented in SOURCES.md.
- [x] Supplemental evidence is explicitly non-additive where appropriate.
- [x] Physical-source provenance manifest exists at data/track3/physical_source_manifest.json.
- [x] Human-readable physical provenance policy exists at PHYSICAL_SOURCES.md.
- [x] The physical validator rejects false raw SHA-256 claims when source bytes are not retained.
- [x] Per-artifact SHA-256 + byte-count generation for retained physical outputs is automated by refresh_physical_source_manifest.py and validated by validate_physical_provenance.py.
- [x] Track 3 public revision is aligned to 2026-09-28.
- [x] README filename corrected to ground_truth_overrides_example.json.
- [x] Claim-level verification results have been refreshed against the retained physical observations: 450 PASS, 293 UNKNOWN, 1 NOT_TESTED; facility-wide state is 0 VERIFIED_PRESENT / 0 VERIFIED_ABSENT / 93 INCONCLUSIVE. A subsequent verifier workflow run failed only at the Git push race; the workflow has since been hardened with serialized runs and rebase-before-push.

## 3. Reproducibility and engineering rigor

- [x] Core registry self-tests/CI exist.
- [x] Track 3 canonical joins have a dedicated validator.
- [x] Physical-source provenance has a dedicated read-only validator.
- [x] Track 3/Epoch/physical artifacts live on main alongside the registry core; no separate gh-pages Track 3 branch was found.
- [x] Epoch crosswalk is generated by code and validated as a 93-site universe.
- [ ] Broader experimental coverage of ai-2040-verification remains incomplete in CI: its current workflow runs Rust build/tests and Python syntax checking, not every documented experiment.

## 4. Plan A visibility

- [x] Dedicated Plan A bridge page.
- [x] Main README states the Plan A / Phase 1 / Track 3 relationship.
- [x] README inventory names Track 3, Epoch explorer/crosswalk material, API, research console, and bulk downloads.
- [x] CITATION.cff exists.
- [x] Related ai-2040-verification repository is cross-linked in both READMEs.
- [x] One-page standalone Track 3 summary is included in this repository.

## 5. Contribution surface

- [x] Research Operations Console.
- [x] README links to research.html.
- [x] Issue templates exist for evidence correction and Track 3 evidence submissions.
- [x] Pull-request template exists with provenance/validation gates.
- [x] README contains by-role contribution guidance.
- [x] Three good-first-issue entry points are open: #30 BPA expansion, #31 MISO 83-row supplemental layer, #32 physical artifact hashing.

## 6. Honest framing

- [x] Missing evidence is explicitly distinguished from absence.
- [x] Main dashboard field-accounting badge now includes a plain-language semantic tooltip.
- [x] Track 3 page and Plan A page have prominent reviewer summaries.
- [x] Facility-wide certification is not implied by claim-specific PASS values.
- [x] The repository explicitly states that it is not an international U.S.–China verification system.

## 7. Current reviewer bottom line

**Present now:** a real public-data accounting layer, a conservative 93-site Epoch crosswalk, 575 processed remote-sensing observations across 92 sites, a provenance manifest, claim-level verification machinery, a 214-task publisher-only research queue and a separate 24-task observation acquisition queue, and explicit uncertainty semantics. The 93-site × 15-domain Track 3 matrix is now terminally assessed at 1,395/1,395 cells.

**Still incomplete at the empirical/verification level:** interval power telemetry; site-specific physical targeting for the remaining 1 unresolved Epoch site; fuller cooling/transformer/service/regulatory evidence; transaction-level compute accounting; physical inspection; serial continuity and decommissioning/recycling verification; comprehensive covert-site discovery; an independent verification authority; and independent external review. Physical artifact hashing is implemented and validated; it is not a substitute for the missing privileged evidence.

**Correct interpretation:** this is a substantially implemented public-evidence contribution to the broader Track 3 problem, not a completed international verification regime and not evidence that covert compute has been comprehensively detected.
## 8. Global accounting expansion

- [x] Aggregate owner/user/sales/component snapshots are retained as a public-source layer.
- [x] Official public source anchors added for NVIDIA/SEC, TSMC manufacturing context, U.S. Census trade data, GLEIF Level 2 ownership, SEC Exhibit 21, and EU WEEE reporting.
- [x] Certificate model and untraced-pool framework are documented.
- [ ] Transaction-level global vendor sales, serial continuity, physical inspection, and verified decommissioning remain unavailable in the public repository.

## 9. Current primary empirical addition

- [x] External-capability handoff is machine-readable at `data/track3/external_capability_handoff_2026-09-28.json`.
- [x] Interval telemetry intake contract is machine-readable at `data/track3/interval_power_telemetry_protocol.json`.
- [x] The unresolved Stargate UAE physical-target question has a documented lead-only ledger at `data/track3/physical_target_leads.json`; conflicting secondary coordinates are preserved as leads and are not promoted to a canonical target.
- [x] Repository engineering closure is machine-checked by `build_track3_engineering_closure.py` and `data/track3/engineering_closure_2026-09-28.json`, with zero untracked defined repository gaps.

- [x] P3108 / Wild Rose Power Hub has a source-backed 1,300 MW load record, public-project identity from provincial/local government records, an official planning point and legal quarter-section set, and six retained multi-modal remote-sensing observations.
- [x] The five-case strict discovery queue has terminal dispositions for P3066, P3198, P3108, P2958, and P2614, with unresolved physical/identity boundaries explicitly preserved.
- [x] The case remains bounded as a proposed project; operation, energization, transformer event and compute workload are not asserted.
