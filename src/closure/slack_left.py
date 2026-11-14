"""How much efficiency slack is left when a verification regime fixes some settings: a reading of probe.json that
decides nothing.

The registered ``s_max`` (H1.6, hw/probe.py) is the largest one-sided 95% upper saving over every allowed variant and
load level the probe measured. Each variant changes one thing from the reference: an SM clock lock, a power limit, a
precision, the BLAS library, or the data the reference stack computes on (the operand variants). A treaty could take
some of these away from an operator: fix the clocks, set the power limit, pin the whole software stack, or predict the
energy of declared work from the data it actually ran on. For each such rule this module reports the largest saving
the probe measured among the variants the rule leaves free. It is arithmetic on the probe's own cells, so with nothing
fixed it gives ``s_max`` exactly (a test checks this on every probe on record).

It is not

* a decision rule. The registered outcome uses ``s_max`` with nothing fixed; these rows describe the same data.
* a measurement of a regime. Fixing a setting would also move the reference the savings are measured against; here
  every saving stays as measured against the probe's own reference.
* complete. Each variant changes one setting, so savings from two changes made together are in no row, the
  registered one included. A kind of setting the probe could not try on a machine (clocks and power limits without
  device control, as in Kaggle's container) is listed as not measured, and a rule that leaves it free gives a lower
  bound.
* a zero. A rule with nothing left means nothing left *in this sweep*; settings and data the sweep did not try are
  not covered.

Two further readings, both post hoc. *Under load*: the same, over load levels above 0 only. At level 0 the GPU does no
work, so a precision, library or data variant cannot change its power, and an idle "saving" from one is drift between
measurements; the idle cells of clock and power variants are set aside with them. *The null twin*: where the probe ran
a variant that is the reference computation under another name (fp16 on a GPU whose native half precision is fp16, as
on a T4), its true saving is zero, so its bound shows how large a bound noise and drift alone produce at the probe's
sample size.
"""
from __future__ import annotations

KINDS = ("clock_cap", "power_cap", "precision", "kernel", "operand")
STACK = ("clock_cap", "power_cap", "precision", "kernel")
WORDS = {"clock_cap": "SM clocks", "power_cap": "power limit", "precision": "precision", "kernel": "BLAS library",
         "operand": "data"}
RULES = (   # (key, what the regime does, the kinds of setting it takes away from an operator)
    ("none", "nothing fixed (the registered s_max)", ()),
    ("clocks", "SM clocks fixed", ("clock_cap",)),
    ("clocks_power", "SM clocks and power limit fixed", ("clock_cap", "power_cap")),
    ("stack", "whole stack pinned: clocks, power limit, precision, BLAS library", STACK),
    ("data", "energy predicted from the data the work ran on; stack free", ("operand",)),
    ("stack_data", "stack pinned and energy predicted from the data", KINDS),
)
DTYPES = {"fp16": "float16", "bf16": "bfloat16", "fp32": "float32"}
SCOPE = ("descriptive: arithmetic on the probe's own cells, read after the data were seen; it decides nothing (the "
         "registered outcome uses s_max with nothing fixed)")


def _cells(probe: dict, kinds, load_only: bool = False, allowed_only: bool = True) -> list:
    """(upper95, point, variant, kind, level) for each cell with a saving, over variants of the given kinds."""
    out = []
    for v in probe.get("variants") or ():
        if v.get("kind") not in kinds or (allowed_only and not v.get("allowed")):
            continue
        for c in v.get("levels") or ():
            if "saving_upper95" in c and (float(c["level"]) > 0 or not load_only):
                out.append((float(c["saving_upper95"]), float(c["saving_point"]), str(v["name"]), str(v["kind"]),
                            float(c["level"])))
    return out


def _at(cell) -> dict:
    return None if cell is None else {"upper95": cell[0], "point": cell[1], "variant": cell[2], "kind": cell[3],
                                      "level": cell[4]}


def best(probe: dict, kinds, load_only: bool = False) -> dict:
    """The cell with the largest upper saving among allowed variants of these kinds, or None if there is none."""
    cells = _cells(probe, kinds, load_only)
    return _at(max(cells) if cells else None)


