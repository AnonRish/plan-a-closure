"""The pre-registered T1 decision rules (docs/PREREGISTRATION.md section 3), read mechanically off one trial's results.

Nothing here is a new analysis: every number comes from results.json. The rules were written for the registered Tier 1
trial (an instrumented H100/H200 node with an independent DC-bus meter). On any other run (a shakedown with NVML only,
a simulation) the same reading says what those data would decide, not what Plan A can claim, and `scope` says so.
A hypothesis is True or False when the run is large enough to decide it, and None when it is not.
"""
from __future__ import annotations

JB_MIN, N_EFF_MIN = 0.01, 15.0                       # H1.1, per regime and channel
N_NULL_MIN, FPR_TIMES_ALPHA = 200, 3.0               # H1.2
DETECT_MIN, PRIMARY, STRETCH = 0.95, 0.05, 0.02      # H1.3 and the overall outcome
MIN_N = 8                                            # the smallest cell the f95 rules count (trial.py); used for H1.3
COVER_MIN = 0.95                                     # H1.4


def _scope(status: str) -> str:
    s = str(status)
    if s.startswith("HARDWARE+DCBUS (independent meter)"):
        return "registered reading (independent DC-bus meter)"
    if s.startswith("HARDWARE+DCBUS"):
        return "meter unverified: not an absolute-power channel, so H1.5 is not supported"
    if s.startswith("HARDWARE (NVML"):
        return ("shakedown reading: NVML only, so assumption A6 does not hold; what these data would decide, not a "
                "Plan A claim")
    return f"{s}: validates the code and estimators only, no physical claim"


def evaluate(res: dict, alpha: float) -> dict:
    cal = [{"channel": ch, "regime": r, "jarque_bera_p": p, "n_eff": n}
           for ch in ("energy", "busy")
           for r, (p, n) in enumerate(zip(res["normality_p"][ch], res["calibration_n_eff"][ch]))]
    h11 = all(c["jarque_bera_p"] >= JB_MIN and c["n_eff"] >= N_EFF_MIN for c in cal)

    fp = res["false_positive"]["combined"]
    h12 = None if fp["n"] < N_NULL_MIN else bool(fp["rate"] <= FPR_TIMES_ALPHA * alpha)

    det = res.get("detection_at_or_above_fraction")             # results from before 0.7.0 do not have it
    h13 = None
    if det:
        h13 = {}
        for name, thr in (("primary", PRIMARY), ("stretch", STRETCH)):
            h13[name] = {cl: {**v, "holds": None if v["n"] < MIN_N else bool(v["rate"] >= DETECT_MIN),
                              "certified": bool(v["n"] and v["cp95_lower"] >= DETECT_MIN)}
                         for cl, v in det[str(thr)].items()}

    cov = res["bound"]["coverage_nonslack"]
    h14 = None if cov is None else bool(cov >= COVER_MIN)

    gap = res.get("closure_gap_fraction")
    slack = res.get("slack") or {}
    sgap = slack.get("slack_inflated_gap_fraction")
    if not h11:
        outcome, why = "UNDERPOWERED", "H1.1 fails, so no false-alarm claim is made"
    elif h12 is None:
        outcome, why = "NOT DECIDED", f"{fp['n']} null audit blocks; H1.2 needs at least {N_NULL_MIN}"
    elif not h12:
        outcome, why = "FAIL", f"false alarms {fp['k']}/{fp['n']} exceed {FPR_TIMES_ALPHA:g} x alpha"
    elif h14 is None:
        outcome, why = "NOT DECIDED", "no hidden blocks with hidden energy, so H1.4 cannot be checked"
    elif not h14:
        outcome, why = "FAIL", f"the hidden-energy bound covers {cov:.1%} of hidden blocks, under {COVER_MIN:.0%}"
    elif gap is None:
        outcome, why = "FAIL", "no hidden fraction was detected 95% of the time, so there is no closure gap"
    elif sgap is None:
        outcome, why = "NOT DECIDED", "efficiency slack was not measured (hw-probe), so there is no slack-inflated gap"
    elif sgap <= STRETCH:
        outcome, why = "PASS-stretch", f"slack-inflated gap {sgap:.1%} <= {STRETCH:.0%}"
    elif sgap <= PRIMARY:
        outcome, why = "PASS-primary", f"slack-inflated gap {sgap:.1%} <= {PRIMARY:.0%}"
    else:
        outcome, why = "FAIL", f"slack-inflated gap {sgap:.1%} is above {PRIMARY:.0%}"
    return {"scope": _scope(res.get("status", "")),
            "H1.1": {"holds": h11, "regimes": cal},
            "H1.2": {"holds": h12, "k": fp["k"], "n": fp["n"], "rate": fp["rate"], "cp95_upper": fp["cp95_upper"],
                     "limit": FPR_TIMES_ALPHA * alpha, "min_null_blocks": N_NULL_MIN},
            "H1.3": h13,
            "H1.4": {"holds": h14, "coverage_nonslack": cov},
            "closure_gap_fraction": gap, "slack_inflated_gap_fraction": sgap,
            "outcome": outcome, "why": why}


