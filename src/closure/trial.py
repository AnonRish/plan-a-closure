"""Pre-registered builder-vs-breaker trial: calibrate -> preregister -> blind audit -> analyse.

The same orchestrator drives the simulator (tests, rehearsal) and real hardware (hw/)."""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from . import residual as R
from .conformal import cp_lower, cp_upper
from .energy import EnergyFloor, block_capacity_j, h100_hours, hidden_flop_bound
from .evidence import Chain, Signer, array_digest, canonical, clean, commit, sha256_hex, verify_commit
from .sim import FEATURES, HiddenSpec

MIN_N_EFF = 15.0  # below this many effective independent calibration blocks per regime, flag UNDERPOWERED
ANALYSES = {"linear": "closure.trial.analyze (alpha/2 Bonferroni for combined)",
            "link": "closure.trial.analyze_link (link.py: calibrated curves, studentised scores, one conformal "
                    "threshold on the larger channel score at alpha)"}

ASSUMPTIONS = [
    "A1 additivity: hidden work adds energy/busy-time on top of verified work (no free lunch from sharing).",
    "A2 exchangeability: calibration and audit blocks come from the same regime mix (same stack, clocks, cooling, firmware).",
    "A3 approximate normality of block residual sums, checked by the Jarque-Bera diagnostic stored with the calibration.",
    "A4 no efficiency slack: the adversary is no more energy-efficient than the calibration reference (the 'slack' class tests this and is expected to evade).",
    "A5 the verified-work features are trustworthy (they come from the tap/recompute evidence, not from the prover).",
    "A6 the power meter is independent of the prover (DC-bus instrument); NVML-only runs are labelled as spoofable.",
]


@dataclass
class TrialConfig:
    status: str = "SIMULATED"
    dt: float = 1.0
    L: int = 300
    n_ref_blocks: int = 600
    n_audit_blocks: int = 1200
    alpha: float = 1e-3
    beta: float = 0.05
    n_regimes: int = 3
    intensities: tuple = (0.005, 0.01, 0.02, 0.05, 0.10, 0.20)
    classes: tuple = ("constant", "idle_gap", "duty", "dilute", "slack")
    p_hidden: float = 0.5
    seed: int = 1
    n_gpu: int = 8
    p_max_w: float = 700.0
    e_floor_j_per_flop: float = 0.5e-12
    e_floor_source: str = "unmeasured-default"
    slack_s_max: float | None = None          # measured by `closure hw-probe` (pre-registered H1.6)
    slack_source: str = "not measured"
    probe_sha256: str | None = None           # seal of the probe.json bound into this pre-registration
    workload: dict | None = None              # hardware runs: the unit of verified work and the measured idle power
    # Design (amendment v0.5). "random": each audit block carries hidden load with probability p_hidden. "balanced":
    # exactly n_per_cell audit blocks for every class x intensity and the rest null, in random order, so no cell is
    # left too small to decide by chance.
    schedule: str = "random"
    n_per_cell: int | None = None
    # "sequential": all reference blocks, then the audit (calibration is fixed before the schedule is committed).
    # "interleaved": reference blocks at committed random positions, one in each of n_ref_blocks equal stretches of
    # the run, and the model is fitted on them once the data are in; slow drift then reaches calibration and audit
    # blocks alike (assumption A2 by design), at the cost of a wider null distribution.
    calibration: str = "sequential"
    warmup_blocks: int = 0                    # run first and kept in raw.npz, never analysed: the GPU warms up
    # "linear": each channel a straight line in the verified work, thresholds Gaussian unless many blocks, the two
    # channels combined at alpha/2 each (the analysis until amendment v0.6; kept so earlier runs reproduce).
    # "link": a calibrated monotone curve per channel, studentised scores and one conformal threshold (link.py).
    analysis: str = "linear"
    campaign: dict | None = None              # {"id", "index", "size"}: one of several trials declared together


def _src_sha256() -> str:
    """Hash of the package source as it is being run, so a pre-registration pins the code even without git."""
    import hashlib
    root = Path(__file__).resolve().parent
    h = hashlib.sha256()
    for p in sorted(root.rglob("*.py")):
        h.update(str(p.relative_to(root)).replace("\\", "/").encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


def _code_version() -> dict:
    import subprocess
    from . import __version__
    try:
        g = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5,
                           cwd=Path(__file__).resolve().parent).stdout.strip() or None
    except Exception:
        g = None
    return {"package": __version__, "git_commit": g, "src_sha256": _src_sha256()}


