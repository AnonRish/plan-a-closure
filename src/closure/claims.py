"""Executable re-derivation of the numeric claims in the AI 2040 verification plan (pasted text).

Status: OK (reproduces), WORDING (true only under a stated reading), INCONSISTENT (no reading reproduces it)."""
from __future__ import annotations

import math
from dataclasses import dataclass

from . import assurance as A
from . import ledger as L
from . import retrofit as R

LN100, LN1000 = math.log(100.0), math.log(1000.0)


def p_undetected(c: float, n_fake: float) -> float:
    return (1.0 - c) ** n_fake


def p_detect_poisson(c: float, n_fake: float) -> float:
    return 1.0 - math.exp(-c * n_fake)


def budget_exact(n_fake: float, conf: float) -> float:
    return 1.0 - (1.0 - conf) ** (1.0 / n_fake)


def budget_poisson(n_fake: float, conf: float) -> float:
    return -math.log(1.0 - conf) / n_fake


def rogue_work_bound(p: float, c: float, conf: float = 0.99) -> float:
    return -math.log(1.0 - conf) * p / c


def backdoor_cost(batch: float, n_fake_tokens: float = 1e5, conf: float = 0.999) -> float:
    return -math.log(1.0 - conf) * batch / n_fake_tokens


@dataclass
class Check:
    id: str
    source: str
    claim: str
    expected: float
    computed: float
    status: str
    note: str = ""


def _c(cid, src, claim, exp, got, rel=0.02, abs_=0.0, status_if_fail="INCONSISTENT", note="", force=None):
    ok = abs(got - exp) <= max(abs_, rel * abs(exp))
    return Check(cid, src, claim, exp, got, force or ("OK" if ok else status_if_fail), note)


