"""THIS PROVIDER PROVES NOTHING ABOUT REAL HARDWARE.

MockAttestationProvider exists so the rest of the system -- evidence
bundling, policy evaluation, receipts, the API, the CLI -- can be built and
tested end to end before real NVIDIA GPU/NVSwitch attestation (Phase 2) is
wired up. It fabricates HardwareEvidence with mock=True and
maturity=Maturity.MOCK on every call.

frontier_verify.policies.evaluator.evaluate() reads that `mock` flag and
rejects it outright unless the policy explicitly sets
allow_mock_hardware=True. No production policy should ever set that to
True; the default is False. See tests/unit/test_policy_evaluator.py for the
enforcement test, not just the docstring promise.
"""
from __future__ import annotations

import uuid

from frontier_verify.attestations.base import AttestationProvider
from frontier_verify.evidence.models import HardwareEvidence, Maturity


class MockAttestationProvider(AttestationProvider):
    provider_name = "mock"

    def get_platform_evidence(self) -> HardwareEvidence:
        return HardwareEvidence(
            provider_name=self.provider_name,
            maturity=Maturity.MOCK,
            mock=True,
            claims={
                "gpu": "SIMULATED-GPU-0",
                "note": "synthetic evidence -- not backed by any hardware root of trust",
            },
            raw_evidence_digest=uuid.uuid4().hex,
        )
