"""How much efficiency slack each rule a verification regime could adopt leaves on the GPUs on record: a descriptive
page, re-derived from the bundles in this folder.

    python results/slack_left.py              # print the page
    python results/slack_left.py --write      # rewrite results/SLACK_LEFT.md (tests/test_runs_on_record.py checks it)

Every number on the page is read from a bundle as it came back (its SHA-256 checked against its folder's README), with
`closure slack-left` (src/closure/slack_left.py) applied to the probe each trial was bound to. The rule with nothing
fixed must reproduce the s_max and slack-inflated gap the trial signed, or the page is not written. The projections in
section 5 are labelled as such: they assume the spread per round the probes measured.
"""
import hashlib
import importlib.util
import json
import math
import sys
import tempfile
from pathlib import Path

import numpy as np

from closure import tier0
from closure.conformal import t_upper
from closure.criteria import PRIMARY
from closure.hw.probe import verify_seal
from closure.slack_left import RULES, WORDS, largest_point, pct, reading

HERE = Path(__file__).resolve().parent
EDGES = np.logspace(-4, -0.5, 15)      # the closure gap's bins (trial._pooled_f95): a gap is the upper edge of one
SHORT = {"none": "nothing fixed (registered)", "clocks": "clocks", "clocks_power": "clocks, power limit",
         "stack": "whole stack", "data": "data", "stack_data": "stack and data"}


