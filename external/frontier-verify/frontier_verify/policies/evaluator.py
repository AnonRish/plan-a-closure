"""Policy evaluation.

This is the one place in Phase 1 that decides pass/fail, so it's the one
place where overclaiming would matter most. It currently checks exactly two
things -- mock-hardware rejection and evidence freshness -- and says so.
Everything AI-2040 actually cares about (was the hardware real, was the
workload the one that was claimed, was anything hidden) is NOT checked here
yet. See docs/assurance-model.md for what assurance level each outcome is
allowed to claim.
"""
from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel

from frontier_verify.evidence.models import Evidence
from frontier_verify.policies.models import Policy


class PolicyResult(BaseModel):
    passed: bool
    reasons: list[str]
    assurance_level_achieved: str


def evaluate(evidence: Evidence, policy: Policy) -> PolicyResult:
    reasons: list[str] = []
    passed = True

    if evidence.hardware_evidence.mock and not policy.allow_mock_hardware:
        passed = False
        reasons.append(
            "hardware_evidence.mock=True but policy.allow_mock_hardware=False: "
            "mock evidence proves nothing about real hardware and is rejected "
            "under this policy"
        )

    age_seconds = (datetime.now(timezone.utc) - evidence.created_at).total_seconds()
    if age_seconds > policy.max_evidence_age_seconds:
        passed = False
        reasons.append(
            f"evidence age {age_seconds:.0f}s exceeds policy.max_evidence_age_seconds="
            f"{policy.max_evidence_age_seconds}s"
        )

    if not passed:
        assurance = "L0"
    else:
        # Phase 1 has no working non-mock AttestationProvider --
        # NvidiaAttestationProvider currently raises NotImplementedError --
        # and even where hardware_evidence.mock is False, this evaluator
        # does not yet validate a real hardware signature chain. So L1
        # (self-reported provenance + a tamper-evident signed receipt) is
        # the honest ceiling for anything Phase 1 can issue, regardless of
        # the mock flag. Raising this to L2 is Phase 2's job, gated on a
        # real AttestationProvider existing at all. See
        # docs/assurance-model.md.
        assurance = "L1"

    if passed:
        reasons.append(
            "evidence satisfies the two checks Phase 1 actually performs "
            "(hardware-mock policy, freshness); see docs/threat-model.md "
            "for everything this does NOT check"
        )

    return PolicyResult(passed=passed, reasons=reasons, assurance_level_achieved=assurance)
