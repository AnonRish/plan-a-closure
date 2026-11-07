"""Economics of model-specific integrated circuits (paper section 7.3).

An MSIC hardwires one model into silicon. It saves a share S of the cost of serving that model on flexible accelerators and
costs a fixed non-recurring engineering (NRE) bill. With D_M the model's share of inference demand and B the lifetime cost of
serving all demand on flexible hardware, a chip is worth building when

    S * D_M * B > NRE.

The paper's own numbers use measured demand shares (OpenRouter, one week); this module takes any list of shares."""
from __future__ import annotations

import csv


def adopt(d_m: float, s: float, b: float, nre: float) -> bool:
    return s * d_m * b > nre


def normalise(demand) -> list:
    """Demand as a list of shares summing to one, largest first. Accepts a dict or a list of numbers (tokens or shares)."""
    vals = list(demand.values()) if isinstance(demand, dict) else list(demand)
    total = float(sum(vals))
    return sorted((v / total for v in vals), reverse=True)


def panel(demand, s: float, b: float, nre: float) -> dict:
    """Designs built, share of tokens served on MSICs, and total saving as a fraction of B (section 7.3.1, Figure 7.1):
    saving = S * coverage - designs * NRE / B."""
    shares = normalise(demand)
    built = [d for d in shares if adopt(d, s, b, nre)]
    coverage = sum(built)
    return {"designs": len(built), "msic_token_share": coverage, "flexible_token_share": 1.0 - coverage,
            "savings_vs_all_flexible": s * coverage - len(built) * nre / b}


def unserved_share_bound(demand, s: float, b: float, nre: float) -> float:
    """Upper bound on the share of demand left unserved in a world where ONLY MSICs may serve (section 7.3.2): every model
    that clears the mixed-world rule is still built, and extra ones may be, so the mixed-world flexible share bounds it."""
    return panel(demand, s, b, nre)["flexible_token_share"]


def savings_from_prices(msic_price: float, flexible_price: float) -> float:
    """Saving implied by two published prices per million tokens (e.g. 7.6 vs 20.2 cents is 62%)."""
    return 1.0 - msic_price / flexible_price


def utilisation_adjusted_savings(s: float, msic_utilisation: float, flexible_utilisation: float = 1.0) -> float:
    """Saving when the MSIC idles part of the day (a model nobody uses at night) and cost per token scales as 1/utilisation."""
    rel = (1.0 - s) / msic_utilisation * flexible_utilisation
    return 1.0 - rel


def stranded_capital(w: float, v: float, k: float, s: float, d_m: float, b: float, nre: float) -> float:
    """Cost of de-whitelisting a model whose chips are partly installed (section 7.3.4):
    W * K * (1 - S) * D_M * B for chips plus V * NRE for unamortised design. W: stranded-chip fraction, V: unamortised design
    fraction, K: chip-capital share of lifetime serving cost."""
    return w * k * (1.0 - s) * d_m * b + v * nre


def breakeven_fraction(s: float, d_m: float, b: float, stranded: float) -> float:
    """Fraction f of the model's lifetime demand that must be served before de-whitelisting for the MSIC to have been the
    cheaper way to serve it even after the stranded capital: f*(1-S)*D*B + stranded <= f*D*B  =>  f >= stranded / (S*D*B)."""
    return stranded / (s * d_m * b)


def replacement_cost_fraction(s: float, designs: int, nre: float, b: float) -> float:
    """Cumulative resource cost, as a fraction of B, if demand shifts so far that the whole initial MSIC fleet is written off
    and replaced (section 7.3.3): two fleets at (1 - S) of B each plus two rounds of design fees."""
    return 2.0 * (1.0 - s) + 2.0 * designs * nre / b


def total_variation(p: dict, q: dict) -> float:
    """Total variation distance between two demand distributions over the models both contain, renormalised."""
    keys = sorted(set(p) & set(q))
    sp, sq = sum(p[k] for k in keys), sum(q[k] for k in keys)
    return 0.5 * sum(abs(p[k] / sp - q[k] / sq) for k in keys)


def zipf_demand(n: int, a: float = 1.0) -> list:
    """Synthetic demand: share of model i proportional to i^-a. For tests and demonstrations only."""
    return normalise([i ** -a for i in range(1, n + 1)])


def load_demand(path: str, model_col: str, token_col: str) -> dict:
    """Read a CSV of per-model token counts (for example a week of OpenRouter traffic) into {model: tokens}."""
    out = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                out[row[model_col]] = out.get(row[model_col], 0.0) + float(row[token_col])
            except (ValueError, KeyError):
                continue
    return out
