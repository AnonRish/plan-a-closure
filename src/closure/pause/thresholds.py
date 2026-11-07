"""Treaty thresholds of a hardwired pause (paper sections 3.2.2 and 6.2, Table 3.1).

Every threshold is indexed to the frozen frontier C_F, the total FLOP of the final training run of the most capable
model at the pause date. A training budget becomes a *fleet*, the hardware an evader needs to run the whole research
programme around that final run within a strategic horizon:

    F_x = rho_x * C_x / (T_x * U_F)          FLOP/s, divided by 989 TFLOP/s to give H100e

rho is the research overhead (all compute around the final run), T the horizon, U_F the utilisation of today's frontier
training. As in the paper's calculation supplement, derived quantities are carried at full precision; rounding is for
printing only (use units.sig)."""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

from .units import SECONDS_PER_YEAR, h100e


@dataclass(frozen=True)
class ThresholdParams:
    c_f: float = 2e27            # frozen frontier, FLOP, year-end 2026 (judgemental input)
    beta_t: float = 1e-3         # treaty compute ceiling C_T = beta_t * C_F
    beta_e: float = 10.0         # covert-evasion target C_E = beta_e * C_F
    c_b: float = 2e29            # overt-breakout level, an absolute capability level (FLOP)
    g: float = 4.5               # frontier training-compute growth per year
    lag_years: float = 4 / 12    # lag between research compute and the final run it feeds
    share_frontier: float = 0.096   # final run's share of a frontier lab's research compute
    share_trailing: float = 0.123   # same for a fast follower (Z.ai); sets rho_P
    delta: float = 1 / 3         # blind-leap increment, orders of magnitude (about six months on the trajectory)
    f_post: float = 0.40         # post-training share of a frontier run's FLOP
    u_pre: float = 0.40          # pretraining utilisation (mid-range of 30-50%)
    u_post: float = 0.125        # RL post-training utilisation (mid-range of 5-20%)
    t_e: float = 5.0             # covert-evasion horizon, years
    t_b: float = 2.0             # overt-breakout horizon, years
    overtrain: float = 100.0     # overtraining factor behind the parameter ceiling (footnote 21)

    def with_(self, **kw) -> "ThresholdParams":
        return replace(self, **kw)


def blended_utilization(f_post: float = 0.40, u_pre: float = 0.40, u_post: float = 0.125) -> float:
    """FLOP-weighted utilisation of a run that is `f_post` post-training: a harmonic mean (section 6.2.1)."""
    return 1.0 / ((1.0 - f_post) / u_pre + f_post / u_post)


def frontier_overhead(g: float = 4.5, lag_years: float = 4 / 12, final_run_share: float = 0.096) -> float:
    """rho_F = g^(-lag) / share: research compute per unit of final-run compute, lag-adjusted (section 6.2.1)."""
    return g ** (-lag_years) / final_run_share


def blind_steps(beta: float, delta: float = 1 / 3) -> float:
    """Steps of `delta` orders of magnitude needed to reach beta times the frontier. Not rounded: the last may be partial."""
    return max(1.0, math.log10(beta) / delta)


def blind_factor(beta: float, delta: float = 1 / 3) -> float:
    """Overhead multiplier of reaching beta in blind leaps: sum_i beta^(i/n) / beta = (1 - 1/beta) / (1 - beta^(-1/n))."""
    if beta <= 1.0:
        return 1.0
    n = blind_steps(beta, delta)
    return (1.0 - 1.0 / beta) / (1.0 - beta ** (-1.0 / n))


def research_overhead(beta: float, rho_f: float, delta: float = 1 / 3) -> float:
    return rho_f * blind_factor(beta, delta)


def fleet_h100e(rho: float, c_flop: float, horizon_years: float, utilization: float) -> float:
    """Fleet (H100e, at peak) that runs rho * c_flop within the horizon at the given utilisation."""
    return h100e(rho * c_flop / (horizon_years * SECONDS_PER_YEAR * utilization))


def covert_evasion_fleet(p: ThresholdParams = ThresholdParams()) -> float:
    rho_e = research_overhead(p.beta_e, frontier_overhead(p.g, p.lag_years, p.share_frontier), p.delta)
    return fleet_h100e(rho_e, p.beta_e * p.c_f, p.t_e, blended_utilization(p.f_post, p.u_pre, p.u_post))


def overt_breakout_fleet(p: ThresholdParams = ThresholdParams(), c_b: float = None, t_b: float = None) -> float:
    c_b = p.c_b if c_b is None else c_b
    beta_b = c_b / p.c_f
    rho_b = research_overhead(beta_b, frontier_overhead(p.g, p.lag_years, p.share_frontier), p.delta)
    return fleet_h100e(rho_b, c_b, p.t_b if t_b is None else t_b, blended_utilization(p.f_post, p.u_pre, p.u_post))


def private_evasion_fleet(p: ThresholdParams = ThresholdParams(), undetected_runs_at_ct: float = 100.0) -> float:
    """F_P: aggregate fleet of private evaders for `undetected_runs_at_ct` runs of size C_T per year (section 6.2.4).
    Private runs stay below the frozen frontier, so the trailing overhead applies and there are no blind steps."""
    rho_p = frontier_overhead(p.g, p.lag_years, p.share_trailing)
    return fleet_h100e(rho_p, undetected_runs_at_ct * p.beta_t * p.c_f, 1.0, blended_utilization(p.f_post, p.u_pre, p.u_post))


