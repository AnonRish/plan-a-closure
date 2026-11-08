"""The middle-powers agreement (Amadori, Alfour, Miotti and Behrens, *How middle powers may prevent the development of
artificial superintelligence*, asi-prevention.com) as rules that can be computed and played: when it activates, who
is pivotal, and what each observed redline triggers.

Activation (section 5): the signatories hold at least 20% of world GDP and at least 20% of world population. The paper
does not say which GDP or which year; this uses the World Bank's GDP in current US$ (2023, or the latest earlier year)
and population (2025), bundled with its source in data/world_bank_gdp_population.csv. Taiwan, which the paper names
as the leading producer of cutting-edge logic chips, is not in World Bank data and is left out of the shares.

Redlines (section 6.1) map to the penalty ladder of section 4.2 plus the self-defence right of section 4.3. Thresholds
the paper leaves open (compute holdings, AI R&D compute) are yes/no findings here; judicial redlines are a panel's
findings, entered as such. Persistence: six months in violation past the wide-embargo line escalates to a full
embargo, six months past the full-embargo line to the self-defence right. A leaked or released system triggers the
highest measure that would otherwise apply, one level up.
"""
from __future__ import annotations

import csv
import itertools
from dataclasses import dataclass
from pathlib import Path

import numpy as np

DATA = Path(__file__).resolve().parent / "data" / "world_bank_gdp_population.csv"
EU27 = ("AUT", "BEL", "BGR", "HRV", "CYP", "CZE", "DNK", "EST", "FIN", "FRA", "DEU", "GRC", "HUN", "IRL", "ITA", "LVA",
        "LTU", "LUX", "MLT", "NLD", "POL", "PRT", "ROU", "SVK", "SVN", "ESP", "SWE")
SUPERPOWERS = ("USA", "CHN")
CHOKEPOINTS = {"NLD": "sole producer of EUV lithography machines", "KOR": "major manufacturer of memory chips",
               "TWN": "leading producer of cutting-edge logic chips (not in World Bank data)"}   # as the paper names them
GDP_QUOTA = POP_QUOTA = 0.20

LEVELS = ("none", "strengthened AI export controls", "widened export controls", "sanctions and tariffs",
          "wide embargo", "full embargo", "self-defence right")
WIDE, FULL, SELF_DEFENCE = 4, 5, 6


@dataclass(frozen=True)
class Country:
    iso3: str
    name: str
    gdp_usd: float
    gdp_year: int
    population: int


def load(path=DATA) -> tuple:
    """({iso3: Country}, world): countries and the World Bank world totals."""
    rows = [ln for ln in Path(path).read_text(encoding="utf-8").splitlines() if ln and not ln.startswith("#")]
    out, world = {}, None
    for r in csv.DictReader(rows):
        c = Country(r["iso3"], r["name"], float(r["gdp_usd"]), int(r["gdp_year"]), int(r["population"]))
        if c.iso3 == "WLD":
            world = c
        else:
            out[c.iso3] = c
    return out, world


def players(countries: dict, world: Country, eu_as_bloc: bool = True, exclude=SUPERPOWERS) -> dict:
    """{player: (gdp share, population share)}. With eu_as_bloc the EU27 is one player ("EU27"), since trade policy,
    the agreement's main lever, is an EU competence."""
    out = {}
    for iso, c in countries.items():
        if iso in exclude or (eu_as_bloc and iso in EU27):
            continue
        out[iso] = (c.gdp_usd / world.gdp_usd, c.population / world.population)
    if eu_as_bloc:
        g = sum(countries[i].gdp_usd for i in EU27) / world.gdp_usd
        p = sum(countries[i].population for i in EU27) / world.population
        out["EU27"] = (g, p)
    return out


def shares(members, table: dict) -> tuple:
    return (sum(table[m][0] for m in members), sum(table[m][1] for m in members))


def activates(members, table: dict, gdp_quota: float = GDP_QUOTA, pop_quota: float = POP_QUOTA) -> bool:
    g, p = shares(members, table)
    return g >= gdp_quota and p >= pop_quota


