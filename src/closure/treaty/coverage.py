"""Traceability matrix for two draft agreements: every article of MIRI's draft agreement (arXiv:2511.10783) and of
FLI's Draft Articles, with what implements it here and an honest status. `validate()` runs the same checks as the Plan
A matrix (closure.coverage): each row that claims code must point at real code and a real test, so the matrix cannot
drift from the repository. `closure treaty coverage --write docs/AGREEMENTS_COVERAGE.md` regenerates the document.

status: implemented (code and tests here) | hardware-gated (code here; what it checks has to be measured on hardware)
| partial (the note says what is missing) | physical (hardware, buildings, enclosures) | policy (law, diplomacy,
institutions, judgement)."""
from __future__ import annotations

from ..coverage import STATUSES, _r, validate_rows

MA = "MIRI agreement"
FLI = "FLI Draft Articles"
TA, TT, TTT = "tests/test_treaty_agreements.py::", "tests/test_treaty.py::", "tests/test_treaty_torch.py::"
M, C, F, O = ("closure.treaty.asi_agreement.", "closure.treaty.chipauth.", "closure.treaty.fli_articles.",
              "closure.treaty.obligations.")
SW, PH, PO = "software", "physical", "policy"

ROWS = [
    # ==== MIRI's draft agreement =======================================================================================
    _r("MA-I", f"{MA} > Art. I", "Primary purpose: no artificial superintelligence and nothing that materially advances "
       "toward it", PO, "policy", note="Carried out by the articles below."),
    _r("MA-II.4", f"{MA} > Art. II s.4", "FLOP counted as FP16-equivalent or in the format used, whichever is higher",
       SW, "implemented", [M + "counted_flop"], [TA + "test_flop_counting_takes_the_higher_of_fp16_equivalent_and_native"],
       note="The text gives no conversion; bit-length scaling is the default and any other can be passed."),
    _r("MA-II.8-10", f"{MA} > Art. II ss.8-10", "Strict Threshold 1e24, Strict Post-training Threshold 1e23, Monitored "
       "Threshold 1e22", SW, "implemented", [M + "classify_run", "closure.treaty.thresholds.THRESHOLDS"],
       [TA + "test_run_classes_follow_article_iv", TT + "test_miris_agreement_thresholds_are_named_and_usable"],
       note="Whether post-training counts toward 1e24 is not stated: counted by default (cumulative=True)."),
    _r("MA-II.11", f"{MA} > Art. II s.11", "Advanced chips: at least as advanced as the 28 nm node", SW, "implemented",
       [M + "is_advanced_chip"], [TA + "test_advanced_chips_are_28nm_or_better"]),
    _r("MA-II.15", f"{MA} > Art. II s.15", "H100-equivalent: 989 TFLOP/s FP16 or TPP 15,824; TPP = 2 x MacTOPS x bit "
       "length", SW, "implemented", [M + "tpp", M + "tpp_from_tflops", M + "chip_tpp", M + "h100e_compute"],
       [TA + "test_h100e_tpp_and_the_ccc_reference_values"]),
    _r("MA-II.16", f"{MA} > Art. II s.16", "Covered chip cluster: more than 16 H100e of compute or memory, networked by "
       "co-location, more than 25 Gbit/s between hosts, or shared work", SW, "implemented",
       [M + "covered_clusters", M + "ccc_reference"], [TA + "test_covered_clusters_by_site_bandwidth_and_shared_work"],
       note="Groups are merged while the links between two groups sum to more than 25 Gbit/s (the reading taken here)."),
    _r("MA-II.16b", f"{MA} > Art. II s.16 (note)", "The bounds should make training across sub-CCC sets of chips "
       "difficult", SW, "implemented", [M + "cross_site_training_gbps", "closure.treaty.bandwidth.needed_gbps"],
       [TA + "test_25_gbits_does_not_stop_training_across_two_sub_ccc_sets"],
       note="Finding: two 16-H100e sets on 25 Gbit/s train synchronously at a 4M-token batch with no slowdown."),
    _r("MA-II.16c", f"{MA} > Art. II s.16", "'Networked to perform workloads together': knowing what chips run",
       SW, "hardware-gated", ["closure.traffic.traffic_closure", "closure.trial.run_trial"],
       ["tests/test_traffic.py::test_closure_flags_unknown_flow_and_extra_bytes",
        "tests/test_trial.py::test_full_sim_trial_is_verifiable_and_sane"],
       note="The clause that catches training across sub-CCC sets; it needs the traffic and energy closure on site."),
    _r("MA-II.20", f"{MA} > Art. II s.20, Art. IV s.5", "AI Technique Whitelist: runs above the Monitored Threshold use "
       "listed techniques only", SW, "implemented", [M + "approve_monitored_run"],
       [TA + "test_a_monitored_run_needs_both_sides_inspectors_and_the_whitelist"],
       note="What goes on the list is the CTB's decision."),
    _r("MA-III.3a", f"{MA} > Art. III s.3(a)", "Executive Council: initially the U.S. and the PRC", PO, "policy"),
    _r("MA-III.3c", f"{MA} > Art. III s.3(c)", "Proactive Council decisions by consensus; each member may veto CTB "
       "decisions", SW, "implemented", [M + "council_consensus", M + "ctb_decision_stands", M + "veto_record"],
       [TA + "test_council_consensus_and_vetoes_over_the_ctb"], note="No veto window is set: a decision stands until vetoed."),
    _r("MA-III.4b", f"{MA} > Art. III s.4(a)-(b)", "Director-General: four-year term, renewable once", SW, "implemented",
       [O + "term_problems"], [TA + "test_calendar_months_and_term_limits"]),
    _r("MA-III.4d", f"{MA} > Art. III s.4(d)(i)", "Emergency changes to thresholds and cluster size last 30 days, then "
       "need Council approval", SW, "implemented", [M + "emergency_change", M + "thresholds_in_force"],
       [TA + "test_emergency_changes_lapse_after_30_days_without_council_approval",
        TA + "test_obligation_deadlines_for_the_miri_agreement"],
       note="Changes to research boundaries are not numbers and are not modelled."),
    _r("MA-III.5", f"{MA} > Art. III s.5", "Budget from the Council members' assessed contributions", PO, "policy"),
    _r("MA-IV.1-3", f"{MA} > Art. IV ss.1-3", "No training above the Strict Thresholds; runs above the Monitored "
       "Threshold declared and approved; nothing below it", SW, "implemented", [M + "classify_run"],
       [TA + "test_run_classes_follow_article_iv"]),
    _r("MA-IV.2ab", f"{MA} > Art. IV s.2(a)-(b)", "Report code, data and a FLOP estimate before starting; written "
       "approval from U.S. and PRC inspectors", SW, "implemented",
       [M + "declaration", M + "declaration_problems", M + "approve_monitored_run"],
       [TA + "test_a_monitored_run_needs_both_sides_inspectors_and_the_whitelist"],
       note="A signature cannot show that the inspector was physically present."),
    _r("MA-IV.2c", f"{MA} > Art. IV s.2(c)", "Inspectors may not remove storage devices or data", PH, "physical"),
    _r("MA-IV.2d", f"{MA} > Art. IV s.2(d)", "The CTB monitors declared runs and receives checkpoints", SW, "hardware-gated",
       [M + "within_declaration", "closure.treaty.mockrun.run_drill"],
       [TA + "test_a_run_is_checked_against_its_declaration",
        TTT + "test_the_provider_stops_the_job_within_its_budget_and_checks_its_start"],
       note="A mock run checks the stop at a budget on a GPU; checkpoint review is not code."),
    _r("MA-IV.2e", f"{MA} > Art. IV s.2(e)", "The CTB can pause a run or a class of runs", SW, "partial",
       ["closure.treaty.mockrun.run_drill"], [TTT + "test_the_provider_stops_the_job_within_its_budget_and_checks_its_start"],
       note="That a provider can stop a run, and how fast, is measured; the order itself is the CTB's."),
    _r("MA-IV.2fg", f"{MA} > Art. IV s.2(f)-(g), s.4", "CTB security, sharing with both Parties, halting runs found "
       "above the thresholds, carve-outs", PO, "policy"),
    _r("MA-V.1", f"{MA} > Art. V s.1", "Covered clusters in declared facilities, each within 12 hours of an "
       "international airport", SW, "implemented", [M + "airport_reach_problems"], [TA + "test_airport_reach"],
       note="Travel times are surveyed, not computed; siting and consolidation orders are policy."),
    _r("MA-V.2", f"{MA} > Art. V s.2", "Stocks below the CCC size are not aggregated, networked or rotated to evade "
       "monitoring", SW, "hardware-gated", [M + "covered_clusters", "closure.traffic.traffic_closure"],
       [TA + "test_covered_clusters_by_site_bandwidth_and_shared_work", "tests/test_traffic.py::test_closure_flags_unknown_flow_and_extra_bytes"]),
    _r("MA-V.3", f"{MA} > Art. V s.3", "Locate, inventory and consolidate covered clusters within 120 days", SW,
       "implemented", [O + "check", O + "RULES"], [TA + "test_obligation_deadlines_for_the_miri_agreement"]),
    _r("MA-V.4", f"{MA} > Art. V s.4", "CTB monitoring and chain-of-custody records", SW, "partial",
       ["closure.evidence.Chain"], ["tests/test_evidence.py::test_chain_detects_tampering_and_truncation"],
       note="Hash-chained, signed records; what the custodians record is theirs to do."),
    _r("MA-V.5", f"{MA} > Art. V s.5", "Register of covered clusters within 120 days (location, type, quantity, "
       "identifiers, interconnects), updated at least every 90 days", SW, "implemented",
       [M + "register_problems", O + "check"],
       [TA + "test_register_entries_and_transfers", TA + "test_obligation_deadlines_for_the_miri_agreement"]),
    _r("MA-V.6", f"{MA} > Art. V s.6", "Chip transfers: notice no less than 14 days ahead, CTB approval first; "
       "emergency transfers notified and verified", SW, "implemented", [M + "transfer_check", O + "check"],
       [TA + "test_register_entries_and_transfers", TA + "test_obligation_deadlines_for_the_miri_agreement"]),
    _r("MA-V.7", f"{MA} > Art. V s.7", "Decommissioned chips count as functional until the CTB certifies their "
       "destruction; no salvage or resale without authorisation", SW, "implemented",
       [M + "ChipStock.certify_destruction", M + "ChipStock.functional_h100e", M + "ChipStock.resale_allowed"],
       [TA + "test_decommissioned_chips_count_until_destruction_is_certified"],
       note="The destruction itself is physical."),
    _r("MA-VI.1-3", f"{MA} > Art. VI ss.1-3", "Monitoring of chip and memory production; production halts where "
       "tracking is not feasible", SW, "partial",
       ["closure.pause.fab.reconcile_fab", "closure.pause.fab.custody_balance", "closure.pause.fab.samples_needed"],
       ["tests/test_pause_fab.py::test_reconcile_fab_flags_unlogged_wafers_and_missing_dies",
        "tests/test_pause_fab.py::test_custody_and_litho_reconciliation"],
       note="Fab accounting from the hardwired-pause layer; inspectors in fabs are physical."),
    _r("MA-VI.4-6", f"{MA} > Art. VI ss.4-6", "Transfers of new chips (presumed approved among Parties, denied to "
       "others), of equipment (Council consensus), of non-AI chips", SW, "implemented", [M + "transfer_check"],
       [TA + "test_register_entries_and_transfers"]),
    _r("MA-VI.7", f"{MA} > Art. VI s.7", "The Council may cap annual AI chip production", PO, "policy",
       note="No figure is given."),
    _r("MA-VII.1-2", f"{MA} > Art. VII ss.1-2", "Continuous on-site verification of declared clusters to detect "
       "prohibited uses", SW, "hardware-gated", ["closure.trial.run_trial", "closure.traffic.traffic_closure"],
       ["tests/test_trial.py::test_full_sim_trial_is_verifiable_and_sane"],
       note="The energy, traffic and state closure this repository builds; the registered trial needs H100-class GPUs."),
    _r("MA-VII.3", f"{MA} > Art. VII s.3", "Where verification is insufficient, hardware is powered off and its "
       "non-operation verified continually", SW, "hardware-gated",
       [M + "powered_off", "closure.dcbus.check_absolute_power", "closure.treaty.cli.cmd_asi_off"],
       [TA + "test_powered_off_needs_low_power_and_no_gaps", TA + "test_treaty_commands_for_the_agreements"],
       note="`closure treaty asi-off` over an independent DC-coupled meter's trace (meter-log)."),
    _r("MA-VII.4", f"{MA} > Art. VII s.4", "Restrictions on bandwidth and latency, FLOP/s and memory bandwidth, "
       "numerical precision", SW, "hardware-gated", ["closure.treaty.bandwidth.assess", "closure.traffic.traffic_closure"],
       [TT + "test_interconnect_arithmetic", "tests/test_traffic.py::test_closure_flags_unknown_flow_and_extra_bytes"],
       note="The arithmetic is here; the limits' values are not in the text."),
    _r("MA-VII.5-6", f"{MA} > Art. VII ss.5-6", "Verification differentiated by facility; CTB research on verification",
       PO, "policy"),
    _r("MA-VIII", f"{MA} > Art. VIII", "Restricted research: training methods, distributed training, fabrication, chip "
       "designs; controlled or prohibited", PO, "policy",
       note="s.1(b) is the agreement's answer to MA-II.16b; the published infrequent-synchronisation methods need no new research."),
    _r("MA-IX", f"{MA} > Art. IX", "Verifying research restrictions: agencies, interviews, auditors, reporting", PO, "policy"),
    _r("MA-X.1-2", f"{MA} > Art. X ss.1-2", "Information consolidation, national technical means, whistleblower "
       "protections", PO, "policy"),
    _r("MA-X.3", f"{MA} > Art. X s.3", "Challenge inspections: Council consensus, access within 24 hours, inspectors "
       "approved by both Parties, at most 20 a year", SW, "implemented",
       [M + "ChallengeInspections.call", M + "ChallengeInspections.team_problems", M + "access_in_time"],
       [TA + "test_challenge_inspections_consensus_quota_and_inspectors", TA + "test_obligation_deadlines_for_the_miri_agreement"],
       note="Plain reading: the Party to be inspected joins the consensus, so a Council member can refuse its own "
            "inspection; on a calendar-year reading 40 can fall within three weeks."),
    _r("MA-X.4", f"{MA} > Art. X s.4", "Independent verification by both sides; the CTB shares everything unfiltered",
       PO, "policy"),
    _r("MA-XI.1", f"{MA} > Art. XI s.1", "A concern is acknowledged within 36 hours and clarified within 5 days", SW,
       "implemented", [O + "check"], [TA + "test_obligation_deadlines_for_the_miri_agreement"]),
    _r("MA-XI.2-3", f"{MA} > Art. XI ss.2-3", "Escalation to the Council and its measures", PO, "policy"),
    _r("MA-XII", f"{MA} > Art. XII ss.1-5, 7-9", "Protective Actions: when, how far, when they end", PO, "policy"),
    _r("MA-XII.6", f"{MA} > Art. XII s.6", "A public Protective Action Statement with four elements", SW, "implemented",
       [M + "statement_problems"], [TA + "test_protective_action_statements_need_four_elements"]),
    _r("MA-XIII", f"{MA} > Art. XIII", "CTB reviews and evaluations of declared models", PO, "policy",
       note="Evaluations show capabilities, not their absence (Barnett and Thiergart)."),
    _r("MA-XIV.1-4", f"{MA} > Art. XIV ss.1-4", "Amendments take effect on Council consensus", SW, "implemented",
       [M + "council_consensus"], [TA + "test_council_consensus_and_vetoes_over_the_ctb"]),
    _r("MA-XIV.5", f"{MA} > Art. XIV s.5", "Review conferences three years after entry into force and every three years",
       SW, "implemented", [O + "check"], [TA + "test_obligation_deadlines_for_the_miri_agreement"]),
    _r("MA-XV.1-2", f"{MA} > Art. XV ss.1-2", "Unlimited duration; withdrawal on 12 months' notice", SW, "implemented",
       [O + "check", O + "until"], [TA + "test_obligation_deadlines_for_the_miri_agreement"]),
    _r("MA-XV.3-4", f"{MA} > Art. XV ss.3-4", "During notice, clusters removed or made inoperable; Art. XII applies "
       "after", PH, "physical"),
    _r("MA-D.3", f"{MA} > Appendix D.3, Tables 1-2", "Time for each cluster size to reach each threshold", SW,
       "implemented", [M + "tables", M + "compare_tables", M + "time_to_thresholds"],
       [TA + "test_tables_1_and_2_reproduce_at_990_and_differ_at_989_in_four_cells"],
       note="Every cell matches 990 TFLOP/s per H100e; with the definition's 989, four cells change in the last digit."),
    _r("MA-D.3.1", f"{MA} > Appendix D.3.1", "Staged registration: Day 1, Day 10, Day 100, Year 2", SW, "implemented",
       [M + "registration_stage"], [TA + "test_registration_stages_and_the_16_h100e_boundary"],
       note="Table 1 registers 16-H100e clusters in Year 2, but Art. II s.16 covers only more than 16."),
    _r("MA-D.note", f"{MA} > Art. V notes, On the Definition of CCCs", "16 H100s at FP8 and 50% utilization: 7.3 days "
       "to 1e22, 2 years to 1e24", SW, "implemented", [M + "fp8_note_days"],
       [TA + "test_the_fp8_note_gives_7_3_days_and_2_years"]),
    # ==== FLI's Draft Articles =========================================================================================
    _r("FLI-1", f"{FLI} > Art. 1", "Object and purpose", PO, "policy"),
    _r("FLI-2.gcr", f"{FLI} > Art. 2", "Global catastrophic risk: more than 50 people killed or seriously injured, or "
       "more than USD 1 billion of damage, in a single incident", SW, "implemented", [F + "is_global_catastrophic"],
       [TA + "test_global_catastrophic_scale_is_strictly_more_than_50_people_or_a_billion"],
       note="Tests an incident's scale; 'foreseeable and material' is a judgement."),
    _r("FLI-2.terms", f"{FLI} > Art. 2", "Advanced AI, systemic risk, AI hardware: no compute threshold", PO, "policy",
       note="The draft avoids continuous measures (Art. 3 commentary)."),
    _r("FLI-3", f"{FLI} > Art. 3(1)-(4)", "No development or deployment of systems with Annex A uses, risks or "
       "capabilities; guarantees to the Agency", PO, "policy",
       note="An Annex A finding is an evaluation's; evaluations cannot show absence."),
    _r("FLI-4.1", f"{FLI} > Art. 4(1)", "AI hardware compatible with verification and enforcement", PH, "physical",
       note="The authorization protocol it enables is software here (FLI-C)."),
    _r("FLI-4.2", f"{FLI} > Art. 4(2)", "Prevent the proliferation of non-compliant hardware", PO, "policy"),
    _r("FLI-5", f"{FLI} > Art. 5(1)-(3)", "A privacy-preserving, secure hardware-enabled verification mechanism (Annex "
       "B), run by the Agency", PO, "policy", note="The mechanism's parts are the Annex B rows."),
    _r("FLI-6.1-2", f"{FLI} > Art. 6(1)-(2)", "Investigate before enforcing, unless a global catastrophic risk is "
       "suspected", SW, "implemented", [F + "enforcement_may_start"], [TA + "test_enforcement_order_and_lifting"]),
    _r("FLI-6.3", f"{FLI} > Art. 6(3)", "The burden reverts to the Agency, which lifts enforcement if it cannot show a "
       "continued breach", SW, "implemented", [F + "enforcement_must_lift", C + "Enforcer.resume"],
       [TA + "test_enforcement_order_and_lifting", TA + "test_the_chip_refuses_work_without_allowance_and_resumes_when_reauthorized"]),
    _r("FLI-7.1-3", f"{FLI} > Art. 7(1)-(3)", "Safety standards on six practices, by an expert panel, approved by the "
       "Conference", PO, "policy"),
    _r("FLI-7.4-5", f"{FLI} > Art. 7(4)-(5)", "A certificate of compliance, renewed by a third-party evaluator every six "
       "months; no certificate, no development", SW, "implemented",
       [F + "Certificates.certify", F + "Certificates.may_operate", O + "check"],
       [TA + "test_certificates_expire_after_six_months_and_need_a_licensed_evaluator",
        TA + "test_obligation_deadlines_for_the_fli_articles"]),
    _r("FLI-7.6-9", f"{FLI} > Art. 7(6), (8), (9)", "Evaluators report to the Agency; guidelines; public reports", PO, "policy"),
    _r("FLI-7.7", f"{FLI} > Art. 7(7)", "Evaluator licences: expertise, conflicts, background checks, continuous "
       "monitoring", SW, "implemented", [F + "licence_problems", F + "Certificates.license"],
       [TA + "test_certificates_expire_after_six_months_and_need_a_licensed_evaluator"]),
    _r("FLI-7.10-11", f"{FLI} > Art. 7(10)-(11)", "Only States Parties challenge; accepted or rejected within a week; "
       "provisional suspension", SW, "implemented",
       [F + "Certificates.challenge", F + "Certificates.decide", F + "Certificates.overdue", O + "check"],
       [TA + "test_certificates_expire_after_six_months_and_need_a_licensed_evaluator",
        TA + "test_obligation_deadlines_for_the_fli_articles"],
       note="Who decides the merits after acceptance is not stated; resolve() records the outcome."),
    _r("FLI-7.12", f"{FLI} > Art. 7(12)", "Third parties may comment", PO, "policy"),
    _r("FLI-8.2", f"{FLI} > Art. 8(2)", "Each State Party reports on its emergency measures every year", SW, "implemented",
       [O + "check"], [TA + "test_obligation_deadlines_for_the_fli_articles"]),
    _r("FLI-8", f"{FLI} > Art. 8(1), (3)-(8)", "Emergency measures, peer review, improvement plans, assistance and "
       "compensation", PO, "policy"),
    _r("FLI-9", f"{FLI} > Art. 9(1)-(2)", "Technical cooperation", PO, "policy"),
    _r("FLI-10.1-3", f"{FLI} > Art. 10(1)-(3)", "A global benefit-sharing framework, possibly with dividends", PO, "policy"),
    _r("FLI-10.4-5", f"{FLI} > Art. 10(4)-(5)", "A tax of at least 5% on AI gains; evaders are not eligible for a "
       "certificate", SW, "implemented", [F + "tax_compliant", F + "Certificates.certify"],
       [TA + "test_agency_funding_and_the_tax", TA + "test_certificates_expire_after_six_months_and_need_a_licensed_evaluator"]),
    _r("FLI-11", f"{FLI} > Art. 11(1)-(2)", "National sanctions and contact points", PO, "policy"),
    _r("FLI-12.2-3", f"{FLI} > Art. 12(2)-(3)", "A session every quarter; rules of procedure within 15 days of entry "
       "into force", SW, "implemented", [O + "check"], [TA + "test_obligation_deadlines_for_the_fli_articles"]),
    _r("FLI-12.4", f"{FLI} > Art. 12(4)", "Extraordinary sessions at the request of at least a third of the States "
       "Parties", SW, "implemented", [F + "extraordinary_session"], [TA + "test_conference_majorities_and_weighted_matters"]),
    _r("FLI-12.7", f"{FLI} > Art. 12(7)", "Simple majority, one vote per State; contribution-weighted votes for the "
       "Director-General, the Agency's rules and verification and enforcement mechanisms", SW, "implemented",
       [F + "conference_decision", F + "fewest_to_decide", F + "weighted_power"],
       [TA + "test_conference_majorities_and_weighted_matters",
        TA + "test_four_economies_decide_weighted_matters_under_a_gdp_stand_in"],
       note="Finding (GDP as a stand-in for contributions): the four largest economies hold 51% of the weighted vote."),
    _r("FLI-12.1-6", f"{FLI} > Art. 12(1), (5)-(6)", "Composition, remote sessions, functions", PO, "policy"),
    _r("FLI-13.3", f"{FLI} > Art. 13(3)", "Director-General: three-year term, renewable once", SW, "implemented",
       [O + "term_problems"], [TA + "test_calendar_months_and_term_limits"]),
    _r("FLI-13.9l", f"{FLI} > Art. 13(9)(l)", "Annual review of the annexes", SW, "implemented", [O + "check"],
       [TA + "test_obligation_deadlines_for_the_fli_articles"]),
    _r("FLI-13.10", f"{FLI} > Art. 13(10), 14(6)(c)", "The Agency is funded by 1% of the contributions", SW, "implemented",
       [F + "agency_funding"], [TA + "test_agency_funding_and_the_tax"]),
    _r("FLI-13", f"{FLI} > Art. 13(1)-(2), (4)-(9), (11)", "The Agency: staff, independence, functions, immunities", PO,
       "policy"),
    _r("FLI-14", f"{FLI} > Art. 14(1)-(10)", "The Global AI Fund: Board, secretariat, trustee, evaluations", PO, "policy"),
    _r("FLI-15.2", f"{FLI} > Art. 15(1)-(2)", "Amendments adopted by two thirds of the States Parties", SW, "implemented",
       [F + "amendment_adopted"], [TA + "test_conference_majorities_and_weighted_matters"]),
    _r("FLI-15.3", f"{FLI} > Art. 15(3)", "The Agency may not recommend removing an Annex A item", SW, "implemented",
       [F + "annex_a_change_problems", F + "ANNEX_A"], [TA + "test_the_agency_may_not_recommend_removing_an_annex_a_item"],
       note="That changes to Annexes B and C must improve verification is a judgement."),
    _r("FLI-16", f"{FLI} > Art. 16(1)-(5)", "The Dispute Settlement Panel", PO, "policy",
       note="Its one-week deadline for challenges is FLI-7.10-11."),
    _r("FLI-17", f"{FLI} > Art. 17(1)", "Universality", PO, "policy"),
    _r("FLI-18", f"{FLI} > Art. 18(1)", "Relationship with other rules of international law", PO, "policy"),
    _r("FLI-A", f"{FLI} > Annex A", "Prohibited uses, risks and capabilities (CBRN, cyber, loss of control, epistemic "
       "manipulation)", PO, "policy", note="Recorded as data (fli_articles.ANNEX_A) for Art. 15(3); a finding is an "
       "evaluation's."),
    _r("FLI-B1.ab", f"{FLI} > Annex B.1(1)(a)-(b), (2)", "Interviews, intelligence, whistleblower programmes", PO, "policy"),
    _r("FLI-B1.c", f"{FLI} > Annex B.1(1)(c)", "A chip registry with a unique ID and declared location for each chip", SW,
       "implemented", [F + "registry_problems", "closure.pause.registry.Registry.register", "closure.ledger.StockLedger"],
       [TA + "test_chip_registry_needs_unique_ids_and_locations", "tests/test_pause_whitelist_registry.py::test_registry_lifecycle_and_dark_charge"]),
    _r("FLI-B1.d", f"{FLI} > Annex B.1(1)(d)", "Location verification by round-trip delay from trusted servers", SW,
       "hardware-gated", ["closure.treaty.geoloc.check", "closure.pause.registry.consistent_with_claim"],
       [TT + "test_a_nearby_landmark_proves_closeness_and_exposes_a_false_declaration",
        TT + "test_landmark_and_chip_over_tcp_and_tampering_is_caught"],
       note="Needs landmarks and a chip key on machines in known places."),
    _r("FLI-B1.e", f"{FLI} > Annex B.1(1)(e)", "On-site inspections", SW, "partial",
       ["closure.treaty.inspection.sample_size", "closure.treaty.inspection.plan_sample"],
       [TT + "test_sample_size_is_the_smallest_that_reaches_the_assurance"],
       note="How many chips to sample, unpredictably; the inspections are physical."),
    _r("FLI-B2.dc", f"{FLI} > Annex B.2", "Agency-owned neutral data centres, provers' data centres, tamper-evident "
       "hardware, routine inspection", PH, "physical"),
    _r("FLI-B2.perimeter", f"{FLI} > Annex B.2 (commentary (2)(ii))", "Digital perimeter: all network traffic verified by "
       "specialised hardware", SW, "hardware-gated", ["closure.traffic.traffic_closure"],
       ["tests/test_traffic.py::test_closure_flags_unknown_flow_and_extra_bytes"],
       note="Air-gapping (i) and the encrypting gateways (iii) are physical."),
    _r("FLI-B2.commit", f"{FLI} > Annex B.2 (commentary (3))", "Cryptographic commitments inside the perimeter", SW,
       "implemented", ["closure.evidence.commit", "closure.evidence.verify_commit"],
       ["tests/test_evidence.py::test_commit_reveal_binds_the_schedule"]),
    _r("FLI-C.auth", f"{FLI} > Annex C.1 and C.2", "Authorizations: chip, allowed cycles, an ID used once, signed; the "
       "chip refuses work without one", SW, "implemented",
       [C + "authorization", C + "GuaranteeProcessor.receive", C + "GuaranteeProcessor.run"],
       [TA + "test_an_authorization_is_checked_for_signature_chip_and_reuse",
        TA + "test_the_chip_refuses_work_without_allowance_and_resumes_when_reauthorized"],
       note="A software stand-in for the security processor."),
    _r("FLI-C.renew", f"{FLI} > Annex C.1 and C.2 (renewal)", "Automatic renewal 'potentially every few minutes'; no "
       "renewal after a verified violation", SW, "implemented", [C + "Enforcer.withhold", C + "simulate", C + "bank_days"],
       [TA + "test_as_written_a_provider_banks_authorizations_and_runs_on_after_renewal_stops",
        TA + "test_fresh_nonces_and_a_cap_bound_the_run_on_to_about_one_period"],
       note="Finding: as written, unused authorizations can be held back and used after renewal stops; fresh nonces "
            "and a cap bound the run-on to about one period."),
    _r("FLI-C.signer", f"{FLI} > Annex C.1 and C.2 (signer)", "The State Party (C.1) or the Agency (C.2) signs; the "
       "enforcer's key(s)", SW, "implemented", [C + "Enforcer.cosign", C + "GuaranteeProcessor"],
       [TA + "test_national_or_agency_signing_and_two_key_authorizations"]),
    _r("FLI-C.firmware", f"{FLI} > Annex C.1 and C.2 (firmware)", "Firmware updates installed as needed; the ruleset can "
       "change", SW, "implemented", [C + "firmware_update", C + "GuaranteeProcessor.install_firmware"],
       [TA + "test_signed_firmware_updates_refuse_rollback_and_can_rotate_keys"]),
    _r("FLI-C.tamper", f"{FLI} > Annex C.1 and C.2 (enclosures)", "Tamper-proof enclosures; a tamper attempt wipes the "
       "firmware and blows fuses", PH, "physical", note="Modelled as a flag (GuaranteeProcessor.tamper)."),
]