def make_schedule(cfg: TrialConfig, rng) -> list:
    if cfg.schedule == "balanced":
        cells = [(c, float(f)) for c in cfg.classes for f in cfg.intensities]
        per = (cfg.n_per_cell if cfg.n_per_cell is not None
               else int(round(cfg.p_hidden * cfg.n_audit_blocks)) // len(cells))
        if per * len(cells) > cfg.n_audit_blocks:
            raise ValueError(f"{per} blocks for each of {len(cells)} cells need more than {cfg.n_audit_blocks} audit blocks")
        out = [{"kind": c, "frac": f} for c, f in cells for _ in range(per)]
        out += [None] * (cfg.n_audit_blocks - len(out))
        return [out[i] for i in rng.permutation(len(out))]
    if cfg.schedule != "random":
        raise ValueError(f"unknown schedule '{cfg.schedule}' (random or balanced)")
    out = []
    for _ in range(cfg.n_audit_blocks):
        if rng.random() < cfg.p_hidden:
            out.append({"kind": str(rng.choice(cfg.classes)), "frac": float(rng.choice(cfg.intensities))})
        else:
            out.append(None)
    return out


def make_order(cfg: TrialConfig, rng) -> list:
    """Interleaved calibration: 1 marks a reference block, 0 an audit block. The run is cut into n_ref_blocks stretches
    of (nearly) equal length with one reference block at a random position in each, so calibration covers the whole run
    evenly. Committed with the schedule before any data exist, so the analysis cannot pick its reference blocks later."""
    n_r, n = cfg.n_ref_blocks, cfg.n_ref_blocks + cfg.n_audit_blocks
    cuts = [(j * n) // n_r for j in range(n_r + 1)]
    order = [0] * n
    for j in range(n_r):
        order[cuts[j] + int(rng.integers(cuts[j + 1] - cuts[j]))] = 1
    return order


_KEYS = ("X", "E", "B", "t0", "hid")
# Ground truth a source may report with each block: the load level it was asked for, and the seconds its hidden load
# actually ran. Kept in raw.npz to check the bounds against; never a regressor and never in the evidence digest.
_TRUTH = (("lev", "level"), ("hs", "hidden_s"))


def _new_parts() -> dict:
    return {k: [] for k in _KEYS + tuple(k for k, _ in _TRUTH)}


def _add(parts: dict, b: dict) -> None:
    parts["X"].append(b["X"]); parts["E"].append(b["E"]); parts["B"].append(b["busy"])
    parts["t0"].append(b["t0"]); parts["hid"].append(b["hidden_j"])
    for k, src in _TRUTH:
        if src in b and k in parts:
            parts[k].append(np.asarray(b[src], float))


def _stack(parts: dict) -> dict:
    n = len(parts["E"])
    return {k: np.concatenate(v) for k, v in parts.items() if len(v) == n}


def collect(source, cfg: TrialConfig, n_blocks: int, schedule=None, parts=None) -> dict:
    """n_blocks blocks; `parts` (lists per field) keeps the finished blocks if the run is interrupted."""
    parts = _new_parts() if parts is None else parts
    for i in range(n_blocks):
        spec = HiddenSpec.from_dict(schedule[i]) if schedule is not None else None
        _add(parts, source.run_block(cfg.L, spec))
    return _stack(parts)


def collect_interleaved(source, cfg: TrialConfig, order: list, schedule: list, ref=None, aud=None):
    """Reference and audit blocks in the committed order; returns (reference, audit), each in time order."""
    ref = _new_parts() if ref is None else ref
    aud = _new_parts() if aud is None else aud
    j = 0
    for is_ref in order:
        if is_ref:
            _add(ref, source.run_block(cfg.L, None))
        else:
            _add(aud, source.run_block(cfg.L, HiddenSpec.from_dict(schedule[j])))
            j += 1
    return _stack(ref), _stack(aud)


def fit_channels(ref: dict, cfg: TrialConfig):
    """The straight-line calibration (the registered analysis until amendment v0.6)."""
    kw = dict(L=cfg.L, n_regimes=cfg.n_regimes, seed=cfg.seed, names=FEATURES)
    return (R.fit(ref["X"], ref["E"], channel="energy_j", unit="J", **kw),
            R.fit(ref["X"], ref["B"], channel="busy_s", unit="s", **kw))


def fit_link(ref: dict, cfg: TrialConfig):
    """The link calibration (amendment v0.6; link.py)."""
    from . import link
    return link.calibrate(ref["X"], {"energy": ref["E"], "busy": ref["B"]}, cfg.L, seed=cfg.seed,
                          exchangeable_by_design=cfg.calibration == "interleaved")


def calibrate(ref: dict, cfg: TrialConfig):
    """The calibration cfg.analysis calls for: (energy, busy) straight-line calibrations, or a link calibration."""
    if cfg.analysis == "link":
        return fit_link(ref, cfg)
    if cfg.analysis != "linear":
        raise ValueError(f"unknown analysis '{cfg.analysis}' (linear or link)")
    return fit_channels(ref, cfg)


def calibration_record(cal) -> dict:
    return {"energy": cal[0].to_dict(), "busy": cal[1].to_dict()} if isinstance(cal, tuple) else cal.to_dict()


def _pooled_f95(hf, det, min_n=8):
    """Smallest hidden-energy fraction (upper edge of a log-spaced bin) from which every populated
    bin is detected >=95% of the time. Binned, so easy large cases cannot inflate small ones."""
    edges = np.logspace(-4, -0.5, 15)
    idx = np.digitize(hf, edges)
    rows = []
    for b in range(1, len(edges)):
        m = idx == b
        n = int(m.sum())
        rows.append((float(edges[b]), (float(det[m].mean()) if n else None), n))
    for i, (up, r, n) in enumerate(rows):
        if r is None or n < min_n:
            continue
        tail = [x for x in rows[i:] if x[2] >= min_n]
        if all(x[1] >= 0.95 for x in tail):
            return up
    return None


def _score_linear(cfg: TrialConfig, calE, calB, aud: dict) -> dict:
    a, a2 = cfg.alpha, cfg.alpha / 2
    rE, rB = R.audit(calE, aud["X"], aud["E"], a), R.audit(calB, aud["X"], aud["B"], a)
    rE2, rB2 = R.audit(calE, aud["X"], aud["E"], a2), R.audit(calB, aud["X"], aud["B"], a2)
    # energy against the block's capacity energy, busy time against the block's length: busy time is the mean
    # utilisation over the GPUs times the seconds, so a block cannot hold more than L x dt of it. Until 0.7.0 both were
    # divided by the energy, which understated the busy figure by a factor of p_max (docs/DEVIATIONS.md section 3);
    # 0.7.0 divided by n_gpu x L x dt, right only for one GPU.
    cap, cap_s = block_capacity_j(cfg.n_gpu, cfg.p_max_w, cfg.L, cfg.dt), cfg.L * cfg.dt
    return {"analysis": "linear",
            "flag": {"energy": rE.flagged, "busy": rB.flagged, "combined": rE2.flagged | rB2.flagged},
            "ub_energy": rE.hidden_ub, "ub_busy": rB.hidden_ub, "pred_energy": rE.pred,
            "md": {"energy": [R.min_detectable(calE, r, a, cfg.beta) / cap for r in range(calE.n_regimes)],
                   "busy": [R.min_detectable(calB, r, a, cfg.beta) / cap_s for r in range(calB.n_regimes)]},
            "normality_p": {"energy": calE.normal_p.tolist(), "busy": calB.normal_p.tolist()},
            "n_eff": {"energy": calE.n_eff.tolist(), "busy": calB.n_eff.tolist(),
                      "rho_energy": calE.rho, "rho_busy": calB.rho,
                      "underpowered": bool(min(calE.n_eff.min(), calB.n_eff.min()) < MIN_N_EFF)},
            # "combined" is each channel at alpha/2; until 0.8.0 only the single-channel methods were reported, which
            # hid a Gaussian fallback behind "conformal" (docs/DEVIATIONS.md section 5)
            "methods": {"energy": rE.method, "busy": rB.method, "combined": sorted(set(rE2.method + rB2.method))},
            "extra": {}}


def _score_link(cfg: TrialConfig, cal, aud: dict) -> dict:
    from . import link
    a = link.audit(cal, aud["X"], {"energy": aud["E"], "busy": aud["B"]}, cfg.alpha)
    cap, cap_s = block_capacity_j(cfg.n_gpu, cfg.p_max_w, cfg.L, cfg.dt), cfg.L * cfg.dt
    return {"analysis": "link", "flag": a["flag"], "ub_energy": a["ub"]["energy"], "ub_busy": a["ub"]["busy"],
            "ub_floor": a["ub_floor"], "pred_energy": a["pred_energy"],
            "md": {"energy": [link.min_detectable(cal, "energy", cfg.alpha, cfg.beta) / cap],
                   "busy": [link.min_detectable(cal, "busy", cfg.alpha, cfg.beta) / cap_s]},
            "normality_p": {"energy": [cal.energy.normal_p], "busy": [cal.busy.normal_p]},
            "n_eff": {"energy": [cal.n_eff], "busy": [cal.n_eff], "rho_energy": cal.energy.rho, "rho_busy": cal.busy.rho,
                      "underpowered": bool(cal.n_eff < MIN_N_EFF)},
            "methods": {k: [v] for k, v in a["method"].items()},
            "extra": {"link": {"reference_blocks": int(len(cal.score)), "n_eff": cal.n_eff,
                               "exchangeable_by_design": cal.exchangeable_by_design,
                               "thresholds": {k: float(v) for k, v in a["threshold"].items()},
                               "block_residual_sd": {c.name: float(np.std(c.S, ddof=1)) for c in cal.channels},
                               "partial_load_slack": cal.energy.curve.partial_load_slack()}}}


def block_table(cfg: TrialConfig, sc: dict, aud: dict, schedule: list) -> dict:
    """One row per audit block: what was scheduled, what the analysis said, and the ground truth the source reported."""
    L = cfg.L
    B = len(aud["E"]) // L
    hid = aud["hid"][: B * L].reshape(B, L).sum(1)
    t = {"kind": [("none" if s is None else s["kind"]) for s in schedule[:B]],
         "frac": [(0.0 if s is None else float(s["frac"])) for s in schedule[:B]],
         "hidden_j": hid, "hidden_fraction": hid / block_capacity_j(cfg.n_gpu, cfg.p_max_w, L, cfg.dt),
         "flag_energy": sc["flag"]["energy"], "flag_busy": sc["flag"]["busy"], "flag_combined": sc["flag"]["combined"],
         "ub_energy_j": sc["ub_energy"], "ub_busy_s": sc["ub_busy"], "pred_energy_j": sc["pred_energy"]}
    if "ub_floor" in sc:
        t["ub_energy_floor_j"], t["ub_busy_floor_s"] = sc["ub_floor"]["energy"], sc["ub_floor"]["busy"]
    if "hs" in aud:
        t["hidden_busy_s"] = aud["hs"][: B * L].reshape(B, L).sum(1)
    return {k: (v.tolist() if isinstance(v, np.ndarray) else list(v)) for k, v in t.items()}


def summarise(cfg: TrialConfig, table: dict, floor: EnergyFloor) -> dict:
    """Rates, f95, the closure gap and bound coverage from a block table (one trial's, or several pooled)."""
    kinds, fracs = np.array(table["kind"]), np.array(table["frac"], float)
    hid, hf = np.array(table["hidden_j"], float), np.array(table["hidden_fraction"], float)
    flag = {ch: np.array(table[f"flag_{ch}"], bool) for ch in ("energy", "busy", "combined")}
    B = len(kinds)
    cap = block_capacity_j(cfg.n_gpu, cfg.p_max_w, cfg.L, cfg.dt)
    null = kinds == "none"
    n_null = int(null.sum())
    fpr = {ch: {"k": int(f[null].sum()), "n": n_null, "rate": float(f[null].mean()) if n_null else None,
                "cp95_upper": cp_upper(int(f[null].sum()), n_null)} for ch, f in flag.items()}
    idle = (kinds != "none") & (hid <= 0)                 # scheduled, but the hidden load never came on: null in fact
    fpr["scheduled_but_never_active"] = {"k": int(flag["combined"][idle].sum()), "n": int(idle.sum())}
    det, f95 = {}, {}
    for cl in cfg.classes:
        det[cl], rates = {}, []
        for fr in cfg.intensities:
            m = (kinds == cl) & (np.isclose(fracs, fr)) & (hid > 0)
            k, n = int(flag["combined"][m].sum()), int(m.sum())
            det[cl][str(fr)] = {"k": k, "n": n, "rate": (k / n if n else None),
                                "cp95_lower": cp_lower(k, n) if n else None}
            rates.append((fr, k / n if n else None, n))
        f95[cl] = None
        for i, (fr, r, n) in enumerate(rates):
            if all(x[1] is not None and x[1] >= 0.95 and x[2] >= 8 for x in rates[i:]):
                f95[cl] = fr
                break
    ns = (kinds != "none") & (kinds != "slack") & (hid > 0)
    pooled = {ch: _pooled_f95(hf[ns], flag[ch][ns]) for ch in flag}
    # H1.3 as registered: detection among blocks whose hidden fraction is at least 5% (primary) or 2% (stretch), per
    # class and pooled over the non-slack classes; a Clopper-Pearson lower bound >= 95% certifies the rate.
    at_least = {}
    for thr in (0.05, 0.02):
        big = ns & (hf >= thr * (1 - 1e-6))
        row = {}
        for cl in [c for c in cfg.classes if c != "slack"] + ["pooled_nonslack"]:
            m = big if cl == "pooled_nonslack" else big & (kinds == cl)
            k, n = int(flag["combined"][m].sum()), int(m.sum())
            row[cl] = {"k": k, "n": n, "rate": (k / n if n else None), "cp95_lower": cp_lower(k, n) if n else None}
        at_least[str(thr)] = row
    ubE = np.array(table["ub_energy_j"], float)
    cover_ns = (ubE >= hid)[ns]
    sl = (kinds == "slack") & (hid > 0)
    cover_sl = (ubE >= hid)[sl]
    tight = (ubE[ns] / np.maximum(hid[ns], 1e-9))[cover_ns] if ns.any() else np.array([])
    bound = {"coverage_nonslack": float(cover_ns.mean()) if len(cover_ns) else None,
             "coverage_slack_expected_to_fail": float(cover_sl.mean()) if len(cover_sl) else None,
             "median_tightness_ratio": float(np.median(tight)) if len(tight) else None}
    if "ub_energy_floor_j" in table and ns.any():        # energy above the least the verified work can cost
        bound["coverage_floor_bound"] = float((np.array(table["ub_energy_floor_j"], float) >= hid)[ns].mean())
    if "hidden_busy_s" in table and table.get("ub_busy_s") is not None:
        # the time bound against the seconds the hidden load really ran (counted by the load generator itself)
        hs, ubB = np.array(table["hidden_busy_s"], float), np.array(table["ub_busy_s"], float)
        nt = ns & (hs > 0)
        ct = (ubB >= hs)[nt]
        tt = (ubB[nt] / np.maximum(hs[nt], 1e-12))[ct] if nt.any() else np.array([])
        bound["time"] = {"n": int(nt.sum()), "coverage_nonslack": float(ct.mean()) if len(ct) else None,
                         "median_tightness_ratio": float(np.median(tt)) if len(tt) else None}
        if "ub_busy_floor_s" in table:                  # the same check for the bound that does not lean on A1
            cf = (np.array(table["ub_busy_floor_s"], float) >= hs)[nt]
            bound["time"]["coverage_floor_bound"] = float(cf.mean()) if len(cf) else None
    gap = pooled["combined"]
    week_j = (gap if gap is not None else float("nan")) * cfg.n_gpu * cfg.p_max_w * 7 * 86400
    flop = hidden_flop_bound(week_j, floor) if gap is not None else None
    pred_frac = float(np.mean(np.array(table["pred_energy_j"], float)) / cap) if B else None
    s_max = cfg.slack_s_max
    slack = {"s_max": s_max, "source": cfg.slack_source, "mean_predicted_fraction_of_capacity": pred_frac,
             "slack_inflated_gap_fraction": (gap + s_max * pred_frac) if (gap is not None and s_max is not None) else None}
    return {
        "status": cfg.status,
        "n_blocks": {"audit": int(B), "null": n_null, "hidden_nonslack": int(ns.sum()), "hidden_slack": int(sl.sum()),
                     "hidden_zero_energy_skipped": int(idle.sum())},
        "false_positive": fpr,
        "detection_combined": det,
        "detection_at_or_above_fraction": at_least,
        "f95_by_class": f95,
        "f95_pooled_hidden_fraction": pooled,
        "closure_gap_fraction": gap,
        "bound": bound,
        "slack": slack,
        "hidden_compute_at_gap_per_week": {"flop": flop, "h100_hours": (h100_hours(flop) if flop else None),
                                           "energy_floor_j_per_flop": floor.j_per_flop,
                                           "energy_floor_source": floor.source},
    }


def _report(cfg: TrialConfig, sc: dict, aud: dict, schedule: list, floor: EnergyFloor) -> dict:
    table = block_table(cfg, sc, aud, schedule)
    res = summarise(cfg, table, floor)
    res.update({"analysis": sc["analysis"], "min_detectable_fraction_per_regime": sc["md"],
                "normality_p": sc["normality_p"], "calibration_n_eff": sc["n_eff"], "methods_used": sc["methods"],
                "assumptions": ASSUMPTIONS, "blocks": table, **sc["extra"]})
    return res


def analyze(cfg: TrialConfig, calE, calB, aud: dict, schedule: list, floor: EnergyFloor) -> dict:
    """The straight-line analysis: each channel linear in the verified work, combined at alpha/2 each."""
    return _report(cfg, _score_linear(cfg, calE, calB, aud), aud, schedule, floor)


def analyze_link(cfg: TrialConfig, cal, aud: dict, schedule: list, floor: EnergyFloor) -> dict:
    """The link analysis (amendment v0.6): calibrated curves, studentised scores, one conformal threshold."""
    return _report(cfg, _score_link(cfg, cal, aud), aud, schedule, floor)


def analyze_any(cfg: TrialConfig, cal, aud: dict, schedule: list, floor: EnergyFloor) -> dict:
    return analyze(cfg, cal[0], cal[1], aud, schedule, floor) if isinstance(cal, tuple) else \
        analyze_link(cfg, cal, aud, schedule, floor)


def _digest(d: dict) -> dict:
    """The evidence: what the verifier would see. Ground truth (hidden energy, level, hidden seconds) is left out."""
    return {k: array_digest(v) for k, v in d.items() if k in ("X", "E", "B", "t0")}


def _save_partial(out: Path, acc: dict, chain: Chain, err: BaseException, reveal) -> None:
    """A run stopped before its data were complete (a signal such as a time limit's SIGTERM, or an error): keep the
    finished blocks in raw_partial.npz, reveal the committed schedule so they can be read, and say so in the chain.
    They are never analysed, since stopping is not part of the pre-registered design, but they are published."""
    if (out / "raw.npz").exists():
        return
    if reveal and not (out / "schedule_reveal.json").exists():
        (out / "schedule_reveal.json").write_text(json.dumps(reveal))
    full = {name: _stack(d) for name, d in acc.items() if d["E"]}
    if full:
        np.savez_compressed(out / "raw_partial.npz", **{f"{n}_{k}": v for n, d in full.items() for k, v in d.items()})
    chain.append({"phase": "interrupted", "reason": f"{type(err).__name__}: {err}",
                  "blocks": {n: len(d["E"]) for n, d in acc.items()},
                  "digest": {n: _digest(d) for n, d in full.items()}})


def run_trial(source, cfg: TrialConfig, out_dir, signer: Signer = None, schedule=None, floor: EnergyFloor = None,
              pause_hook=None) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    floor = floor or EnergyFloor(cfg.e_floor_j_per_flop, cfg.e_floor_source)
    if cfg.calibration not in ("sequential", "interleaved"):
        raise ValueError(f"unknown calibration '{cfg.calibration}' (sequential or interleaved)")
    interleaved = cfg.calibration == "interleaved"
    chain = Chain(out / "chain.jsonl")
    rng = np.random.default_rng(cfg.seed + 7919)
    acc = {name: _new_parts() for name in ("warm", "ref", "aud")}               # finished blocks, kept if stopped
    state = {"reveal": None}
    try:
        return _run(source, cfg, out, signer, schedule, floor, pause_hook, interleaved, chain, rng, acc, state)
    except BaseException as e:
        try:
            _save_partial(out, acc, chain, e, state["reveal"])
        except Exception:                # keeping the partial data is a courtesy; the original exception is what matters
            pass
        raise


def _run(source, cfg, out, signer, schedule, floor, pause_hook, interleaved, chain, rng, acc, state) -> dict:
    warm = None

    def fit(ref):
        cal = calibrate(ref, cfg)
        chain.append({"phase": "calibration", "cfg": asdict(cfg), "ref_digest": _digest(ref),
                      **calibration_record(cal)})
        return cal

    if not interleaved:                 # calibrate first: the model is fixed before the schedule is committed
        warm = collect(source, cfg, cfg.warmup_blocks, parts=acc["warm"]) if cfg.warmup_blocks else None
        ref = collect(source, cfg, cfg.n_ref_blocks, parts=acc["ref"])
        cal = fit(ref)
    schedule = schedule if schedule is not None else make_schedule(cfg, rng)
    order = make_order(cfg, rng) if interleaved else None
    cm, om = commit(schedule), (commit(order) if interleaved else None)
    reveal = {"schedule": schedule, "nonce": cm["nonce"]}
    if interleaved:
        reveal.update(order=order, order_nonce=om["nonce"])
    state["reveal"] = reveal
    prereg = {"cfg": asdict(cfg), "code": _code_version(), "schedule_commitment": cm["commitment"],
              "assumptions": ASSUMPTIONS, "analysis": ANALYSES[cfg.analysis]}
    if interleaved:                     # nothing has been measured yet; the reference positions are committed too
        prereg["order_commitment"] = om["commitment"]
    else:
        prereg["calibration_head"] = chain.head
    (out / "prereg.json").write_text(json.dumps(clean(prereg), indent=2, sort_keys=True))
    pre_sha = sha256_hex(canonical(prereg))
    chain.append({"phase": "prereg", "prereg_sha256": pre_sha, "schedule_commitment": cm["commitment"],
                  **({"order_commitment": om["commitment"]} if interleaved else {})})
    if pause_hook:                      # lets you externally timestamp prereg.json BEFORE any audit data exist
        pause_hook(out / "prereg.json", pre_sha)
    if interleaved:
        warm = collect(source, cfg, cfg.warmup_blocks, parts=acc["warm"]) if cfg.warmup_blocks else None
        ref, aud = collect_interleaved(source, cfg, order, schedule, ref=acc["ref"], aud=acc["aud"])
        chain.append({"phase": "audit_data", "audit_digest": _digest(aud), "ref_digest": _digest(ref)})
    else:
        aud = collect(source, cfg, cfg.n_audit_blocks, schedule, parts=acc["aud"])
        chain.append({"phase": "audit_data", "audit_digest": _digest(aud)})
    assert verify_commit(schedule, cm["commitment"], cm["nonce"])
    # the data and the reveal are on disk before anything is fitted, so a failed analysis can be rerun from them
    (out / "schedule_reveal.json").write_text(json.dumps(reveal))
    np.savez_compressed(out / "raw.npz", **{f"ref_{k}": v for k, v in ref.items()}, **{f"aud_{k}": v for k, v in aud.items()},
                        **({f"warm_{k}": v for k, v in warm.items()} if warm else {}))
    if interleaved:
        cal = fit(ref)
    res = analyze_any(cfg, cal, aud, schedule, floor)
    (out / "results.json").write_text(json.dumps(clean(res), indent=2, sort_keys=True))
    head = chain.append({"phase": "results", "results_sha256": sha256_hex(canonical(res))})
    if signer:
        (out / "signature.json").write_text(json.dumps(
            {"chain_head": head, "public_key": signer.public_hex(), "signature": signer.sign_hex(head.encode())}))
    from .compose import to_markdown
    (out / "results.md").write_text(to_markdown(res, cfg))
    return res
