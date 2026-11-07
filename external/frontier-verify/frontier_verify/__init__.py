"""Frontier Verify -- Phase 1 core verification fabric (reference implementation).

Maturity: EXPERIMENTAL. See docs/ai2040-coverage-matrix.md for a workstream-by-
workstream honest status, and docs/threat-model.md before trusting any of this
for anything real.
"""

from frontier_verify.sdk.client import VerifierClient

__all__ = ["VerifierClient"]
__version__ = "0.4.0"
