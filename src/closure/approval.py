"""R&D workload approval (Plan A 'Total Research Transparency'): white/black/gold lists, compute caps and the
suggested titration progression. Policy engine only: it checks a manifest, it does not judge safety cases."""
from __future__ import annotations

from dataclasses import dataclass, field

STAGES = ("caps", "ad_hoc", "human_interpretable", "safety_case")


@dataclass
class Manifest:
    workload_id: str
    code_sha256: str
    data_sha256: tuple = ()
    techniques: frozenset = frozenset()
    flops: float = 0.0
    domain: str = "software"
    reviewers: int = 0
    safety_case_sha256: str = None


@dataclass
class Policy:
    stage: str = "caps"
    flops_cap: float = 1e22
    code_whitelist: frozenset = frozenset()
    data_whitelist: frozenset = frozenset()
    technique_blacklist: frozenset = frozenset()
    gold: dict = field(default_factory=dict)          # domain -> techniques required on every workload
    min_reviewers: int = 2
    accepted_safety_cases: frozenset = frozenset()


@dataclass
class Decision:
    approved: bool
    reasons: list


def approve(m: Manifest, p: Policy) -> Decision:
    s, why = STAGES.index(p.stage), []
    if m.flops > p.flops_cap:
        why.append(f"compute {m.flops:.3g} FLOP exceeds cap {p.flops_cap:.3g}")
    bad = sorted(set(m.techniques) & set(p.technique_blacklist))
    if bad:
        why.append(f"blacklisted techniques: {bad}")
    miss = sorted(set(p.gold.get(m.domain, ())) - set(m.techniques))
    if miss:
        why.append(f"required (gold) techniques missing: {miss}")
    if s >= 1:
        if m.code_sha256 not in p.code_whitelist:
            why.append("code hash not on the whitelist")
        off = [d for d in m.data_sha256 if d not in p.data_whitelist]
        if off:
            why.append(f"{len(off)} data hash(es) not on the whitelist")
    if s >= 2 and m.reviewers < p.min_reviewers:
        why.append(f"needs {p.min_reviewers} human reviewers, has {m.reviewers}")
    if s >= 3 and m.safety_case_sha256 not in p.accepted_safety_cases:
        why.append("no accepted safety case")
    return Decision(not why, why)


def stage_for_year(year: int) -> str:
    """Suggested progression read off the plan's figure (approximate years): caps ~2030, safety-case ~2035."""
    return "caps" if year <= 2030 else "ad_hoc" if year <= 2033 else "human_interpretable" if year <= 2034 else "safety_case"


def record(chain, m: Manifest, d: Decision) -> str:
    return chain.append({"phase": "approval", "workload_id": m.workload_id, "code_sha256": m.code_sha256,
                         "approved": d.approved, "reasons": d.reasons})
