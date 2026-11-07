import uuid
from datetime import datetime, timedelta, timezone

from frontier_verify.evidence.models import (
    Evidence,
    HardwareEvidence,
    Maturity,
    ModelIdentity,
    RuntimeIdentity,
)
from frontier_verify.policies.evaluator import evaluate
from frontier_verify.policies.models import Policy


def _evidence(mock: bool = True, created_at=None) -> Evidence:
    return Evidence(
        evidence_id=str(uuid.uuid4()),
        created_at=created_at or datetime.now(timezone.utc),
        model_identity=ModelIdentity(model_digest="d1"),
        runtime_identity=RuntimeIdentity(serving_engine="e1"),
        hardware_evidence=HardwareEvidence(
            provider_name="mock" if mock else "nvidia",
            maturity=Maturity.MOCK if mock else Maturity.EXPERIMENTAL,
            mock=mock,
        ),
    )


def test_mock_evidence_rejected_when_policy_disallows_mock():
    policy = Policy(policy_id="p", version="0.1.0", allow_mock_hardware=False)
    result = evaluate(_evidence(mock=True), policy)
    assert result.passed is False
    assert any("mock" in reason.lower() for reason in result.reasons)
    assert result.assurance_level_achieved == "L0"


def test_mock_evidence_accepted_when_policy_allows_mock():
    policy = Policy(policy_id="p", version="0.1.0", allow_mock_hardware=True)
    result = evaluate(_evidence(mock=True), policy)
    assert result.passed is True
    assert result.assurance_level_achieved == "L1"


def test_stale_evidence_rejected():
    policy = Policy(policy_id="p", version="0.1.0", allow_mock_hardware=True, max_evidence_age_seconds=1)
    stale = datetime.now(timezone.utc) - timedelta(seconds=10)
    result = evaluate(_evidence(mock=True, created_at=stale), policy)
    assert result.passed is False


def test_fresh_evidence_within_window_accepted():
    policy = Policy(policy_id="p", version="0.1.0", allow_mock_hardware=True, max_evidence_age_seconds=3600)
    fresh = datetime.now(timezone.utc) - timedelta(seconds=5)
    result = evaluate(_evidence(mock=True, created_at=fresh), policy)
    assert result.passed is True
