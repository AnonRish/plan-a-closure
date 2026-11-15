"""FLI's Draft Articles on the Safe Development and Diffusion of Artificial Intelligence as rules a computer can apply.

Source: Future of Life Institute with the Centre for International Governance Innovation, *Draft Articles on the Safe
Development and Diffusion of Artificial Intelligence* (web version 2, 18 June 2026, global-governance.ai). Article
numbers are the draft's. What is here: the Article 2 test for a global catastrophic risk; when enforcement may start
and must be lifted (Art. 6); certificates of compliance, evaluator licences, challenges and provisional suspension
(Art. 7) with the benefit-sharing tax as a condition of certification (Art. 10); the Conference's voting rules, with
contribution-weighted voting for some matters (Art. 12); amendments and the rule that the Agency may not recommend
removing an Annex A item (Art. 15); the Agency's funding (Arts. 13(10), 14(6)(c)); and the chip registry of Annex
B.1(1)(c). Chip authorization (Annexes C.1 and C.2) is chipauth.py; deadlines are obligations.py; location by network
delay (B.1(1)(d)) is geoloc.py; sampled inspections (B.1(1)(e)) are inspection.py; the digital perimeter's traffic
check (B.2) is traffic.py; commitments (B.2) are evidence.commit.

The draft sets no compute threshold. Its trigger is a list of uses, risks and capabilities (Annex A), and its
commentary to Article 3 explains that it avoids continuous measures such as operation counts; whether a system has an
Annex A capability is an evaluation's finding, which, as Barnett and Thiergart argue, can show a capability but not
its absence.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from fractions import Fraction

import numpy as np

from .obligations import add, ts

GCR_PEOPLE = 50                         # Art. 2: death of, or serious injury to, more than 50 people ...
GCR_DAMAGE_USD = 1_000_000_000          # ... or more than one billion dollars of damage to, or loss of, property
CERTIFICATE_MONTHS = 6                  # Art. 7(4)
CHALLENGE_DECISION_DAYS = 7             # Art. 7(10): "within a week"
MIN_AI_GAINS_TAX = 0.05                 # Art. 10(4)
AGENCY_SHARE = 0.01                     # Arts. 13(10), 14(6)(c)
DG_TERM_YEARS, DG_MAX_TERMS = 3, 2      # Art. 13(3): three years, renewable once
AMENDMENT_SHARE = Fraction(2, 3)        # Art. 15(2): two thirds of the States Parties
EXTRAORDINARY_SHARE = Fraction(1, 3)    # Art. 12(4): at least one third of the States Parties
WEIGHTED_MATTERS = ("director_general", "agency_rules_of_procedure", "verification_or_enforcement_mechanism")
LICENCE_CONDITIONS = {                  # Art. 7(7)(a)-(d); (e) is whatever else the Agency asks for
    "expertise": "evidence of relevant expertise (a)",
    "conflicts_of_interest": "a declaration of conflicts of interest (b)",
    "background_check": "a background check of evaluation staff that at least addresses information security (c)",
    "continuous_monitoring": "submission to the Agency's continuous monitoring of the evaluator's capacity (d)",
}
ANNEX_A = {
    "1": "risks from chemical, biological, radiological and nuclear attacks or accidents",
    "2": "uncontrolled cyber-offensive agents capable of mass disruption of critical infrastructure",
    "3": "loss of control",
    "3(a)": "alignment faking",
    "3(b)": "autonomous recursive self-improvement",
    "3(c)": "self-replication",
    "3(d)": "non-interpretability of chain-of-thought",
    "3(e)": "autonomous sabotage",
    "4": "highly effective epistemic manipulation of political, electoral or civic decisions",
}


# ---- Article 2 ----------------------------------------------------------------------------------------------------
def is_global_catastrophic(people_killed_or_seriously_injured: int, damage_usd: float = 0.0,
                           single_incident: bool = True) -> dict:
    """Art. 2: a foreseeable and material risk that an AI system materially contributes to the death of, or serious
    injury to, more than 50 people, or to more than USD 1,000,000,000 of damage to or loss of property, in a single
    incident (adapted from California's SB 53). This tests an incident's scale; whether a risk of it was foreseeable
    and material is a judgement."""
    why = []
    if int(people_killed_or_seriously_injured) > GCR_PEOPLE:
        why.append(f"{int(people_killed_or_seriously_injured)} people killed or seriously injured: more than 50")
    if float(damage_usd) > GCR_DAMAGE_USD:
        why.append(f"USD {float(damage_usd):,.0f} of damage: more than one billion")
    if why and not single_incident:
        return {"scale_met": False, "reasons": why + ["but not in a single incident"]}
    return {"scale_met": bool(why), "reasons": why}


# ---- Article 6 ----------------------------------------------------------------------------------------------------
def enforcement_may_start(investigated: bool, suspected_global_catastrophic_risk: bool) -> dict:
    """Art. 6(1)-(2): the Agency investigates, in consultation with the provider, before enforcement, unless the
    suspected breach poses a global catastrophic risk, when it may enforce first."""
    if investigated:
        return {"may_start": True, "basis": "after an objective investigation (Art. 6(1))"}
    if suspected_global_catastrophic_risk:
        return {"may_start": True, "basis": "before investigation: a suspected global catastrophic risk (Art. 6(2))"}
    return {"may_start": False, "basis": "investigate first (Art. 6(1))"}


def enforcement_must_lift(provider_showed_compliance: bool, agency_showed_continued_breach: bool) -> bool:
    """Art. 6(3): once the provider shows compliance, the burden reverts to the Agency; if it cannot show continued
    breach, it lifts enforcement (under Annex C, by authorizing the chips again)."""
    return bool(provider_showed_compliance) and not bool(agency_showed_continued_breach)


# ---- Articles 7 and 10: certificates, licences, challenges, the tax -------------------------------------------------
def licence_problems(application: dict, extra_required=()) -> list:
    """Art. 7(7): what an evaluator's application must contain; extra_required is (e), the Agency's further asks."""
    out = [f"missing: {v}" for k, v in LICENCE_CONDITIONS.items() if not application.get(k)]
    out += [f"missing: {x} (asked for by the Agency, (e))" for x in extra_required if not application.get(x)]
    return out


def tax_compliant(rate: float) -> bool:
    """Art. 10(4): States Parties tax AI gains at five percent or more."""
    return float(rate) >= MIN_AI_GAINS_TAX


def agency_funding(contributions_total: float) -> float:
    """Arts. 13(10) and 14(6)(c): the Agency receives one percent of the contributions."""
    return AGENCY_SHARE * float(contributions_total)


@dataclass
class Certificates:
    """Certificates of compliance (Art. 7(4)-(5), (10)-(11)) and their conditions.

    A provider may develop, test, produce, manufacture or commercialise advanced AI systems only with a valid
    certificate: issued or renewed by a licensed evaluator within the last six months, not suspended, and not held by
    a provider that evades the benefit-sharing tax (Art. 10(5)). Only States Parties may challenge a certificate or a
    licence; the Dispute Settlement Panel accepts or rejects a challenge within a week and may suspend the certificate
    or licence until the matter is resolved if it finds a reasonable likelihood that the challenge will succeed. The
    draft does not say who decides the merits once a challenge is accepted; `resolve` records the outcome as given."""
    licensed: dict = field(default_factory=dict)          # evaluator -> licensed at
    certs: dict = field(default_factory=dict)             # provider -> {"evaluator", "at"}
    suspended: dict = field(default_factory=dict)         # ("certificate"|"licence", name) -> challenge id
    tax_evaders: set = field(default_factory=set)
    challenges: list = field(default_factory=list)

    def license(self, evaluator: str, application: dict, at, extra_required=()) -> list:
        problems = licence_problems(application, extra_required)
        if not problems:
            self.licensed[evaluator] = ts(at)
        return problems

    def evader(self, provider: str):
        self.tax_evaders.add(provider)

    def certify(self, provider: str, evaluator: str, at) -> list:
        """Issue or renew. Refused for an unlicensed or suspended evaluator and for a tax evader."""
        problems = []
        if evaluator not in self.licensed:
            problems.append(f"{evaluator} holds no evaluator licence (Art. 7(7))")
        if ("licence", evaluator) in self.suspended:
            problems.append(f"{evaluator}'s licence is suspended (Art. 7(11))")
        if provider in self.tax_evaders:
            problems.append(f"{provider} evades the AI gains tax: not eligible (Art. 10(5))")
        if not problems:
            self.certs[provider] = {"evaluator": evaluator, "at": ts(at)}
        return problems

    def valid_until(self, provider: str):
        c = self.certs.get(provider)
        return None if c is None else add(c["at"], CERTIFICATE_MONTHS, "months")

    def may_operate(self, provider: str, now) -> dict:
        """Art. 7(5)."""
        now, why = ts(now), []
        c = self.certs.get(provider)
        if c is None:
            why.append("no certificate of compliance")
        elif now > self.valid_until(provider):
            why.append("the certificate was not renewed within six months (Art. 7(4))")
        if ("certificate", provider) in self.suspended:
            why.append("the certificate is suspended pending a challenge (Art. 7(11))")
        if provider in self.tax_evaders:
            why.append("evades the AI gains tax (Art. 10(5))")
        return {"may_operate": not why, "reasons": why}

    def challenge(self, challenger: str, challenger_is_state_party: bool, kind: str, target: str, filed_at) -> dict:
        """Art. 7(10): a State Party challenges a certificate decision or an evaluator licence decision."""
        if kind not in ("certificate", "licence"):
            raise ValueError("kind is 'certificate' or 'licence'")
        if not challenger_is_state_party:
            return {"filed": False, "problems": ["only States Parties may challenge (Art. 7(10))"]}
        c = {"id": len(self.challenges) + 1, "by": challenger, "kind": kind, "target": target, "filed": ts(filed_at),
             "decided": None, "accepted": None, "resolved": None}
        self.challenges.append(c)
        return {"filed": True, "id": c["id"], "decide_by": add(c["filed"], CHALLENGE_DECISION_DAYS, "days")}

    def _get(self, cid: int) -> dict:
        return self.challenges[int(cid) - 1]

    def decide(self, cid: int, accept: bool, at, reasonable_likelihood: bool = False) -> dict:
        """The Panel accepts or rejects (within a week), and may suspend provisionally (Art. 7(11))."""
        c, at = self._get(cid), ts(at)
        c["decided"], c["accepted"] = at, bool(accept)
        on_time = at <= add(c["filed"], CHALLENGE_DECISION_DAYS, "days")
        if accept and reasonable_likelihood:
            self.suspended[(c["kind"], c["target"])] = c["id"]
        return {"on_time": on_time, "suspended": (c["kind"], c["target"]) in self.suspended}

    def resolve(self, cid: int, upheld: bool, at) -> dict:
        """The outcome on the merits. Upheld: a certificate is withdrawn or a licence revoked; either way a
        provisional suspension ends."""
        c = self._get(cid)
        c["resolved"] = ts(at)
        self.suspended.pop((c["kind"], c["target"]), None)
        if upheld:
            (self.certs if c["kind"] == "certificate" else self.licensed).pop(c["target"], None)
        return {"upheld": bool(upheld)}

    def overdue(self, now) -> list:
        now = ts(now)
        return [c["id"] for c in self.challenges
                if c["decided"] is None and now > add(c["filed"], CHALLENGE_DECISION_DAYS, "days")]


# ---- Article 12: the Conference ---------------------------------------------------------------------------------------
def extraordinary_session(supporters: int, n_parties: int) -> bool:
    """Art. 12(4): a written request supported by at least one third of the States Parties."""
    return Fraction(int(supporters)) >= EXTRAORDINARY_SHARE * int(n_parties)


def conference_decision(matter: str, yes, no, contributions: dict = None, n_parties: int = None,
                        base: str = "cast") -> dict:
    """Art. 12(7): decisions by simple majority, one vote per State, except the Director-General's appointment, the
    Agency's rules of procedure and the approval or amendment of verification or enforcement mechanisms, which are
    weighted by contributions to the Fund. `yes` and `no` are lists of States. The draft does not say whether a
    majority is of the votes cast (base="cast") or of all States Parties (base="parties", which needs n_parties or,
    for weighted matters, everyone's contributions)."""
    yes, no = list(yes), list(no)
    if set(yes) & set(no):
        raise ValueError("a State voted both ways")
    weighted = matter in WEIGHTED_MATTERS
    if weighted:
        if contributions is None:
            raise ValueError(f"{matter} is decided by contribution-weighted vote: give contributions")
        wy, wn = sum(contributions.get(s, 0.0) for s in yes), sum(contributions.get(s, 0.0) for s in no)
        total = (wy + wn) if base == "cast" else sum(contributions.values())
        passed = wy > total / 2.0
        return {"matter": matter, "weighted": True, "yes_weight": wy, "no_weight": wn, "base_weight": total,
                "passed": passed}
    total = len(yes) + len(no) if base == "cast" else int(n_parties)
    return {"matter": matter, "weighted": False, "yes": len(yes), "no": len(no), "base": total,
            "passed": len(yes) * 2 > total}


def fewest_to_decide(weights: dict) -> list:
    """The fewest States whose weights are more than half of the total: the largest first is optimal for a simple
    majority of weights."""
    total, acc, out = sum(weights.values()), 0.0, []
    for k, v in sorted(weights.items(), key=lambda kv: -kv[1]):
        out.append(k)
        acc += v
        if acc > total / 2.0:
            return out
    return out


def weighted_power(weights: dict, permutations: int = 20000, seed: int = 0) -> dict:
    """Monte Carlo Shapley-Shubik power in a majority-of-weights game: over random orders, the share in which a
    State's joining first takes the yes weight past half. {State: (index, standard error)}."""
    names = sorted(weights)
    w = np.array([float(weights[n]) for n in names])
    half = w.sum() / 2.0
    rng = np.random.default_rng(seed)
    counts, done = np.zeros(len(names)), 0
    while done < permutations:
        m = min(2000, permutations - done)
        order = np.argsort(rng.random((m, len(names))), axis=1)
        piv = order[np.arange(m), (np.cumsum(w[order], axis=1) > half).argmax(axis=1)]
        np.add.at(counts, piv, 1.0)
        done += m
    p = counts / permutations
    return {n: (float(p[i]), float(math.sqrt(p[i] * (1 - p[i]) / permutations))) for i, n in enumerate(names)}


def gdp_stand_in(members=None) -> dict:
    """Contributions in proportion to GDP (World Bank, 2023, current US$; the table bundled for coalition.py) for the
    given members, or for every economy in the table: a stand-in, since the draft ties contributions to a tax on AI
    gains that nobody can measure yet. EU members count separately: the EU is not a State."""
    from . import coalition as C
    countries, _ = C.load()
    keep = set(members) if members else set(countries)
    return {c.iso3: c.gdp_usd for c in countries.values() if c.iso3 in keep}


# ---- Article 15: amendments and the annexes ---------------------------------------------------------------------------
def amendment_adopted(yes: int, n_parties: int) -> bool:
    """Art. 15(2): adopted by a majority of two thirds of the States Parties (all of them, not those voting)."""
    return Fraction(int(yes)) >= AMENDMENT_SHARE * int(n_parties)


def annex_a_change_problems(current, proposed, proposer: str, yes: int = 0, n_parties: int = 0) -> list:
    """Art. 15(3): the Agency may recommend annex amendments each year but may not recommend removing an Annex A item;
    a State Party's proposal (15(1)) can remove one only if two thirds of the States Parties adopt it (15(2))."""
    removed = sorted(set(current) - set(proposed))
    out = []
    if proposer == "agency" and removed:
        out.append(f"the Agency may not recommend removing Annex A items: {', '.join(removed)} (Art. 15(3))")
    if proposer != "agency" and not amendment_adopted(yes, n_parties):
        out.append(f"{yes} of {n_parties} States Parties: an amendment needs two thirds (Art. 15(2))")
    return out


# ---- Annex B.1(1)(c): the chip registry ------------------------------------------------------------------------------
def registry_problems(chips: list) -> list:
    """Annex B.1(1)(c): a chip registry with a unique ID and the declared location of each chip."""
    out, seen = [], set()
    for i, c in enumerate(chips):
        cid = c.get("id")
        if not cid:
            out.append(f"chip {i}: no unique ID")
        elif cid in seen:
            out.append(f"chip {i}: ID {cid} is not unique")
        seen.add(cid)
        if not c.get("location"):
            out.append(f"chip {i}: no declared location")
    return out
