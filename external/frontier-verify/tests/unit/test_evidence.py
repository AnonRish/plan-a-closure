from datetime import datetime, timezone

from frontier_verify.evidence.models import (
    Evidence,
    HardwareEvidence,
    Maturity,
    ModelIdentity,
    RuntimeIdentity,
)

FIXED_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _hw() -> HardwareEvidence:
    return HardwareEvidence(
        provider_name="mock",
        maturity=Maturity.MOCK,
        mock=True,
        claims={"gpu": "SIMULATED-GPU-0"},
        raw_evidence_digest="fixed-digest",
        collected_at=FIXED_TIME,
    )


def _evidence(model_digest: str = "d1") -> Evidence:
    return Evidence(
        evidence_id="fixed-id",
        created_at=FIXED_TIME,
        model_identity=ModelIdentity(model_digest=model_digest),
        runtime_identity=RuntimeIdentity(serving_engine="e"),
        hardware_evidence=_hw(),
    )


def test_digest_changes_with_model_identity():
    assert _evidence("d1").digest() != _evidence("d2").digest()


def test_digest_stable_for_identical_evidence():
    # Both built via fully-deterministic construction (fixed id, fixed
    # timestamp, fixed hardware evidence) -- no default_factory randomness
    # should leak in here.
    assert _evidence("d1").digest() == _evidence("d1").digest()


def test_mock_flag_is_preserved_through_the_bundle():
    ev = _evidence()
    assert ev.hardware_evidence.mock is True
    assert ev.hardware_evidence.maturity == Maturity.MOCK
