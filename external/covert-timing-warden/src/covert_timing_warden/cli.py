"""``covert-timing-warden``: bounds, exfiltration arithmetic, detection on your own traces, and a self-check demo."""
from __future__ import annotations

import argparse
import json
import sys

import numpy as np

from . import mitigate as M
from .channels import LevelChannel, QuantileChannel, random_symbols
from .detect import Warden
from .traffic import BurstyMarkov, LogNormalIID, load_ipd_csv


def _out(obj) -> None:
    json.dump(obj, sys.stdout, indent=2)
    sys.stdout.write("\n")


def _bound_dict(b: M.CapacityBound) -> dict:
    return {"mitigation": b.mitigation, "lower_bits_per_packet": b.lower_bits,
            "upper_bits_per_packet": b.upper_bits, "assumptions": b.assumptions}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="covert-timing-warden", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("bounds", help="per-packet leakage bracket for a mitigation")
    b.add_argument("--mitigation", choices=["quantizer", "jitter", "fixed"], required=True)
    b.add_argument("--param", type=float, required=True, help="tick period / jitter width / schedule period, seconds")
    b.add_argument("--max-extra-delay", type=float, default=0.0, help="D: largest delay the sender can add, seconds")

    e = sub.add_parser("exfil", help="time to move a secret through a channel")
    e.add_argument("--secret-bits", type=float, required=True)
    e.add_argument("--bits-per-packet", type=float, required=True)
    e.add_argument("--pps", type=float, required=True, help="packets per second per stream")
    e.add_argument("--streams", type=int, default=1)

    d = sub.add_parser("detect", help="scan a candidate trace against an honest reference trace")
    d.add_argument("--reference", required=True)
    d.add_argument("--candidate", required=True)
    d.add_argument("--column", type=int, default=0)
    d.add_argument("--delays", action="store_true", help="files hold inter-packet delays, not timestamps")
    d.add_argument("--window", type=int, default=200)
    d.add_argument("--alpha", type=float, default=0.01)

    m = sub.add_parser("demo", help="detection rates on built-in synthetic scenarios")
    m.add_argument("--seed", type=int, default=0)
    m.add_argument("--windows", type=int, default=400)
    return p


def _demo(seed: int, n_windows: int, W: int = 200, alpha: float = 0.05) -> dict:
    rng = np.random.default_rng(seed)
    iid = Warden(LogNormalIID().sample(2 * 520 * W, rng), window=W, alpha=alpha)
    bur = Warden(BurstyMarkov().sample(2 * 520 * W, rng), window=W, alpha=alpha)
    n = n_windows * W
    rows = {}
    rows["honest i.i.d. (false-alarm rate)"] = iid.alarm_rate(LogNormalIID().sample(n, rng))
    rows["honest bursty (false-alarm rate)"] = bur.alarm_rate(BurstyMarkov().sample(n, rng))
    rows["naive 4-level channel, 2 bits/packet, vs i.i.d."] = iid.alarm_rate(
        LevelChannel(4, 0.02, 0.02).encode(random_symbols(n, 4, rng)))
    for bits in (1, 3):
        ch = QuantileChannel(LogNormalIID(), bits)
        rows[f"exact-marginal quantile channel, {bits} bit(s)/packet, vs i.i.d."] = iid.alarm_rate(
            ch.encode(random_symbols(n, ch.levels, rng), rng))
    ch = QuantileChannel(BurstyMarkov(), 2)
    rows["marginal-only quantile channel, 2 bits/packet, vs bursty"] = bur.alarm_rate(
        ch.encode(random_symbols(n, 4, rng), rng))
    return {"alpha": alpha, "window": W, "windows_per_scenario": n_windows, "alarm_rate": rows}


def main(argv=None) -> int:
    a = build_parser().parse_args(argv)
    if a.cmd == "bounds":
        mit = {"quantizer": M.QuantizedRelease, "jitter": M.UniformJitter, "fixed": M.FixedSchedule}[a.mitigation](a.param)
        _out(_bound_dict(mit.capacity(a.max_extra_delay)))
    elif a.cmd == "exfil":
        s = M.exfiltration_seconds(a.secret_bits, a.bits_per_packet, a.pps, a.streams)
        _out({"seconds": s, "days": s / 86400.0, "years": s / (86400.0 * 365.25)})
    elif a.cmd == "detect":
        ref = load_ipd_csv(a.reference, a.column, timestamps=not a.delays)
        cand = load_ipd_csv(a.candidate, a.column, timestamps=not a.delays)
        w = Warden(ref, window=a.window, alpha=a.alpha)
        res = w.scan(cand)
        trig: dict = {}
        for r in res:
            for n in r.triggered:
                trig[n] = trig.get(n, 0) + 1
        _out({"windows": len(res), "alarm_rate": float(np.mean([r.alarm for r in res])) if res else None,
              "alpha": a.alpha, "null_windows": w.n_null, "triggered_by_detector": trig,
              "min_p_combined": min((r.p_combined for r in res), default=None)})
    elif a.cmd == "demo":
        _out(_demo(a.seed, a.windows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
