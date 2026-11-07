"""AttestationProvider: the contract every hardware/platform attestation
backend must implement.

Fixing this interface now -- before real NVIDIA integration exists -- is a
deliberate Phase 1 goal (see docs/adr/0001-attestation-abstraction-and-network-tap-deferral.md).
The shape is deliberately narrow: one method, one return type. Vendor-
specific complexity (NVML vs NSCQ evidence collection, local vs NRAS remote
verification, PPCIE topology checks, etc.) lives inside a provider's
implementation, not in this interface, so the core system never has to know
which hardware vendor it's talking to.

See docs/hardware-provider-guide.md for what a real implementation must do
to be trustworthy, not just structurally valid.
"""
from __future__ import annotations

import abc

from frontier_verify.evidence.models import HardwareEvidence


class AttestationProvider(abc.ABC):
    provider_name: str

    @abc.abstractmethod
    def get_platform_evidence(self) -> HardwareEvidence:
        """Return HardwareEvidence for the platform this process is running
        on right now. Implementations MUST set `mock` and `maturity`
        honestly -- see frontier_verify.evidence.models.Maturity."""
        raise NotImplementedError