def largest_point(probe: dict, kinds, load_only: bool = True) -> dict:
    """The cell with the largest measured (point) saving among allowed variants of these kinds."""
    cells = _cells(probe, kinds, load_only)
    return _at(max(cells, key=lambda c: (c[1], c[0])) if cells else None)


def measured_kinds(probe: dict) -> list:
    """Kinds of setting the probe tried on this machine (a dropped variant is not in probe.json)."""
    have = {v.get("kind") for v in probe.get("variants") or ()}
    return [k for k in KINDS if k in have]


def twin(probe: dict) -> dict:
    """The variant that is the reference computation under another name, if the probe ran one: the null twin
    (amendment v0.8), or else a precision variant whose dtype is the reference's (fp16 on a T4)."""
    ref = (probe.get("rig") or {}).get("reference_dtype")
    vs = list(probe.get("variants") or ())
    pick = next((v for v in vs if v.get("kind") == "null"), None) or next(
        (v for v in vs if ref and v.get("kind") == "precision" and DTYPES.get(str(v.get("value"))) == ref), None)
    if pick is None:
        return None
    one, kind = {**probe, "variants": [pick]}, (pick["kind"],)
    points = [c[1] for c in _cells(one, kind, allowed_only=False)]
    return {"variant": pick["name"], "deliberate": pick["kind"] == "null", "reference_dtype": ref,
            "counted_in_s_max": pick["kind"] != "null" and bool(pick.get("allowed")),
            "at": best(one, kind), "at_under_load": best(one, kind, load_only=True),
            "largest_point_abs": max((abs(p) for p in points), default=None)}


def paired(probe: dict, alpha: float = 0.05) -> dict:
    """Round-paired savings (amendment v0.8; declared, decides nothing). In each round a variant's power at a level is
    set against the mean of the two reference measurements that bracket that round, which takes drift between rounds
    out of the comparison, and a one-sided upper bound is taken over rounds. Needs the per-round powers probes keep
    since v0.8 (``power_w``); None for older probes. Cells are the ones the registered s_max counts."""
    import math

    from .conformal import t_upper
    vs = list(probe.get("variants") or ())
    ref = next((v for v in vs if v.get("kind") == "reference"), None)
    if ref is None:
        return None
    rw = {float(c["level"]): c.get("power_w") for c in ref.get("levels") or ()}
    cells, rounds = [], 0
    for v in vs:
        if v.get("kind") == "reference" or not v.get("allowed"):
            continue
        for c in v.get("levels") or ():
            pw, r = c.get("power_w"), rw.get(float(c["level"]))
            if "saving_upper95" not in c or not pw or not r or len(r) != 2 * len(pw) or len(pw) < 2:
                continue
            s = [1.0 - p / (0.5 * (r[2 * i] + r[2 * i + 1])) for i, p in enumerate(pw)]
            m = sum(s) / len(s)
            se = math.sqrt(sum((x - m) ** 2 for x in s) / (len(s) - 1) / len(s))
            cells.append((m + t_upper(alpha, len(s) - 1) * se, m, str(v["name"]), str(v["kind"]), float(c["level"])))
            rounds = max(rounds, len(pw))
    if not cells:
        return None
    counted = [c for c in cells if c[3] in KINDS]
    nul = [c for c in cells if c[3] == "null"]
    top, twin_top = (max(counted) if counted else None), (max(nul) if nul else None)
    return {"rounds": rounds, "s_max_paired": max(0.0, top[0]) if top else None, "at": _at(top),
            "s_null_paired": max(0.0, twin_top[0]) if twin_top else None, "null_at": _at(twin_top)}


