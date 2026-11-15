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
    try:
        a.threshold = T.flop_threshold(a.threshold)
    except ValueError as e:
        print(e)
        return 2
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
    reveals = {c["party"]: (c["nonce"], c["value"]) for c in contribs}
    if a.allow_missing and not a.public_value:
        print("refusing: --allow-missing without --public-value would let the last party to reveal choose between two "
              "draws it can already see")
        return 2
    seed = B.seed(comm, reveals, allow_missing=a.allow_missing)
    if a.public_value:
        seed = B.finalize(seed, bytes.fromhex(a.public_value))
    withheld = B.missing(comm, reveals)
    if withheld:
        print(f"withheld (named; their values are not in the seed): {', '.join(withheld)}", file=sys.stderr)
    print(seed.hex())
    return 0


def cmd_clause(a) -> int:
    from . import clauses as K
    r = K.in_force(_read(a.finding), _read(a.approvals), _read(a.members), a.k, time.time() if a.now is None else a.now)
    _print(r)
    return 0 if r["quorum"]["approved"] else 1


def cmd_bandwidth(a) -> int:
    from . import bandwidth as W
    _print(W.assess(a.cap_gbps, a.params, a.steps_per_s, a.pods, a.tokens_per_s, a.sync_every, a.bytes_per_value,
                    a.compression, a.bytes_per_token))
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


# ---- MIRI's draft agreement (arXiv:2511.10783) -------------------------------------------------------------------
def cmd_asi_tables(a) -> int:
    from . import asi_agreement as A
    got = A.tables(a.flop_s, a.boundaries)
    print(f"Appendix D.3, Tables 1 and 2, recomputed at {a.flop_s:.4g} FLOP/s per H100e ({a.boundaries} boundaries)")
    print(f"{'':22}" + "".join(f"{s:>10,}" for s in A.TABLE_SIZES))
    for k in A.TABLE_PRINTED:
        print(f"{k:22}" + "".join(f"{x:>10}" for x in got[k]))
    diff = A.compare_tables(a.flop_s, a.boundaries)
    print("\nevery cell matches the printed table" if not diff else
          "\ncells that differ from the printed table:\n" +
          "\n".join(f"  {k} at {s:,} H100e: printed {p}, recomputed {g}" for k, s, p, g in diff))
    return 0


def cmd_asi_run(a) -> int:
    from . import asi_agreement as A
    r = A.classify_run(a.pretraining, a.post_training, cumulative=not a.separate)
    _print({"category": r.category, "reasons": list(r.reasons), "needs": list(r.needs)})
    return 0


def cmd_asi_cluster(a) -> int:
    from . import asi_agreement as A
    d = _read(a.hosts)
    hosts = [A.Host(str(h["id"]), str(h.get("site", h["id"])),
                    float(h["tpp"]) if "tpp" in h else float(h["h100e"]) * A.H100E_TPP,
                    float(h["memory_gb"]) if "memory_gb" in h else float(h.get("h100e", 0.0)) * A.H100E_MEMORY_GB)
             for h in d["hosts"]]
    out = A.covered_clusters(hosts, [tuple(x) for x in d.get("links", [])], d.get("together", []))
    _print(out)
    return 0


def cmd_asi_off(a) -> int:
    from .. import dcbus
    from . import asi_agreement as A
    t, p = dcbus.load_csv(a.csv)
    r = A.powered_off(t, p, a.off_w, a.max_gap_s)
    _print(r)
    return 0 if r["verified_off"] else 1


def cmd_asi_crosssite(a) -> int:
    from . import asi_agreement as A
    _print(A.cross_site_training_gbps(a.h100e_per_site, a.sites, a.utilization, a.tokens_per_step, a.sync_every,
                                      a.bytes_per_value, a.compression, a.cap_gbps))
    return 0


# ---- FLI's Draft Articles ----------------------------------------------------------------------------------------
def cmd_chip_auth(a) -> int:
    from . import chipauth as CA
    r = CA.simulate(a.mode, a.period_min * 60, a.allowance_min * 60, a.duty, a.days, hoard=not a.no_hoard,
                    cap_s=None if a.cap_min is None else a.cap_min * 60, ids=a.ids)
    _print(r)
    print(f"after {a.days:g} days, renewal stops; the chip can still compute at full speed for "
          f"{r['run_on_s'] / 3600:,.2f} hours ({r['run_on_days']:,.2f} days)", file=sys.stderr)
    return 0


