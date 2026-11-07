"""Real GPU/NVSwitch attestation via NVIDIA's attestation tooling.

STATUS: NOT IMPLEMENTED for live hardware. This class exists to fix the
interface shape (see base.AttestationProvider) so a real implementation is
a matter of filling this in against a real SDK, not redesigning how the
rest of the system talks to attestation providers. A narrower, real
capability -- parsing NVAT's evidence JSON shape into the portable
HardwareEvidence schema -- IS implemented below; see parse_nvat_evidence().

Findings from FRESH current-state research (re-done for Phase 2, per this
document's own section 2 instruction not to trust prior findings -- see
docs/hardware/nvidia-attestation.md for the full writeup and sources).
Notably, this research SUPERSEDES Phase 1's ADR-0001, which called NVAT
"alpha" with an "unstable ABI" -- that was accurate two months earlier and
is no longer accurate now:

  * NVAT ("NV Attest", the `nvattest` CLI + C API, successor to nvTrust's
    Python guest tools) has shipped versioned releases since December
    2025 and reached 1.2.0 in March 2026 -- past alpha, not yet the kind
    of multi-year API stability a production dependency usually wants,
    but a real, current, targetable interface.
  * The Python Attestation SDK (`nv-attestation-sdk`) it supersedes has a
    firm end-of-support date of 2026-09-15.
  * `nvattest collect-evidence` produces JSON shaped like
    frontier_verify/attestations/fixtures/nvidia_evidence_synthetic.json
    (fabricated values, real field names) -- confirmed from NVIDIA's own
    documentation, not invented.
  * NVIDIA's own architecture docs explicitly use RATS (IETF RFC 9334)
    terminology -- Attester/Verifier/Relying Party -- which maps directly
    onto this project's Prover/Verifier/Auditor roles. See
    docs/ecosystem-interoperability.md.
  * Both local and remote (NRAS) attestation still require a Hopper-or-
    later GPU with Confidential Computing enabled. None of that exists in
    the sandbox this repository was built in (no GPU, no NVML, no
    /dev/nvidia*, confirmed by inspection each phase, not assumed).

A real implementation should target NVAT/nvattest specifically (not the
expiring Python SDK), and MUST re-run current-state research before
starting -- this note will itself be stale within months, exactly as
Phase 1's version of this note already was.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from frontier_verify.attestations.base import AttestationProvider
from frontier_verify.evidence.models import HardwareEvidence, Maturity


class NvidiaAttestationProvider(AttestationProvider):
    provider_name = "nvidia"

    def get_platform_evidence(self) -> HardwareEvidence:
        raise NotImplementedError(
            "Real NVIDIA attestation is not implemented in this environment. "
            "There is no GPU, no NVML, and no attestation SDK installed here, "
            "and the upstream SDK landscape is still evolving even though it "
            "has stabilized somewhat since Phase 1 (see this module's "
            "docstring). Implementing this against faked evidence would be "
            "exactly the kind of fabrication the project's non-hallucination "
            "rule prohibits -- so it raises instead of pretending. See "
            "docs/hardware/nvidia-attestation.md.\n\n"
            "What DOES exist here: parse_nvat_evidence(), which turns a real "
            "`nvattest collect-evidence` JSON document into a portable "
            "HardwareEvidence -- see "
            "frontier_verify/attestations/fixtures/nvidia_evidence_synthetic.json "
            "and tests/conformance/test_nvidia_evidence_parsing.py for what "
            "that narrower claim actually covers, and does not."
        )

    @staticmethod
    def parse_nvat_evidence(raw: dict[str, Any], *, mock: bool) -> HardwareEvidence:
        """Parse the JSON shape produced by `nvattest collect-evidence`
        (see docs/hardware/nvidia-attestation.md) into a portable
        HardwareEvidence.

        This is REAL, TESTED parsing logic against the REAL field
        names/shape NVIDIA documents for this output -- but it does NOT
        validate the embedded certificate chain or the evidence bytes
        against NVIDIA's remote attestation service (NRAS). That's a
        materially stronger claim this method does not make. Call it with
        mock=True for anything that isn't a genuine `nvattest` invocation
        against real hardware, including the bundled synthetic fixture,
        which exists to test this parser's shape-handling without
        claiming hardware backing.
        """
        evidences = raw.get("evidences", [])
        if not evidences:
            raise ValueError("no 'evidences' entries in nvattest output")
        first = evidences[0]
        return HardwareEvidence(
            provider_name="nvidia",
            maturity=Maturity.MOCK if mock else Maturity.EXPERIMENTAL,
            mock=mock,
            claims={
                "arch": first.get("arch"),
                "vbios_version": first.get("vbios_version"),
                "driver_version": first.get("driver_version"),
                "nvat_evidence_version": first.get("version"),
                "result_code": raw.get("result_code"),
                "result_message": raw.get("result_message"),
            },
            raw_evidence_digest=None,
        )


def load_synthetic_fixture() -> dict[str, Any]:
    """The fabricated-but-real-shaped fixture bundled with this repo. See
    frontier_verify/attestations/fixtures/nvidia_evidence_synthetic.json
    for the prominent warning about what this is and is not."""
    path = Path(__file__).parent / "fixtures" / "nvidia_evidence_synthetic.json"
    return json.loads(path.read_text())