def reading(probe: dict, gap: float = None, load: float = None) -> dict:
    """Per rule: the largest saving left, over all load levels (as s_max counts them) and under load; with a trial's
    closure gap and mean predicted share of capacity, the slack-inflated gap each would give, holding both as measured
    (a trial run under that rule would measure them again)."""
    meas = measured_kinds(probe)
    rows = []
    for key, label, fixed in RULES:
        free = [k for k in KINDS if k not in fixed]
        a, u = best(probe, free), best(probe, free, load_only=True)
        row = {"rule": key, "label": label, "fixed": list(fixed), "free": free,
               "free_not_measured": [k for k in free if k not in meas],
               "s": max(0.0, a["upper95"]) if a else 0.0, "at": a,
               "s_under_load": max(0.0, u["upper95"]) if u else 0.0, "at_under_load": u,
               "largest_point_under_load": largest_point(probe, free),
               "nothing_left_in_sweep": a is None}
        row["lower_bound"] = bool(row["free_not_measured"])
        if gap is not None and load is not None:
            row["slack_inflated_gap"] = float(gap) + row["s"] * float(load)
            row["slack_inflated_gap_under_load"] = float(gap) + row["s_under_load"] * float(load)
        rows.append(row)
    s_max = probe.get("s_max")
    return {"scope": SCOPE, "kinds_measured": meas, "kinds_not_measured": [k for k in KINDS if k not in meas],
            "repeats": (probe.get("settings") or {}).get("repeats"), "s_max": s_max,
            "reproduces_s_max": (abs(rows[0]["s"] - float(s_max)) < 1e-12) if s_max is not None else None,
            "closure_gap_fraction": gap, "mean_predicted_fraction_of_capacity": load,
            "rules": rows, "null_twin": twin(probe), "paired": paired(probe)}


def pct(x, d: int = 1) -> str:
    return "n/a" if x is None else f"{100 * x:.{d}f}%"


def where(at: dict) -> str:
    return "nothing in the sweep" if at is None else f"{at['variant']} at load {at['level']:g}"


def summary_lines(rep: dict) -> list:
    out = [f"efficiency slack left under each rule ({rep['scope']})",
           f"kinds measured: {', '.join(WORDS[k] for k in rep['kinds_measured']) or 'none'}"
           + (f"; not measured: {', '.join(WORDS[k] for k in rep['kinds_not_measured'])} (a rule that leaves them "
              f"free gives a lower bound)" if rep["kinds_not_measured"] else "")
           + (f"; {rep['repeats']} rounds" if rep.get("repeats") else "")]
    gap, load = rep["closure_gap_fraction"], rep["mean_predicted_fraction_of_capacity"]
    for r in rep["rules"]:
        lb = ">= " if r["lower_bound"] else ""
        if r["nothing_left_in_sweep"]:
            line = f"  {r['label']}: nothing left in this sweep (not a measured zero)"
        else:
            p = r["largest_point_under_load"]
            line = (f"  {r['label']}: {lb}{pct(r['s'])} ({where(r['at'])}, measured {pct(r['at']['point'])}); "
                    f"under load {lb}{pct(r['s_under_load'])} ({where(r['at_under_load'])})"
                    + (f"; largest measured saving under load {pct(p['point'])} ({where(p)})" if p else ""))
        if "slack_inflated_gap" in r:
            line += f"; with this run's gap {pct(gap, 2)} and load {load:.2f}: {pct(r['slack_inflated_gap'])}"
        out.append(line)
    t = rep.get("null_twin")
    if t:
        what = ("the null twin (the reference run again under another name)" if t["deliberate"] else
                f"{t['variant']} (the reference computation here: {t['reference_dtype']})")
        out.append(f"  {what} has a true saving of zero, and a bound of {pct((t['at'] or {}).get('upper95'))} over all "
                   f"levels, {pct((t['at_under_load'] or {}).get('upper95'))} under load (measured savings at most "
                   f"{pct(t['largest_point_abs'])} either way): the bound noise and drift alone give at this sample size")
    pa = rep.get("paired")
    if pa:
        out.append(f"  round-paired (each round against the reference measurements that bracket it; declared in "
                   f"amendment v0.8, decides nothing): s_max {pct(pa['s_max_paired'])} ({where(pa['at'])})"
                   + (f", null twin {pct(pa['s_null_paired'])}" if pa.get("s_null_paired") is not None else "")
                   + f", over {pa['rounds']} rounds")
    if rep["reproduces_s_max"] is False:
        out.append("  WARNING: the rule with nothing fixed does not reproduce this probe's s_max")
    return out
