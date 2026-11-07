"""Traceability matrix for "The Feasibility of a Hardwired Pause of Frontier AI Training": every requirement, mechanism and
quantitative method in the paper mapped to what implements it here, with an honest status. `validate()` runs the same checks
as the Plan A matrix (closure.coverage): each claim must point at real code, a real test or a known repository, so the matrix
cannot drift from the repo.

status: implemented (code + tests here) | hardware-gated (code here, needs real hardware or design data) | external (another
repo on the account) | partial | not-started | physical | policy (outside software scope)."""
from __future__ import annotations

from ..coverage import STATUSES, X, _r, validate_rows

HP = "Hardwired Pause"
T = "tests/"
TH, TL, TC, TI, TF = (T + "test_pause_thresholds.py::", T + "test_pause_ledger.py::", T + "test_pause_census.py::",
                      T + "test_pause_inference_only.py::", T + "test_pause_fab.py::")
TW, TT, TM, TB, TK = (T + "test_pause_whitelist_registry.py::", T + "test_pause_transition.py::",
                      T + "test_pause_msic_game.py::", T + "test_pause_bridge.py::", T + "test_pause_claims.py::")
TS = T + "test_pause_supply_chain.py::"
P = "closure.pause."

ROWS = [
    # ---- 1.1 the hardwired pause ---------------------------------------------------------------------------------------------
    _r("HP-1.1", f"{HP} > 1.1 requirement 1", "Prohibit training of new frontier models: an operational test for a beyond-threshold model (compute OR parameter ceiling)",
       "software", "implemented", [P + "thresholds.is_beyond_threshold", P + "thresholds.params_for_compute"],
       [TH + "test_is_beyond_threshold_either_ceiling", TH + "test_chinchilla_mapping_roundtrip"],
       note="The prohibition is law; the test of what it covers is code."),
    _r("HP-1.2", f"{HP} > 1.1 requirement 2", "Whitelist of existing models considered sufficiently safe to deploy", "software", "implemented",
       [P + "whitelist.Whitelist.submit", P + "whitelist.Whitelist.decide", P + "whitelist.Whitelist.servable"],
       [TW + "test_whitelist_deadline_and_duplicates", TW + "test_dewhitelist_rewhitelist_conditions"],
       note="Who decides what is safe enough is the paper's open question (3.2.4) and is not answered by code."),
    _r("HP-1.3", f"{HP} > 1.1 requirement 3", "Allow production of model-restricted inference-only chips, only for whitelisted models", "software", "partial",
       [P + "whitelist.Whitelist.may_fabricate", P + "whitelist.AuthenticatedWeightChip"],
       [TW + "test_dewhitelist_rewhitelist_conditions", TW + "test_awic_accepts_only_hardwired_hash"],
       note="The acceptance rule is modelled; the circuit is physical."),
    _r("HP-1.4a", f"{HP} > 1.1 requirement 4", "Production books close at declared fabs (wafers, prints, dies, rejects)", "software", "implemented",
       [P + "fab.reconcile_fab"], [TF + "test_reconcile_fab_flags_unlogged_wafers_and_missing_dies"]),
    _r("HP-1.4b", f"{HP} > 1.1 requirement 4", "Halt or sharply reduce production of training-capable chips", "policy", "policy"),
    _r("HP-1.5", f"{HP} > 1.1 requirement 5", "Global census of the pre-pause stock of training-capable chips", "software", "partial",
       [P + "census.reconcile", P + "census.k_missing"], [TC + "test_reconcile_documented_but_undeclared", TC + "test_table_5_1_reproduces"],
       note="The estimator and the reconciliation are here; the census itself needs real registration and record data."),
    # ---- 2.3 game theory -----------------------------------------------------------------------------------------------------
    _r("HP-2.3a", f"{HP} > 2.3", "A mutual pause is an equilibrium in a Stag Hunt, not in a Prisoner's Dilemma", "software", "implemented",
       [P + "pausegame.classify", P + "pausegame.pure_equilibria"], [TM + "test_game_classification_and_equilibria"]),
    _r("HP-2.3b", f"{HP} > 2.3", "Repeated play sustains cooperation if players are patient and public signals are informative and timely", "software", "implemented",
       [P + "pausegame.patience_threshold", P + "pausegame.min_detection", P + "pausegame.monitoring_supports_pause"],
       [TM + "test_patience_threshold_closed_form_matches_bisection", TM + "test_monitoring_quality_changes_the_threshold"]),
    _r("HP-2.3c", f"{HP} > 2.3", "Measured verification quality, not asserted quality, decides whether monitoring is informative enough", "software", "hardware-gated",
       [P + "bridge.detection_at", P + "bridge.monitoring_supports_pause"], [TB + "test_detection_at_and_game"],
       note="Feeds a closure trial's per-block detection probability into the threshold. A simulated trial is a method check only."),
    _r("HP-2.2", f"{HP} > 2.2", "Historical lessons: governance needs observable units, imperfect monitoring, benefits and institutions", "policy", "policy"),
    # ---- 3.2 operationalising the technical requirements ---------------------------------------------------------------------
    _r("HP-3.1", f"{HP} > 3.1", "Initial participants: the jurisdictions with a collective monopoly on cutting-edge chips and frontier training, plus high-value chip hosts", "software", "implemented",
       [P + "supply_chain.PARTICIPANTS_3_1", P + "supply_chain.STOCK_HOSTS", P + "supply_chain.census_gaps"],
       [TS + "test_paper_coalition_controls_every_listed_stage", TS + "test_census_gaps"]),
    _r("HP-3.2.1a", f"{HP} > 3.2.1", "Units: H100e, training FLOPs as dynamic matrix multiplication, inference-H100e", "software", "implemented",
       [P + "units.h100e", P + "inference_only.inference_h100e"], [TH + "test_h100e_constants", TI + "test_residual_training_factor_and_fleet_exposure"]),
    _r("HP-3.2.1b", f"{HP} > 3.2.1", "Residual training factor phi, fleet average weighted by inference-H100e, 99.9% reduction at phi = 0.001", "software", "implemented",
       [P + "inference_only.residual_training_factor", P + "inference_only.fleet_phi", P + "inference_only.training_capacity_reduction"],
       [TI + "test_residual_training_factor_and_fleet_exposure", TI + "test_fleet_phi_weighting"]),
    _r("HP-3.2.2a", f"{HP} > 3.2.2, Table 3.1", "Thresholds C_F, C_T, N_T, C_E, C_B and fleet thresholds F_E, F_B", "software", "implemented",
       [P + "thresholds.treaty_thresholds", P + "thresholds.covert_evasion_fleet", P + "thresholds.overt_breakout_fleet"],
       [TH + "test_table_3_1_values_at_full_precision", TH + "test_fleet_threshold_scaling_laws", TH + "test_blind_leap_overhead_closed_form_matches_geometric_sum"],
       note="Reproduces the authors' unrounded values (F_E = 6,387,820; F_B = 175,665,057)."),
    _r("HP-3.2.2b", f"{HP} > 3.2.2 and 6.3", "Thresholds shrink as training-efficiency gains accumulate", "software", "implemented",
       [P + "thresholds.erode", P + "thresholds.years_for_oom", P + "thresholds.pause_delay"],
       [TH + "test_erosion_and_years_for_oom", TH + "test_breakout_sensitivity_and_pause_delay"]),
    _r("HP-3.2.3a", f"{HP} > 3.2.3 and 6.4", "Covert-evasion and overt-breakout ledgers with political and technical discounts and allowances", "software", "implemented",
       [P + "treaty_ledger.Source", P + "treaty_ledger.Ledger", P + "treaty_ledger.section_6_4"],
       [TL + "test_section_6_4_lines_match_reference_values", TL + "test_certify_and_erosion", TL + "test_scenarios_order_the_dark_compute_line"]),
    _r("HP-3.2.3b", f"{HP} > 3.2.3", "The lever: cap each state's licences until both inequalities hold", "software", "implemented",
       [P + "treaty_ledger.Ledger.max_licensed", P + "treaty_ledger.allowance"], [TL + "test_max_licensed_is_the_binding_budget", TL + "test_allowance_schedule"]),
    _r("HP-3.2.4a", f"{HP} > 3.2.4", "Whitelist entries commit to architecture and weights by hash; deployed weights are checked against it; submission deadline", "software", "implemented",
       [P + "whitelist.manifest_hash", P + "whitelist.Whitelist.verify_deployed", P + "whitelist.Whitelist.submit"],
       [TW + "test_manifest_hash_binds_architecture_and_weights", TW + "test_verify_deployed_detects_changed_weights", TW + "test_whitelist_deadline_and_duplicates"]),
    _r("HP-3.2.4b", f"{HP} > 3.2.4 and 7.3.4", "De-whitelisting, re-whitelisting behind external safeguards, approved fine-tunes, tamper-evident record", "software", "implemented",
       [P + "whitelist.Whitelist.de_whitelist", P + "whitelist.Whitelist.re_whitelist", P + "whitelist.Whitelist.approve_finetune"],
       [TW + "test_dewhitelist_rewhitelist_conditions", TW + "test_finetune_requires_servable_base_inherits_conditions_and_follows_recall",
        TW + "test_whitelist_events_are_chained_and_tamper_evident"],
       note="A recall of a base model takes its fine-tunes with it: a design choice the paper does not specify."),
    _r("HP-3.2.4c", f"{HP} > 3.2.4", "A legitimate, independent process for judging whether a model is safe enough to whitelist", "policy", "policy"),
    # ---- 3.3 hardware governance ---------------------------------------------------------------------------------------------
    _r("HP-3.3.1", f"{HP} > 3.3.1 and 6.4.2-6.4.7", "Residual uses of training-capable chips: transitional service, sovereign fleets, scientific preserves, sealed reserves", "software", "implemented",
       [P + "treaty_ledger.section_6_4", P + "treaty_ledger.strategic_reserve", P + "treaty_ledger.scientific_preserve"],
       [TL + "test_section_6_4_lines_match_reference_values", TL + "test_strategic_reserve_and_preserve_lines"]),
    _r("HP-3.3.2a", f"{HP} > 3.3.2", "Registration at entry or manufacture, tracking, re-registration on transfer, destruction as the only exit, lost chips charged as dark compute", "software", "implemented",
       [P + "registry.Registry"], [TW + "test_registry_lifecycle_and_dark_charge"]),
    _r("HP-3.3.2b", f"{HP} > 3.3.2", "Latency-based location attestation: chips stay where registered", "software", "hardware-gated",
       [P + "registry.consistent_with_claim", P + "registry.verify_in_region"], [TW + "test_latency_location_check", TW + "test_impossible_location_marks_chip_silent"],
       ext=["cuda-guard"], note="The speed-of-light check is here; the on-chip attestation that produces round-trip times is hardware."),
    _r("HP-3.3.2c", f"{HP} > 3.3.2 and 5.4.2", "Census incentives: amnesty, bounties and buybacks priced against the fiscal capacity of states", "software", "partial",
       [P + "census.buyback_budget"], [TC + "test_buyback_budget"], note="Arithmetic only; the incentive design is policy."),
    _r("HP-3.3.2d", f"{HP} > 3.3.2", "AI companies ineligible for hardware and inference licences, to limit capture", "policy", "policy"),
    _r("HP-3.3.3a", f"{HP} > 3.3.3", "Transitional service verified by router, sampled recomputation and power reconciled with provider records", "software", "hardware-gated",
       [P + "bridge.closure_discount", P + "bridge.transitional_source", "closure.residual.audit", "closure.assurance.recompute_detection"],
       [TB + "test_closure_discount_from_synthetic_results", TB + "test_blended_pi_and_source", TB + "test_bridge_on_a_real_quick_trial",
        T + "test_residual.py::test_detects_constant_hidden_load_and_bound_covers_truth",
        T + "test_probe.py::test_bridge_charges_the_slack_inflated_gap_when_slack_was_measured"],
       note="Replaces the paper's assumed covert discount (pi_E = 0.001) with the closure gap on the audited share of a fleet. Descriptive, not pre-registered; "
            "inherits the trial's limits: efficiency slack is charged (slack-inflated gap) only when a hw-probe result was bound into the trial, and is otherwise invisible."),
    _r("HP-3.3.2e", f"{HP} > 3.3.2", "Retrofit pre-pause chips for on-chip location attestation", "physical", "physical"),
    _r("HP-3.3.3b", f"{HP} > 3.3.3", "Consent, administrative and challenge inspections modelled on the Chemical Weapons Convention", "policy", "policy"),
    _r("HP-3.3.3c", f"{HP} > 3.3.3", "Scientific preserves: named participants, declared workloads, logged and replayable on demand", "policy", "policy",
       note="The accounting of a preserve is a ledger line (HP-3.3.1); the workload log is operational."),
    _r("HP-3.3.3d", f"{HP} > 3.3.3", "Sovereign fleets: negotiated verification, with a lower discount for evidence offered", "software", "partial",
       [P + "treaty_ledger.Source"], [TL + "test_section_6_4_lines_match_reference_values"], note="The discount arithmetic is here; what evidence earns it is negotiated."),
    _r("HP-3.3.3e", f"{HP} > 3.3.3", "Strategic reserves powered off under seal, counted by periodic inspection", "software", "partial",
       [P + "treaty_ledger.strategic_reserve", P + "fab.custody_balance"], [TL + "test_strategic_reserve_and_preserve_lines", TF + "test_custody_and_litho_reconciliation"],
       note="Accounting and counting are here; the seals and the inspections are physical."),
    _r("HP-3.3.3f", f"{HP} > 3.3.3", "Trusted execution environments, proof-carrying code and tamper-proof runtime monitors with heartbeats", "software", "hardware-gated",
       [P + "registry.Registry.heartbeat", X + "fides/src/fides/server_attestation.py::verify_response",
        X + "cuda-guard/cuda_guard/ledger.py::TamperEvidentLedger"],
       [TW + "test_impossible_location_marks_chip_silent",
        X + "fides/tests/test_server_attestation.py::test_modified_software_fails_even_with_correct_state",
        X + "cuda-guard/tests/test_ledger.py::test_modification_detected"], ["cuda-guard", "fides"],
       note="Chip heartbeats, a challenge-response heartbeat for the monitor itself and a hash-chained ledger, in software. TEE attestation needs a confidential-computing GPU; proof-carrying code is not built."),
    _r("HP-3.3.3g", f"{HP} > 3.3.3", "Non-invasive verification of existing hardware from physical signals (power, timing)", "software", "hardware-gated",
       ["closure.residual.audit", "closure.dcbus.window_energy"],
       [T + "test_residual.py::test_detects_constant_hidden_load_and_bound_covers_truth", T + "test_dcbus.py::test_window_energy_is_exact_for_constant_and_ramp_power"],
       note="This is what the closure kit already does with DC-bus power; the paper lists side-channel techniques as a possibility."),
    _r("HP-3.3.3h", f"{HP} > 3.3.3", "Telemetry-based workload classification as defence in depth", "software", "hardware-gated",
       ["closure.cadence.statistic", "closure.cadence.calibrate", "closure.cadence.detect"],
       ["tests/test_cadence.py::test_training_is_flagged_and_inference_false_alarms_stay_near_alpha",
        "tests/test_cadence.py::test_varying_the_work_per_iteration_weakens_the_line",
        "tests/test_cadence.py::test_cadence_check_cli"],
       note="Training-cadence detector calibrated on null traces (defence in depth, not a bound); tested on synthetic traces, real telemetry needs a cluster. Closure accounting stays classifier-independent."),
    _r("HP-3.3.4a", f"{HP} > 3.3.4 and 6.5.4", "Lithography census: register machines, reconcile with vendor delivery and service records, charge unaccounted machines as dark compute", "software", "implemented",
       [P + "fab.reconcile_litho", P + "fab.dark_stock_after", P + "fab.litho_dark_source"], [TF + "test_custody_and_litho_reconciliation", TF + "test_litho_dark_source"]),
    _r("HP-3.3.4b", f"{HP} > 3.3.4 and 5.3.2", "Sample outgoing chips: detection probability, sample size and time to detect a diversion", "software", "implemented",
       [P + "fab.p_detect", P + "fab.samples_needed", P + "fab.min_detectable_diversion", P + "fab.months_to_detect"],
       [TF + "test_sampling_detection_matches_paper", TF + "test_min_detectable_and_months"]),
    _r("HP-3.3.4c", f"{HP} > 3.3.4", "Mass balance of perishable inputs such as photoresist", "software", "implemented",
       [P + "fab.consumable_balance"], [TF + "test_consumable_balance"]),
    _r("HP-3.3.4d", f"{HP} > 3.3.4 and 5.3.1", "Component custody: every lens accounted for, failed lenses replaced by the vendor and returned", "software", "implemented",
       [P + "fab.custody_balance"], [TF + "test_custody_and_litho_reconciliation"]),
    _r("HP-3.3.4e", f"{HP} > 3.3.4 and 5.3.1", "Find undeclared clean-room facilities: imagery, HVAC, gas by-products, substation metering, intelligence", "software", "partial",
       [X + "continental-load-registry/track3_bound.py::compute_track3_bound", X + "ai-2040-verification/undeclared_compute.py::covert_facility_mw"],
       [X + "continental-load-registry/tests/test_track3_bound.py::test_open_population_stays_unknown"], ["continental-load-registry", "ai-2040-verification"],
       note="Substation metering has a public-grid analogue (a residual-load bound that stays 'unknown' while the population is open) and a facility-size estimate; satellite imagery, HVAC and gas monitoring are not implemented."),
    # ---- 3.4-3.6 transition, exit, institutions ------------------------------------------------------------------------------
    _r("HP-3.3.5", f"{HP} > 3.6 and 3.3.3", "Inspectors on site at data centres, fabs and seals; physical and digital defence of the regime's own infrastructure", "physical", "physical"),
    _r("HP-3.4.1", f"{HP} > 3.4.1", "Economic alignment: declare to keep earning from inference; late declaration penalised; seizures fund bounties", "policy", "policy"),
    _r("HP-3.4.2", f"{HP} > 3.4.2 and 1.1", "Phases 0-3 and what starts each; Phase 1 emergency halt and whitelist deadline", "software", "implemented",
       [P + "transition.classify_phase", P + "whitelist.Whitelist.submit"], [TT + "test_phase_classifier", TW + "test_whitelist_deadline_and_duplicates"]),
    _r("HP-3.4.3", f"{HP} > 3.4.3", "Phase 2: capped licence auctions with a falling cap, trade-in at expiry", "software", "implemented",
       [P + "transition.clear_auction", P + "transition.cap_schedule", P + "transition.trade_in_due"],
       [TT + "test_license_auction_clears_uniformly", TT + "test_cap_schedule_and_trade_in"]),
    _r("HP-3.4.4", f"{HP} > 3.4.4", "Traded-in chips: retrofit, sovereign fleet, preserve or destruction", "software", "partial",
       [P + "registry.Registry.destroy", P + "registry.Registry.transfer"], [TW + "test_registry_lifecycle_and_dark_charge"], note="Mechanics here; which fate a chip gets is a decision."),
    _r("HP-3.5", f"{HP} > 3.5", "Exit conditions and renewal procedure", "policy", "policy"),
    _r("HP-3.6", f"{HP} > 3.6", "Institutional governance: treaty organisation, inspectorate, funding, legitimacy", "policy", "policy"),
    # ---- 4 inference-only hardware -------------------------------------------------------------------------------------------
    _r("HP-4.1", f"{HP} > 4.1", "GEMM laundering through the token interface alone is bounded (about 12 GFLOP/s)", "software", "implemented",
       [P + "inference_only.token_oracle_gemm_rate", P + "inference_only.machines_to_match"], [TI + "test_token_oracle_bound"]),
    _r("HP-4.2", f"{HP} > 4.2", "Licensing criterion for dynamic matrix multiplications: no exposed operands or outputs", "software", "hardware-gated",
       [P + "gemm_audit.audit", P + "gemm_audit.design_from_dict", P + "gemm_audit.attention_flop_share"],
       [TI + "test_gemm_audit_open_design_is_exposed", TI + "test_gemm_audit_sealed_or_authenticated_passes",
        TI + "test_gemm_audit_partial_protection_and_multi_feeder", TI + "test_token_port_is_not_an_attack_surface", TI + "test_attention_flop_share"],
       note="A design-time screen of a dataflow graph. The paper requires a physical audit of the realised system, tamper paths included."),
    _r("HP-4.3", f"{HP} > 4.3", "Hardwired-weight and authenticated-weight inference-only chips", "software", "partial",
       [P + "whitelist.AuthenticatedWeightChip"], [TW + "test_awic_accepts_only_hardwired_hash"], note="Acceptance rule only. The circuit, and the authors' FPGA demonstration, are hardware."),
    _r("HP-4.5", f"{HP} > 4.4", "Design, tape out and mass-produce inference-only chips fast enough to retire the training-capable stock", "physical", "physical"),
    _r("HP-4.4a", f"{HP} > 4.4 and Table 4.1", "Phase 1 duration: design to tapeout, tapeout to silicon, silicon to production; chip design timelines", "software", "implemented",
       [P + "transition.phase1_months", P + "transition.TABLE_4_1"], [TT + "test_phase_durations", TT + "test_table_4_1_matches_the_paper"]),
    _r("HP-4.4b", f"{HP} > 4.4", "Phase 2 duration from the stock to displace and the installation rate", "software", "implemented",
       [P + "transition.phase2_months", P + "transition.phase2_months_growing"], [TT + "test_phase_durations"]),
    # ---- 5 hardware governance feasibility -----------------------------------------------------------------------------------
    _r("HP-5.2", f"{HP} > 5.2", "Supply-chain chokepoints: a stage is controlled only if every jurisdiction with a capable supplier participates", "software", "implemented",
       [P + "supply_chain.CHOKEPOINTS", P + "supply_chain.uncovered", P + "supply_chain.critical_members", P + "supply_chain.minimum_coalition"],
       [TS + "test_each_departure_opens_the_stages_the_paper_describes", TS + "test_a_single_outside_supplier_is_a_leak"],
       note="The table is the paper's own reading of section 5.2, not an independent survey."),
    _r("HP-5.4a", f"{HP} > 5.4.1", "Thirteen documentary sources reconcile a census (tax, customs, vendor, rental, power, financing, warranty, ...)", "software", "implemented",
       [P + "census.EVIDENCE_SOURCES", P + "census.reconcile"], [TC + "test_reconcile_documented_but_undeclared"]),
    _r("HP-5.4b", f"{HP} > 5.4.2", "A buyback of the whole stock is affordable: $500B, doubled to $1T, under a quarter of US pandemic relief", "software", "implemented",
       [P + "census.buyback_budget"], [TC + "test_buyback_budget"]),
    _r("HP-5.5a", f"{HP} > 5.5, Table 5.1", "Chips a thorough census would miss, by holding type: the chain of anchors behind mu(h)", "software", "implemented",
       [P + "census.missing_fraction", P + "census.table_5_1", P + "census.split_residual"],
       [TC + "test_missing_fraction_chain", TC + "test_table_5_1_reproduces", TC + "test_split_residual"]),
    _r("HP-5.5b", f"{HP} > 5.5.2", "Failed chips with no record: failure rate by vintage, warranty and out-of-warranty accounting", "software", "implemented",
       [P + "census.failed_by_vintage", P + "census.missing_failed"], [TC + "test_failure_model_vintages"],
       note="Needs a vintage table (chips by sale date); the paper's comes from Epoch AI sales data."),
    _r("HP-5.5c", f"{HP} > 5.4 (extension, not in the paper)", "Estimate chips in no record at all from overlapping record sets", "software", "implemented",
       [P + "census.chao1_unseen", P + "census.lincoln_petersen"], [TC + "test_chao1_and_lincoln_petersen"],
       note="Capture-recapture lower bounds. Assumes sources miss chips independently, which shared blind spots violate."),
    # ---- 6 verification feasibility ------------------------------------------------------------------------------------------
    _r("HP-6.2.3", f"{HP} > 6.2.3", "Breakout fleet depends on the leader's timeline and the horizon", "software", "implemented",
       [P + "thresholds.breakout_sensitivity", P + "thresholds.arrival_years"], [TH + "test_breakout_sensitivity_and_pause_delay"]),
    _r("HP-6.2.4", f"{HP} > 6.2.4", "Private evasion fleet and its stress case (lower utilisation, inference share, heavy-tailed violation sizes)", "software", "implemented",
       [P + "thresholds.private_evasion_fleet", P + "thresholds.private_evasion_stress"], [TH + "test_private_evasion_fleet_and_pareto_stress"]),
    _r("HP-6.3", f"{HP} > 6.3", "Training-efficiency gains: historical estimates and the effect of a pause", "software", "partial",
       [P + "thresholds.erode", P + "thresholds.oom_per_year"], [TH + "test_erosion_and_years_for_oom"],
       note="Erosion arithmetic is here; the rate after a pause is unknowable (and the paper says so)."),
    _r("HP-6.4", f"{HP} > 6.4", "Ledger estimates for transitional service, dark compute (three cooperation scenarios), inference-only, consumer GPUs, sovereign fleets", "software", "implemented",
       [P + "treaty_ledger.section_6_4", P + "treaty_ledger.TABLE_6_1", P + "census.dark_compute"],
       [TL + "test_section_6_4_lines_match_reference_values", TC + "test_dark_compute_scenarios", TS + "test_table_6_1_ranges_move_the_transitional_line"]),
    _r("HP-6.5a", f"{HP} > 6.5", "Durability: headroom in orders of magnitude, line by line and summed, and years at an efficiency-gain rate", "software", "implemented",
       [P + "treaty_ledger.Ledger.headroom", P + "treaty_ledger.Ledger.years_of_durability"], [TL + "test_headroom_per_line_vs_summed", TL + "test_years_of_durability"],
       note="The paper reads lines separately; the ledger is defined as a sum, so both are reported."),
    _r("HP-6.5b", f"{HP} > 6.5.2", "Mitigations for transitional breakout exposure: shrinking allowance, offshore custody", "software", "implemented",
       [P + "treaty_ledger.allowance", P + "treaty_ledger.offshore"], [TL + "test_allowance_schedule", TL + "test_offshore_removes_breakout_exposure_only"]),
    _r("HP-6.5c", f"{HP} > 6.5.3", "Extension options: declare dark compute into reserves, or a consortium trains a larger frozen frontier", "policy", "policy"),
    _r("HP-6.5d", f"{HP} > 6.5.4", "Lithography proliferation: one unregistered DUV machine adds 24k-38k H100e a month", "software", "implemented",
       [P + "fab.dark_stock_after", P + "fab.litho_dark_source"], [TF + "test_litho_dark_source"]),
    # ---- 7 implications ------------------------------------------------------------------------------------------------------
    _r("HP-7.1", f"{HP} > 7.1", "Would restraints on frontier AI crash the economy? Spending, wealth effects, financial stability", "policy", "policy",
       note="Economics, not code. The arithmetic the section prints is re-derived in closure.pause.paper_claims."),
    _r("HP-7.2", f"{HP} > 7.2", "Inference costs fall when training compute is reallocated and hardware specialises", "software", "partial",
       [P + "transition.reallocation_gain", P + "transition.demand_catches_up_years"], [TT + "test_reallocation_and_demand_catch_up"]),
    _r("HP-7.3a", f"{HP} > 7.3.1-7.3.3", "MSIC economics: adoption rule, designs built, token share, savings, unserved share, utilisation, demand shifts", "software", "implemented",
       [P + "msic_econ.adopt", P + "msic_econ.panel", P + "msic_econ.unserved_share_bound", P + "msic_econ.utilisation_adjusted_savings"],
       [TM + "test_msic_adoption_rule_and_panel", TM + "test_prices_utilisation_and_replacement", TM + "test_total_variation_and_load_demand"],
       note="Takes any demand shares. The paper's own run uses a week of OpenRouter traffic; see docs/HARDWIRED_PAUSE.md for the cross-check."),
    _r("HP-7.3b", f"{HP} > 7.3.4", "De-whitelisting: stranded capital and the break-even share of lifetime demand", "software", "implemented",
       [P + "msic_econ.stranded_capital", P + "msic_econ.breakeven_fraction"], [TM + "test_stranded_capital_and_breakeven"],
       note="Insurance against de-whitelisting is a policy design."),
    _r("HP-7.4", f"{HP} > 7.4", "Concentration of power: capture of the whitelisting body, oligopoly rents, surveillance trade-offs", "policy", "policy"),
    _r("HP-7.5", f"{HP} > 7.5", "Receding knowledge cutoffs, locked-in values, approved fine-tunes as the remedy", "software", "partial",
       [P + "whitelist.Whitelist.approve_finetune"], [TW + "test_finetune_requires_servable_base_inherits_conditions_and_follows_recall"]),
    _r("HP-7.6", f"{HP} > 7.6", "Other measures are still needed: misuse, malfunction, dependence, military use", "policy", "policy"),
    # ---- 8 and reproducibility -----------------------------------------------------------------------------------------------
    _r("HP-8", f"{HP} > 8", "Conditions for pause-willingness: technology, great-power politics, domestic coalitions, firms", "policy", "policy"),
    _r("HP-R.1", f"{HP} > throughout", "Every printed number can be re-derived from code, with its status", "software", "implemented",
       [P + "paper_claims.check_all", P + "paper_claims.summary"], [TK + "test_paper_claims_reproduce_except_flagged", TK + "test_claims_are_sensitive_to_the_model"]),
]


