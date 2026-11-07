import json
import numpy as np
import matplotlib.pyplot as plt

from compute_graph import transformer_block_graph
from cluster import run_cluster
from verification import aggregate_discrepancy, spot_check_round, detection_probability_over_rounds

if __name__ == "__main__":
    graph = transformer_block_graph(n_layers=24, batch=4, seq_len=2048, d_model=2048, n_heads=16, d_ff=8192)
    declared = graph.declared_flops()
    print(f"Declared graph: 24-layer transformer block, batch=4, seq_len=2048, d_model=2048")
    print(f"Analytically declared FLOPs: {declared:.4e}")

    print("\n=== Aggregate detection sensitivity vs. cluster size ===")
    print("(fixed: exactly 1 Byzantine node, under-reporting 30% of its own true work)")
    cluster_sizes = [4, 16, 64, 256, 1024]
    agg_results = {}
    for n in cluster_sizes:
        rng = np.random.default_rng(42)
        reports = run_cluster(graph, n, byzantine_fraction=0.0, underreport_fraction=0.30, rng=rng, force_byzantine_ids=[0])
        n_byz = sum(1 for r in reports if r.is_byzantine)
        result = aggregate_discrepancy(graph, reports, tolerance=0.02)
        agg_results[n] = {**result, "n_byzantine_actual": n_byz}
        print(f"  N={n:5d} nodes  ({n_byz} byzantine)  relative_gap={result['relative_gap']*100:6.3f}%  "
              f"flagged(>2% tolerance)={result['flagged']}")

    print("\n=== Spot-check detection probability vs. audit rate and rounds ===")
    print("(exact geometric probability -- independent of cluster size)")
    for audit_rate in [0.01, 0.05, 0.10]:
        for rounds in [1, 5, 10, 20]:
            p = detection_probability_over_rounds(True, audit_rate, rounds)
            print(f"  audit_rate={audit_rate:.2f}  rounds={rounds:3d}  P(caught at least once)={p:.4f}")

    print("\n=== Spot-check confirmed empirically: does it ever false-positive on honest nodes? ===")
    rng = np.random.default_rng(7)
    reports = run_cluster(graph, 200, byzantine_fraction=0.05, underreport_fraction=0.25, rng=rng)
    total_fp, total_audited, total_caught = 0, 0, 0
    for round_i in range(30):
        rng_round = np.random.default_rng(1000 + round_i)
        res = spot_check_round(reports, audit_rate=0.10, rng=rng_round)
        total_audited += res["audited_count"]
        total_caught += len(res["caught_byzantine"])
        total_fp += len(res["false_positives"])
    n_byz_actual = sum(1 for r in reports if r.is_byzantine)
    print(f"  200 nodes, {n_byz_actual} truly byzantine, 30 rounds at 10% audit rate:")
    print(f"  total audits performed: {total_audited}, byzantine-catches: {total_caught}, false positives on honest nodes: {total_fp}")

    # plot
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    gaps = [abs(agg_results[n]["relative_gap"]) * 100 for n in cluster_sizes]
    axes[0].plot(cluster_sizes, gaps, "o-", color="#C05B48")
    axes[0].axhline(2.0, color="#5B594F", linestyle="--", linewidth=1, label="2% tolerance threshold")
    axes[0].set_xscale("log")
    axes[0].set_xlabel("cluster size (nodes)")
    axes[0].set_ylabel("aggregate relative gap (%)")
    axes[0].set_title("Aggregate check: 1 lying node gets diluted as N grows")
    axes[0].legend(fontsize=9)

    rounds_range = list(range(1, 21))
    for audit_rate, color in [(0.01, "#C9922E"), (0.05, "#4A93A6"), (0.10, "#5B8A5B")]:
        probs = [detection_probability_over_rounds(True, audit_rate, r) for r in rounds_range]
        axes[1].plot(rounds_range, probs, "o-", color=color, label=f"audit_rate={audit_rate}", markersize=3)
    axes[1].set_xlabel("audit rounds")
    axes[1].set_ylabel("P(a given byzantine node caught at least once)")
    axes[1].set_title("Spot-check: detection probability, independent of N")
    axes[1].legend(fontsize=9)
    fig.tight_layout()
    fig.savefig("detection_comparison.png", dpi=170, facecolor="white")
    plt.close(fig)
    print("\nSaved detection_comparison.png")

    with open("results.json", "w") as f:
        json.dump({
            "declared_flops": declared,
            "aggregate_by_cluster_size": {str(k): v for k, v in agg_results.items()},
            "spot_check_empirical": {"total_audited": total_audited, "total_caught": total_caught, "false_positives": total_fp, "n_byzantine_actual": n_byz_actual},
        }, f, indent=2)
    print("Saved results.json")
