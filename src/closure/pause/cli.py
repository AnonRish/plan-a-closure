"""`closure pause ...`: command-line access to the hardwired-pause layer."""
from __future__ import annotations

import json
from pathlib import Path

from ..evidence import clean


def _print(obj) -> None:
    print(json.dumps(clean(obj), indent=2))


def _claims(a) -> int:
    from . import paper_claims
    cs = paper_claims.check_all()
    for c in cs:
        if a.all or c.status != "OK":
            print(f"{c.status:12} {c.id:20} expected={c.expected:<12.5g} computed={c.computed:<12.5g} {c.claim}"
                  + (f"  [{c.note}]" if c.note else ""))
    s = paper_claims.summary(cs)
    print(f"\n{s['total']} numbers from the hardwired-pause paper re-derived: {s['OK']} OK, {s['WORDING']} WORDING "
          f"(true only under a stated reading), {s['INCONSISTENT']} INCONSISTENT")
    return 1 if (s["INCONSISTENT"] or (a.strict and s["WORDING"])) else 0


def _coverage(a) -> int:
    from . import coverage
    errs = coverage.validate()
    print(json.dumps(coverage.summary()))
    if a.write:
        Path(a.write).parent.mkdir(parents=True, exist_ok=True)
        Path(a.write).write_text(coverage.to_markdown(), encoding="utf-8")
        print(f"wrote {a.write}")
    for e in errs:
        print("ERROR", e)
    return 1 if errs else 0


def _thresholds(a) -> int:
    from . import thresholds as T
    p = T.ThresholdParams(c_f=a.c_f, c_b=a.c_b, beta_e=a.beta_e, t_e=a.t_e, t_b=a.t_b)
    out = {"thresholds": T.treaty_thresholds(p), "printed_in_paper": T.TABLE_3_1_PRINTED,
           "breakout_sensitivity": T.breakout_sensitivity(p), "later_pause": {str(d): T.pause_delay(p, d) for d in (0.5, 1.0, 2.0)},
           "months_per_blind_step": T.months_per_blind_step(p)}
    _print(out)
    return 0


def _coalition(a) -> int:
    from . import supply_chain as S
    members = [m.strip() for m in a.members.split(",") if m.strip()] if a.members else list(S.PARTICIPANTS_3_1)
    open_stages = S.uncovered(members)
    _print({"members": members, "open_stages": open_stages, "critical_members": S.critical_members(members),
            "census_gaps": S.census_gaps(members), "source": "paper sections 3.1, 3.3.2 and 5.2"})
    return 1 if open_stages else 0


def _ledger(a) -> int:
    from . import treaty_ledger as TL
    L = TL.section_6_4(a.state, a.scenario, phi=a.phi, stock=a.stock)
    gain = a.annual_gain
    out = {"state": a.state, "scenario": a.scenario, "F_E": L.f_e, "F_B": L.f_b, "lines": L.lines(),
           "headroom_with_transitional": L.headroom(False), "headroom_after_transition": L.headroom(True),
           "years_of_durability_after_transition": L.years_of_durability(gain, True), "annual_gain": gain}
    _print(out)
    return 0


def _census(a) -> int:
    from . import census
    _print({"table_5_1": census.table_5_1(),
            "dark_compute": {sc: {st: census.dark_compute(sum(h.total_missing for h in census.TABLE_5_1[st]), st, sc)
                                  for st in census.TABLE_5_1} for sc in census.DARK_SCENARIOS}})
    return 0


def _diversion(a) -> int:
    from . import fab
    n = int(a.samples_per_year * a.months / 12)
    _print({"samples": n, "p_detect": fab.p_detect(n, a.diversion, a.p_recognize),
            "samples_needed": fab.samples_needed(a.diversion, a.p_recognize, a.confidence),
            "months_to_detect": fab.months_to_detect(a.samples_per_year, a.diversion, a.p_recognize, a.confidence),
            "min_detectable_diversion": fab.min_detectable_diversion(max(n, 1), a.p_recognize, a.confidence)})
    return 0


def _transition(a) -> int:
    from . import transition as X
    p1 = X.phase1_months(*a.phase1)
    p2 = X.phase2_months(a.stock, a.monthly)
    _print({"phase1_months": p1, "phase2_months": p2, "total_years": X.transition_years(p1, p2),
            "reallocation_gain": X.reallocation_gain(a.training_share),
            "demand_catches_up_years": X.demand_catches_up_years(X.reallocation_gain(a.training_share)),
            "table_4_1_months": sorted(m for _, m, _ in X.TABLE_4_1)})
    return 0


def _msic(a) -> int:
    from . import msic_econ as M
    demand = M.load_demand(a.demand, a.model_col, a.token_col) if a.demand else M.zipf_demand(a.models, a.zipf)
    out = {"source": a.demand or f"synthetic Zipf({a.zipf}) over {a.models} models",
           "panel": M.panel(demand, a.savings, a.b, a.nre),
           "unserved_share_bound_pure_msic_world": M.unserved_share_bound(demand, a.savings, a.b, a.nre)}
    _print(out)
    return 0


