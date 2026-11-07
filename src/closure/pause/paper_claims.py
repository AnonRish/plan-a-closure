"""Executable re-derivation of the numbers printed in "The Feasibility of a Hardwired Pause of Frontier AI Training"
(working paper v1.0.1, 10 October 2026), computed by the modules in closure.pause rather than copied from the paper.

Status: OK (reproduces to the paper's printed precision), WORDING (true only under a stated reading), INCONSISTENT (no
reading reproduces it). The paper prints derived quantities to two significant figures and carries them unrounded
(its footnote 50), so tolerances are the rounding of the printed figure, not a free choice: a 2-figure number such as 6.4M
stands for anything from 6.35M to 6.45M, and the tolerance is set a little wider only where the paper's inputs are themselves
printed to two figures. Every WORDING row says what reading makes it true."""
from __future__ import annotations

import math

from ..claims import Check, _c
from . import census, fab, gemm_audit, inference_only as IO, msic_econ, pausegame, thresholds as T
from . import transition, treaty_ledger as TL
from .units import H100E_FLOP_PER_YEAR, H100E_FLOPS, SECONDS_PER_YEAR


def _le(cid, src, claim, bound, got, note=""):
    return Check(cid, src, claim, bound, got, "OK" if got <= bound else "INCONSISTENT", note)


def _ge(cid, src, claim, bound, got, note=""):
    return Check(cid, src, claim, bound, got, "OK" if got >= bound else "INCONSISTENT", note)


