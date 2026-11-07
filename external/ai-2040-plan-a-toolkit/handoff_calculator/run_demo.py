import matplotlib.pyplot as plt
import numpy as np

from handoff import (
    evaluate, evaluate_scenario, full_table, breakeven_d_prob,
    ALIGNMENT_SCENARIOS, DEAL_DECLINE_SCENARIOS, DEFAULTS,
)

if __name__ == "__main__":
    print("=== Worked example (the page's own defaults) ===")
    r = evaluate(**DEFAULTS)
    print(f"  d_prob={DEFAULTS['d_prob']:.1%}  a_prob={DEFAULTS['a_prob']:.1%}  "
          f"d_loss={DEFAULTS['d_loss']:.1%}  a_change={DEFAULTS['a_change']:.1%}")
    print(f"  benefit of handoff = {r.benefit_of_handoff:.2%}")
    print(f"  cost of handoff    = {r.cost_of_handoff:.2%}")
    print(f"  net                = {r.net:+.2%}  ->  {r.recommendation}")

    print("\n=== Full published 4x3 table (reproduced) ===")
    header = f"{'':32s}" + "".join(f"{d:>16s}" for d in DEAL_DECLINE_SCENARIOS)
    print(header)
    table = full_table()
    for a_name, row in table.items():
        line = f"{a_name:32s}"
        for d_name, result in row.items():
            line += f"{result.net:+15.2%} "
        print(line)

    print("\n=== Breakeven extension: how bad would deal-decline risk need to")
    print("    get before the recommendation flips, holding alignment fixed? ===")
    for a_name, a in ALIGNMENT_SCENARIOS.items():
        for d_name, d in DEAL_DECLINE_SCENARIOS.items():
            d_star = breakeven_d_prob(a["a_prob"], d["d_loss"], a["a_change"])
            current = d["d_prob"]
            direction = "already past breakeven" if current >= d_star else f"would need {d_star:.2%} (currently {current:.2%})"
            print(f"  {a_name:32s} / {d_name:12s}  breakeven d_prob={d_star:.3%}  [{direction}]")

    # plot: net benefit vs d_prob for each alignment scenario, at Medium-risk d_loss, breakeven marked
    fig, ax = plt.subplots(figsize=(8, 5.5))
    d_probs = np.linspace(0.0001, 0.15, 300)
    colors = ["#4A93A6", "#C9922E", "#C05B48", "#8A6FB3"]
    for (a_name, a), color in zip(ALIGNMENT_SCENARIOS.items(), colors):
        d_loss_fixed = DEAL_DECLINE_SCENARIOS["Medium risk"]["d_loss"]
        nets = [evaluate(dp, a["a_prob"], d_loss_fixed, a["a_change"]).net * 100 for dp in d_probs]
        ax.plot(d_probs * 100, nets, color=color, label=a_name)
        d_star = breakeven_d_prob(a["a_prob"], d_loss_fixed, a["a_change"])
        if d_probs[0] <= d_star <= d_probs[-1]:
            ax.plot(d_star * 100, 0, "o", color=color, markersize=7)
    ax.axhline(0, color="#1C1F26", linewidth=1)
    ax.set_xlabel("deal decline probability, d_prob (%/yr)")
    ax.set_ylabel("net benefit of handoff (%)")
    ax.set_title("Net benefit vs. deal-decline risk, at Medium-risk d_loss=20%\n(dots = breakeven point per alignment scenario)")
    ax.legend(fontsize=8.5)
    fig.tight_layout()
    fig.savefig("handoff_breakeven.png", dpi=170, facecolor="white")
    plt.close(fig)
    print("\nSaved handoff_breakeven.png")