def _record():
    spec = importlib.util.spec_from_file_location("closure_results_record", HERE / "record.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def collect(results: Path = HERE) -> list:
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        for run, where, folder, tgz, trial in _record().RUNS:
            if folder is None or trial is None:
                continue
            path = results / folder / tgz
            sha = hashlib.sha256(path.read_bytes()).hexdigest()
            if sha not in (results / folder / "README.md").read_text(encoding="utf-8"):
                raise SystemExit(f"{path}: its sha256 {sha} is not in {folder}/README.md")
            root = tier0.unpack(path, Path(tmp) / f"run{run}", sha)
            probe = json.loads((root / trial / "probe.json").read_text())
            res = json.loads((root / trial / "results.json").read_text())
            sl = res["slack"]
            if not verify_seal(probe) or str(probe["sha256"])[:16] not in str(sl["source"]):
                raise SystemExit(f"run {run}: the probe in the bundle is not the one its trial was bound to")
            rep = reading(probe, res["closure_gap_fraction"], sl["mean_predicted_fraction_of_capacity"])
            if not rep["reproduces_s_max"] or abs(rep["rules"][0]["slack_inflated_gap"]
                                                  - sl["slack_inflated_gap_fraction"]) > 1e-12:
                raise SystemExit(f"run {run}: nothing fixed does not reproduce the signed s_max and slack-inflated gap")
            if not np.isclose(EDGES, res["closure_gap_fraction"]).any():
                raise SystemExit(f"run {run}: the closure gap is not a bin edge; the bins in this script are out of date")
            out.append({"run": run, "where": where, "rep": rep, "probe": probe})
    return out


def _rule(x, key):
    return next(r for r in x["rep"]["rules"] if r["rule"] == key)


def _at(at) -> str:
    return "nothing in the sweep" if at is None else f"{at['variant']}, load {at['level']:g}"


def _cell(r, key="s", at="at") -> str:
    if r["nothing_left_in_sweep"]:
        return "nothing in the sweep"
    return f"{'≥ ' if r['lower_bound'] else ''}{pct(r[key])} ({_at(r[at])})"


def _span(xs, d=1) -> str:
    lo, hi = min(xs), max(xs)
    return pct(lo, d) if abs(hi - lo) < 5e-4 else f"{100 * lo:.{d}f} to {pct(hi, d)}"


def _projected(probe, rounds: int, only=None) -> float:
    """The largest upper bound over counted cells (or over one variant's) if the probe had run `rounds` rounds with
    the spread per round it measured and the same point estimates: a projection, not a measurement."""
    now = (probe.get("settings") or {}).get("repeats") or 3
    ref = {c["level"]: c for c in next(v for v in probe["variants"] if v["kind"] == "reference")["levels"]}
    best = None
    for v in probe["variants"]:
        if v["kind"] == "reference" or not v["allowed"] or (only and v["name"] != only):
            continue
        for c in v["levels"]:
            if "saving_upper95" not in c:
                continue
            r = ref[c["level"]]
            n, rn = c["n"] * rounds / now, r["n"] * rounds / now
            tc = t_upper(0.05, max(1.0, min(n, rn) - 1.0))
            se, rse = c["power_w_se"] * math.sqrt(c["n"] / n), r["power_w_se"] * math.sqrt(r["n"] / rn)
            u = 1.0 - (c["power_w_mean"] - tc * se) / (r["power_w_mean"] + tc * rse)
            best = u if best is None else max(best, u)
    return best


def page(results: Path = HERE) -> str:
    data = collect(results)
    N = len(data)
    runs = ", ".join(x["run"] for x in data)
    none = [_rule(x, "none") for x in data]
    head = "| rule: what the regime takes away | " + " | ".join(f"run {x['run']}" for x in data) + " |"
    sep = "| " + " | ".join(["---"] * (N + 1)) + " |"

    def by_rule(key, at):
        return [f"| {label} | " + " | ".join(_cell(_rule(x, k), key, at) for x in data) + " |" for k, label, _ in RULES]

    # section 1
    rows1 = []
    for x in data:
        rep, r0, t = x["rep"], _rule(x, "none"), x["rep"]["null_twin"] or {}
        lp = r0["largest_point_under_load"]
        tried = ", ".join(WORDS[k] for k in rep["kinds_measured"])
        if rep["kinds_not_measured"]:
            tried += f" (not {', '.join(WORDS[k] for k in rep['kinds_not_measured'])}: no device control)"
        rows1.append(f"| {x['run']} | {x['where']} | {tried} | {rep['repeats']} | {_cell(r0)} | "
                     f"{pct(r0['at']['point'])} | {pct(lp['point'])} ({_at(lp)}) | "
                     f"{pct((t.get('at') or {}).get('upper95'))}; {pct((t.get('at_under_load') or {}).get('upper95'))} "
                     f"| {pct(t.get('largest_point_abs'))} |")
    # section 4
    rows4 = []
    for x in data:
        rep = x["rep"]
        rows4.append(f"| {x['run']} | {pct(rep['closure_gap_fraction'], 2)} | "
                     f"{rep['mean_predicted_fraction_of_capacity']:.2f} | "
                     + " | ".join(pct(_rule(x, k)["slack_inflated_gap"]) for k, _, _ in RULES) + " |")
    # the findings, computed
    op = [x for x in data if _rule(x, "none")["at"]["kind"] == "operand"]
    moved = [(x["run"], _rule(x, "none")["s"], _rule(x, "stack")["s"]) for x in data
             if abs(_rule(x, "stack")["s"] - _rule(x, "none")["s"]) > 1e-12]
    pinned = [_rule(x, "stack")["largest_point_under_load"] for x in data]
    pinned_names = ", ".join(f"`{k}`" for k in sorted({p["variant"] for p in pinned}))
    pinned_levels = ", ".join(sorted({f"{p['level']:g}" for p in pinned}))
    clocks = [largest_point(x["probe"], ("clock_cap",)) for x in data if "clock_cap" in x["rep"]["kinds_measured"]]
    libs = [largest_point(x["probe"], ("kernel",)) for x in data]
    alone = [_rule(x, k)["s"] for x in data for k in ("stack", "data")]
    twins = [x["rep"]["null_twin"] for x in data]
    tw_runs = [x for x in data if x["rep"]["kinds_not_measured"]]
    gaps = [x["rep"]["closure_gap_fraction"] for x in data]
    loads = [x["rep"]["mean_predicted_fraction_of_capacity"] for x in data]
    edge = float(max(e for e in EDGES if e <= PRIMARY + 1e-12))
    budget = [(PRIMARY - edge) / u for u in loads]
    best_gap = min(gaps)
    best_runs = ", ".join(x["run"] for x in data if abs(x["rep"]["closure_gap_fraction"] - best_gap) < 1e-12)
    others = [g for g in gaps if g > best_gap + 1e-12]
    tw6 = [_projected(x["probe"], 6, x["rep"]["null_twin"]["variant"]) for x in data]
    tw12 = [_projected(x["probe"], 12, x["rep"]["null_twin"]["variant"]) for x in data]
    s6 = [_projected(x["probe"], 6) for x in data]
    over6, over12 = sum(t > b for t, b in zip(tw6, budget)), sum(t > b for t, b in zip(tw12, budget))
    twin_pts = [c["saving_point"] for x in data for v in x["probe"]["variants"]
                if v["name"] == x["rep"]["null_twin"]["variant"] for c in v["levels"] if "saving_point" in c]
    findings = [
        f"1. **Two sources of slack are large and measured, not just bounded: cheap data and low clocks.** Point "
        f"estimates under load: the data pattern {pinned_names}, on the reference stack, saves "
        f"{_span([p['point'] for p in pinned])} at load {pinned_levels} on every GPU; a low clock lock saves "
        f"{_span([c['point'] for c in clocks])} on the {len(clocks)} GPUs where clocks could be locked. The BLAS "
        f"library's largest measured saving is {_span([c['point'] for c in libs])}.",
        f"2. **Pinning the stack leaves the data, and accounting for the data leaves the stack.** The registered bound "
        f"peaks on a data variant on {len(op)} of {N} GPUs, so pinning the whole stack (clocks, power limit, "
        f"precision and library) lowers it on {len(moved)} of {N}"
        + (" (" + "; ".join(f"run {r}: {pct(a)} to {pct(b)}" for r, a, b in moved) + ")" if moved else "")
        + f". Either rule alone leaves {_span(alone)}. With both, nothing in the sweep is left on all {N}: that is "
        f"the edge of what was tried, not a measured zero.",
        f"3. **At {data[0]['rep']['repeats']} rounds the bound is mostly noise where the real savings are small.** On "
        f"a T4 the fp16 variant is the reference computation under another name (a T4's native half precision is "
        f"fp16), so its true saving is zero. The probe gave it bounds of {_span([t['at']['upper95'] for t in twins])}, "
        f"with measured savings of {100 * min(twin_pts):+.1f} to {100 * max(twin_pts):+.1f}%. On runs "
        f"{', '.join(x['run'] for x in tw_runs)}, where only precision, library and data could be tried, s_max "
        f"({', '.join(pct(_rule(x, 'none')['s']) for x in tw_runs)}) is close to the twin's bound "
        f"({', '.join(pct(x['rep']['null_twin']['at']['upper95']) for x in tw_runs)}).",
        f"4. **What a PASS would take.** The registered outcome needs the closure gap plus s × load at "
        f"{pct(PRIMARY, 0)} or less. The gap is reported at the upper edge of a quarter-decade bin, so in practice "
        f"it has to be in the bin ending at {pct(edge, 2)} or lower, which leaves room for a slack of at most "
        f"{_span(budget)} at these loads ({min(loads):.2f} to {max(loads):.2f} of capacity). On these runs no rule "
        f"would have been enough: with nothing left the reading is the closure gap itself, {pct(best_gap, 2)} at "
        f"best (runs {best_runs}) and {_span(others)} on the others.",
        f"5. **For the next run (projections, not measurements).** With the spread per round these probes measured "
        f"and the same point estimates, six rounds (amendment v0.8's default) would put the twin's bound at about "
        f"{_span(tw6)} and s_max at about {_span(s6)}; twelve rounds would put the twin at about {_span(tw12)}. The "
        f"twin's bound would still exceed the slack a PASS leaves on {over6} of {N} GPUs at six rounds and on "
        f"{over12} of {N} at twelve, so on GPUs and meters like these more rounds are not enough by themselves: the "
        f"meter's noise and the probe's own offset (the twin's measured savings) have to come down too. From v0.8 "
        f"every probe runs a deliberate null twin and keeps each cell's powers, so the next run measures its own "
        f"noise floor and can be read paired by round.",
    ]
    return "\n".join([
        "# Efficiency slack left under each rule a regime could adopt", "",
        "A descriptive reading of the probes on record. **It decides nothing**: the registered outcome uses s_max "
        "with nothing fixed, and these readings were made after the data were seen (from amendment v0.8 on, the "
        "pilot reports the same reading for every run, declared before its data). This page is written by "
        "`python results/slack_left.py --write` from the bundles in this folder, each checked against its SHA-256, "
        "and a test fails if it is out of date. The method is `closure slack-left` "
        "([src/closure/slack_left.py](../src/closure/slack_left.py)); on one unpacked bundle, "
        "`closure slack-left --run <the trial folder inside it>` prints the same rows.", "",
        "Why it matters. Closure bounds hidden work by the energy the verified work does not explain. An operator who "
        "can do the declared work for less energy than the energy model expects (a lower clock, another library, "
        "cheaper data) can run hidden work in the difference, so the registered reading adds that efficiency slack, "
        "times the load, to the closure gap. A treaty could take some of those choices away. Which ones would it "
        "have to take?", "",
        f"The probe changes one setting at a time from its reference and measures power at the same work rate, at "
        f"load levels 0, 0.25, 0.5 and 0.9 of capacity. A rule here removes the kinds of setting it fixes, and the "
        f"slack left is the largest one-sided 95% upper bound on a saving among the variants it leaves free. A "
        f"variant whose numerics fail the accuracy check never counts, as in the registered s_max (int8 here; fp8 "
        f"does not run on a T4).", "",
        "## 1. Where the slack is on each GPU", "",
        "| run | when and where | settings the probe could try | rounds | registered s_max (95% upper bound) | "
        "measured saving there | largest measured saving under load | twin's bound: all levels; under load | "
        "twin's largest measured saving |",
        "| " + " | ".join(["---"] * 9) + " |", *rows1, "",
        "The twin is the fp16 variant, the reference computation itself on a T4, so its true saving is zero. "
        "A **≥** marks a lower bound: the probe could not try every kind of setting the rule leaves free.", "",
        "## 2. What each rule leaves: 95% upper bound over all load levels, as s_max counts them", "",
        head, sep, *by_rule("s", "at"), "",
        "## 3. The same under load only (levels above 0; post hoc)", "",
        "At level 0 the GPU does no work, so a precision, library or data variant cannot change its power: an idle "
        "\"saving\" from one is drift between measurements. This reading sets all idle cells aside.", "",
        head, sep, *by_rule("s_under_load", "at_under_load"), "",
        "## 4. The slack-inflated gap each rule would give, holding each run's closure gap and load as measured", "",
        "A trial run under a rule would measure its gap and load again; this only shows how much of each reading "
        "the slack accounts for. The first column of readings is the registered one, as signed.", "",
        "| run | closure gap | mean load | " + " | ".join(SHORT[k] for k, _, _ in RULES) + " |",
        "| " + " | ".join(["---"] * (len(RULES) + 3)) + " |", *rows4, "",
        "## What these numbers say", "", *findings, "",
        "In treaty terms: on this evidence, energy accounting can bound hidden work only as tightly as the efficiency "
        "choices left to the operator, and closing them takes both a pinned stack (clocks and power limit included) "
        "and an energy prediction made from the data the declared work actually ran on, for example from committed "
        "request logs with a sample recomputed on a verifier's machine. How to predict energy from data is an open "
        "problem and outside this kit. Kimpson, Baker and Graham (arXiv 2610.07476) describe the attack this guards "
        "against: declared work run on cheap operands, with the energy saved spent on covert work.", "",
        "## What they do not say", "",
        f"- Runs {runs} are shakedowns on Tesla T4s with NVML as the only meter. The registered trial needs an "
        "H100-class GPU and an independent power meter; magnitudes there will differ.",
        "- Each saving stays measured against the probe's own reference. A regime that fixes a setting moves the "
        "reference too, so a rule's row is the slack among the choices left, not a measurement of that regime.",
        "- Variants change one setting at a time. Savings from two changes made together are in no row, the "
        "registered one included.",
        "- \"Nothing in the sweep\" is not zero: other data patterns, libraries, kernels or settings the probe did "
        "not try are not covered.",
        "- On runs where the container refused device control, clock and power-limit savings were not measured; "
        "every rule that leaves them free gives a lower bound (**≥**).", ""])


if __name__ == "__main__":
    text = page()
    if "--write" in sys.argv[1:]:
        (HERE / "SLACK_LEFT.md").write_text(text, encoding="utf-8")
        print(f"wrote {HERE / 'SLACK_LEFT.md'}")
    else:
        print(text)
