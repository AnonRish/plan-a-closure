"""Traceability matrix: every requirement in the pasted Plan A documents (AI 2040 verification plan and its Get
Involved page) mapped to what implements it, with an honest status. `validate()` checks that each claim points at
real code, a real test or a known repository, so the matrix cannot drift from the repo.

status: implemented (code + tests here) | hardware-gated (code here, needs a cluster) | external (another repo on the
account) | partial | not-started | physical | policy (outside software scope).

References that start with external/ point into the repositories vendored under external/ (pinned by
external/MANIFEST.json). They are checked by parsing the file, not importing it, and their tests run with
`closure external test`, each repository in its own pytest process."""
from __future__ import annotations

import importlib
import re
from pathlib import Path

STATUSES = ("implemented", "hardware-gated", "external", "partial", "not-started", "physical", "policy")
KNOWN_REPOS = {"fides", "ai-2040-plan-a-toolkit", "weight-diode", "covert-timing-warden", "assurance-curves",
               "frontier-verify", "ai-2040-verification", "cuda-guard", "continental-load-registry", "aisecurity-rfds",
               "compute-ledger", "packet-forge", "tap-logger-rtl"}
VP, GI = "Verification Plan", "Get Involved"
T = "tests/"
X = "external/"                                    # vendored repositories (see external/README.md)
FI, CL, WD, CT, CG = (X + "fides/src/fides/", X + "compute-ledger/src/compute_ledger/", X + "weight-diode/src/weight_diode/",
                      X + "covert-timing-warden/src/covert_timing_warden/", X + "cuda-guard/cuda_guard/")
LR, PF, AV, TR = (X + "continental-load-registry/", X + "packet-forge/src/packet_forge/", X + "ai-2040-verification/",
                  X + "tap-logger-rtl/")


def _r(i, src, req, kind, status, where=(), tests=(), ext=(), note=""):
    return dict(id=i, source=src, requirement=req, kind=kind, status=status, where=list(where),
                tests=list(tests), ext=list(ext), note=note)


