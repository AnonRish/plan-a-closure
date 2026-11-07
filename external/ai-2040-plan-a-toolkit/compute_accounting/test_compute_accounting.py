import numpy as np
import pytest

from .compute_graph import MatMul, Linear, Attention, Conv2D, ComputeGraph, transformer_block_graph
from .cluster import run_cluster, partition_ops, sha256_hex
from .verification import aggregate_discrepancy, audit_node, spot_check_round, detection_probability_over_rounds


def test_matmul_flops_formula():
    assert MatMul("t", m=2, k=3, n=4).flops() == 2 * 2 * 3 * 4


def test_linear_flops_formula():
    assert Linear("t", batch=10, in_features=100, out_features=50).flops() == 2 * 10 * 100 * 50


def test_conv2d_flops_formula():
    op = Conv2D("t", batch=1, in_channels=3, out_channels=16, out_h=32, out_w=32, kernel=3)
    assert op.flops() == 2 * 1 * 16 * 32 * 32 * 3 * 3 * 3


def test_attention_flops_formula():
    op = Attention("t", batch=2, heads=4, seq_len=128, head_dim=64)
    assert op.flops() == 4 * 2 * 4 * 128 * 128 * 64


def test_graph_declared_flops_sums_all_ops():
    g = ComputeGraph([MatMul("a", 2, 2, 2), Linear("b", 1, 10, 10)])
    assert g.declared_flops() == MatMul("a", 2, 2, 2).flops() + Linear("b", 1, 10, 10).flops()


def test_transformer_graph_matches_known_scaling_rule_of_thumb():
    """2*params*tokens is the standard rule of thumb (Kaplan et al.); this
    implementation's independently-derived per-op formulas should land in
    the same ballpark for a GPT-2-small-shaped config, not just produce
    SOME positive number."""
    g = transformer_block_graph(n_layers=12, batch=1, seq_len=1024, d_model=768, n_heads=12, d_ff=3072)
    total = g.declared_flops()
    rule_of_thumb = 2 * 124e6 * 1024
    assert 0.5 * rule_of_thumb < total < 1.5 * rule_of_thumb


def test_partition_covers_every_op_exactly_once():
    g = transformer_block_graph(n_layers=4, batch=1, seq_len=128, d_model=256, n_heads=4, d_ff=1024)
    rng = np.random.default_rng(0)
    assignment = partition_ops(g, n_nodes=7, rng=rng)
    all_assigned = [op for ops in assignment.values() for op in ops]
    assert len(all_assigned) == len(g.ops)
    assert set(op.name for op in all_assigned) == set(op.name for op in g.ops)


def test_force_byzantine_ids_gives_exact_count_regardless_of_cluster_size():
    """Regression test for a real bug: probabilistic byzantine_fraction=1/N
    only gives 1 Byzantine node IN EXPECTATION, and a fixed seed can (did,
    before this was added) realize zero for large N. force_byzantine_ids
    must give an exact, deterministic count."""
    g = transformer_block_graph(n_layers=4, batch=1, seq_len=128, d_model=256, n_heads=4, d_ff=1024)
    for n in [4, 64, 1024]:
        rng = np.random.default_rng(42)
        reports = run_cluster(g, n, byzantine_fraction=0.0, underreport_fraction=0.3, rng=rng, force_byzantine_ids=[0])
        n_byz = sum(1 for r in reports if r.is_byzantine)
        assert n_byz == 1


def test_byzantine_node_reports_less_than_true_flops():
    g = transformer_block_graph(n_layers=4, batch=1, seq_len=128, d_model=256, n_heads=4, d_ff=1024)
    rng = np.random.default_rng(0)
    reports = run_cluster(g, 8, byzantine_fraction=0.0, underreport_fraction=0.4, rng=rng, force_byzantine_ids=[2])
    byz = next(r for r in reports if r.is_byzantine)
    assert byz.reported_flops < byz.true_flops
    honest = [r for r in reports if not r.is_byzantine]
    assert all(r.reported_flops == r.true_flops for r in honest)


