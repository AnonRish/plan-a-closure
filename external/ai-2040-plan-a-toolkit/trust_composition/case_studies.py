"""
case_studies.py

Two applications of the checker:

1. Arbiter, as actually built in this conversation -- a self-audit, since I
   have the real source and no guesswork is required.

2. A reconstruction of an AI-2040-style verification architecture's claimed
   trust roots, built from the public Verification Plan / SITREP / RFD board
   material discussed earlier in this conversation. This is NOT Amodo's
   actual internal dependency graph -- that isn't public, and some of it
   probably shouldn't be. It's an informed, illustrative model built the way
   an outside auditor would have to: from what's published. Treat the
   specific dependency names as representative, not authoritative.
"""

import json
import networkx as nx
import matplotlib.pyplot as plt

from trust_composition import TrustRoot, analyze


def draw(trust_roots, hazard_set, title, outfile):
    G = nx.Graph()
    roots = [tr.name for tr in trust_roots]
    resources = sorted(set().union(*(tr.depends_on for tr in trust_roots)))
    G.add_nodes_from(roots, bipartite=0)
    G.add_nodes_from(resources, bipartite=1)
    for tr in trust_roots:
        for r in tr.depends_on:
            G.add_edge(tr.name, r)

    pos = {}
    for i, r in enumerate(roots):
        pos[r] = (0, -i * 1.4 + (len(roots) - 1) * 0.7)
    for i, r in enumerate(resources):
        pos[r] = (3, -i * 1.0 + (len(resources) - 1) * 0.5)

    hazard_set = hazard_set or set()
    fig, ax = plt.subplots(figsize=(9, max(4.5, 0.9 * max(len(roots), len(resources)))))

    nx.draw_networkx_edges(
        G, pos, ax=ax,
        edge_color=["#C05B48" if (u in hazard_set or v in hazard_set) else "#B9B6AC" for u, v in G.edges()],
        width=[2.4 if (u in hazard_set or v in hazard_set) else 1.0 for u, v in G.edges()],
    )
    nx.draw_networkx_nodes(G, pos, nodelist=roots, node_color="#171B22", edgecolors="#4A93A6", linewidths=2, node_size=2600, ax=ax)
    safe_resources = [r for r in resources if r not in hazard_set]
    nx.draw_networkx_nodes(G, pos, nodelist=safe_resources, node_color="#E9E6DC", edgecolors="#5B594F", linewidths=1.3, node_size=1900, ax=ax)
    nx.draw_networkx_nodes(G, pos, nodelist=list(hazard_set), node_color="#C05B48", edgecolors="#7E382C", linewidths=1.8, node_size=1900, ax=ax)

    nx.draw_networkx_labels(G, pos, labels={r: r for r in roots}, font_color="#E9E6DC", font_size=9, font_weight="bold", ax=ax)
    nx.draw_networkx_labels(G, pos, labels={r: r for r in safe_resources}, font_color="#1C1F26", font_size=8, ax=ax)
    nx.draw_networkx_labels(G, pos, labels={r: r for r in hazard_set}, font_color="#FBEAE5", font_size=8, font_weight="bold", ax=ax)

    ax.set_title(title, fontsize=12, color="#1C1F26", loc="left", pad=14)
    ax.axis("off")
    ax.set_xlim(-1.6, 5.2)
    fig.tight_layout()
    fig.savefig(outfile, dpi=180, facecolor="white")
    plt.close(fig)
    print(f"  saved {outfile}")


# ============================== CASE 1: ARBITER ==============================
arbiter_roots = [
    TrustRoot("licensing", {"authority_private_key", "web_crypto_impl", "sha256_impl", "client_js_integrity"}),
    TrustRoot("workload_review", {"anthropic_api", "client_js_integrity"}),
    TrustRoot("audit_statistics", {"physical_audit_ground_truth", "client_js_integrity"}),
    TrustRoot("ledger_integrity", {"sha256_impl", "browser_storage_backend", "client_js_integrity"}),
]

# ============================== CASE 2: PLAN-A-STYLE (RECONSTRUCTED) ==============================
plan_a_roots = [
    TrustRoot("optical_tap", {"tap_vendor_firmware", "network_protocol_standard", "physical_installation_audit"}),
    TrustRoot("recomputation_server", {"tee_vendor_root_of_trust", "crypto_library", "network_protocol_standard"}),
    TrustRoot("side_channel_warden", {"tee_vendor_root_of_trust", "crypto_library"}),
    TrustRoot("human_auditor", {"personnel_vetting_process", "physical_installation_audit"}),
    TrustRoot("verification_ledger", {"crypto_library", "personnel_vetting_process"}),
]


if __name__ == "__main__":
    results = []

    r1 = analyze(arbiter_roots, claimed_threshold=4, label="Arbiter (as built -- self-audit)")
    draw(arbiter_roots, r1["min_attack_set"], "Arbiter: trust roots vs. dependencies (hazard in red)", "arbiter_graph.png")
    results.append(r1)

    r2 = analyze(plan_a_roots, claimed_threshold=3, label="AI-2040-style architecture (reconstructed from public docs)")
    draw(plan_a_roots, r2["min_attack_set"], "Reconstructed Plan A verification stack (hazard in red)", "plan_a_graph.png")
    results.append(r2)

    with open("results.json", "w") as f:
        json.dump(
            [{k: (sorted(v) if isinstance(v, set) else v) for k, v in r.items() if k != "fanout"} for r in results],
            f, indent=2,
        )
    print("\nSaved results.json, arbiter_graph.png, plan_a_graph.png")