def _word(h) -> str:
    return "not decided" if h is None else "holds" if h else "fails"


def _pct(x, d=1) -> str:
    return "n/a" if x is None else f"{100 * x:.{d}f}%"


def summary_lines(ev: dict) -> list:
    """The lines tier0's SUMMARY.md and results.md show."""
    c = "; ".join(f"{r['channel']}{'' if len(ev['H1.1']['regimes']) <= 2 else ' ' + str(r['regime'])}: "
                  f"Jarque-Bera p {r['jarque_bera_p']:.2g}, n_eff {r['n_eff']:.1f}" for r in ev["H1.1"]["regimes"])
    h2 = ev["H1.2"]
    lines = [f"- scope: {ev['scope']}",
             f"- H1.1 calibration valid (Jarque-Bera p >= {JB_MIN} and n_eff >= {N_EFF_MIN:g} in every regime): "
             f"{_word(ev['H1.1']['holds'])} ({c})",
             f"- H1.2 false alarms (at most {FPR_TIMES_ALPHA:g} x alpha = {_pct(h2['limit'])} on at least "
             f"{h2['min_null_blocks']} null blocks): {_word(h2['holds'])}: {h2['k']}/{h2['n']} "
             f"(95% upper bound {_pct(h2['cp95_upper'])})"]
    if ev["H1.3"] is None:
        lines.append("- H1.3 detection at hidden fraction >= 5%: not computed (results from before 0.7.0)")
    else:
        for name, thr in (("primary", PRIMARY), ("stretch", STRETCH)):
            row = ev["H1.3"][name]
            per = "; ".join(f"{cl} {v['k']}/{v['n']} {_word(v['holds'])}" for cl, v in row.items()
                            if cl != "pooled_nonslack")
            p = row["pooled_nonslack"]
            lines.append(f"- H1.3 {name}: detection >= 95% at hidden fraction >= {thr:.0%}, per class (decided once a "
                         f"class has {MIN_N} such blocks): {per}. Pooled over classes: {p['k']}/{p['n']}, 95% lower "
                         f"bound {_pct(p['cp95_lower'])} ({'certified' if p['certified'] else 'not certified'} at 95%)")
    lines += [f"- H1.4 hidden-energy bound covers at least 95% of non-slack hidden blocks (against the hidden energy "
              f"recorded; on hardware, what the load was set to inject): {_word(ev['H1.4']['holds'])} "
              f"({_pct(ev['H1.4']['coverage_nonslack'])})",
              f"- outcome: **{ev['outcome']}** ({ev['why']}); closure gap {_pct(ev['closure_gap_fraction'], 2)}, "
              f"slack-inflated {_pct(ev['slack_inflated_gap_fraction'], 2)}"]
    return lines
