"""The pre-registered T1 decision rules (docs/PREREGISTRATION.md section 3), read mechanically off one trial's results.

Nothing here is a new analysis: every number comes from results.json. The rules were written for the registered Tier 1
trial (an instrumented H100/H200 node with an independent DC-bus meter). On any other run (a shakedown with NVML only,
a simulation, an analysis applied after the fact) the same reading says what those data would decide, not what Plan A
can claim, and `scope` says so. A hypothesis is True or False when the run is large enough to decide it, and None when
it is not.

Two rules changed with amendment v0.6 and are read by the analysis a run used:
  H1.1  straight-line analysis: Jarque-Bera p >= 0.01 and n_eff >= 15 in every regime (its thresholds lean on
        normality). Link analysis: the combined threshold is conformal, which needs at least 1/alpha - 1 effective
        reference blocks and assumes no distribution; normality is reported, not required.
  H1.4  link analysis, where the load generator counted the seconds its hidden load ran: the floor time bound (busy
        time above the least the verified work can take) covers them in at least 95% of non-slack hidden blocks. The
        calibrated time bound and the energy bound are reported beside it as checks on assumption A1. Otherwise (the
        straight-line analysis, earlier runs): the energy bound against the hidden energy recorded.
"""
from __future__ import annotations

JB_MIN, N_EFF_MIN = 0.01, 15.0                       # H1.1, straight-line analysis
N_NULL_MIN, FPR_TIMES_ALPHA = 200, 3.0               # H1.2
DETECT_MIN, PRIMARY, STRETCH = 0.95, 0.05, 0.02      # H1.3 and the overall outcome
MIN_N = 8                                            # the smallest cell the f95 rules count (trial.py); used for H1.3
COVER_MIN = 0.95                                     # H1.4


def _scope(status: str) -> str:
    s = str(status)
    if "POST HOC" in s:
        return ("post hoc reading: this analysis was chosen after these data were seen, so it describes them and "
                "decides nothing")
    if "POOLED" in s and "NVML" in s:
        return ("shakedown reading of several trials pooled: NVML only, so assumption A6 does not hold; what these "
                "data would decide, not a Plan A claim")
    if s.startswith("HARDWARE+DCBUS (independent meter)"):
        return "registered reading (independent DC-bus meter)"
    if s.startswith("HARDWARE+DCBUS"):
        return "meter unverified: not an absolute-power channel, so H1.5 is not supported"
    if s.startswith("HARDWARE (NVML"):
        return ("shakedown reading: NVML only, so assumption A6 does not hold; what these data would decide, not a "
                "Plan A claim")
    return f"{s}: validates the code and estimators only, no physical claim"


def evaluate(res: dict, alpha: float) -> dict:
    link = res.get("analysis") == "link"
    cal = [{"channel": ch, "regime": r, "jarque_bera_p": p, "n_eff": n}
           for ch in ("energy", "busy")
           for r, (p, n) in enumerate(zip(res["normality_p"][ch], res["calibration_n_eff"][ch]))]
    how = list((res.get("methods_used") or {}).get("combined") or [])
    if link:
        h11 = bool(how) and all(str(m).startswith("conformal") for m in how)
    else:
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

    bound = res.get("bound") or {}
    cov_e, time = bound.get("coverage_nonslack"), bound.get("time") or {}
    by_time = link and time.get("coverage_floor_bound") is not None
    cov = time["coverage_floor_bound"] if by_time else cov_e
    h14 = None if cov is None else bool(cov >= COVER_MIN)
    what = "time bound" if by_time else "hidden-energy bound"

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
        outcome, why = "NOT DECIDED", "no hidden blocks with hidden load, so H1.4 cannot be checked"
    elif not h14:
        outcome, why = "FAIL", f"the {what} covers {cov:.1%} of hidden blocks, under {COVER_MIN:.0%}"
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
    return {"scope": _scope(res.get("status", "")), "analysis": "link" if link else "linear",
            "H1.1": {"holds": h11, "rule": "conformal threshold" if link else "normality and n_eff",
                     "threshold_methods": how, "regimes": cal},
            "H1.2": {"holds": h12, "k": fp["k"], "n": fp["n"], "rate": fp["rate"], "cp95_upper": fp["cp95_upper"],
                     "limit": FPR_TIMES_ALPHA * alpha, "min_null_blocks": N_NULL_MIN},
            "H1.3": h13,
            "H1.4": {"holds": h14, "basis": "time" if by_time else "energy", "coverage_nonslack": cov,
                     "energy_coverage_nonslack": cov_e, "energy_coverage_floor_bound": bound.get("coverage_floor_bound"),
                     "time": time or None},
            "closure_gap_fraction": gap, "slack_inflated_gap_fraction": sgap,
            "outcome": outcome, "why": why}


def _word(h) -> str:
    return "not decided" if h is None else "holds" if h else "fails"


def _pct(x, d=1) -> str:
    return "n/a" if x is None else f"{100 * x:.{d}f}%"


def summary_lines(ev: dict) -> list:
    """The lines tier0's SUMMARY.md and results.md show."""
    regs = ev["H1.1"]["regimes"]
    c = "; ".join(f"{r['channel']}{'' if len(regs) <= 2 else ' ' + str(r['regime'])}: "
                  f"Jarque-Bera p {r['jarque_bera_p']:.2g}, n_eff {r['n_eff']:.1f}" for r in regs)
    h2 = ev["H1.2"]
    if ev["H1.1"]["rule"] == "conformal threshold":
        h1 = (f"- H1.1 calibration valid (the threshold is conformal: no distribution assumed, at least 1/alpha - 1 "
              f"effective reference blocks): {_word(ev['H1.1']['holds'])} (threshold: "
              f"{', '.join(ev['H1.1']['threshold_methods']) or 'none'}; reported only: {c})")
    else:
        h1 = (f"- H1.1 calibration valid (Jarque-Bera p >= {JB_MIN} and n_eff >= {N_EFF_MIN:g} in every regime): "
              f"{_word(ev['H1.1']['holds'])} ({c})")
    lines = [f"- scope: {ev['scope']}", h1,
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
    h4 = ev["H1.4"]
    if h4["basis"] == "time":
        t = h4["time"]
        lines.append(f"- H1.4 the time bound covers the seconds the hidden load really ran in at least 95% of non-slack "
                     f"hidden blocks: {_word(h4['holds'])} ({_pct(h4['coverage_nonslack'])} of {t['n']}, by the floor "
                     f"bound: busy time above the least the verified work can take). Reported only, as checks on "
                     f"additivity (A1): the calibrated time bound covers {_pct(t.get('coverage_nonslack'))}; the "
                     f"energy bound covers the hidden load's solo energy in {_pct(h4['energy_coverage_nonslack'])} "
                     f"(calibrated) and {_pct(h4.get('energy_coverage_floor_bound'))} (floor)")
    else:
        lines.append(f"- H1.4 hidden-energy bound covers at least 95% of non-slack hidden blocks (against the hidden "
                     f"energy recorded; on hardware, what the load was set to inject): {_word(h4['holds'])} "
                     f"({_pct(h4['coverage_nonslack'])})")
    lines.append(f"- outcome: **{ev['outcome']}** ({ev['why']}); closure gap {_pct(ev['closure_gap_fraction'], 2)}, "
                 f"slack-inflated {_pct(ev['slack_inflated_gap_fraction'], 2)}")
    return lines
