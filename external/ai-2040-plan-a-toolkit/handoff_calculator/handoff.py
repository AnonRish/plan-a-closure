"""
handoff.py

A faithful reimplementation of the "should we hand off or delay" calculator
embedded in AI 2040's Capability Scaling Strategy supplement
(https://ai-2040.com/supplements/capability-scaling-strategy), re-fetched
directly for this rather than worked from memory of research many turns
earlier in this conversation -- for a fidelity task specifically, that
distinction matters more than anywhere else in this set.

THE FORMULA, verbatim from the source:

    u_handoff_minus_u_delay = d_prob * a_prob * d_loss - a_change

Where, exactly as defined on the page:
    d_prob    -- Deal decline probability: yearly chance the deal dissolves
                 or is substantially impaired without official dissolution.
    a_prob    -- Alignment probability: current p(alignment). Deal
                 dissolution/impairment is more costly the more likely
                 alignment is.
    d_loss    -- Deal decline badness: % of the future's value lost if the
                 deal dissolves or is impaired.
    a_change  -- Alignment gain: extra p(alignment) bought per year of delay.

Positive result -> hand off now (the benefit of avoiding deal-decline risk
by handing off exceeds the alignment-probability gained by waiting a year).
Negative -> delay (the reverse). The page is explicit that this "only weighs
the single most important factor on each side" -- not a complete decision
procedure, exactly as disclosed there and here.
"""

from dataclasses import dataclass

# ---- exact presets from the published page ----

ALIGNMENT_SCENARIOS = {
    "High confidence alignment solution": {"a_prob": 0.995, "a_change": 0.001},
    "Alignment probably solved": {"a_prob": 0.95, "a_change": 0.01},
    "Alignment likely solved": {"a_prob": 0.80, "a_change": 0.03},
    "Alignment clearly unsolved": {"a_prob": 0.10, "a_change": 0.02},
}

DEAL_DECLINE_SCENARIOS = {
    "Low risk": {"d_prob": 0.005, "d_loss": 0.10},
    "Medium risk": {"d_prob": 0.03, "d_loss": 0.20},
    "High risk": {"d_prob": 0.10, "d_loss": 0.35},
}

DEFAULTS = {"d_prob": 0.03, "a_prob": 0.995, "d_loss": 0.20, "a_change": 0.001}  # the page's own defaults


@dataclass
class HandoffResult:
    d_prob: float
    a_prob: float
    d_loss: float
    a_change: float
    benefit_of_handoff: float   # d_prob * a_prob * d_loss
    cost_of_handoff: float      # a_change
    net: float                  # benefit - cost
    recommendation: str         # "Hand off" or "Delay"


def evaluate(d_prob, a_prob, d_loss, a_change) -> HandoffResult:
    benefit = d_prob * a_prob * d_loss
    cost = a_change
    net = benefit - cost
    return HandoffResult(
        d_prob=d_prob, a_prob=a_prob, d_loss=d_loss, a_change=a_change,
        benefit_of_handoff=benefit, cost_of_handoff=cost, net=net,
        recommendation="Hand off" if net > 0 else "Delay",
    )


def evaluate_scenario(alignment_scenario: str, deal_decline_scenario: str) -> HandoffResult:
    a = ALIGNMENT_SCENARIOS[alignment_scenario]
    d = DEAL_DECLINE_SCENARIOS[deal_decline_scenario]
    return evaluate(d["d_prob"], a["a_prob"], d["d_loss"], a["a_change"])


def full_table():
    """Reproduces the published 4x3 grid exactly."""
    rows = {}
    for a_name in ALIGNMENT_SCENARIOS:
        rows[a_name] = {}
        for d_name in DEAL_DECLINE_SCENARIOS:
            rows[a_name][d_name] = evaluate_scenario(a_name, d_name)
    return rows


# ---- extension: not on the original page, clearly marked as such ----

def breakeven_d_prob(a_prob, d_loss, a_change):
    """Not part of the original calculator. Solves the same formula for the
    d_prob at which the recommendation flips: d_prob*a_prob*d_loss = a_change
    => d_prob = a_change / (a_prob * d_loss). Useful as "how bad would deal-
    decline risk have to get, holding everything else fixed, before this
    flips to hand off" -- a natural question the point-estimate calculator
    doesn't answer directly."""
    if a_prob * d_loss == 0:
        return float("inf")
    return a_change / (a_prob * d_loss)