ROWS = [
    _r("VP-0.1", f"{VP} > Summary", "Enforceable without trust: defection is caught or inconsequential (assurance curve)", "software", "implemented",
       ["closure.assurance.assurance_curve", "closure.assurance.confidence_at_coverage"], [T + "test_assurance.py::test_assurance_curve_matches_plan_formula"]),
    _r("VP-0.2", f"{VP} > Problem 1", "Verify that known compute is compliant", "software", "hardware-gated",
       ["closure.trial.run_trial", "closure.residual.audit"], [T + "test_trial.py::test_full_sim_trial_is_verifiable_and_sane"], ["fides", "frontier-verify"],
       "Estimators tested in simulation; the physical claim needs the trial on a cluster."),
    _r("VP-0.3", f"{VP} > Problem 2", "Verify that unknown compute is inconsequential (<1%; covert median 0.5%, 80% CI 0.1-1.4%)", "software", "implemented",
       ["closure.ledger.reconcile", "closure.ledger.undeclared_upper_bound", CL + "distributions.py::TwoPieceLogNormal", CL + "reconcile.py::Posterior"],
       [T + "test_ledger.py::test_reconcile_flags_underdeclaration",
        X + "compute-ledger/tests/test_distributions_reconcile.py::test_reproduces_the_three_published_quantiles_exactly",
        X + "compute-ledger/tests/test_distributions_reconcile.py::test_wider_estimates_leave_more_room_for_hidden_stock"],
       ["continental-load-registry", "compute-ledger"],
       "The accounting: a hidden-compute distribution that reproduces the plan's 0.1% / 0.5% / 1.4% quantiles exactly, and an exact posterior on the undeclared part of a declared stock. Finding covert compute in the world is VP-3.8 and GI-T3."),
    _r("VP-1.1", f"{VP} > Phase 1 / 2026-2028 chip tracking", "Know how much AI compute exists and who owns it (about 2% / 4% uncertainty by 2028)", "software", "implemented",
       ["closure.ledger.StockLedger", "closure.ledger.combine", CL + "planA.py::reproduce"],
       [T + "test_ledger.py::test_stock_ledger_accounting", T + "test_ledger.py::test_combine_reduces_uncertainty",
        X + "compute-ledger/tests/test_plan_a.py::test_every_published_figure_is_reproduced_from_its_inputs"],
       ["continental-load-registry", "compute-ledger"], "The text uses 'uncertainty' with two different definitions (see claims U.definition). compute-ledger re-derives the 289M H100e stock, ownership and locations from their inputs."),
    _r("VP-1.2", f"{VP} > Phase 1 priorities 1-2", "R&D funding: about 80% on the inference-only retrofit, 20% on supplementary work", "policy", "policy"),
    _r("VP-1.3", f"{VP} > 2027", "Network-tap plus recomputation approach chosen through RFIs and pilots", "physical", "physical", ext=["fides", "ai-2040-verification"]),
    _r("VP-IO.1", f"{VP} > Inference-only retrofit 1", "Remove east-west (backend) networking so datacenters become isolated inference units", "physical", "physical"),
    _r("VP-IO.1b", f"{VP} > Inference-only retrofit 1", "Check that no unexplained backend traffic remains (TAP on a backend NIC)", "software", "hardware-gated",
       ["closure.traffic.traffic_closure", "closure.traffic.iter_pcap"],
       [T + "test_traffic.py::test_closure_flags_unknown_flow_and_extra_bytes",
        T + "test_meter_pcap.py::test_unattributed_frames_fail_the_closure_unless_explicitly_tolerated"]),
    _r("VP-IO.2", f"{VP} > Inference-only retrofit 2", "Passive network taps copy all frontend I/O to a recomputation server", "physical", "physical"),
    _r("VP-IO.2b", f"{VP} > Inference-only retrofit 2", "Tap evidence is complete: every captured byte accounted, tap loss detected", "software", "hardware-gated",
       ["closure.traffic.read_pcap", "closure.traffic.iter_pcap", "closure.traffic.PcapStats", "closure.traffic.traffic_closure"],
       [T + "test_traffic.py::test_closure_reports_tap_loss_as_missing",
        T + "test_meter_pcap.py::test_iter_pcap_is_a_generator_parses_ipv6_and_counts_what_it_cannot_attribute"], ["fides"],
       "Streaming parser (IPv4, IPv6, one VLAN tag); frames it cannot attribute (ARP, ICMP, fragments) count as unexplained."),
    _r("VP-IO.3", f"{VP} > Inference-only retrofit 3", "Workloads organised into discrete, reproducible packets", "software", "hardware-gated",
       ["closure.repro.measure_reproducibility", "closure.repro.torch_repro_check", FI + "packet_reconstruction.py::reconstruct_and_verify",
        FI + "determinism.py::deterministic_sum"],
       [T + "test_repro.py::test_variant_kernel_is_batch_dependent_invariant_is_not",
        X + "fides/tests/test_packet_reconstruction.py::test_message_reconstructs_correctly_regardless_of_arrival_order",
        X + "fides/tests/test_determinism.py::test_deterministic_sum_gives_identical_bits_across_repeated_calls"],
       ["ai-2040-plan-a-toolkit", "fides"],
       "Messages are content-addressed and reassembled whatever the arrival order; a batch-invariant kernel makes a packet's result independent of its batch on CPU. The GPU measurement (torch_repro_check) needs a GPU."),
    _r("VP-IO.4", f"{VP} > Inference-only retrofit 4", "Partial recomputation of random packet samples verifies correctness", "software", "implemented",
       ["closure.claims.rogue_work_bound", "closure.assurance.recompute_detection"], [T + "test_claims.py::test_packet_math_identities"], ["assurance-curves", "fides"]),
    _r("VP-IO.5", f"{VP} > Inference-only retrofit 5", "Strong physical security of the verification hardware", "physical", "physical"),
    _r("VP-IO.6a", f"{VP} > Inference-only retrofit 6", "Completeness: periodic memory wipes (forced memorisation)", "software", "hardware-gated",
       ["closure.state.run_challenge", "closure.state.TorchProver"], [T + "test_state.py::test_dropping_stream_blocks_is_caught_at_the_binomial_rate"],
       note="Device-memory timing separation is decided by `closure hw-state` on a GPU."),
    _r("VP-IO.6b", f"{VP} > Inference-only retrofit 6", "Completeness: bound side-channel communication", "software", "hardware-gated",
       ["closure.traffic.covert_capacity_bound_bps", "closure.traffic.timing_grid_conformance"], [T + "test_traffic.py::test_timing_grid_conformance_and_capacity_bound"], ["covert-timing-warden"]),
    _r("VP-IO.6c", f"{VP} > Inference-only retrofit 6", "The plan does not verify that spare compute is unused: bound it by energy and busy-time accounting", "software", "hardware-gated",
       ["closure.trial.run_trial", "closure.residual.audit", "closure.hw.probe.run_probe", "closure.dcbus.check_absolute_power"],
       [T + "test_residual.py::test_detects_constant_hidden_load_and_bound_covers_truth",
        T + "test_probe.py::test_run_probe_on_the_fake_rig_measures_three_variants_and_a_floor",
        T + "test_meter_pcap.py::test_ac_coupled_trace_is_rejected_and_a_dc_coupled_trace_is_accepted"],
       note="New in this repo: closure accounting, signature-independent. Efficiency slack and the J/FLOP floor are measured by hw-probe (hardware-gated); the independent meter must be absolute (DC-coupled) power."),
    _r("VP-IO.7", f"{VP} > Inference-only retrofit (upgrade)", "Secure network gateways with random sampling and weight whitelisting", "software", "hardware-gated",
       ["closure.gateway.Gateway", "closure.gateway.Recomputer", "closure.gateway.sample_is_honest", "closure.gateway.verify_log"],
       [T + "test_gateway.py::test_boot_accepts_only_whitelisted_weights_and_serving_waits_for_boot",
        T + "test_gateway.py::test_keyed_sampling_hits_epsilon_and_the_revealed_key_proves_the_sample",
        T + "test_gateway.py::test_the_io_log_is_a_hash_chain_that_exposes_edits_drops_and_reordering"], ["ai-2040-verification"],
       "Protocol here (RFD 017 SNG/SRC): boot whitelist, hash-chained I/O log, committed keyed sampling, recomputation within a calibrated tolerance. The gateway device is hardware."),
    _r("VP-IO.8a", f"{VP} > Other promising directions", "Memory-challenge-based verification", "software", "hardware-gated",
       ["closure.state.Verifier"], [T + "test_state.py::test_stream_is_random_access_and_verifier_needs_no_storage"]),
    _r("VP-IO.8b", f"{VP} > Other promising directions", "Zero-knowledge proofs for AI workloads", "software", "partial",
       [FI + "zk_verification.py::ZKProver", FI + "zk_verification.py::ZKVerifier"],
       [X + "fides/tests/test_zk_verification.py::test_honest_inference_epoch_proof_verifies",
        X + "fides/tests/test_zk_verification.py::test_training_epoch_cannot_produce_a_valid_inference_only_proof"],
       ["fides", "ai-2040-verification"],
       "An RSA-accumulator non-membership proof that no forbidden operation ran in an epoch (it needs a trusted setup). A zero-knowledge proof of the computation itself is open; the plan calls this direction speculative."),
    _r("VP-IO.8c", f"{VP} > Other promising directions", "Crude hardware modifications (remove interconnect, add sensors)", "physical", "physical"),
    _r("VP-T.2028", f"{VP} > 2028", "Chip tracking mature: 80% CI 222M-226M (US) and 25M-27M (China) H100e", "software", "implemented",
       ["closure.ledger.reconcile"], [T + "test_ledger.py::test_reconcile_flags_underdeclaration"]),
    _r("VP-2.1", f"{VP} > Jan 2029 declaration", "Mutual compute declaration and supply-chain audit by a few hundred inspectors", "software", "implemented",
       ["closure.ledger.audit_sample_size", "closure.ledger.reconcile"], [T + "test_ledger.py::test_audit_sample_size_hypergeometric"]),
    _r("VP-2.2", f"{VP} > Jan 2029 bucket table", "Interventions by cluster size (>10K H100e retrofit; small: reporting + spot checks; consumer: intelligence)", "software", "implemented",
       ["closure.ledger.bucket_intervention"], [T + "test_ledger.py::test_bucket_and_tier_rules"]),
    _r("VP-2.3", f"{VP} > Chip flow restrictions", "Tier 0 / Tier 1 chips; destinations are inference-only datacenters or cold storage", "software", "implemented",
       ["closure.ledger.chip_tier", "closure.ledger.ChipTierThresholds", CL + "units.py::ai_relevant", CL + "units.py::h100e_from_tpp"],
       [T + "test_ledger.py::test_bucket_and_tier_rules",
        X + "compute-ledger/tests/test_units_stock.py::test_ai_relevance_matches_the_plans_three_examples",
        X + "compute-ledger/tests/test_units_stock.py::test_tpp_round_trip"], ["compute-ledger"],
       "Memory capacity and bandwidth thresholds come from the text. Compute and interconnect thresholds appear only in the figure, so chip_tier takes them as parameters and says when they were not applied. The AI-relevance floor reproduces the plan's three examples."),
    _r("VP-2.4", f"{VP} > Feb 2029 retrofit", "Rollout: 40% in month 1, 80% by month 3, >95% beyond; interim power-offs", "software", "implemented",
       ["closure.retrofit.schedule", "closure.retrofit.proportional"], [T + "test_claims.py::test_retrofit_schedule_matches_plan"]),
    _r("VP-2.5", f"{VP} > Apr-May 2029", "Third countries join the declaration (17 listed)", "policy", "policy"),
    _r("VP-2.6", f"{VP} > Mar 2029", "SL5 R&D clusters (Mongolia / Canada), scorched-earth guards", "physical", "physical"),
    _r("VP-2.7", f"{VP} > ZDR inference", "SL5 inference clusters and ZDR tiers with global fleet caps (100K / 100M / 100B H100e)", "software", "implemented",
       ["closure.captrade.FleetCaps"], [T + "test_approval_captrade.py::test_fleet_caps_and_edge_cap"]),
    _r("VP-2.8", f"{VP} > Verification metrics", "Five metrics: assurance curve, execution difficulty, preparation, privacy level, economic cost (plus scope)", "software", "implemented",
       ["closure.metrics.Scorecard", "closure.metrics.validate", "closure.metrics.CARDS", "closure.assurance.assurance_curve"],
       [T + "test_metrics.py::test_every_recorded_scorecard_is_complete_and_in_range", T + "test_metrics.py::test_the_assurance_metric_is_the_plans_formula",
        T + "test_metrics.py::test_bad_scorecards_are_refused", T + "test_metrics.py::test_metrics_cli"],
       note="`closure metrics`. The assurance curve is the plan's formula; the other five are recorded judgments, each with a stated basis, for reviewers to dispute."),
    _r("VP-2.9", f"{VP} > Key ingredients", "Physical security, human-based methods, mutually trusted manufacturing", "physical", "physical"),
    _r("VP-2.10", f"{VP} > Workload approval", "Approve workloads against white / black / gold lists", "software", "implemented",
       ["closure.approval.approve", "closure.approval.record"], [T + "test_approval_captrade.py::test_approval_stages_and_lists"]),
    _r("VP-2.11", f"{VP} > Research titration", "Progression: compute caps, ad-hoc rules, human-interpretable, safety-case burden of proof", "software", "implemented",
       ["closure.approval.stage_for_year"], [T + "test_approval_captrade.py::test_stage_progression"]),
    _r("VP-2.12", f"{VP} > Workload approval mitigations", "Anti-steganography, auditor compilation to GPU instructions, AI-assisted filtering", "software", "partial",
       [CT + "capacity.py::blahut_arimoto", AV + "stego_capacity.py::water_fill_capacity", AV + "workload_approval.py::check_against_policy",
        AV + "workload_approval.py::compile_and_certify_v2"],
       [X + "covert-timing-warden/tests/test_capacity.py::test_bsc_matches_closed_form_and_bracket_contains_it"],
       ["covert-timing-warden", "ai-2040-verification", "aisecurity-rfds"],
       "Capacity bounds for timing channels (tested) and for token-choice steganography (a script); an auditor's list check and a reproducible compile of an approved op list to a C binary, not to GPU instructions. AI-assisted data filtering is not built."),
    _r("VP-2.13", f"{VP} > Workload verification", "Evidence collection plus partial recomputation at falling packet sizes (4K, 400, 100 H100e)", "software", "implemented",
       ["closure.assurance.GRANULARITY_H100E", "closure.assurance.detection_time_hours"], [T + "test_assurance.py::test_detection_time_and_granularity"]),
    _r("VP-2.14", f"{VP} > Evaluations and release", "Final weights move from the opaque store to inference clusters", "software", "hardware-gated",
       [WD + "encoder.py::Encoder", WD + "receiver.py::Receiver", WD + "format.py::verify_manifest_signature"],
       [X + "weight-diode/tests/test_transfer.py::test_clean_transfer_and_progress_api",
        X + "weight-diode/tests/test_udp_cli.py::test_real_udp_transfer_over_loopback_with_loss_and_the_receiver_never_transmits"],
       ["weight-diode"],
       "One-way transfer with Reed-Solomon coding, Merkle-checked chunks and a signed manifest, tested over loopback UDP with loss. The one-way link itself is a hardware data diode."),
    _r("VP-2.15", f"{VP} > Late 2030", "Cold-storage compute banks (5M / 500K H100e) sized above plausible covert projects", "software", "implemented",
       ["closure.claims.check_all"], [T + "test_claims.py::test_all_claims_reproduce_except_flagged"]),
    _r("VP-2.16", f"{VP} > Late 2030", "Hardened cold-storage model-weights bank", "policy", "policy"),
    _r("VP-3.1", f"{VP} > 2031", "Restrictions on hardware R&D (robots, nanotech, easier-to-make AI compute)", "policy", "policy"),
    _r("VP-3.2", f"{VP} > 2031", "Inference restrictions: refusals, monitoring, compression", "policy", "policy"),
    _r("VP-3.3", f"{VP} > 2032", "Cap and trade for robots and AI chips (doubling about every 6 months)", "software", "implemented",
       ["closure.captrade.CapPath", "closure.captrade.PermitLedger"], [T + "test_approval_captrade.py::test_permit_ledger_respects_cap_path"]),
    _r("VP-3.4", f"{VP} > 2032", "Unverified edge-compute cap of 30M H100e (25M existing + 5M credits)", "software", "implemented",
       ["closure.captrade.EdgeCap"], [T + "test_approval_captrade.py::test_fleet_caps_and_edge_cap"]),
    _r("VP-3.5", f"{VP} > 2033", "Security improvements: SL5 datacenters, new fabs, hardware-software co-design", "physical", "physical"),
    _r("VP-3.6", f"{VP} > 2034", "Per-GPU packets, 1% budget: 99% catch at about 46,000 H100e-hours (10K H100e in 4.6 h)", "software", "implemented",
       ["closure.assurance.detection_time_hours", "closure.claims.rogue_work_bound"], [T + "test_assurance.py::test_detection_time_and_granularity"], ["assurance-curves"]),
    _r("VP-3.7", f"{VP} > 2035", "Ocean datacenters and mutually assured compute destruction", "physical", "physical"),
    _r("VP-3.8", f"{VP} > Phase 3 covert compute", "Reduce compute available to covert projects (intelligence, waste heat, power accounting)", "software", "partial",
       [LR + "track3_bound.py::compute_track3_bound", LR + "track3_certificate.py::one_sided_failure_upper_bound",
        AV + "undeclared_compute.py::covert_facility_mw"],
       [X + "continental-load-registry/tests/test_track3_bound.py::test_closed_population_produces_conservative_site_bound",
        X + "continental-load-registry/tests/test_track3_bound.py::test_open_population_stays_unknown",
        X + "continental-load-registry/tests/test_track3_certificate.py::test_zero_failure_bound_matches_closed_form"],
       ["continental-load-registry", "ai-2040-verification"],
       "Power accounting on a public-grid analogue: a residual bound that refuses to be numeric while the population is open. Intelligence collection and waste-heat sensing are not software."),
    _r("VP-3.9", f"{VP} > Phase 3 favourable directions", "Scale by hardware rather than software; hardware-software co-design", "policy", "policy"),
    _r("VP-3.10", f"{VP} > 2036+", "Advanced robustness: formal verification, large-scale red teaming, AI silver bullets", "software", "partial",
       ["closure.trial.run_trial", "closure.gateway.red_team"],
       [T + "test_trial.py::test_full_sim_trial_is_verifiable_and_sane",
        T + "test_gateway.py::test_red_team_flags_every_substitution_it_samples_and_never_the_honest_server"],
       note="A builder-versus-breaker harness and a recomputation red team (`closure redteam`). Formal verification and AI 'silver bullets' are not built."),
    _r("VP-A.1", f"{VP} > Appendix A.1", "Packet setup: packet size, budget C, N_verified = C / s", "software", "implemented",
       ["closure.assurance.n_verified"], [T + "test_assurance.py::test_assurance_curve_matches_plan_formula"]),
    _r("VP-A.2", f"{VP} > Appendix A.2", "Detection by random sampling, exact versus Poisson", "software", "implemented",
       ["closure.claims.p_undetected", "closure.claims.p_detect_poisson"], [T + "test_claims.py::test_packet_math_identities"], ["assurance-curves"]),
    _r("VP-A.3", f"{VP} > Appendix A.3", "Assurance curve (coverage x confidence, in nines)", "software", "implemented",
       ["closure.assurance.assurance_curve", "closure.assurance.nines"], [T + "test_assurance.py::test_assurance_curve_matches_plan_formula"]),
    _r("VP-A.4", f"{VP} > Appendix A.4", "Worked examples: 100K-token backdoor; rogue internal deployment bound", "software", "implemented",
       ["closure.claims.backdoor_cost", "closure.claims.rogue_work_bound"], [T + "test_claims.py::test_all_claims_reproduce_except_flagged"]),
    # SITREP workstreams
    _r("GI-WS-01", f"{GI} > SITREP: passive optical taps (active)", "Passive optical taps on the frontend network", "physical", "physical"),
    _r("GI-WS-02", f"{GI} > SITREP: recomputation servers, capture (active)", "Capture all frontend traffic for recomputation", "software", "hardware-gated",
       ["closure.gateway.Gateway.serve", "closure.traffic.iter_pcap"],
       [T + "test_gateway.py::test_red_team_flags_every_substitution_it_samples_and_never_the_honest_server",
        T + "test_taps.py::test_payload_mode_returns_the_bytes_and_the_default_mode_is_unchanged"], ["fides", "frontier-verify"],
       "Every I/O pair is logged and a keyed sample forwarded for recomputation; capture at line rate is hardware."),
    _r("GI-WS-03", f"{GI} > SITREP: new tap types and bandwidth limits (not started)", "Sampling or hashing taps; cut capture bandwidth", "software", "hardware-gated",
       ["closure.taphash.commit_pcap", "closure.taphash.merkle_proof", "closure.taphash.challenge_indices", "closure.taphash.detection_probability"],
       [T + "test_taps.py::test_one_flipped_byte_is_located_to_its_group",
        T + "test_taps.py::test_merkle_proofs_open_one_group_and_bind_its_position",
        T + "test_taps.py::test_challenges_come_from_the_nonce_and_the_detection_math_is_exact",
        X + "tap-logger-rtl/tests/test_rtl.py::test_core_matches_hashlib_on_random_messages",
        X + "tap-logger-rtl/tests/test_reference.py::test_any_single_bit_flip_is_detected_at_its_frame"], ["fides", "tap-logger-rtl"],
       "Group hashing with Merkle openings and nonce-derived challenges (Cankaya's tap design); 32 bytes out per group, 2048x less at 64 KiB. "
       "tap-logger-rtl is a SHA-256 hash-chain frame logger in Verilog, simulated against hashlib; no tap device or FPGA build exists yet."),
    _r("GI-WS-04", f"{GI} > SITREP: storage bank to inference path (not on track)", "One-way weight path from storage to inference units", "software", "hardware-gated",
       [WD + "encoder.py::Encoder", WD + "receiver.py::Receiver", WD + "format.py::verify_manifest_signature"],
       [X + "weight-diode/tests/test_udp_cli.py::test_real_udp_transfer_over_loopback_with_loss_and_the_receiver_never_transmits",
        X + "weight-diode/tests/test_negative_controls.py::test_without_a_whitelist_an_unapproved_file_is_accepted"],
       ["weight-diode"],
       "Sender and receiver tested over loopback UDP with loss; the receiver never transmits. The negative control shows the whitelist is what stops an unapproved file. A real diode is hardware."),
    _r("GI-WS-05", f"{GI} > SITREP: inference reproducibility workarounds (active)", "Work around non-determinism", "software", "implemented",
       ["closure.repro.conformal_tolerance", FI + "determinism.py::deterministic_sum", FI + "determinism.py::canonical_reduce",
        AV + "reduction_order.py::fixed_tree_sum"],
       [T + "test_repro.py::test_tolerance_calibration_controls_false_alarms",
        X + "fides/tests/test_determinism.py::test_deterministic_sum_gives_identical_bits_across_repeated_calls"],
       ["ai-2040-verification", "fides"],
       "Both workarounds: a calibrated tolerance with a controlled false-alarm rate, and a fixed reduction order that gives identical bits. Measured on CPU; GPU kernels are GI-WS-06."),
    _r("GI-WS-06", f"{GI} > SITREP: reproducible inference stack (not started)", "Fully reproducible inference stack", "software", "hardware-gated",
       ["closure.repro.torch_repro_check"], [T + "test_repro.py::test_variant_kernel_is_batch_dependent_invariant_is_not"]),
    _r("GI-WS-07", f"{GI} > SITREP: network reproducibility (not started)", "Packets individually reproducible on the network", "software", "partial",
       [PF + "assembler.py::StreamAssembler", PF + "normalize.py::normalize_pcap", FI + "packet_reconstruction.py::reconstruct_and_verify"],
       [X + "packet-forge/tests/test_corpus.py::test_pipeline_matches_oracle_for_every_arrival_order",
        X + "packet-forge/tests/test_assembler_vs_oracle.py::test_dense_overlap_fuzz",
        X + "fides/tests/test_packet_reconstruction.py::test_message_reconstructs_correctly_regardless_of_arrival_order"],
       ["packet-forge", "fides"],
       "Software side: 59 adversarial TCP captures, a reassembler that flags overlapping bytes that disagree instead of choosing, and order-independent message reconstruction. Bit-reproducible packets from the NIC need firmware."),
    _r("GI-WS-08", f"{GI} > SITREP: recomputation algorithms (active)", "TOPLOC / DiFR-style schemes", "software", "implemented",
       [FI + "toploc_reference.py::select_topk_by_magnitude", FI + "toploc_reference.py::lagrange_coefficients", FI + "difr_reference.py::gumbel_max_sample",
        FI + "difr_reference.py::verify_sequence", AV + "difr.py::verify", "closure.frontier.speculative_check"],
       [X + "fides/tests/test_toploc_reference.py::test_fabricated_unrelated_values_fail_to_match_well",
        X + "fides/tests/test_toploc_reference.py::test_honest_recomputation_with_small_jitter_matches_mostly",
        X + "fides/tests/test_difr_reference.py::test_tampered_distribution_shows_measurable_divergence",
        X + "fides/tests/test_difr_reference.py::test_matching_only_the_mode_does_not_evade_detection",
        T + "test_frontier.py::test_a_sampled_answer_is_reproducible_only_with_the_committed_seed"],
       ["fides", "ai-2040-verification"],
       "Reference implementations on small models: TOPLOC's top-k activation commitment and DiFR's seeded Gumbel-max replay, each with honest, tampered and red-team cases. Running them on frontier models needs the cluster."),
    _r("GI-WS-09", f"{GI} > SITREP: frontier recomputation algorithms (not started)", "Algorithms that track new architectures", "software", "partial",
       ["closure.frontier.moe_check", "closure.frontier.tied_routings", "closure.frontier.speculative_check"],
       [T + "test_frontier.py::test_moe_check_accepts_an_honest_fp16_router_and_needs_ties_only_where_routing_flips",
        T + "test_frontier.py::test_moe_check_rejects_a_provider_that_skips_the_router",
        T + "test_frontier.py::test_speculative_decoding_output_is_the_targets_and_the_draft_is_ignored"],
       note="Rules for mixture-of-experts routing near-ties and for speculative decoding, on toy models. Production architectures need their developers, as the SITREP says."),
    _r("GI-WS-10", f"{GI} > SITREP: recomputation red-teaming (not started)", "Red-team recomputation checks", "software", "implemented",
       ["closure.gateway.red_team", "closure.repro.detection_curve"],
       [T + "test_gateway.py::test_red_team_flags_every_substitution_it_samples_and_never_the_honest_server",
        T + "test_gateway.py::test_changes_below_the_honest_numerical_spread_pass_recomputation",
        T + "test_repro.py::test_substitution_detection_curve_is_monotone"], ["ai-2040-verification"],
       "Toy model: LoRA delta, requantisation, a different model and tampered outputs on a fraction of requests; the limit (changes below honest spread pass) is tested too. Frontier models need a cluster."),
    _r("GI-WS-11", f"{GI} > SITREP: recomputation server security (not on track)", "Integrity of the recomputation server", "software", "hardware-gated",
       [FI + "server_attestation.py::issue_challenge", FI + "server_attestation.py::verify_response", CG + "evidence.py::EvidenceClass",
        CG + "verdict.py::VerdictEngine"],
       [X + "fides/tests/test_server_attestation.py::test_honest_server_passes_challenge",
        X + "fides/tests/test_server_attestation.py::test_modified_software_fails_even_with_correct_state",
        X + "cuda-guard/tests/test_hardware.py::test_attestation_skips_fast_without_hanging_when_no_cc_gpu"],
       ["cuda-guard", "fides", "frontier-verify"],
       "A challenge-response heartbeat that a modified server fails, and evidence classes that keep 'unknown' apart from 'verified'. GPU attestation needs a confidential-computing GPU."),
    _r("GI-WS-12", f"{GI} > SITREP: tap installation and monitoring (not on track)", "Tap installed correctly and stays installed", "software", "hardware-gated",
       ["closure.tapwatch.schedule", "closure.tapwatch.check", "closure.tapwatch.detection_bound_s", "closure.traffic.traffic_closure"],
       [T + "test_taps.py::test_canaries_confirm_a_present_tap_and_a_removed_one_is_caught_within_the_bound",
        T + "test_taps.py::test_canary_times_and_payloads_cannot_be_predicted_without_the_key",
        T + "test_traffic.py::test_closure_reports_tap_loss_as_missing"], ["tap-logger-rtl"],
       note="Keyed canaries (unpredictable times; payloads indistinguishable from ciphertext) catch a removed or bypassed tap within one gap; loss and unknown flows as before. Needs real taps."),
    _r("GI-WS-13", f"{GI} > SITREP: verification reporting (not on track)", "Integrity of what the verifier reports", "software", "implemented",
       ["closure.evidence.Chain", "closure.evidence.Signer"], [T + "test_evidence.py::test_chain_detects_tampering_and_truncation"], ["frontier-verify"]),
    _r("GI-WS-14", f"{GI} > SITREP: physical security and audits (not on track)", "Inspecting compute at scale and inspecting the verifier", "physical", "physical"),
    _r("GI-WS-15", f"{GI} > SITREP: memory wipes (uncertain)", "Memory wipes (PoSE-style)", "software", "hardware-gated",
       ["closure.state.run_challenge"], [T + "test_state.py::test_parking_state_in_a_slow_tier_is_caught_by_time_not_digest"]),
    _r("GI-WS-16", f"{GI} > SITREP: side-channel mitigation (not on track)", "Shielding plus noise on a frontier cluster", "software", "hardware-gated",
       [CT + "mitigate.py::QuantizedRelease", CT + "mitigate.py::UniformJitter", CT + "mitigate.py::CapacityBound"],
       [X + "covert-timing-warden/tests/test_mitigate.py::test_quantizer_capacity_brackets"], ["covert-timing-warden"],
       "Timing noise and quantised release with capacity brackets, in software; it has to run on the cluster to mean anything. Physical shielding is out of scope."),
    _r("GI-WS-17", f"{GI} > SITREP: side-channel wardens (not on track)", "Scan side channels for covert communication", "software", "hardware-gated",
       ["closure.residual.audit", "closure.traffic.timing_grid_conformance"], [T + "test_residual.py::test_detects_constant_hidden_load_and_bound_covers_truth"], ["covert-timing-warden"]),
    # tracks and open problems
    _r("GI-T1", f"{GI} > Track 1", "Company auditing with embedded auditors and existing hardware", "policy", "policy"),
    _r("GI-T2", f"{GI} > Track 2", "Initial international verification: the inference-only retrofit", "software", "hardware-gated",
       ["closure.trial.run_trial"], [T + "test_trial.py::test_full_sim_trial_is_verifiable_and_sane"], ["fides"]),
    _r("GI-T3", f"{GI} > Track 3", "Verify the absence of secret compute", "software", "partial",
       ["closure.ledger.reconcile", CL + "reconcile.py::Posterior", LR + "track3_bound.py::compute_track3_bound", LR + "track3_tail_audit.py::audit_recipient"],
       [T + "test_ledger.py::test_reconcile_flags_underdeclaration",
        X + "continental-load-registry/tests/test_track3_bound.py::test_missing_site_evidence_blocks_numeric_global_bound",
        X + "continental-load-registry/tests/test_track3_tail_audit.py::test_balanced_population_produces_zero_failures"],
       ["continental-load-registry", "compute-ledger"],
       "Stock reconciliation, a residual bound that stays 'unknown' while the population is open, and a sampled audit of small owners. Absence of secret compute also needs intelligence and physical inspection."),
    _r("GI-T4", f"{GI} > Track 4", "Full workload verification, increasingly granular", "software", "partial",
       ["closure.approval.approve", "closure.assurance.GRANULARITY_H100E", AV + "proof_of_learning.py::verify_segment"],
       [T + "test_assurance.py::test_detection_time_and_granularity"], ["ai-2040-verification"],
       "Approval lists, the granularity schedule, and proof-of-learning segment replay for training (a script; Fang et al. 2023 show its limits). Verifying arbitrary training at scale is open."),
    _r("GI-OP.1", f"{GI} > Roenn: physical-layer monitoring", "Prove I/O by tapping the physical layer; next line rates; covert-channel gaps", "software", "hardware-gated",
       ["closure.traffic.traffic_closure", "closure.traffic.iter_pcap"],
       [T + "test_traffic.py::test_pcap_roundtrip", T + "test_meter_pcap.py::test_traffic_check_cli_streams_ipv6_and_reports_unparsed"], ["packet-forge"],
       "packet-forge's adversarial TCP corpus tests what a tap reader does with overlapping and conflicting segments."),
    _r("GI-OP.2", f"{GI} > Roenn: covert channels and steganography", "Measure and ceiling hidden channel capacity", "software", "partial",
       ["closure.traffic.covert_capacity_bound_bps", CT + "capacity.py::bsc_capacity", CT + "capacity.py::blahut_arimoto",
        AV + "stego_capacity.py::water_fill_capacity"],
       [T + "test_traffic.py::test_timing_grid_conformance_and_capacity_bound",
        X + "covert-timing-warden/tests/test_capacity.py::test_bsc_matches_closed_form_and_bracket_contains_it"],
       ["covert-timing-warden", "ai-2040-verification"],
       "Timing channels are measured and bounded (closed forms, Blahut-Arimoto brackets); token-choice steganography is bounded per position by water-filling (a script). Physical emanations are not measured."),
    _r("GI-OP.3", f"{GI} > Roenn: cryptographic proof of computation", "Zero-knowledge proofs of inference or training", "software", "partial",
       [FI + "zk_verification.py::ZKProver", FI + "zk_verification.py::ZKVerifier", AV + "proof_of_learning.py::verify_segment"],
       [X + "fides/tests/test_zk_verification.py::test_training_epoch_cannot_produce_a_valid_inference_only_proof"],
       ["fides", "ai-2040-verification"],
       "A proof about which operations ran (RSA accumulator, trusted setup) and proof-of-learning replay. A succinct zero-knowledge proof of a full forward pass is open."),
    _r("GI-OP.4", f"{GI} > Roenn: composing trust roots", "Prove the combination of mechanisms is sound", "software", "partial",
       ["closure.assurance.compose", AV + "trust_root_composition.py::attempt_forge_approval"],
       [T + "test_assurance.py::test_compose_independent_vs_correlated"], ["ai-2040-plan-a-toolkit", "ai-2040-verification"],
       "Independence is an assumption, so both bounds are reported; a key-reuse audit shows two trust roots collapsing into one. A soundness proof is open."),
    _r("GI-OP.5", f"{GI} > Roenn: binding verification to governance", "Machine-checkable artifacts that institutions can act on", "software", "implemented",
       ["closure.evidence.Chain", "closure.approval.record", CG + "verdict.py::GovernanceVerdict", FI + "ledger.py::AuditLedger"],
       [T + "test_trial.py::test_verify_catches_tampered_results_prereg_and_signature",
        X + "cuda-guard/tests/test_verdict.py::test_never_reduces_to_pass_fail", X + "fides/tests/test_ledger.py::test_untampered_chain_verifies"],
       ["cuda-guard", "fides"], "Signed, hash-chained evidence and verdicts that keep 'unknown' distinct from 'pass'. Legal instruments are out of scope."),
    _r("GI-OP.6", f"{GI} > Roenn: hardening trusted parts", "TEE hardening and independent corroboration", "software", "hardware-gated",
       [CG + "verdict.py::VerdictEngine", CG + "evidence.py::EvidenceClass", CG + "ledger.py::TamperEvidentLedger"],
       [X + "cuda-guard/tests/test_hardware.py::test_composition_never_upgrades_unknown_registry_to_authorized",
        X + "cuda-guard/tests/test_ledger.py::test_modification_detected"], ["cuda-guard"],
       "Composition never upgrades unknown evidence to authorised; the attestation path needs a confidential-computing GPU."),
    _r("GI-OP.7", f"{GI} > Harack: physical inspection and monitoring", "Inspection and perimeter monitoring acceptable to security teams", "physical", "physical"),
]


