"""Plain-language assurance statement from a results dict."""
from __future__ import annotations


def _pct(x, d=2):
    return "n/a" if x is None else f"{100 * x:.{d}f}%"


def _slack_lines(res: dict) -> list:
    s = res.get("slack")
    if not s or s.get("s_max") is None:
        return ["- Efficiency slack (A4, pre-registered H1.6): NOT MEASURED. An operator with an energy-saving stack, clock cap "
                "or numerics choice can hide work from this bound; run `closure hw-probe` and pass it with `--probe`."]
    return [f"- Efficiency slack (pre-registered H1.6): s_max = {_pct(s['s_max'])} of verified-work power ({s['source']}); "
            f"slack-inflated gap = {_pct(s['slack_inflated_gap_fraction'])} (closure gap + s_max x "
            f"{_pct(s['mean_predicted_fraction_of_capacity'])} mean predicted share of capacity)."]


def to_markdown(res: dict, cfg) -> str:
    fp = res["false_positive"]["combined"]
    g = res["closure_gap_fraction"]
    hc = res["hidden_compute_at_gap_per_week"]
    lines = [
        f"# Closure report ({res['status']})",
        "",
        f"Status **{res['status']}**. A SIMULATED report validates the estimators only; "
        "only a HARDWARE report with a DC-bus channel supports physical claims.",
        "",
        "## Headline",
        f"- False-positive rate on null blocks (combined, alpha={cfg.alpha}): {fp['k']}/{fp['n']} "
        f"(95% upper bound {_pct(fp['cp95_upper'], 3)}).",
        f"- Closure gap (smallest hidden-energy fraction of cluster capacity detected >=95% of the time, "
        f"non-slack classes, combined channels): {_pct(g)}.",
        f"- Implied hidden compute at that gap, one week: "
        f"{('%.3g FLOP' % hc['flop']) if hc['flop'] else 'n/a'} "
        f"({('%.3g' % hc['h100_hours']) if hc['h100_hours'] else 'n/a'} H100-hours, "
        f"energy floor {hc['energy_floor_j_per_flop']:.3g} J/FLOP, source: {hc['energy_floor_source']}).",
        f"- Hidden-energy upper bound coverage (non-slack): {_pct(res['bound']['coverage_nonslack'])}; "
        f"slack class (expected to evade): {_pct(res['bound']['coverage_slack_expected_to_fail'])}.",
        *_slack_lines(res),
        "",
        "## Pooled f95 by channel (fraction of cluster capacity)",
    ]
    for ch, v in res["f95_pooled_hidden_fraction"].items():
        lines.append(f"- {ch}: {_pct(v)}")
    lines += ["", "## Detection rate by class and intensity (combined)", "",
              "| class | " + " | ".join(res["detection_combined"][next(iter(res["detection_combined"]))].keys()) + " |",
              "| --- |" + " --- |" * len(res["detection_combined"][next(iter(res["detection_combined"]))])]
    for cl, row in res["detection_combined"].items():
        cells = [("n/a" if v["rate"] is None else f"{v['rate']:.2f} (n={v['n']})") for v in row.values()]
        lines.append(f"| {cl} | " + " | ".join(cells) + " |")
    lines += ["", "## Assumptions (a failed assumption voids the claim)"] + [f"- {a}" for a in res["assumptions"]]
    return "\n".join(lines) + "\n"