def smallest_coalitions(table: dict, max_size: int = 4, top: int = 40, gdp_quota: float = GDP_QUOTA,
                        pop_quota: float = POP_QUOTA) -> dict:
    """Coalitions with the fewest members that activate the agreement. Exhaustive over all players up to size 3;
    for larger sizes, over the `top` players largest by either share (reported as such)."""
    names = sorted(table)
    for size in range(1, int(max_size) + 1):
        pool = names if size <= 3 else sorted(names, key=lambda n: -max(table[n]))[: int(top)]
        hits = [c for c in itertools.combinations(pool, size) if activates(c, table, gdp_quota, pop_quota)]
        if hits:
            hits.sort(key=lambda c: -shares(c, table)[0])
            return {"size": size, "exhaustive": size <= 3, "searched": len(pool), "coalitions": hits}
    return {"size": None, "exhaustive": False, "searched": 0, "coalitions": []}


def shapley_shubik(table: dict, permutations: int = 20000, seed: int = 0, gdp_quota: float = GDP_QUOTA,
                   pop_quota: float = POP_QUOTA) -> dict:
    """Monte Carlo Shapley-Shubik power in the activation game: over random orders of joining, the share of orders in
    which a player's joining first makes both quotas met. {player: (index, standard error)}; orders in which the
    whole table never activates count for no one."""
    names = sorted(table)
    w = np.array([table[n] for n in names])
    rng = np.random.default_rng(seed)
    counts = np.zeros(len(names))
    chunk = 2000
    done = 0
    while done < permutations:
        m = min(chunk, permutations - done)
        order = np.argsort(rng.random((m, len(names))), axis=1)
        cg, cp = np.cumsum(w[order, 0], axis=1), np.cumsum(w[order, 1], axis=1)
        ok = (cg >= gdp_quota) & (cp >= pop_quota)
        any_ok = ok.any(axis=1)
        piv = order[np.arange(m), ok.argmax(axis=1)]
        np.add.at(counts, piv[any_ok], 1.0)
        done += m
    p = counts / permutations
    se = np.sqrt(p * (1 - p) / permutations)
    return {n: (float(p[i]), float(se[i])) for i, n in enumerate(names)}


def shapley_exact(table: dict, gdp_quota: float = GDP_QUOTA, pop_quota: float = POP_QUOTA) -> dict:
    """Exact Shapley-Shubik power by enumerating every order (small tables only; used to check the estimator)."""
    names = sorted(table)
    if len(names) > 9:
        raise ValueError("exact enumeration is for up to 9 players")
    counts = dict.fromkeys(names, 0)
    total = 0
    for order in itertools.permutations(names):
        g = p = 0.0
        total += 1
        for n in order:
            g, p = g + table[n][0], p + table[n][1]
            if g >= gdp_quota and p >= pop_quota:
                counts[n] += 1
                break
    return {n: counts[n] / total for n in names}