def summary(rows=None) -> dict:
    rows = rows or ROWS
    s = {k: 0 for k in STATUSES}
    for r in rows:
        s[r["status"]] += 1
    sw = [r for r in rows if r["kind"] == "software"]
    s["rows"] = len(rows)
    s["software_rows"] = len(sw)
    s["software_with_code_or_repo"] = sum(1 for r in sw if r["status"] != "not-started")
    return s


def _defined_in(path: Path, name: str) -> bool:
    """Is `name` (a top-level function or class, or Class.method) defined in the Python file at `path`? Parsed, not imported,
    so vendored repositories with their own dependencies can be checked without installing them."""
    import ast
    if not path.exists() or not name:
        return False
    tree = ast.parse(path.read_text(encoding="utf-8"))
    head, _, tail = name.partition(".")
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.name == head:
            if not tail:
                return True
            return isinstance(node, ast.ClassDef) and any(
                isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)) and m.name == tail for m in node.body)
        if isinstance(node, ast.Assign) and not tail and any(isinstance(t, ast.Name) and t.id == head for t in node.targets):
            return True
    return False


def validate_rows(rows, root=None) -> tuple:
    """Check every row of a matrix points at real code, a real test or a known repository. Returns (errors, ids seen).
    Shared by the Plan A matrix and the hardwired-pause matrix (closure.pause.coverage)."""
    root = Path(root) if root else Path(__file__).resolve().parents[2]
    errs, seen = [], set()
    for r in rows:
        if r["id"] in seen:
            errs.append(f"duplicate id {r['id']}")
        seen.add(r["id"])
        if r["status"] not in STATUSES:
            errs.append(f"{r['id']}: bad status")
        if r["kind"] not in ("software", "physical", "policy"):
            errs.append(f"{r['id']}: bad kind")
        if r["status"] in ("implemented", "hardware-gated") and not (r["where"] and r["tests"]):
            errs.append(f"{r['id']}: {r['status']} needs code and a test")
        if r["status"] == "external" and not r["ext"]:
            errs.append(f"{r['id']}: external needs a repo")
        for w in r["where"]:
            if w.startswith("external/"):                # vendored code: external/<repo>/<file>.py::<name> or ::<Class>.<method>
                if not _defined_in(root / w.partition("::")[0], w.partition("::")[2]):
                    errs.append(f"{r['id']}: {w} not found")
                continue
            mod, _, rest = w.rpartition(".")
            try:
                obj = importlib.import_module(mod)
            except ImportError:
                try:                                    # class attribute / nested path
                    mod2, _, cls = mod.rpartition(".")
                    obj = getattr(importlib.import_module(mod2), cls)
                except Exception:
                    errs.append(f"{r['id']}: cannot import {w}")
                    continue
            if not hasattr(obj, rest):
                errs.append(f"{r['id']}: {w} not found")
        for t in r["tests"]:
            f, _, name = t.partition("::")
            p = root / f
            if not p.exists() or not re.search(rf"def {re.escape(name)}\b", p.read_text(encoding="utf-8")):
                errs.append(f"{r['id']}: test {t} not found")
        for e in r["ext"]:
            if e not in KNOWN_REPOS:
                errs.append(f"{r['id']}: unknown repo {e}")
    return errs, seen