def pareto_mean(theta: float, x_max: float = None) -> float:
    """E[x] for a Pareto(theta) on [1, inf), or truncated at x_max (the paper's text uses the untruncated mean)."""
    if x_max is None:
        if theta <= 1.0:
            return math.inf
        return theta / (theta - 1.0)
    if abs(theta - 1.0) < 1e-9:
        return math.log(x_max) / (1.0 - 1.0 / x_max)
    return (theta / (theta - 1.0)) * (1.0 - x_max ** (1.0 - theta)) / (1.0 - x_max ** (-theta))


def private_evasion_stress(p: ThresholdParams = ThresholdParams(), theta: float = 2.0, utilization_ratio: float = 0.5,
                           inference_share: float = 0.5, x_max: float = None) -> float:
    """F_P when evaders reach only `utilization_ratio` of frontier utilisation, spend `inference_share` of their compute
    on inference and violate at Pareto(theta)-distributed sizes: the paper's factor 4*theta/(theta-1) at the defaults."""
    return private_evasion_fleet(p) / (utilization_ratio * (1.0 - inference_share)) * pareto_mean(theta, x_max)


def params_for_compute(c_flop: float, overtrain: float = 1.0) -> float:
    """Chinchilla mapping C = 120 N^2 (times the overtraining factor): the parameter count whose run costs c_flop."""
    return math.sqrt(c_flop / (120.0 * overtrain))


def compute_for_params(n_params: float, overtrain: float = 1.0) -> float:
    return 120.0 * overtrain * n_params * n_params


def treaty_thresholds(p: ThresholdParams = ThresholdParams()) -> dict:
    """The quantities of Table 3.1 at full precision, plus the pieces they are built from."""
    rho_f = frontier_overhead(p.g, p.lag_years, p.share_frontier)
    c_t = p.beta_t * p.c_f
    return {"C_F": p.c_f, "C_T": c_t, "N_T": params_for_compute(c_t, p.overtrain), "C_E": p.beta_e * p.c_f, "C_B": p.c_b,
            "F_E": covert_evasion_fleet(p), "F_B": overt_breakout_fleet(p), "F_P": private_evasion_fleet(p),
            "rho_F": rho_f, "rho_E": research_overhead(p.beta_e, rho_f, p.delta),
            "rho_B": research_overhead(p.c_b / p.c_f, rho_f, p.delta),
            "U_F": blended_utilization(p.f_post, p.u_pre, p.u_post)}


TABLE_3_1_PRINTED = {"C_F": 2e27, "C_T": 2e24, "N_T": 13e9, "C_E": 2e28, "C_B": 2e29, "F_E": 6.4e6, "F_B": 180e6}


def is_beyond_threshold(train_flop: float, n_params: float, c_t: float, n_t: float) -> bool:
    """A model is beyond-threshold if it exceeds the compute ceiling OR the parameter ceiling (section 3.2.2)."""
    return train_flop > c_t or n_params > n_t


def erode(x0: float, years: float, annual_gain: float) -> float:
    """A threshold after `years` of training-efficiency gains of `annual_gain` per year (e.g. 1.57)."""
    return x0 / annual_gain ** years


def oom_per_year(annual_gain: float) -> float:
    return math.log10(annual_gain)


def years_for_oom(orders: float, annual_gain: float) -> float:
    """Years until `orders` orders of magnitude of erosion have accumulated."""
    return orders / oom_per_year(annual_gain)


def arrival_years(beta: float, g: float = 4.5) -> float:
    """Years on the unpaused trajectory until the frontier has grown by a factor beta (section 6.2.3)."""
    return math.log(beta) / math.log(g)


def months_per_blind_step(p: ThresholdParams = ThresholdParams()) -> float:
    """Months of the pre-pause trajectory one blind step represents: delta orders of magnitude at g per year. Each half-year
    of delay in starting a pause removes about one blind step from a fixed breakout target (section 6.2.3)."""
    return 12.0 * p.delta / math.log10(p.g)


def breakout_sensitivity(p: ThresholdParams = ThresholdParams(), steps=range(3, 9), horizons=(1.0, 2.0, 3.0)) -> list:
    """F_B for breakout targets `n` blind steps above the frontier and several horizons: the table behind section 6.2.3."""
    rows = []
    for n in steps:
        beta = 10.0 ** (n * p.delta)
        row = {"n_steps": n, "beta_B": beta, "C_B": beta * p.c_f, "arrival_years": arrival_years(beta, p.g)}
        for t in horizons:
            row[f"F_B_T{t:g}"] = overt_breakout_fleet(p, c_b=beta * p.c_f, t_b=t)
        rows.append(row)
    return rows


def pause_delay(p: ThresholdParams, delay_years: float) -> dict:
    """Thresholds if the pause starts `delay_years` after year-end 2026. The frontier has moved along its trend, so F_E
    scales with it, while the breakout level C_B is an absolute capability and so has fewer blind steps left (section 6.2)."""
    q = p.with_(c_f=p.c_f * p.g ** delay_years)
    return {"C_F": q.c_f, "F_E": covert_evasion_fleet(q), "F_B": overt_breakout_fleet(q), "beta_B": p.c_b / q.c_f}
