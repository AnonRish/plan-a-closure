"""compute-ledger command line."""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from . import planA
from .distributions import TwoPieceLogNormal
from .ledger import Ledger, LedgerError
from .reconcile import Estimate, Fitted, Flat, HalfNormal, consistency, posterior_hidden
from .stock import roll_forward

_SUFFIX = {"k": 1e3, "m": 1e6, "b": 1e9}


def parse_amount(text: str) -> float:
    t = text.strip().replace(",", "").replace("_", "")
    if t and t[-1].lower() in _SUFFIX:
        return float(t[:-1]) * _SUFFIX[t[-1].lower()]
    return float(t)


def fmt(x: float) -> str:
    return ("%.2fM" % (x / 1e6)) if abs(x) >= 1e5 else ("%.1fK" % (x / 1e3)) if abs(x) >= 1e2 else "%.3g" % x


def fmt_value(c, v: float) -> str:
    if c.unit == "H100e":
        return fmt(v)
    if c.unit == "%":
        return "%.3f%%" % v
    return "%.6g" % v


def cmd_plan_a(a) -> int:
    checks = planA.reproduce()
    if a.json:
        json.dump([{"name": c.name, "computed": c.computed, "published": c.published, "tol": c.tol, "unit": c.unit,
                    "ok": c.ok, "note": c.note} for c in checks], sys.stdout, indent=1)
        print()
    else:
        for c in checks:
            pub = "-" if c.published is None else fmt_value(c, c.published)
            print("%-4s %-84s computed %-10s published %-10s tolerance %s" % ("ok" if c.ok else "FAIL", c.name[:84],
                                                                          fmt_value(c, c.computed), pub, fmt_value(c, c.tol)))
        bad = [c for c in checks if not c.ok]
        print("\n%d checks, %d failing" % (len(checks), len(bad)))
    return 1 if any(not c.ok for c in checks) else 0


def cmd_roll(a) -> int:
    prod = [parse_amount(x) for x in a.production.split(",")]
    hl = None if a.half_life in (None, "none") else float(a.half_life)
    s = roll_forward(parse_amount(a.stock0), prod, hl)
    for i, v in enumerate(s, 1):
        print("after year %d: %s" % (i, fmt(v)))
    return 0


def _prior(spec: str):
    if spec == "flat":
        return Flat()
    kind, _, rest = spec.partition(":")
    if kind == "halfnormal":
        return HalfNormal(parse_amount(rest))
    if kind == "fitted":
        p10, p50, p90 = (parse_amount(x) for x in rest.split(","))
        return Fitted(TwoPieceLogNormal(p10, p50, p90))
    raise SystemExit("prior must be flat, halfnormal:TAU or fitted:P10,P50,P90")


def cmd_reconcile(a) -> int:
    d = parse_amount(a.declared)
    est = Estimate(parse_amount(a.lo), parse_amount(a.hi), a.level)
    c = consistency(d, est)
    post = posterior_hidden(d, est, _prior(a.prior))
    print("declared %s; independent estimate %s to %s (%d%% interval, sigma %s)" % (fmt(d), fmt(est.lo), fmt(est.hi), round(100 * est.level), fmt(est.sigma)))
    print("estimate centre is %.2f sigma %s the declaration; chance of an estimate this high if the declaration is complete: %.3f" % (
        abs(c.z), "above" if c.z >= 0 else "below", c.p_if_complete))
    print("undeclared stock, posterior: median %s, mean %s, 10%%-90%% %s to %s, 99%% %s" % (
        fmt(post.median), fmt(post.mean), fmt(post.quantile(0.1)), fmt(post.quantile(0.9)), fmt(post.quantile(0.99))))
    print("as a share of the declared stock: median %.2f%%, 90th percentile %.2f%%" % (100 * post.median / d, 100 * post.quantile(0.9) / d))
    for x in (a.exceeds or []):
        t = parse_amount(x)
        print("P(undeclared > %s) = %.3f" % (fmt(t), post.prob_exceeds(t)))
    return 0


def cmd_ledger(a) -> int:
    try:
        led = Ledger.from_dict(json.load(open(a.file)))
        led.check()
    except (LedgerError, KeyError, ValueError, OSError) as e:
        print("INVALID: %s" % e)
        return 1
    print("valid: %d accounts, %d events, total %s, produced %s, retired %s; digest %s" % (
        len(led.accounts()), len(led.history), fmt(led.total()), fmt(led.produced), fmt(led.retired), led.digest()[:16]))
    for k, v in sorted(led.by_owner().items()):
        print("  owner %-10s %s" % (k, fmt(v)))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="compute-ledger", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("plan-a", help="reproduce the Plan A compute figures from their inputs (exit 1 if any check fails)")
    c.add_argument("--json", action="store_true")
    c.set_defaults(fn=cmd_plan_a)
    c = sub.add_parser("roll", help="roll a stock forward with chip survival")
    c.add_argument("--stock0", required=True)
    c.add_argument("--production", required=True, help="comma list, e.g. 14.2M,35.7M")
    c.add_argument("--half-life", default="none", help="years, or 'none' for a running sum")
    c.set_defaults(fn=cmd_roll)
    c = sub.add_parser("reconcile", help="how much of the true stock could be undeclared?")
    c.add_argument("--declared", required=True)
    c.add_argument("--lo", required=True, help="low end of the independent estimate's central interval")
    c.add_argument("--hi", required=True)
    c.add_argument("--level", type=float, default=0.8)
    c.add_argument("--prior", default="flat", help="flat | halfnormal:TAU | fitted:P10,P50,P90")
    c.add_argument("--exceeds", action="append", help="also print P(undeclared > X); repeatable")
    c.set_defaults(fn=cmd_reconcile)
    c = sub.add_parser("ledger", help="load and verify a ledger file (replays events, checks conservation)")
    c.add_argument("file")
    c.set_defaults(fn=cmd_ledger)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