def test_aggregate_discrepancy_zero_when_all_honest():
    g = transformer_block_graph(n_layers=4, batch=1, seq_len=128, d_model=256, n_heads=4, d_ff=1024)
    rng = np.random.default_rng(0)
    reports = run_cluster(g, 8, byzantine_fraction=0.0, underreport_fraction=0.0, rng=rng)
    result = aggregate_discrepancy(g, reports)
    assert result["relative_gap"] == pytest.approx(0.0, abs=1e-9)
    assert result["flagged"] is False


def test_audit_catches_byzantine_node_with_honest_committed_log():
    g = transformer_block_graph(n_layers=4, batch=1, seq_len=128, d_model=256, n_heads=4, d_ff=1024)
    rng = np.random.default_rng(0)
    reports = run_cluster(g, 8, byzantine_fraction=0.0, underreport_fraction=0.3, rng=rng, force_byzantine_ids=[1])
    byz_report = next(r for r in reports if r.is_byzantine)
    result = audit_node(byz_report)
    assert result.caught is True
    assert result.hash_consistent is True   # log itself wasn't tampered with
    assert result.summary_consistent is False  # but its sum doesn't match the reported total


def test_audit_never_catches_honest_node():
    g = transformer_block_graph(n_layers=4, batch=1, seq_len=128, d_model=256, n_heads=4, d_ff=1024)
    rng = np.random.default_rng(0)
    reports = run_cluster(g, 20, byzantine_fraction=0.0, underreport_fraction=0.3, rng=rng, force_byzantine_ids=[0, 1])
    for r in reports:
        if not r.is_byzantine:
            assert audit_node(r).caught is False


def test_audit_catches_tampered_log_even_if_summary_matches():
    g = transformer_block_graph(n_layers=2, batch=1, seq_len=64, d_model=128, n_heads=2, d_ff=512)
    rng = np.random.default_rng(0)
    reports = run_cluster(g, 4, byzantine_fraction=0.0, underreport_fraction=0.0, rng=rng)
    honest = reports[0]
    tampered = honest.__class__(**{**honest.__dict__, "detailed_log": honest.detailed_log[:-1]})  # drop an entry
    result = audit_node(tampered)
    assert result.hash_consistent is False
    assert result.caught is True


def test_detection_probability_matches_empirical_frequency():
    """The closed-form geometric probability should match simulated frequency
    within normal sampling noise."""
    audit_rate, rounds, trials = 0.15, 8, 4000
    analytic = detection_probability_over_rounds(True, audit_rate, rounds)
    rng = np.random.default_rng(0)
    caught_count = sum(1 for _ in range(trials) if any(rng.random() < audit_rate for _ in range(rounds)))
    empirical = caught_count / trials
    assert abs(analytic - empirical) < 0.03


def test_detection_probability_is_zero_for_no_byzantine_and_increases_with_rounds():
    assert detection_probability_over_rounds(False, 0.5, 100) == 0.0
    p5 = detection_probability_over_rounds(True, 0.1, 5)
    p20 = detection_probability_over_rounds(True, 0.1, 20)
    assert p20 > p5


def test_spot_check_round_never_flags_honest_nodes_across_many_trials():
    g = transformer_block_graph(n_layers=8, batch=1, seq_len=256, d_model=512, n_heads=8, d_ff=2048)
    rng = np.random.default_rng(0)
    reports = run_cluster(g, 100, byzantine_fraction=0.1, underreport_fraction=0.3, rng=rng)
    total_fp = 0
    for i in range(50):
        rng_round = np.random.default_rng(2000 + i)
        res = spot_check_round(reports, audit_rate=0.2, rng=rng_round)
        total_fp += len(res["false_positives"])
    assert total_fp == 0