def cmd_obligations(a) -> int:
    from . import obligations as O
    d = _read(a.events)
    events, subjects = (d, []) if isinstance(d, list) else (d["events"], d.get("subjects", []))
    rows = O.check(events, a.now or time.time(), subjects, a.source)
    for r in rows:
        print(f"{r['status']:8} {r['ref']:22} {r['subject'] or '-':16} due {r['deadline']}  {r['what']}"
              + (f"  ({r['note']})" if r["note"] else ""))
    bad = O.failures(rows)
    print(f"\n{len(rows)} deadlines, {len(bad)} missed or overdue")
    return 1 if bad else 0


def cmd_fli_weighted(a) -> int:
    from . import fli_articles as F
    w = F.gdp_stand_in([x for x in a.members.split(",") if x] or None)
    total = sum(w.values())
    few = F.fewest_to_decide(w)
    power = F.weighted_power(w, a.permutations, a.seed)
    _print({"stand_in": "contributions in proportion to GDP (World Bank 2023, current US$)", "parties": len(w),
            "fewest_deciding_weighted_matters": [{"state": s, "share": w[s] / total} for s in few],
            "their_share": sum(w[s] for s in few) / total,
            "states_needed_for_one_vote_matters": len(w) // 2 + 1,
            "shapley_shubik_top": [{"state": k, "index": v[0], "se": v[1]}
                                   for k, v in sorted(power.items(), key=lambda kv: -kv[1][0])[:a.show]]})
    return 0


def cmd_agreements_coverage(a) -> int:
    from . import coverage as V
    errs = V.validate()
    print(json.dumps(V.summary()))
    if a.write:
        Path(a.write).parent.mkdir(parents=True, exist_ok=True)
        Path(a.write).write_text(V.to_markdown(), encoding="utf-8")
    for e in errs:
        print("ERROR", e, file=sys.stderr)
    return 1 if errs else 0