def summary(rows=None) -> dict:
    rows = rows or ROWS
    s = {k: 0 for k in STATUSES}
    for r in rows:
        s[r["status"]] += 1
    sw = [r for r in rows if r["kind"] == "software"]
    s["rows"], s["software_rows"] = len(rows), len(sw)
    s["software_with_code"] = sum(1 for r in sw if r["where"])
    for src in (MA, FLI):
        s[src] = sum(1 for r in rows if r["source"].startswith(src))
    return s


def validate(root=None) -> list:
    errs, _ = validate_rows(ROWS, root)
    errs += [f"{r['id']}: software row without code and a test" for r in ROWS
             if r["kind"] == "software" and not (r["where"] and r["tests"])]
    return errs


def to_markdown() -> str:
    s = summary()
    out = ["# Two draft agreements, article by article (generated by `closure treaty coverage --write`; do not edit by "
           "hand)", "",
           "Sources: [MA] Scher, Abecassis, Barnett and Abeyta, *An International Agreement to Prevent the Premature "
           "Creation of Artificial Superintelligence* (MIRI Technical Governance Team, arXiv:2511.10783, v3); [FLI] "
           "Future of Life Institute with the Centre for International Governance Innovation, *Draft Articles on the "
           "Safe Development and Diffusion of Artificial Intelligence* (web version 2, 18 June 2026, "
           "global-governance.ai). Status: implemented (code and tests here), hardware-gated (code here; what it "
           "checks has to be measured on hardware), partial (the note says what is missing), physical and policy "
           "(outside software).", "",
           f"**{s['rows']} rows**: {s[MA]} for [MA], {s[FLI]} for [FLI]. Software rows: {s['software_rows']}, every one "
           f"with code and a test (implemented {s['implemented']}, hardware-gated {s['hardware-gated']}, partial "
           f"{s['partial']}). Physical {s['physical']}, policy {s['policy']}: not counted as covered.", "",
           "Every article of both texts has at least one row (`tests/test_treaty_agreements.py::"
           "test_every_article_and_annex_has_a_row`). The findings the computations make are in "
           "docs/TREATY_COVERAGE.md under \"What the computations show\".", "",
           "| id | source | requirement | status | implemented by | tests | note |",
           "| --- | --- | --- | --- | --- | --- | --- |"]
    for r in ROWS:
        out.append("| " + " | ".join([r["id"], r["source"], r["requirement"], r["status"],
                                      "<br>".join(f"`{w}`" for w in r["where"]) or "-",
                                      "<br>".join(f"`{t}`" for t in r["tests"]) or "-", r["note"] or "-"]) + " |")
    return "\n".join(out) + "\n"