def check_all() -> list:
    out = []
    S = "Appendix A"
    out += [
        _c("A3.ln100", S + ".3", "99% catch needs C*N_fake >= ln(100) ~ 4.6", 4.6, LN100, rel=0.01),
        _c("A3.n461", S + ".3", "C=1% needs ~461 fake packets", 461, math.ceil(LN100 / 0.01), abs_=1),
        _c("A3.exact100", S + ".3", "N_fake=100: exact budget for 99% is 4.5%", 0.045, budget_exact(100, 0.99), rel=0.01),
        _c("A3.poisson100", S + ".3", "N_fake=100: Poisson budget is 4.6%", 0.046, budget_poisson(100, 0.99), rel=0.01),
        _c("A3.exact1000", S + ".3", "N_fake=1000: exact budget 0.459%", 0.00459, budget_exact(1000, 0.99), rel=0.01),
        _c("A3.single", S + ".3", "N_fake=1: P(catch)=C, so 99% needs 99% recompute", 0.99, 1.0 - p_undetected(0.99, 1), rel=1e-9),
        _c("A41.ln1000", S + ".4.1", "ln(1000) ~ 7", 7.0, LN1000, rel=0.015),
    ]
    for b, exp in ((10_000, 0.70), (1_000, 0.07), (100, 0.007), (10, 0.0007)):
        out.append(_c(f"A41.B{b}", S + ".4.1", f"batch {b}: recompute cost {exp:.2%}", exp, backdoor_cost(b), rel=0.02))
    for p, c, exp in ((100, 0.01, 46_000), (100, 0.001, 460_000), (10, 0.01, 4_600), (1, 0.01, 460)):
        out.append(_c(f"A42.p{p}c{c}", S + ".4.2", f"packet {p} H100e-h, budget {c:.1%}: max undetected {exp:,} H100e-h",
                      exp, rogue_work_bound(p, c), rel=0.01))
    out += [
        _c("A42.n461", S + ".4.2", "C=1%: 461 packets, independent of pool size", 461, math.ceil(LN100 / 0.01), abs_=1),
        _c("2034.t10k", "2034 verification improvements", "sustained 10K H100e caught within ~4.6 h", 4.6,
           A.detection_time_hours(0.01, 100.0, 10_000), rel=0.01),
        _c("2034.t1k", "2034 verification improvements", "1K H100e within ~46 h", 46.0,
           A.detection_time_hours(0.01, 100.0, 1_000), rel=0.01),
    ]
    # compute declaration (Jan 2029)
    us, cn, row = 224.0, 26.0, 39.0
    tot = us + cn + row
    out += [
        _c("D.total", "Jan 2029 declaration", "US 224M + China 26M + RoW 39M = 289M", 289.0, tot, rel=0.001),
        _c("D.share_us", "Jan 2029 declaration", "US 77%", 0.77, us / tot, abs_=0.01),
        _c("D.share_cn", "Jan 2029 declaration", "China 9%", 0.09, cn / tot, abs_=0.01),
        _c("D.share_row", "Jan 2029 declaration", "RoW 14%", 0.14, row / tot, abs_=0.01),
        _c("D.us_cn_85", "Phase 2 rationale", "~85% of compute is US or Chinese", 0.85, (us + cn) / tot, rel=0.02),
    ]
    dc = {"10M+": (10.0, 3.5), "1M-10M": (149.0, 51.4), "100K-1M": (76.0, 26.4), "10K-100K": (15.0, 5.3),
          "1K-10K": (2.6, 0.9), "<1K": (0.397, 0.1)}
    for k, (v, share) in dc.items():
        out.append(_c(f"D.bucket.{k}", "Jan 2029 buckets", f"{k} bucket share {share}%", share / 100, v / tot, abs_=0.003))
    dc_sum = sum(v for v, _ in dc.values())
    out += [
        _c("D.sum", "Jan 2029 buckets", "buckets + in-transit 35M + AI consumer 0.938M ~ 289M", 289.0, dc_sum + 35.0 + 0.938, rel=0.005),
        _c("D.in_transit", "Jan 2029 buckets", "in-transit 12.0%", 0.12, 35.0 / tot, abs_=0.003),
        _c("D.nonai_consumer", "Jan 2029 buckets", "non-AI consumer 7.7M = 2.7% (outside the 289M total)", 0.027, 7.7 / tot, abs_=0.002),
    ]
    big = sum(v for k, (v, _) in dc.items() if k in ("10M+", "1M-10M", "100K-1M", "10K-100K"))
    out += [
        _c("D.cover_dc", "Jan 2029 table", ">10K H100e DCs = 99% of AI *datacenter* compute", 0.99, big / dc_sum, abs_=0.005),
        _c("D.cover_world", "Fig. caption, Jan 2029", "same retrofit covers ~99% of world AI-relevant compute", 0.99, big / tot, rel=0.02,
           status_if_fail="WORDING", note="true for datacenter compute (98.8%); 86.5% of the 289M total because 12% is in transit"),
        _c("D.hidden_pct", "Jan 2029 declaration", "1.5M undeclared ~ 0.5% of world compute", 0.005, 1.5 / tot, abs_=0.001),
        _c("D.hidden_ci", "Covert supplement figure", "80% CI top ~4M ~ 1.4% of world compute", 0.014, 4.0 / tot, abs_=0.001),
        _c("D.bank", "Phase 3 cold storage", "US 5M bank above the ~4M top of the diversion CI", 4.0, 5.0, rel=0.0,
           status_if_fail="INCONSISTENT", force="OK" if 5.0 > 4.0 else "INCONSISTENT"),
        _c("D.bank_ratio", "Phase 3 cold storage", "bank ratio ~ pre-deal compute ratio", us / cn, 5.0 / 0.5, rel=0.2),
    ]
    # uncertainty statements (Phase 1, 2028)
    out += [
        _c("U.us_full", "2028 chip tracking", "US 'around 2% uncertainty' (222M-226M)", 0.02, (226 - 222) / 224, abs_=0.003,
           status_if_fail="WORDING", note="matches the FULL width of the 80% interval (1.8%), not the half-width (0.9%)"),
        _c("U.cn_half", "2028 chip tracking", "China 'around 4% uncertainty' (25M-27M)", 0.04, (27 - 25) / 2 / 26, abs_=0.003,
           status_if_fail="WORDING", note="matches the HALF width (3.8%); the full width is 7.7%"),
        Check("U.definition", "2028 chip tracking", "one definition of 'uncertainty' for both sides", 1.0, 0.0, "INCONSISTENT",
              "US fits full width, China fits half width; no single definition reproduces both"),
    ]
    # retrofit (Feb 2029)
    us_r, cn_r = 200_000, 100_000
    cn_covers_us = R.schedule(us_r, 20_000, 10_000, 4)
    us_covers_cn = R.schedule(cn_r, 10_000, 10_000, 4)
    out += [
        _c("R.hpr_us", "Feb 2029 retrofit", "US ~1K+ H100e per rack", 1000, 0.95 * us * 1e6 / us_r, rel=0.1, note="1,064"),
        _c("R.hpr_cn", "Feb 2029 retrofit", "China ~250 H100e per rack", 250, 0.95 * cn * 1e6 / cn_r, rel=0.05),
        _c("R.m1", "Feb 2029 retrofit", "month 1: 40% with existing taps (1 tap per 4-rack unit)", 0.40, cn_covers_us[0][2], abs_=1e-9),
        _c("R.m3", "Feb 2029 retrofit", "month 3: 80% with 10K taps/month purchases", 0.80, cn_covers_us[2][2], abs_=1e-9),
        _c("R.us_side_m1", "Feb 2029 retrofit", "US taps also give 40% of China's racks in month 1", 0.40, us_covers_cn[0][2], abs_=1e-9),
        _c("R.prop", "Feb 2029 retrofit", "proportional schedule follows the slower side", 0.80, R.proportional(cn_covers_us, us_covers_cn)[2][1], abs_=1e-9),
    ]
    # 2030s trajectory
    out += [
        _c("T.sl5", "Late 2030", "~370M of ~930M H100e in SL5 inference clusters = 40%", 0.40, 370 / 930, abs_=0.01),
        _c("T.rd_world", "Early 2030", "100M H100e in R&D clusters = 20% of 2030 world compute (500M)", 0.20, 100 / 500, abs_=1e-9),
        _c("T.rd_start", "Early 2030", "= 35% of compute at deal start (289M)", 0.35, 100 / tot, abs_=0.01),
        _c("T.fabs", "2033 security", "3x/yr production: 90% of fabs are new every 2 years", 0.90, 1 - 1 / 9.0, abs_=0.015),
        _c("T.doubling", "2032 cap & trade", "3B (2032) -> 60B (2034): doubling ~6 months",
           6.0, 24.0 / math.log2(60 / 3), rel=0.12),
        _c("T.edge_cap", "2032 cap & trade", "edge cap 30M = 25M existing + 5M credits", 30.0, 25.0 + 5.0, rel=0.0),
        _c("T.edge_share", "2032 cap & trade", "25M edge compute ~ 10% of AI-relevant compute", 0.10, 25 / tot, rel=0.15),
        _c("T.zdr", "ZDR tiers", "inference-fleet caps 100K / 100M / 100B H100e vs 60B world compute (2034)",
           60.0e9, 100e9, rel=0.0, status_if_fail="WORDING", note="the 100B cap exceeds the 2034 world-compute figure (60B): non-binding in 2034"),
        _c("A42.pool", "Appendix A.4.2", "'100B H100e of verified R&D' vs the 2034 figure's ~33B pool", 33e9, 100e9, rel=0.0,
           status_if_fail="WORDING", note="the bound 4.6*p/C does not depend on pool size, so the label does not affect the result"),
    ]
    return out


def summary(checks=None) -> dict:
    checks = checks or check_all()
    s = {"OK": 0, "WORDING": 0, "INCONSISTENT": 0}
    for c in checks:
        s[c.status] += 1
    s["total"] = len(checks)
    return s
