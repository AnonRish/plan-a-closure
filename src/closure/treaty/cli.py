"""`closure treaty ...`: the treaty mechanisms from the command line (docs/TREATY_COVERAGE.md)."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path


def _print(obj) -> None:
    print(json.dumps(obj, indent=2, default=float))


def _read(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


# ---- thresholds and deterrence ---------------------------------------------------------------------------------
def cmd_thresholds(a) -> int:
    from . import thresholds as T
    for t in T.THRESHOLDS.values():
        print(f"{t.key:26} {t.value:9.0e} {t.unit:7} {t.what} ({t.source})")
    r = T.narrow_path_regime_ratio_s(1e25, 1e17)
    print(f"\nA Narrow Path's Phase 0 pair: 1e25 FLOP at 1e17 FLOP/s takes {r / T.DAY_S:,.0f} days; its Phase 1 limits "
          "are said to allow a largest run 'within 12 days', which needs a ratio near 1e6 s.")
    return 0


def cmd_covert_days(a) -> int:
    from . import thresholds as T
    if a.run:
        run = Path(a.run)
        try:
            r = T.covert_days_from_trial(_read(run / "results.json"), _read(run / "prereg.json")["cfg"], a.threshold,
                                         a.fleet, use_slack=not a.no_slack)
        except ValueError as e:                     # e.g. a smoke trial too small to reach 95% detection anywhere
            print(f"{run}: {e}; give --gap to compute from an assumed gap instead")
            return 1
    else:
        if a.gap is None:
            print("give --run <trial folder> or --gap <share of capacity>")
            return 2
        r = T.covert_days(a.threshold, a.gap, a.fleet, a.p_max, a.floor, "given")
    _print(r.to_dict())
    return 0


def cmd_deterrence(a) -> int:
    from . import deterrence as D
    _print({"per_period_detection_needed": D.per_period_threshold(a.gain, a.penalty) if a.gain else None,
            "race": {"periods": a.periods, "prize_over_penalty": a.prize / a.penalty,
                     "cumulative_detection_needed": D.required_cumulative_detection(a.prize, a.penalty),
                     "per_period_detection_needed": D.race_threshold(a.periods, a.prize, a.penalty, a.discount)}})
    return 0


def cmd_race(a) -> int:
    from . import deterrence as D
    sigma = a.sigma if a.sigma is not None else D.sigma_from_min_detectable(a.min_detectable, a.alpha, a.beta)
    rows = [D.race_against_detection(f, sigma, a.block_s, a.threshold, a.fleet, a.p_max, a.floor,
                                     a.false_alarm_years) for f in a.fractions]
    _print({"sigma_fraction": sigma, "rows": rows})
    return 0


# ---- inspections, randomness, quorum ---------------------------------------------------------------------------
def cmd_inspect_plan(a) -> int:
    from . import inspection as I
    n = I.sample_size(a.declared, a.missing, a.assurance)
    _print({"declared": a.declared, "missing": a.missing, "assurance": a.assurance, "sample": n,
            "per_inspection_if_sampling_half": I.detection_probability(a.declared, a.missing, n // 2),
            "after_4_inspections_of_half": I.repeated_detection(a.declared, a.missing, n // 2, 4)})
    return 0


def cmd_beacon_commit(a) -> int:
    from . import beacon as B
    c = B.new_contribution(a.party)
    Path(a.out).write_text(json.dumps(c, indent=2), encoding="utf-8")
    print(f"publish this commitment now, reveal {a.out} (value and nonce) only after every party has committed:\n"
          f"{a.party}: {c['commitment']}")
    return 0


def cmd_beacon_seed(a) -> int:
    from . import beacon as B
    contribs = [_read(p) for p in a.contributions]
    comm = {c["party"]: c["commitment"] for c in contribs} if not a.commitments else _read(a.commitments)
    seed = B.seed(comm, {c["party"]: (c["nonce"], c["value"]) for c in contribs})
    print(seed.hex())
    return 0


def cmd_sortition(a) -> int:
    from . import beacon as B
    _print(B.sortition(bytes.fromhex(a.seed), _read(a.candidates), _read(a.per_group)))
    return 0


def cmd_quorum_verify(a) -> int:
    from . import quorum as Q
    r = Q.verify(_read(a.action), _read(a.approvals), _read(a.members), a.k, time.time())
    _print(r)
    return 0 if r["approved"] else 1


# ---- location --------------------------------------------------------------------------------------------------
def cmd_geo_keygen(a) -> int:
    from . import geoloc as G
    print(G.save_key(G.keygen(), a.out))
    return 0


def _hostport(s: str) -> tuple:
    host, _, port = s.rpartition(":")
    return host or "0.0.0.0", int(port)


def cmd_geo_landmark(a) -> int:
    from . import geoloc as G
    host, port = _hostport(a.listen)
    print(f"landmark {a.name} at ({a.lat}, {a.lon}) waiting on {host}:{port}", file=sys.stderr, flush=True)
    rec = G.serve_landmark(host, port, a.name, a.lat, a.lon, a.chip_pub, a.rounds, timeout=a.timeout)
    Path(a.out).write_text(json.dumps(rec.to_dict(), indent=2), encoding="utf-8")
    best = "none valid" if rec.min_rtt_s is None else f"{1e3 * rec.min_rtt_s:.3f} ms -> within {rec.max_km:,.0f} km"
    print(f"{rec.valid_rounds}/{rec.rounds} valid; fastest {best}; wrote {a.out}")
    return 0 if rec.valid_rounds else 1


def cmd_geo_chip(a) -> int:
    from . import geoloc as G
    host, port = _hostport(a.connect)
    print(f"answered {G.run_chip(host, port, G.load_key(a.key), timeout=a.timeout)} challenges")
    return 0


def cmd_geo_check(a) -> int:
    from . import geoloc as G
    recs = G.load_records(a.records)
    lat, lon = (float(x) for x in a.declared.split(","))
    r = G.check(recs, lat, lon)
    r["signatures_reverified"] = all(G.reverify(x) for x in recs)
    _print(r)
    return 0 if (r["consistent"] and r["signatures_reverified"]) else 1


# ---- coalition and redlines ------------------------------------------------------------------------------------
def cmd_coalition(a) -> int:
    from . import coalition as C
    countries, world = C.load()
    exclude = tuple(x for x in a.exclude.split(",") if x)
    table = C.players(countries, world, eu_as_bloc=not a.no_bloc, exclude=exclude)
    out = {"data": "World Bank GDP (current US$, 2023) and population (2025); see treaty/data/",
           "players": len(table), "excluded": list(exclude), "eu_as_bloc": not a.no_bloc}
    if a.members:
        m = [x for x in a.members.split(",") if x]
        g, p = C.shares(m, table)
        out["members"] = {"members": m, "gdp_share": g, "population_share": p, "activates": C.activates(m, table)}
    sm = C.smallest_coalitions(table, max_size=a.max_size, top=a.top)
    out["smallest"] = {**sm, "coalitions": [{"members": list(c), "gdp_share": C.shares(c, table)[0],
                                             "population_share": C.shares(c, table)[1]} for c in sm["coalitions"][:10]],
                       "count": len(sm["coalitions"])}
    ss = C.shapley_shubik(table, permutations=a.permutations, seed=a.seed)
    out["shapley_shubik_top"] = [{"player": k, "index": v[0], "se": v[1]}
                                 for k, v in sorted(ss.items(), key=lambda kv: -kv[1][0])[:a.show]]
    _print(out)
    return 0


def cmd_redlines(a) -> int:
    from . import coalition as C
    d = _read(a.findings)
    if isinstance(d, list):
        _print(C.run_timeline(d))
    else:
        lv, why = C.assess(d)
        _print({"level": lv, "measure": C.LEVELS[lv], "reasons": why})
    return 0


# ---- mock training run -----------------------------------------------------------------------------------------
def cmd_mock_job(a) -> int:
    from . import mockrun as M
    return M.job(a.out, a.dim, a.layers, a.batch, a.seed, a.device, a.max_steps, a.not_from_scratch)


def cmd_mock_run(a) -> int:
    from . import mockrun as M
    device = a.device
    if a.device.startswith("cuda"):
        from ..hw import gpu as G
        target = G.resolve(int(a.device.split(":")[1]) if ":" in a.device else 0)   # the physical GPU, by UUID
        print("GPU:", target.describe(), file=sys.stderr, flush=True)
        meter, device = M.NvmlMeter(target.nvml_index), target.torch_device          # "cpu" in a rehearsal
        if a.e_floor:
            floor, src = a.e_floor, "given"
        elif a.probe:
            pr = _read(a.probe)
            floor, src = pr.get("e_floor_j_per_flop"), f"hw-probe {pr.get('sha256', '')[:16]} ({pr.get('status')})"
            if not floor:
                print(f"{a.probe} has no energy floor (hw-probe measured none); give --e-floor J/FLOP instead")
                return 2
        else:
            print("on a GPU give --probe probe.json (hw-probe's measured energy floor) or --e-floor J/FLOP")
            return 2
    else:
        meter = M.ProcCpuMeter(a.watts_per_core)
        floor, src = (a.e_floor, "given") if a.e_floor else (M.cpu_energy_floor(a.watts_per_core),
                                                             "measured: large float32 matmul under the same model")
    rec = M.run_drill(a.budget_flop, floor, meter, a.out, a.dim, a.layers, a.batch, a.seed, device,
                      a.max_steps, floor_source=src, not_from_scratch=a.not_from_scratch, count_from=a.count_from)
    _print(rec)
    return 0 if (rec["compliant"] and rec["init_weights_match_seed"]) else 1


def add_parser(sp) -> None:
    t = sp.add_parser("treaty", help="mechanisms from the halt and treaty proposals (docs/TREATY_COVERAGE.md)")
    ts = t.add_subparsers(dest="treaty_cmd", required=True)
    s = ts.add_parser("thresholds"); s.set_defaults(f=cmd_thresholds)
    s = ts.add_parser("covert-days", help="days to a threshold-sized covert run at the hidden rate verification allows")
    s.add_argument("--threshold", type=float, default=1e25); s.add_argument("--fleet", type=float, default=100_000)
    s.add_argument("--run", default=None, help="a trial folder with results.json and prereg.json")
    s.add_argument("--gap", type=float, default=None); s.add_argument("--p-max", type=float, default=700.0)
    s.add_argument("--floor", type=float, default=0.5e-12); s.add_argument("--no-slack", action="store_true")
    s.set_defaults(f=cmd_covert_days)
    s = ts.add_parser("deterrence", help="detection needed for a covert programme not to pay")
    s.add_argument("--prize", type=float, default=100.0); s.add_argument("--penalty", type=float, default=1.0)
    s.add_argument("--periods", type=int, default=10); s.add_argument("--discount", type=float, default=1.0)
    s.add_argument("--gain", type=float, default=None); s.set_defaults(f=cmd_deterrence)
    s = ts.add_parser("race", help="sequential detection of sustained hidden load against time to a threshold run")
    s.add_argument("--fractions", type=float, nargs="+", default=[0.01, 0.001, 0.0001])
    s.add_argument("--sigma", type=float, default=None, help="per-block residual SD as a share of block capacity")
    s.add_argument("--min-detectable", type=float, default=0.02); s.add_argument("--alpha", type=float, default=0.01)
    s.add_argument("--beta", type=float, default=0.05); s.add_argument("--block-s", type=float, default=120.0)
    s.add_argument("--threshold", type=float, default=1e25); s.add_argument("--fleet", type=float, default=100_000)
    s.add_argument("--p-max", type=float, default=700.0); s.add_argument("--floor", type=float, default=0.5e-12)
    s.add_argument("--false-alarm-years", type=float, default=10.0); s.set_defaults(f=cmd_race)
    s = ts.add_parser("inspect-plan", help="chips to sample to find missing ones with a given assurance")
    s.add_argument("--declared", type=int, required=True); s.add_argument("--missing", type=int, required=True)
    s.add_argument("--assurance", type=float, default=0.95); s.set_defaults(f=cmd_inspect_plan)
    s = ts.add_parser("beacon-commit"); s.add_argument("--party", required=True); s.add_argument("--out", required=True)
    s.set_defaults(f=cmd_beacon_commit)
    s = ts.add_parser("beacon-seed"); s.add_argument("contributions", nargs="+")
    s.add_argument("--commitments", default=None, help="the commitments as published, {party: hex}")
    s.set_defaults(f=cmd_beacon_seed)
    s = ts.add_parser("sortition"); s.add_argument("--seed", required=True); s.add_argument("--candidates", required=True)
    s.add_argument("--per-group", required=True); s.set_defaults(f=cmd_sortition)
    s = ts.add_parser("quorum-verify"); s.add_argument("--action", required=True); s.add_argument("--approvals", required=True)
    s.add_argument("--members", required=True); s.add_argument("--k", type=int, required=True)
    s.set_defaults(f=cmd_quorum_verify)
    s = ts.add_parser("geo-keygen"); s.add_argument("--out", required=True); s.set_defaults(f=cmd_geo_keygen)
    s = ts.add_parser("geo-landmark", help="time a chip's signed answers from a known place")
    s.add_argument("--listen", default="0.0.0.0:7707"); s.add_argument("--name", required=True)
    s.add_argument("--lat", type=float, required=True); s.add_argument("--lon", type=float, required=True)
    s.add_argument("--chip-pub", required=True); s.add_argument("--rounds", type=int, default=50)
    s.add_argument("--timeout", type=float, default=600.0); s.add_argument("--out", required=True)
    s.set_defaults(f=cmd_geo_landmark)
    s = ts.add_parser("geo-chip", help="answer a landmark's challenges (connects out, so NAT is fine)")
    s.add_argument("--connect", required=True); s.add_argument("--key", required=True)
    s.add_argument("--timeout", type=float, default=600.0); s.set_defaults(f=cmd_geo_chip)
    s = ts.add_parser("geo-check"); s.add_argument("records", nargs="+")
    s.add_argument("--declared", required=True, help="LAT,LON of the declared site"); s.set_defaults(f=cmd_geo_check)
    s = ts.add_parser("coalition", help="the middle-powers agreement: activation, smallest coalitions, voting power")
    s.add_argument("--members", default=""); s.add_argument("--exclude", default="USA,CHN")
    s.add_argument("--no-bloc", action="store_true"); s.add_argument("--max-size", type=int, default=6)
    s.add_argument("--top", type=int, default=30); s.add_argument("--permutations", type=int, default=20000)
    s.add_argument("--seed", type=int, default=0); s.add_argument("--show", type=int, default=12)
    s.set_defaults(f=cmd_coalition)
    s = ts.add_parser("redlines", help="the measure a set of findings (or a monthly list of them) triggers")
    s.add_argument("--findings", required=True); s.set_defaults(f=cmd_redlines)
    s = ts.add_parser("mock-run", help="A Narrow Path's mock training run: can the provider stop a run at its budget?")
    s.add_argument("--budget-flop", type=float, required=True); s.add_argument("--device", default="cpu")
    s.add_argument("--e-floor", type=float, default=None); s.add_argument("--probe", default=None)
    s.add_argument("--watts-per-core", type=float, default=10.0); s.add_argument("--out", default="runs/mock-run")
    s.add_argument("--dim", type=int, default=256); s.add_argument("--layers", type=int, default=4)
    s.add_argument("--batch", type=int, default=64); s.add_argument("--seed", type=int, default=1)
    s.add_argument("--max-steps", type=int, default=None); s.add_argument("--not-from-scratch", action="store_true")
    s.add_argument("--count-from", choices=["spawn", "start"], default="spawn",
                   help="charge energy from process start (default) or from the job's start line (small drills)")
    s.set_defaults(f=cmd_mock_run)
    s = ts.add_parser("mock-job"); s.add_argument("--out", required=True); s.add_argument("--dim", type=int, required=True)
    s.add_argument("--layers", type=int, required=True); s.add_argument("--batch", type=int, required=True)
    s.add_argument("--seed", type=int, required=True); s.add_argument("--device", default="cpu")
    s.add_argument("--max-steps", type=int, required=True); s.add_argument("--not-from-scratch", action="store_true")
    s.set_defaults(f=cmd_mock_job)
