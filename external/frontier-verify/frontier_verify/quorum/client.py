"""QuorumClient: submits the same evidence to N independent verifier
instances and analyzes whether they agree.

MATURITY: EXPERIMENTAL / RESEARCH. Real, tested against genuinely
separate server processes with independent keys and storage (see
tests/integration/test_quorum.py) -- not simulated in-process. What this
does NOT test, and cannot: whether the verifiers' shared SOURCE CODE
contains a bug or design flaw that would affect every instance
identically. Running three copies of the same program is not the same
experiment as running three independently-designed programs -- see
docs/research/verifier-trust.md, which this module's test suite exists to
give real (not hypothetical) evidence for.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from frontier_verify.evidence.models import Evidence
from frontier_verify.policies.models import Policy
from frontier_verify.receipts.models import Receipt
from frontier_verify.sdk.client import VerifierClient


@dataclass
class QuorumMemberResult:
    endpoint: str
    passed: bool | None
    assurance_level: str | None
    receipt: Receipt | None
    error: str | None = None


@dataclass
class QuorumReport:
    results: list[QuorumMemberResult]

    @property
    def all_agree(self) -> bool:
        """True iff every member that responded successfully reached the
        SAME (passed, assurance_level) decision. A member that errored
        entirely is excluded here -- see any_errors, a different finding
        (member unreachable, not member disagreeing)."""
        successful = [r for r in self.results if r.error is None]
        if not successful:
            return False
        first_vote = (successful[0].passed, successful[0].assurance_level)
        return all((r.passed, r.assurance_level) == first_vote for r in successful)

    @property
    def any_errors(self) -> bool:
        return any(r.error is not None for r in self.results)

    @property
    def dissenting_members(self) -> list[QuorumMemberResult]:
        """Members whose decision differs from the majority vote among
        members that responded. Empty when all_agree is True. Does NOT
        determine which side is "correct" -- a quorum can tell you SOMEONE
        disagrees, not WHO is honest. See docs/research/verifier-trust.md."""
        successful = [r for r in self.results if r.error is None]
        if not successful:
            return []
        votes = Counter((r.passed, r.assurance_level) for r in successful)
        majority_vote, _ = votes.most_common(1)[0]
        return [r for r in successful if (r.passed, r.assurance_level) != majority_vote]


class QuorumClient:
    def __init__(self, endpoints: list[str], api_key: str):
        self.clients = [VerifierClient(endpoint=ep) for ep in endpoints]
        for c in self.clients:
            c._http.headers.update({"X-Api-Key": api_key})

    def submit_and_verify(self, evidence: Evidence, policy: Policy) -> QuorumReport:
        results: list[QuorumMemberResult] = []
        for client in self.clients:
            try:
                client.submit_evidence(evidence)
                client.validate_policy(policy)
                result = client.verify_inference(evidence.evidence_id, policy.policy_id)
                receipt = Receipt.model_validate(result["receipt"]) if result.get("receipt") else None
                results.append(
                    QuorumMemberResult(
                        endpoint=client.endpoint,
                        passed=result["passed"],
                        assurance_level=result["assurance_level_achieved"],
                        receipt=receipt,
                    )
                )
            except Exception as e:  # noqa: BLE001 -- deliberate: one quorum member
                # failing (network error, member down) must not crash the whole
                # quorum check -- it's recorded as this member's own finding.
                results.append(
                    QuorumMemberResult(
                        endpoint=client.endpoint, passed=None, assurance_level=None, receipt=None, error=str(e)
                    )
                )
        return QuorumReport(results=results)

    def close(self) -> None:
        for c in self.clients:
            c.close()