def add_parser(sp) -> None:
    t = sp.add_parser("treaty", help="mechanisms from the halt and treaty proposals (docs/TREATY_COVERAGE.md)")
    ts = t.add_subparsers(dest="treaty_cmd", required=True)
    s = ts.add_parser("thresholds"); s.set_defaults(f=cmd_thresholds)
    s = ts.add_parser("covert-days", help="days to a threshold-sized covert run at the hidden rate verification allows")
    s.add_argument("--threshold", default="1e25", help="FLOP, or a name from `closure treaty thresholds` "
                   "(np-training-licence, miri-monitored, miri-strict, ...)")
    s.add_argument("--fleet", type=float, default=100_000)
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
    s.add_argument("--public-value", default=None, help="hex of a public value that did not exist when the reveals "
                   "were due (a block hash, a randomness-service round fixed in advance); mixed into the seed")
    s.add_argument("--allow-missing", action="store_true", help="go ahead without a withheld reveal and name the "
                   "party; only with --public-value")
    s.set_defaults(f=cmd_beacon_seed)
    s = ts.add_parser("clause", help="what a panel's signed finding switches on (suspended enforcement clauses)")
    s.add_argument("--finding", required=True); s.add_argument("--approvals", required=True)
    s.add_argument("--members", required=True); s.add_argument("--k", type=int, required=True)
    s.add_argument("--now", type=float, default=None, help="Unix time to judge expiry at (default: now)")
    s.set_defaults(f=cmd_clause)
    s = ts.add_parser("bandwidth", help="what a cap on the link between pods does to training and to serving")
    s.add_argument("--cap-gbps", type=float, required=True); s.add_argument("--params", type=float, required=True)
    s.add_argument("--steps-per-s", type=float, default=1.0); s.add_argument("--pods", type=int, default=2)
    s.add_argument("--tokens-per-s", type=float, default=1e5); s.add_argument("--sync-every", type=int, default=1)
    s.add_argument("--bytes-per-value", type=float, default=2.0); s.add_argument("--compression", type=float, default=1.0)
    s.add_argument("--bytes-per-token", type=float, default=16.0); s.set_defaults(f=cmd_bandwidth)
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
    s.add_argument("--no-bloc", action="store_true"); s.add_argument("--max-size", type=int, default=7)
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
    s = ts.add_parser("asi-tables", help="MIRI's draft agreement: Tables 1 and 2 (time to the thresholds, staged "
                      "registration) recomputed and compared with the printed cells")
    s.add_argument("--flop-s", type=float, default=990e12, help="FLOP/s per H100e (the definition says 989e12)")
    s.add_argument("--boundaries", choices=["table", "text"], default="table"); s.set_defaults(f=cmd_asi_tables)
    s = ts.add_parser("asi-run", help="MIRI's draft agreement: is a training run banned, monitored or free (Art. IV)?")
    s.add_argument("--pretraining", type=float, required=True); s.add_argument("--post-training", type=float, default=0.0)
    s.add_argument("--separate", action="store_true", help="do not count post-training toward the Strict Threshold")
    s.set_defaults(f=cmd_asi_run)
    s = ts.add_parser("asi-cluster", help="MIRI's draft agreement: which hosts form covered chip clusters (Art. II s.16)")
    s.add_argument("--hosts", required=True, help='JSON: {"hosts": [{"id", "site", "h100e" or "tpp" and "memory_gb"}], '
                   '"links": [[id, id, gbit/s]], "together": [[ids running one workload]]}')
    s.set_defaults(f=cmd_asi_cluster)
    s = ts.add_parser("asi-off", help="MIRI's draft agreement, Art. VII s.3: was the hardware off all the time an "
                      "independent meter's trace covers?")
    s.add_argument("--csv", required=True, help="timestamp_s,power_w (meter-log, dcbus-import or dcbus-decimate)")
    s.add_argument("--off-w", type=float, required=True, help="the most an idle, powered-off rig may draw")
    s.add_argument("--max-gap-s", type=float, default=5.0, help="the longest stretch without a reading")
    s.set_defaults(f=cmd_asi_off)
    s = ts.add_parser("asi-crosssite", help="bandwidth that training across sub-CCC sets needs, against 25 Gbit/s")
    s.add_argument("--h100e-per-site", type=float, default=16.0); s.add_argument("--sites", type=int, default=2)
    s.add_argument("--utilization", type=float, default=0.4); s.add_argument("--tokens-per-step", type=float, default=4e6)
    s.add_argument("--sync-every", type=int, default=1); s.add_argument("--bytes-per-value", type=float, default=2.0)
    s.add_argument("--compression", type=float, default=1.0); s.add_argument("--cap-gbps", type=float, default=25.0)
    s.set_defaults(f=cmd_asi_crosssite)
    s = ts.add_parser("chip-auth", help="FLI Annex C chip authorization: how long a chip runs on after renewal stops")
    s.add_argument("--mode", choices=["as-written", "fresh"], default="as-written")
    s.add_argument("--period-min", type=float, default=5.0, help="minutes between renewals")
    s.add_argument("--allowance-min", type=float, default=10.0, help="full-speed minutes each authorization allows")
    s.add_argument("--duty", type=float, default=1.0, help="share of full speed the chip uses")
    s.add_argument("--days", type=float, default=30.0, help="days of operation before renewal stops")
    s.add_argument("--no-hoard", action="store_true", help="the provider hands every authorization over at once")
    s.add_argument("--cap-min", type=float, default=None, help="most allowance the chip holds, in minutes")
    s.add_argument("--ids", choices=["set", "increasing"], default="set"); s.set_defaults(f=cmd_chip_auth)
    s = ts.add_parser("obligations", help="deadlines of both draft agreements against a log of dated events")
    s.add_argument("--events", required=True, help='JSON list of {"type", "at", "subject"}, or {"events": [...], '
                   '"subjects": [Parties]}')
    s.add_argument("--now", default=None, help="ISO time or Unix seconds to judge at (default: now)")
    s.add_argument("--source", choices=["MA", "FLI"], default=None); s.set_defaults(f=cmd_obligations)
    s = ts.add_parser("fli-weighted", help="FLI Art. 12(7): who decides contribution-weighted matters (GDP stand-in)")
    s.add_argument("--members", default="", help="ISO3 codes of the States Parties (default: every economy)")
    s.add_argument("--permutations", type=int, default=20000); s.add_argument("--seed", type=int, default=0)
    s.add_argument("--show", type=int, default=8); s.set_defaults(f=cmd_fli_weighted)
    s = ts.add_parser("coverage", help="every article of MIRI's draft agreement and FLI's Draft Articles, mapped")
    s.add_argument("--write", default=None); s.set_defaults(f=cmd_agreements_coverage)
    s = ts.add_parser("mock-job"); s.add_argument("--out", required=True); s.add_argument("--dim", type=int, required=True)
    s.add_argument("--layers", type=int, required=True); s.add_argument("--batch", type=int, required=True)
    s.add_argument("--seed", type=int, required=True); s.add_argument("--device", default="cpu")
    s.add_argument("--max-steps", type=int, required=True); s.add_argument("--not-from-scratch", action="store_true")
    s.set_defaults(f=cmd_mock_job)