def summary(rows=None) -> dict:
    rows = rows or ROWS
    s = {k: 0 for k in STATUSES}
    for r in rows:
        s[r["status"]] += 1
    sw = [r for r in rows if r["kind"] == "software"]
    s["rows"], s["software_rows"] = len(rows), len(sw)
    s["software_with_code_or_repo"] = sum(1 for r in sw if r["status"] != "not-started")
    return s


def validate(root=None) -> list:
    errs, _ = validate_rows(ROWS, root)
    return errs


def to_markdown() -> str:
    s = summary()
    out = ["# Hardwired-pause coverage matrix (generated by `closure pause coverage --write`; do not edit by hand)", "",
           "Source: \"The Feasibility of a Hardwired Pause of Frontier AI Training\", Working Group on AI Pause Feasibility, working paper "
           "v1.0.1, 10 October 2026. Status vocabulary: implemented (code and tests here), hardware-gated (code here, needs real hardware or design "
           "data), external (another repo on the account), partial, not-started, physical and policy (outside software scope).", "",
           f"**{s['rows']} items.** Software-addressable: {s['software_rows']}, of which {s['software_with_code_or_repo']} have code or a repository "
           f"behind them. implemented {s['implemented']}, hardware-gated {s['hardware-gated']}, external {s['external']}, partial {s['partial']}, "
           f"not-started {s['not-started']}, physical {s['physical']}, policy {s['policy']}.", "",
           "A pause is mostly institutions, inspections and politics. Those items are marked as such and are not counted as covered; the code "
           "here makes the paper's quantitative claims checkable and its accounting executable.", "",
           "Paths that start with `external/` are in the repositories vendored under external/ (pinned by external/MANIFEST.json); "
           "`closure external test` runs their own test suites.", "",
           "| id | source | requirement | status | implemented by | tests | other repos | note |",
           "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in ROWS:
        out.append("| " + " | ".join([r["id"], r["source"], r["requirement"], r["status"],
                                      "<br>".join(f"`{w}`" for w in r["where"]) or "-",
                                      "<br>".join(f"`{t}`" for t in r["tests"]) or "-",
                                      ", ".join(r["ext"]) or "-", r["note"] or "-"]) + " |")
    return "\n".join(out) + "\n"