def validate(root=None) -> list:
    errs, seen = validate_rows(ROWS, root)
    for i in range(1, 18):
        if f"GI-WS-{i:02d}" not in seen:
            errs.append(f"missing SITREP workstream {i}")
    return errs


def to_markdown() -> str:
    s = summary()
    out = ["# Plan A coverage matrix (generated by `closure coverage --write`; do not edit by hand)", "",
           "Sources: the AI 2040 Verification Plan and its Get Involved page, as pasted. Status vocabulary: "
           "implemented (code and tests here), hardware-gated (code here, needs a cluster), external (another repo on the "
           "account), partial, not-started, physical and policy (outside software scope).", "",
           f"**{s['rows']} requirements.** Software-addressable: {s['software_rows']}, of which "
           f"{s['software_with_code_or_repo']} have code or a repository behind them. "
           f"implemented {s['implemented']}, hardware-gated {s['hardware-gated']}, external {s['external']}, "
           f"partial {s['partial']}, not-started {s['not-started']}, physical {s['physical']}, policy {s['policy']}.", "",
           "Total completion of Plan A is not achievable in software: physical, diplomatic and manufacturing items are "
           "marked as such and are not counted as covered.", "",
           "Paths that start with `external/` are in the repositories vendored under external/ (pinned by "
           "external/MANIFEST.json); `closure external test` runs their own test suites.", "",
           "| id | source | requirement | status | implemented by | tests | other repos | note |",
           "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in ROWS:
        out.append("| " + " | ".join([r["id"], r["source"], r["requirement"], r["status"],
                                      "<br>".join(f"`{w}`" for w in r["where"]) or "-",
                                      "<br>".join(f"`{t}`" for t in r["tests"]) or "-",
                                      ", ".join(r["ext"]) or "-", r["note"] or "-"]) + " |")
    return "\n".join(out) + "\n"
