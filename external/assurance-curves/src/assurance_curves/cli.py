"""Command line: ``python -m assurance_curves`` / ``assurance-curves``. JSON on stdout."""
from __future__ import annotations

import argparse
import json
import sys

from . import canary, core, falsealarm
from .rogue import RogueDeploymentModel, granularity_table


def _out(obj) -> None:
    json.dump(obj, sys.stdout, indent=2)
    sys.stdout.write("\n")


def _sizes(s: str):
    return [float(x) for x in s.split(",") if x.strip()]


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="assurance-curves", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("detect", help="P(detect) for budget c and n fake packets")
    d.add_argument("--budget", type=float, required=True)
    d.add_argument("--fake", type=float, required=True)

    b = sub.add_parser("budget", help="budget needed to catch n fakes at a confidence")
    b.add_argument("--fake", type=float, required=True)
    b.add_argument("--confidence", type=float, required=True)

    m = sub.add_parser("min-fake", help="fakes needed for a confidence at a budget")
    m.add_argument("--budget", type=float, required=True)
    m.add_argument("--confidence", type=float, required=True)

    r = sub.add_parser("rogue", help="detection of a rogue deployment")
    r.add_argument("--budget", type=float, required=True)
    r.add_argument("--packet-size", type=float, required=True, help="H100e-hours per packet")
    r.add_argument("--size", type=float, required=True, help="rogue deployment size, H100e")
    r.add_argument("--confidence", type=float, default=0.99)
    r.add_argument("--hours", type=float, default=None)
    r.add_argument("--pool", type=float, default=None, help="total pool in H100e (for recompute cost)")

    g = sub.add_parser("granularity", help="hours-to-detect by tap granularity")
    g.add_argument("--budget", type=float, required=True)
    g.add_argument("--confidence", type=float, default=0.99)
    g.add_argument("--sizes", type=_sizes, default=[1e3, 1e4, 1e5])
    g.add_argument("--hours-per-packet", type=float, default=1.0)
    g.add_argument("--model", choices=["exact", "poisson"], default="poisson")

    f = sub.add_parser("false-alarm", help="false-flag budget at deployment scale")
    f.add_argument("--pool", type=float, required=True)
    f.add_argument("--budget", type=float, required=True)
    f.add_argument("--packet-size", type=float, required=True)
    f.add_argument("--max-alarms-per-year", type=float, default=1.0)
    f.add_argument("--delta", type=float, default=0.05)

    c = sub.add_parser("canary", help="canaries needed to catch a suppressing server")
    c.add_argument("--suppression", type=float, required=True)
    c.add_argument("--confidence", type=float, default=0.99)
    return p


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    if a.cmd == "detect":
        _out({
            "budget": a.budget, "n_fake": a.fake,
            "p_detected_exact": core.p_detected_exact(a.budget, a.fake),
            "p_detected_poisson": core.p_detected_poisson(1.0, min(1.0, a.budget * a.fake)),
            "p_undetected_exact": core.p_undetected_exact(a.budget, a.fake),
            "nines_exact": core.nines(core.p_detected_exact(a.budget, a.fake)),
        })
    elif a.cmd == "budget":
        _out({"n_fake": a.fake, "confidence": a.confidence,
              "budget_exact": core.required_budget(a.fake, a.confidence),
              "budget_poisson": core.required_budget(a.fake, a.confidence, model="poisson")})
    elif a.cmd == "min-fake":
        _out({"budget": a.budget, "confidence": a.confidence,
              "fake_packets_exact_real": core.fake_packets_for_confidence(a.budget, a.confidence),
              "fake_packets_exact_int": core.min_fake_packets_exact(a.budget, a.confidence),
              "fake_packets_poisson": core.fake_packets_for_confidence(a.budget, a.confidence, model="poisson")})
    elif a.cmd == "rogue":
        mdl = RogueDeploymentModel(a.budget, a.packet_size)
        res = {
            "h100e_hours_to_detect_exact": mdl.h100e_hours_to_detect(a.confidence),
            "h100e_hours_to_detect_poisson": mdl.h100e_hours_to_detect(a.confidence, model="poisson"),
            "hours_to_detect_exact": mdl.hours_to_detect(a.size, a.confidence),
            "hours_to_detect_poisson": mdl.hours_to_detect(a.size, a.confidence, model="poisson"),
        }
        if a.hours is not None:
            res["p_detect_within_hours"] = mdl.p_detect(a.size, a.hours)
        if a.pool is not None:
            res["recompute_capacity_h100e"] = mdl.recompute_capacity_h100e(a.pool)
        _out(res)
    elif a.cmd == "granularity":
        _out(granularity_table(a.budget, a.confidence, a.sizes,
                               hours_per_packet=a.hours_per_packet, model=a.model))
    elif a.cmd == "false-alarm":
        n = falsealarm.audited_packets_per_year(a.pool, a.budget, a.packet_size)
        fpr = falsealarm.max_fpr_for_alarm_budget(n, a.max_alarms_per_year)
        _out({
            "audited_packets_per_year": n,
            "max_per_packet_fpr": fpr,
            "gaussian_threshold_sigma": falsealarm.gaussian_threshold_sigma(fpr),
            "honest_packets_to_certify_that_fpr": falsealarm.packets_to_certify_fpr(fpr, a.delta),
        })
    elif a.cmd == "canary":
        n = canary.canaries_needed(a.suppression, a.confidence)
        _out({"suppression_rate": a.suppression, "confidence": a.confidence, "canaries_needed": n,
              "p_catch_with_that_many": canary.p_catch_suppression(a.suppression, n)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
