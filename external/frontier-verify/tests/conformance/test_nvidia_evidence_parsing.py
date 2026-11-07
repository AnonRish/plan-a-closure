"""Tests the ONE real capability frontier_verify.attestations.nvidia_provider
has today: parsing NVAT-shaped evidence JSON into the portable
HardwareEvidence schema. Does NOT test (because nothing here can) real
hardware attestation, certificate chain validation, or NRAS remote
verification -- see docs/hardware/nvidia-attestation.md for what those
would require.
"""
from __future__ import annotations

import pytest

from frontier_verify.attestations.nvidia_provider import (
    NvidiaAttestationProvider,
    load_synthetic_fixture,
)
from frontier_verify.evidence.models import Maturity


def test_get_platform_evidence_is_honestly_not_implemented():
    provider = NvidiaAttestationProvider()
    with pytest.raises(NotImplementedError):
        provider.get_platform_evidence()


def test_parses_synthetic_fixture_shape_correctly():
    raw = load_synthetic_fixture()
    hw = NvidiaAttestationProvider.parse_nvat_evidence(raw, mock=True)
    assert hw.provider_name == "nvidia"
    assert hw.mock is True
    assert hw.maturity == Maturity.MOCK
    assert hw.claims["arch"] == "HOPPER"
    assert hw.claims["driver_version"] == "575.03"
    assert hw.claims["result_code"] == 0


def test_parser_rejects_missing_evidences_list():
    with pytest.raises(ValueError, match="evidences"):
        NvidiaAttestationProvider.parse_nvat_evidence({"result_code": 0}, mock=True)


def test_mock_true_produces_mock_maturity_mock_false_produces_experimental_not_validated():
    """Even parsing a REAL nvattest document (mock=False) only earns
    EXPERIMENTAL, never VALIDATED or PRODUCTION_READY -- this parser does
    not check the certificate chain, so it cannot honestly claim more.
    See the maturity vocabulary rules in frontier_verify.evidence.models."""
    raw = load_synthetic_fixture()
    hw = NvidiaAttestationProvider.parse_nvat_evidence(raw, mock=False)
    assert hw.maturity == Maturity.EXPERIMENTAL
    assert hw.mock is False


def test_synthetic_fixture_is_clearly_labeled_as_fabricated():
    """Guards against someone quietly removing the warning fields from
    the fixture file later."""
    raw = load_synthetic_fixture()
    assert raw.get("_FABRICATED") is True
    assert "SYNTHETIC" in raw.get("_WARNING", "")