def check_all() -> list:
    out = []
    t = T.treaty_thresholds()
    p = T.ThresholdParams()

    # ---- Table 3.1 and section 6.2: thresholds ---------------------------------------------------------------------------
    S = "Table 3.1 / 6.2"
    out += [
        _c("HP.T31.CT", S, "treaty compute ceiling C_T = 2e24 FLOP (0.001 of the frozen frontier)", 2e24, t["C_T"], rel=1e-9),
        _c("HP.T31.NT", S, "parameter ceiling N_T = 13B (Chinchilla with 100x overtraining)", 13e9, t["N_T"], rel=0.02),
        _c("HP.T31.CE", S, "covert-evasion training budget C_E = 2e28 FLOP", 2e28, t["C_E"], rel=1e-9),
        _c("HP.T31.FE", S, "covert-evasion fleet F_E = 6.4M H100e", 6.4e6, t["F_E"], rel=0.01),
        _c("HP.T31.FB", S, "overt-breakout fleet F_B = 180M H100e", 180e6, t["F_B"], rel=0.03,
           note="printed to two figures from 175.7M"),
        _c("HP.62.rhoF", "6.2.1", "frontier research overhead rho_F = 6.3", 6.3, t["rho_F"], rel=0.01),
        _c("HP.62.rhoP", "6.2.1", "trailing research overhead rho_P = 4.9", 4.9, T.frontier_overhead(p.g, p.lag_years, p.share_trailing), rel=0.01),
        _c("HP.62.rhoE", "6.2.2", "covert-evasion overhead rho_E = 11", 11, t["rho_E"], rel=0.04, note="10.6, printed 11"),
        _c("HP.62.rhoB", "6.2.3", "breakout overhead rho_B = 12", 12, t["rho_B"], rel=0.03, note="11.7, printed 12"),
        _c("HP.62.UF", "6.2.1", "blended utilisation U_F = 0.21 (harmonic mean of 40% and 12.5% at 60/40)", 0.21, t["U_F"], rel=0.02),
        _c("HP.62.FE.printed", "6.2.2", "F_E = 11 * 2e28 / (5 * 0.21) = 6.4M, evaluated with the printed intermediates", 6.4e6,
           11 * 2e28 / (5 * 0.21) / H100E_FLOP_PER_YEAR, rel=0.01, force="WORDING",
           note="true only with unrounded intermediates (rho_E = 10.6, U_F = 0.2128), as footnote 50 states; the rounded "
                "values printed beside the formula give 6.7M"),
        _c("HP.62.FP", "6.2.4", "private-evasion fleet F_P = 150k H100e for 100 undetected runs of size C_T a year", 150e3, t["F_P"], rel=0.02),
        _c("HP.62.FP.stress", "6.2.4", "with half the utilisation, half the compute on inference and theta = 2: 4*theta/(theta-1) -> 1.2M",
           1.2e6, T.private_evasion_stress(p, theta=2.0), rel=0.03),
        _c("HP.62.FE.2027", "6.2.2", "a mid-2027 pause (C_F = 4.2e27) gives F_E = 14M", 14e6, T.pause_delay(p, 0.5)["F_E"], rel=0.04),
        _c("HP.62.CF.2027", "6.2.2", "C_F at mid-2027 = 4.2e27 FLOP", 4.2e27, T.pause_delay(p, 0.5)["C_F"], rel=0.02),
    ]
    rows = {r["n_steps"]: r for r in T.breakout_sensitivity(p, steps=[4, 6])}
    out += [
        _c("HP.62.CB.2028", "6.2.3", "a leader expecting a decisive model by end-2028 (four blind steps): C_B = 4.3e28", 4.3e28, rows[4]["C_B"], rel=0.01),
        _c("HP.62.beta.2028", "6.2.3", "...beta_B = 22", 22, rows[4]["beta_B"], rel=0.03),
        _c("HP.62.FB.2028", "6.2.3", "...F_B = 36M", 36e6, rows[4]["F_B_T2"], rel=0.02),
        _c("HP.62.FB.2028.T1", "6.2.3", "...and 73M at a one-year horizon", 73e6, rows[4]["F_B_T1"], rel=0.01),
        _c("HP.62.FB.T1", "6.2.3", "adopted target at a one-year horizon: 350M", 350e6, rows[6]["F_B_T1"], rel=0.01),
        _c("HP.62.arrival", "6.2.3", "four blind steps is about two years after the pause (end-2028)", 2.0, rows[4]["arrival_years"], rel=0.05),
        _c("HP.62.step.months", "6.2.3", "one blind step is about six months of trajectory", 6.0, T.months_per_blind_step(p), rel=0.03),
        _c("HP.62.growth18", "Executive summary", "4.5x a year is an order of magnitude about every 18 months", 18.0, 12.0 / math.log10(p.g), rel=0.03),
        _c("HP.62.chinchilla", "6.2.5", "Chinchilla-optimal model at C_T has about 130B parameters", 130e9, T.params_for_compute(t["C_T"]), rel=0.02),
        _c("HP.62.overtrain", "3.2.2 fn 21", "Llama3-8B: 15T tokens is roughly two orders of magnitude over 160B", 100.0, 15e12 / 160e9, rel=0.07),
        _le("HP.62.rl.share", "6.2.5", "an RL fine-tune below C_T is under 1% of the original model's post-training compute",
            0.01, t["C_T"] / (p.f_post * p.c_f)),
        _c("HP.62.gpt6.low", "6.2 fn 64", "228k H100e for 3 months at 40% utilisation: 6.9e26 FLOP", 6.9e26,
           228e3 * H100E_FLOPS * 0.25 * SECONDS_PER_YEAR * 0.4, rel=0.04),
        _c("HP.62.gpt6.high", "6.2 fn 64", "...6 months: 1.4e27 FLOP", 1.4e27, 228e3 * H100E_FLOPS * 0.5 * SECONDS_PER_YEAR * 0.4, rel=0.03),
        _c("HP.62.gpt6.full", "6.2 fn 64", "full run if post-training is 40%: 1.2e27 to 2.4e27", 2.4e27,
           228e3 * H100E_FLOPS * 0.5 * SECONDS_PER_YEAR * 0.4 / 0.6, rel=0.03),
    ]

    # ---- 6.3 and 6.5: training-efficiency gains ---------------------------------------------------------------------------
    out += [
        _c("HP.63.ho.20000", "6.3.1", "2.7x a year extrapolated ten years: one 20,000th of the cost", 20_000, 2.7 ** 10, rel=0.05),
        _c("HP.63.ho.five", "6.3.1", "...so GPT-6 Astra on about five accelerators instead of 100,000", 5.0, 100_000 / 2.7 ** 10, rel=0.05),
        _c("HP.63.gundlach", "6.3.1", "a total gain of 60x over 2012-2023 is about 45% a year", 1.45, 60 ** (1 / 11), rel=0.01),
        _le("HP.65.patel5", "6.5", "57% a year is slightly slower than one order of magnitude every five years", 10.0, 1.57 ** 5),
        _c("HP.65.moore", "6.5", "57% a year matches an 18-month doubling (Moore's law)", 1.57, 2 ** (1 / 1.5), rel=0.02),
        _c("HP.65.decade", "6.5", "a decade of durability at 57% a year needs two orders of magnitude of headroom", 2.0, 10 * math.log10(1.57), rel=0.03),
        _c("HP.65.half", "6.5", "at 2.7x a year the treaty is about half as durable", 0.5, math.log10(1.57) / math.log10(2.7), rel=0.1),
    ]

    # ---- 5.3 and 5.4: production and census -------------------------------------------------------------------------------
    out += [
        _c("HP.53.detect95", "5.3.2", "2400 chips a year, 1-in-4 recognition, 1% diverted: caught within six months with 95%", 0.95,
           fab.p_detect(1200, 0.01, 0.25), abs_=0.001),
        _c("HP.53.poisson", "5.3.2 fn 52", "...equivalently Poisson(3): at least one detection 95%", 0.95, 1 - math.exp(-3.0), abs_=0.001),
        _c("HP.54.cost", "5.4.2", "25M accelerators at about $20k: $500B", 500e9, census.buyback_budget(25e6, 20e3, 1.0), rel=0),
        _le("HP.54.buyback", "5.4.2", "even doubled, the buyback ($1T) is under a quarter of US pandemic relief ($4.5T)", 4.5e12 / 4,
            census.buyback_budget(25e6, 20e3, 2.0)),
        _c("HP.55.site", "5.5.2", "chips not findable through a data centre: 10% + 6% = 16%", 0.16, census.site_miss_fraction(), abs_=1e-9),
        _c("HP.55.mu.on", "5.5.2", "mu(on-books) <= 0.19%", 0.0019, census.missing_fraction("on_books"), rel=0.02),
        _c("HP.55.mu.off", "5.5.2", "mu(off-books) <= 1.6%", 0.016, census.missing_fraction("off_books"), rel=0.01),
        _c("HP.55.mu.inf", "5.5.2", "mu(informal) <= 10%", 0.10, census.missing_fraction("informal"), rel=1e-9),
        _c("HP.55.diverted", "5.5.1", "660k diverted over two years, extrapolated to three: 990k", 990e3, 660e3 / 2 * 3, rel=0),
        _c("HP.55.offbooks", "5.5.1", "10% of the diverted stock off the books in China: 99k", 99e3, census.split_residual(2379e3, 990e3)["off_books"], rel=0.01),
        _c("HP.55.informal.us", "5.5.1", "US informal holdings 35k (1% of the residual plus half a month of diversion)", 35e3,
           census.split_residual(2135e3)["informal"], rel=0.02),
        _c("HP.55.informal.cn", "5.5.1", "China informal holdings 38k", 38e3, census.split_residual(2379e3, 990e3)["informal"], rel=0.02),
    ]
    tab = census.table_5_1()
    us, cn = tab["United States"], tab["China"]
    out += [
        _c("HP.T51.KM.us", "Table 5.1", "US: 12k H100e missing in total", 12e3, us["K_M"], rel=0.02),
        _c("HP.T51.KM.cn", "Table 5.1", "China: 11k H100e missing in total", 11e3, cn["K_M"], rel=0.04),
        _c("HP.T51.fm.us", "Table 5.1", "US working chips missing: 7.5k", 7.5e3, us["functional_missing"], rel=0.02),
        _c("HP.T51.fm.cn", "Table 5.1", "China working chips missing: 9.6k", 9.6e3, cn["functional_missing"], rel=0.02),
        _c("HP.T51.failed.us", "Table 5.1", "US failed chips with no record: 4.5k", 4.5e3, us["failed_missing"], rel=0.02),
        _c("HP.T51.failed.cn", "Table 5.1", "China failed chips with no record: 1.7k", 1.7e3, cn["failed_missing"], rel=0.02),
        _c("HP.T51.stock.us", "Table 5.1", "US stock about 35M H100e", 35e6, us["stock"], rel=0.01),
        _c("HP.T51.stock.cn", "Table 5.1", "China stock about 3.1M H100e", 3.1e6, cn["stock"], rel=0.01),
    ]

    # ---- 6.4 and 6.5: ledgers ---------------------------------------------------------------------------------------------
    f_e, f_b = t["F_E"], t["F_B"]
    led = {(s, sc): TL.section_6_4(s, sc) for s in ("United States", "China") for sc in ("high", "low", "non_deniable")}
    us_h, cn_h = led[("United States", "high")], led[("China", "high")]
    line = lambda L, name: next(x for x in L.lines() if x["name"] == name)
    out += [
        _c("HP.64.trans.us.E", "6.4.2", "US transitional service, covert: 35k, 0.55% of F_E", 0.0055, line(us_h, "transitional service")["share_E"], rel=0.01),
        _c("HP.64.trans.cn.E", "6.4.2", "China transitional service, covert: 31k", 31e3, line(cn_h, "transitional service")["K_E"], rel=0.01),
        _c("HP.64.trans.us.B", "6.4.2", "US transitional service, overt: 20% of F_B", 0.20, line(us_h, "transitional service")["share_B"], rel=0.01),
        _c("HP.64.trans.cn.B", "6.4.2", "China transitional service, overt: 1.8% of F_B", 0.018, line(cn_h, "transitional service")["share_B"], rel=0.02),
        _c("HP.64.dark.hc.us", "6.4.3", "high cooperation, US dark compute: 7.2k, 0.11% of F_E", 7.2e3, line(us_h, "dark compute")["K_E"], rel=0.02),
        _c("HP.64.dark.hc.cn", "6.4.3", "high cooperation, China: 6.8k", 6.8e3, line(cn_h, "dark compute")["K_E"], rel=0.03),
        _c("HP.64.dark.lc.us", "6.4.3", "low cooperation, US: 0.94% of F_E", 0.0094, line(led[("United States", "low")], "dark compute")["share_E"], rel=0.02),
        _c("HP.64.dark.lc.cn", "6.4.3", "low cooperation, China: 1.8% of F_E", 0.018, line(led[("China", "low")], "dark compute")["share_E"], rel=0.03),
        _c("HP.64.dark.lc.us.B", "6.4.3", "low cooperation, US: 0.034% of F_B", 0.00034, line(led[("United States", "low")], "dark compute")["share_B"], rel=0.02),
        _c("HP.64.dark.lc.cn.B", "6.4.3", "low cooperation, China: 0.064% of F_B", 0.00064, line(led[("China", "low")], "dark compute")["share_B"], rel=0.03),
        _c("HP.64.dark.nc.us", "6.4.3", "non-deniable concealment, US 300k: 4.7% of F_E", 0.047, line(led[("United States", "non_deniable")], "dark compute")["share_E"], rel=0.01),
        _c("HP.64.dark.nc.cn", "6.4.3", "...China 1M: 16% of F_E", 0.16, line(led[("China", "non_deniable")], "dark compute")["share_E"], rel=0.035,
           note="15.65%, printed 16%"),
        _c("HP.64.dark.nc.cn.B", "6.4.3", "...0.57% of F_B", 0.0057, line(led[("China", "non_deniable")], "dark compute")["share_B"], rel=0.01),
        _c("HP.64.million", "6.4.3", "a million missing H100e would approach 16% of F_E", 0.16, 1e6 / f_e, rel=0.03),
        _c("HP.64.inf.share", "6.4.4", "two thirds of 47M H100e is inference: about 31M", 31e6, TL.INFERENCE_COMPUTE_SHARE * 47e6, rel=0.02, note="31.3M, printed 'roughly 31M'"),
        _c("HP.64.inf.B", "6.4.4", "inference-only at phi = 1e-4, 100x the inference service: breakout exposure 310k, 0.18% of F_B", 0.0018,
           line(us_h, "inference-only fleet")["share_B"], rel=0.03),
        _c("HP.64.inf.E", "6.4.4", "...covert exposure 0.0049% of F_E", 0.000049, line(us_h, "inference-only fleet")["share_E"], rel=0.02),
        _c("HP.64.cons.K0", "6.4.5", "100M consumer cards at 30 TFLOP/s: 3M H100e", 3e6, TL.CONSUMER_CARDS * TL.CONSUMER_TFLOPS * 1e12 / H100E_FLOPS, rel=0.02),
        _c("HP.64.cons.E", "6.4.5", "consumer GPUs, covert: 3.0k, 0.047% of F_E", 0.00047, line(us_h, "consumer GPUs")["share_E"], rel=0.02),
        _c("HP.64.cons.B", "6.4.5", "consumer GPUs, overt: 0.043% of F_B", 0.00043, line(us_h, "consumer GPUs")["share_B"], rel=0.02),
        _c("HP.64.elcap.K0", "6.4.6", "El Capitan: 46k APUs at 980.6 TFLOP/s is 46k H100e", 46e3, TL.EL_CAPITAN_APUS * TL.EL_CAPITAN_TFLOPS * 1e12 / H100E_FLOPS, rel=0.01),
        _c("HP.64.elcap.B", "6.4.6", "El Capitan, overt: 0.026% of F_B", 0.00026, line(us_h, "sovereign supercomputer (El Capitan scale)")["share_B"], rel=0.02),
        _c("HP.64.elcap.E", "6.4.6", "El Capitan, covert (pi = 0.2): 0.14% of F_E", 0.0014, line(us_h, "sovereign supercomputer (El Capitan scale)")["share_E"], rel=0.03),
        _c("HP.64.elcap.E25", "6.4.6", "...with pi and tau each five times lower: 0.0057% of F_E", 0.000057,
           line(us_h, "sovereign supercomputer (El Capitan scale)")["share_E"] / 25, rel=0.02),
        _c("HP.65.allow.E", "6.5", "covert allowance alpha_E * F_E = 1.6M", 1.6e6, 0.25 * f_e, rel=0.01),
        _c("HP.65.allow.B", "6.5", "overt allowance alpha_B * F_B = 44M", 44e6, 0.25 * f_b, rel=0.01),
        _c("HP.65.two.E", "6.5", "two orders of magnitude of headroom means L_E <= 16k", 16e3, 0.25 * f_e / 100, rel=0.01),
        _c("HP.65.two.B", "6.5", "...and L_B <= 440k", 440e3, 0.25 * f_b / 100, rel=0.01),
        _c("HP.65.trans53", "6.5.2", "US breakout share of 20% grows to 53% over the 26 months to inference-only production at 57%/yr", 0.53,
           line(us_h, "transitional service")["share_B"] * 1.57 ** (26 / 12), rel=0.02),
        _c("HP.65.sixfold", "6.5.1", "non-deniable concealment survives roughly six-fold efficiency gains", 6.0, f_e / 1e6, rel=0.07),
        _ge("HP.65.lc.oom", "6.4.3", "low cooperation survives one order of magnitude of gains (every line, both states)", 1.0,
            min(min(x["headroom_E_oom"] for x in led[(s, "low")].lines(durable=True)) for s in ("United States", "China"))),
    ]
    # Claims about two orders of magnitude: the paper reads headroom line by line; the ledger is a sum (section 3.2.3)
    per_line = min(led[(s, "high")].headroom(durable=True)["E_line_oom"] for s in ("United States", "China"))
    summed = min(min(led[(s, "high")].headroom(durable=True)[k] for k in ("E_sum_oom", "B_sum_oom")) for s in ("United States", "China"))
    out += [
        _c("HP.64.hc.two.line", "6.4.3", "high cooperation survives two orders of magnitude, read line by line", 2.0, per_line, rel=0.0,
           force="OK" if per_line >= 2.0 else "INCONSISTENT", note=f"binding line {per_line:.2f} orders of magnitude"),
        _c("HP.64.hc.two.sum", "6.4.3", "...and read as the summed ledger the same lines give", 2.0, summed, rel=0.0, force="WORDING",
           note=f"{summed:.2f} orders of magnitude when the lines are added: the authors' supplement reads lines separately "
                "(the supplement says the lines are not added, since they apply at different dates), so this holds line by line"),
    ]
    non_dark_e = sum(x["K_E"] for x in us_h.lines(durable=True) if x["name"] != "dark compute") / f_e
    non_dark_b = sum(x["K_B"] for x in us_h.lines(durable=True) if x["name"] != "dark compute") / f_b
    out += [
        _le("HP.61.below025", "6.1", "excluding transitional service and dark compute, both ledgers start below 0.25% of the fleet thresholds",
            0.0025, max(non_dark_e, non_dark_b), note=f"covert {non_dark_e:.3%}, overt {non_dark_b:.3%}"),
    ]
    others_pct, twin_pct = 100 * non_dark_e, 0.25          # percent of F_E: the other lines, and one twin issue at its limit
    out += [
        _c("HP.61.twin", "6.1", "twin issues each below 0.25% sustain a 25% allowance with two orders of magnitude of headroom", 2.0,
           math.log10(25.0 / (others_pct + twin_pct)), rel=0.0, force="WORDING",
           note=f"exactly 2.0 for a twin term on its own; adding the other lines ({others_pct:.2f}% covert) leaves "
                f"{math.log10(25.0 / (others_pct + twin_pct)):.2f}"),
    ]

    # ---- 4: inference-only hardware ---------------------------------------------------------------------------------------
    out += [
        _c("HP.41.token", "4.1", "token interface alone: about 12 GFLOP/s at a billion-token context and a million tokens/s", 12e9,
           IO.token_oracle_gemm_rate(1e9, 1e6), rel=0.03),
        _ge("HP.41.machines", "4.1", "...so more than 80,000 such machines to match one H100", 80_000, IO.machines_to_match(H100E_FLOPS, IO.token_oracle_gemm_rate(1e9, 1e6))),
        _c("HP.31.phi", "3.2.1", "phi = 0.001 removes 99.9% of the fleet's training capacity", 0.999, IO.training_capacity_reduction(0.001), abs_=1e-12),
        _c("HP.43.speed", "4.3", "Taalas HC1 17,000 vs 353 tokens/s per user: about 50-fold", 50.0, 17_000 / 353, rel=0.05),
        _c("HP.65f.ord", "6.2.2 fn 65", "a 50-fold speed advantage is roughly a 15-fold training-FLOP advantage (eta = 0.7)", 15.0,
           IO.inference_speed_as_training_multiple(50.0), rel=0.05),
        _c("HP.64.phi.rate", "6.4.4", "phi = 1e-4 is 100 GFLOP/s of GEMM laundering per H100e", 100e9, 1e-4 * H100E_FLOPS, rel=0.02),
        _c("HP.64.serve.01", "6.4.4", "1M H100e of breakout allowance serves 100M H100e of demand at phi = 0.01", 100e6, IO.servable_demand(1e6, 0.01), rel=1e-9),
        _c("HP.64.serve.001", "6.4.4", "...and 1B at phi = 0.001", 1e9, IO.servable_demand(1e6, 0.001), rel=1e-9),
        _c("HP.42.attn", "4.2", "an exposed attention path hands over tens of percent of arithmetic (long context, d = 4096)", 0.25,
           gemm_audit.attention_flop_share(4096, 8192), rel=0.01, note="n/(6d+n); 8% at 2k context, 84% at 128k"),
        _c("HP.44.phase1", "4.4", "Phase 1 for Jalapeno: 13 + 6 + 7 = 26 months", 26, transition.phase1_months(*transition.JALAPENO_MONTHS.values()), rel=0),
        _c("HP.44.phase2", "4.4", "Phase 2: 47M / 2.9M per month is about 16 months", 16, transition.phase2_months(47e6, 2.9e6), rel=0.02),
    ]

    # ---- 7.3: MSIC economics ----------------------------------------------------------------------------------------------
    st = msic_econ.stranded_capital(0.5, 0.5, 1.0, 0.85, 0.3, 2e12, 500e6)
    out += [
        _c("HP.73.price.r1", "7.3 fn 79", "DeepSeek R1: 7.6 vs 20.2 cents per Mtoken is about 62% saving", 0.62, msic_econ.savings_from_prices(7.6, 20.2), abs_=0.005),
        _c("HP.73.price.llama", "7.3 fn 79", "Llama 3.1 8B: 0.75 vs 3.63 cents is 79%", 0.79, msic_econ.savings_from_prices(0.75, 3.63), abs_=0.005),
        _c("HP.73.x120", "7.3.1", "worst case: savings exceed the fixed cost about 120x for a 14% model", 120.0, 0.85 * 0.14 * 500e9 / 500e6, rel=0.02),
        _c("HP.73.stranded", "7.3.4", "stranded capital of de-whitelisting a 30% model: about $45B", 45e9, st, rel=0.01),
        _c("HP.73.breakeven", "7.3.4", "MSICs stay cheaper if more than 9% of lifetime demand was served first", 0.09,
           msic_econ.breakeven_fraction(0.85, 0.3, 2e12, st), rel=0.02),
        _c("HP.73.util", "7.3.3", "at 50% utilisation an MSIC still saves 70%", 0.70, msic_econ.utilisation_adjusted_savings(0.85, 0.5), abs_=1e-9),
        _c("HP.73.replace.lo", "7.3.3", "replacing the whole fleet costs roughly 30% of B (design fees small)", 0.30, msic_econ.replacement_cost_fraction(0.85, 196, 10e6, 500e9), rel=0.05),
        _c("HP.73.replace.hi", "7.3.3", "...up to roughly 40% when 60 large designs are rebuilt", 0.40, msic_econ.replacement_cost_fraction(0.85, 60, 500e6, 500e9), rel=0.07),
        _c("HP.71.mpc", "7.1", "3% of a $6.5T fall in Mag7 value is $195B", 195e9, 0.03 * 6.5e12, rel=1e-9),
    ]

    # ---- 2.3: game theory -------------------------------------------------------------------------------------------------
    out += [
        _c("HP.23.pd", "2.3", "a Prisoner's Dilemma has no pause equilibrium", 1, len(pausegame.pure_equilibria(5, 3, 1, 0)), abs_=0,
           note="the only pure equilibrium is both racing"),
        _c("HP.23.sh", "2.3", "a Stag Hunt has two pure equilibria, both pausing and both racing", 2, len(pausegame.pure_equilibria(4, 5, 2, 0)), abs_=0),
        _c("HP.23.folk", "2.3", "grim trigger sustains a pause iff delta >= (T-R)/(T-P)", 0.5, pausegame.patience_threshold(5, 3, 1, 1.0), abs_=1e-6),
    ]
    return out


def summary(checks=None) -> dict:
    checks = checks or check_all()
    s = {"OK": 0, "WORDING": 0, "INCONSISTENT": 0}
    for c in checks:
        s[c.status] += 1
    s["total"] = len(checks)
    return s