def _gemm(a) -> int:
    from . import gemm_audit as G
    if a.design:
        d = G.design_from_dict(json.loads(Path(a.design).read_text(encoding="utf-8")))
    else:
        d = G.example_attention_block(open_links=not a.sealed, authenticated_links=a.authenticated)
    r = G.audit(d)
    _print({"design": d.name, "passes_licensing_criterion": r.passes_licensing_criterion,
            "exposed_fraction": r.exposed_fraction, "exposed_or_obstructed_fraction": r.exposed_or_obstructed_fraction,
            "matmuls": r.matmuls, "findings": r.findings(),
            "note": "design-time screen only: the paper requires a physical audit of the realised system"})
    return 0 if r.passes_licensing_criterion else 1


def _bridge(a) -> int:
    from . import bridge
    res = json.loads((Path(a.results) / "results.json").read_text(encoding="utf-8")) if Path(a.results).is_dir() \
        else json.loads(Path(a.results).read_text(encoding="utf-8"))
    d = bridge.closure_discount(res)
    src = bridge.transitional_source(a.fleet, res, a.coverage, a.pi_unaudited)
    _print({"closure_discount": d, "ledger_line": {"name": src.name, "k0": src.k0, "pi_e": src.pi_e, "tau_e": src.tau_e,
                                                  "k_e": src.k_e, "note": src.note},
            "paper_assumption_pi_e": 0.001})
    return 0


def _game(a) -> int:
    from . import pausegame as G
    _print(G.monitoring_supports_pause((a.T, a.R, a.P, a.S), a.delta, a.detect, a.false_alarm))
    return 0


def register(sp) -> None:
    pp = sp.add_parser("pause", help="hardwired-pause layer (thresholds, ledgers, census, fab balance, ...)")
    ps = pp.add_subparsers(dest="pcmd", required=True)
    s = ps.add_parser("claims"); s.add_argument("--all", action="store_true"); s.add_argument("--strict", action="store_true"); s.set_defaults(f=_claims)
    s = ps.add_parser("coverage"); s.add_argument("--write", default=None); s.set_defaults(f=_coverage)
    s = ps.add_parser("thresholds"); s.add_argument("--c-f", type=float, default=2e27); s.add_argument("--c-b", type=float, default=2e29)
    s.add_argument("--beta-e", type=float, default=10.0); s.add_argument("--t-e", type=float, default=5.0)
    s.add_argument("--t-b", type=float, default=2.0); s.set_defaults(f=_thresholds)
    s = ps.add_parser("ledger"); s.add_argument("--state", choices=["United States", "China"], default="United States")
    s.add_argument("--scenario", choices=["high", "low", "non_deniable"], default="high"); s.add_argument("--phi", type=float, default=1e-4)
    s.add_argument("--annual-gain", type=float, default=1.57)
    s.add_argument("--stock", type=float, default=None, help="installed H100e in the state (Table 6.1 range: US 26M-44M, China 2.6M-4.5M)")
    s.set_defaults(f=_ledger)
    s = ps.add_parser("coalition"); s.add_argument("--members", default=None, help="comma-separated jurisdictions (default: paper section 3.1)")
    s.set_defaults(f=_coalition)
    s = ps.add_parser("census"); s.set_defaults(f=_census)
    s = ps.add_parser("diversion"); s.add_argument("--samples-per-year", type=float, default=2400); s.add_argument("--months", type=float, default=6)
    s.add_argument("--diversion", type=float, default=0.01); s.add_argument("--p-recognize", type=float, default=0.25)
    s.add_argument("--confidence", type=float, default=0.95); s.set_defaults(f=_diversion)
    s = ps.add_parser("transition"); s.add_argument("--stock", type=float, default=47e6); s.add_argument("--monthly", type=float, default=2.9e6)
    s.add_argument("--phase1", type=float, nargs=3, default=[13, 6, 7]); s.add_argument("--training-share", type=float, default=0.62)
    s.set_defaults(f=_transition)
    s = ps.add_parser("msic"); s.add_argument("--demand", default=None, help="CSV of per-model token counts")
    s.add_argument("--model-col", default="model"); s.add_argument("--token-col", default="tokens")
    s.add_argument("--models", type=int, default=315); s.add_argument("--zipf", type=float, default=1.1)
    s.add_argument("--savings", type=float, default=0.85); s.add_argument("--b", type=float, default=500e9)
    s.add_argument("--nre", type=float, default=50e6); s.set_defaults(f=_msic)
    s = ps.add_parser("gemm-audit"); s.add_argument("--design", default=None, help="JSON dataflow graph")
    s.add_argument("--sealed", action="store_true"); s.add_argument("--authenticated", action="store_true"); s.set_defaults(f=_gemm)
    s = ps.add_parser("bridge"); s.add_argument("results", help="closure run directory or results.json")
    s.add_argument("--fleet", type=float, default=35.2e6); s.add_argument("--coverage", type=float, default=0.5)
    s.add_argument("--pi-unaudited", type=float, default=0.001); s.set_defaults(f=_bridge)
    s = ps.add_parser("game"); s.add_argument("--T", type=float, default=5.0); s.add_argument("--R", type=float, default=3.0)
    s.add_argument("--P", type=float, default=1.0); s.add_argument("--S", type=float, default=0.0)
    s.add_argument("--delta", type=float, default=0.8); s.add_argument("--detect", type=float, default=0.5)
    s.add_argument("--false-alarm", type=float, default=0.0); s.set_defaults(f=_game)