# ---- redlines --------------------------------------------------------------------------------------------------
TECHNICAL = (   # (finding, threshold or None for yes/no, level, wording)
    ("compute_holdings_above_threshold", None, 2, "compute holdings above a threshold"),
    ("full_stack_industrial_capacity", None, 3, "full-stack industrial capacity for general-purpose AI"),
    ("ai_rnd_compute_above_threshold", None, 3, "total AI R&D compute above a threshold"),
    ("economy_automated", 0.10, 4, "10% of the economy automated by general-purpose AI"),
    ("economy_automated", 0.25, 5, "25% of the economy automated"),
    ("economy_automated", 0.50, 6, "50% of the economy automated"),
    ("ai_in_weapons_command_and_control", None, 4, "general-purpose AI in real-time weapons command and control"),
    ("military_automation_proof_of_concept", None, 5, "military industries automated as a proof of concept"),
    ("military_automation_increased_output", None, 6, "military industries automated with much greater output"),
    ("large_scale_ai_cyberattack", None, 5, "a large-scale AI-powered cyberwarfare attack"),
)
JUDICIAL = (
    ("cyber_partial_automation", None, 3, "partial automation of cyberwarfare tasks"),
    ("cyber_expert_speedup", 3.0, 3, "3x expert speed-up in cyberwarfare"),
    ("nonexperts_basic_cyberwarfare_at_scale", None, 3, "non-experts running basic cyberwarfare at scale"),
    ("destabilising_ai_propaganda", None, 3, "AI propaganda or misinformation destabilising other states"),
    ("ai_rnd_partial_automation", None, 3, "partial automation of AI R&D"),
    ("ai_rnd_engineer_speedup", 2.0, 3, "2x engineer speed-up in AI R&D"),
    ("cyber_almost_full_automation", None, 4, "almost full automation of cyberwarfare, enabling non-experts"),
    ("cyber_expert_speedup", 10.0, 4, "10x expert speed-up in cyberwarfare"),
    ("wmd_partial_automation", None, 4, "partial automation of WMD R&D"),
    ("wmd_expert_speedup", 3.0, 4, "3x expert speed-up in WMD R&D"),
    ("ai_rnd_engineer_speedup", 4.0, 4, "4x engineer speed-up in AI R&D"),
    ("crippling_cyberattack_capability", None, 5, "capability for a crippling AI-powered cyberwarfare attack"),
    ("ai_rnd_critical_bottleneck_mostly_automated", None, 5, "AI mostly automating a critical AI R&D bottleneck"),
    ("ai_rnd_almost_full_automation", None, 6, "almost full automation of AI R&D"),
    ("ai_rnd_engineer_speedup", 10.0, 6, "10x engineer speed-up in AI R&D"),
    ("wmd_almost_full_automation", None, 6, "almost full automation of WMD R&D"),
    ("wmd_expert_speedup", 10.0, 6, "10x expert speed-up in WMD R&D"),
    ("ai_escaped_or_uncontrolled", None, 6, "an AI system that escaped control or runs without adequate shutdown"),
)
FINDINGS = {k for k, *_ in TECHNICAL + JUDICIAL} | {"ai_system_leaked"}


def assess(findings: dict) -> tuple:
    """(level, reasons) for one actor's findings, before persistence. Unknown findings raise, so a typo cannot pass
    silently."""
    unknown = set(findings) - FINDINGS
    if unknown:
        raise ValueError(f"unknown findings: {sorted(unknown)}")
    level, why = 0, []
    for key, thr, lv, text in TECHNICAL + JUDICIAL:
        v = findings.get(key)
        hit = bool(v) if thr is None else (v is not None and float(v) >= thr)
        if hit:
            why.append((lv, text))
            level = max(level, lv)
    if findings.get("ai_system_leaked"):
        level = min(SELF_DEFENCE, level + 1)
        why.append((level, "a system was released or leaked: the measure that would apply, one level up"))
    return level, [t for _, t in sorted(why, reverse=True)]


def run_timeline(monthly_findings: list) -> list:
    """Month-by-month levels with the six-month persistence rules. Each entry: {month, level, measure, reasons}."""
    out, at_wide, at_full = [], 0, 0
    for m, f in enumerate(monthly_findings):
        level, why = assess(f)
        at_wide = at_wide + 1 if level >= WIDE else 0          # consecutive months past the wide-embargo line
        if at_wide > 6 and level < FULL:                       # crossed six or more months ago: full embargo
            level, why = FULL, why + ["six months in violation past the wide-embargo line"]
        at_full = at_full + 1 if level >= FULL else 0           # consecutive months past the full-embargo line
        if at_full > 6 and level < SELF_DEFENCE:
            level, why = SELF_DEFENCE, why + ["six months in violation past the full-embargo line"]
        out.append({"month": m, "level": level, "measure": LEVELS[level], "reasons": why})
    return out


def presumed_level(observed_compute: float, plausible: list) -> tuple:
    """The risk-averse presumption for an actor whose findings are unknown: the most concerning findings that are
    plausible at its observed compute. plausible: [(minimum compute, findings dict)], which the paper leaves to the
    members to set."""
    best = (0, [])
    for min_compute, f in plausible:
        if observed_compute >= min_compute:
            best = max(best, assess(f), key=lambda x: x[0])
    return best


def impromptu_session(requests: int, members: int) -> bool:
    """An impromptu session is called by 'a fifth of members plus one' (read here as floor(n / 5) + 1)."""
    return int(requests) >= int(members) // 5 + 1
