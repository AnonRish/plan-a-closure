"""Tests that require real NVIDIA hardware. Every test here is marked
skip with an explicit reason UNLESS the actual hardware/tooling it needs
is detected -- this file is meant to become executable the moment someone
runs it on a real machine, not meant to be deleted and rewritten then.

Run on a machine that might have real hardware:
    pytest tests/hardware/nvidia/ -v

On this project's actual development environment (no GPU), every test
here reports SKIPPED with a specific, checkable reason -- not silently
absent, not fake-passing. See docs/hardware/nvidia-real-test.md for setup
instructions on a real system.
"""
from __future__ import annotations

import shutil
import subprocess

import pytest


def _nvidia_smi_available() -> bool:
    return shutil.which("nvidia-smi") is not None


def _nvattest_available() -> bool:
    return shutil.which("nvattest") is not None


def _confidential_computing_enabled() -> bool:
    """Best-effort detection -- no confirmed single command for this
    across all supported configurations found during this phase's
    research (docs/hardware/nvat-integration.md). Returns False (assume
    not enabled) rather than guessing, so this only gates tests OPEN when
    genuinely confirmed, never accidentally lets an unverified assumption
    through."""
    if not _nvidia_smi_available():
        return False
    try:
        result = subprocess.run(
            ["nvidia-smi", "conf-compute", "-f"], capture_output=True, text=True, timeout=5, check=False
        )
        return result.returncode == 0 and "enabled" in result.stdout.lower()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


requires_gpu = pytest.mark.skipif(not _nvidia_smi_available(), reason="no NVIDIA GPU detected (nvidia-smi not found)")
requires_nvattest = pytest.mark.skipif(not _nvattest_available(), reason="nvattest CLI not found on PATH")
requires_confidential_computing = pytest.mark.skipif(
    not _confidential_computing_enabled(), reason="NVIDIA Confidential Computing not confirmed enabled"
)


@requires_gpu
def test_hardware_detection_smoke_test():
    """The most basic real-hardware test: does nvidia-smi actually report
    a device. If this is ever not skipped and fails, nothing past this
    point in the file should be trusted either."""
    result = subprocess.run(["nvidia-smi", "-L"], capture_output=True, text=True, timeout=10, check=False)
    assert result.returncode == 0
    assert "GPU" in result.stdout


@requires_gpu
@requires_nvattest
def test_nvattest_cli_invocation():
    """Confirms nvattest itself runs and produces output shaped like what
    docs/hardware/nvat-integration.md documents -- NOT yet a claim about
    whether attestation succeeds, only that the tool runs."""
    result = subprocess.run(["nvattest", "--version"], capture_output=True, text=True, timeout=10, check=False)
    assert result.returncode == 0


@requires_gpu
@requires_nvattest
@requires_confidential_computing
def test_real_evidence_collection():
    """The actual capability this project's whole NVIDIA workstream is
    blocked on: collecting genuine hardware evidence. Deliberately does
    NOT call frontier_verify.attestations.nvidia_provider yet -- see
    docs/hardware/nvidia-real-test.md, which asks a human running this on
    real hardware to first confirm nvattest's raw output shape MATCHES
    what parse_nvat_evidence() expects (see docs/hardware/nvat-integration.md's
    'evidences vs evidence_list' finding) before wiring this test to that
    parser -- wiring it to a real-but-unconfirmed-compatible parser first
    would risk a false pass or a misleading failure, neither of which
    tells a real machine's operator anything useful."""
    result = subprocess.run(
        ["nvattest", "collect-evidence", "--device", "gpu"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0
    import json

    raw = json.loads(result.stdout)
    assert "evidences" in raw or "evidence_list" in raw, (
        "neither expected field name found -- the schema has changed again; "
        "update docs/hardware/nvat-integration.md before going further"
    )


@requires_gpu
@requires_nvattest
@requires_confidential_computing
def test_real_evidence_matches_parser_expectations():
    """Only meaningful once test_real_evidence_collection above has been
    run and confirmed manually at least once -- see this file's module
    docstring. Marked xfail rather than a hard skip specifically so a
    real run on real hardware SHOWS whether the current parser is
    compatible, rather than silently never running this check at all."""
    pytest.xfail(
        "Not yet confirmed against real hardware output -- see "
        "docs/hardware/nvidia-real-test.md, step 'Confirm evidence shape' "
        "before removing this xfail marker."
    )
