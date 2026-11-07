"""Storage for the verifier API.

MATURITY: EXPERIMENTAL. A real, if partial, step up from Phase 1's
in-memory-only MOCK: evidence and attestation bytes are now persisted via
ContentAddressedStore (durable, integrity-checked on read), not just held
in a dict that vanishes on restart. Policies, verification records, and
receipts are still in-memory-only -- upgrading those too is possible with
the same ContentAddressedStore, deferred here to keep this change reviewable
as one coherent step rather than rewriting every collection at once. See
docs/protocol-roadmap.md.

Data location: FV_DATA_DIR env var if set, otherwise a fresh temporary
directory created once per process. That means the DEFAULT behavior does
NOT survive a process restart -- set FV_DATA_DIR explicitly to a real path
for that. This is an honest default for experimental code, not an
oversight: a temp-dir default keeps every test run and every local demo
hermetic without needing external cleanup, at the cost of requiring an
explicit choice to get real persistence. See docs/protocol/key-management.md
for the identical reasoning applied to FV_KEY_DIR.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from frontier_verify.evidence.models import Evidence, HardwareEvidence
from frontier_verify.policies.models import Policy
from frontier_verify.receipts.models import Receipt
from frontier_verify.storage.content_addressed import ContentAddressedStore


def _default_data_dir() -> Path:
    env = os.environ.get("FV_DATA_DIR")
    if env:
        return Path(env)
    return Path(tempfile.mkdtemp(prefix="frontier-verify-data-"))


class EvidenceConflict(Exception):
    """Raised when an evidence_id is resubmitted with DIFFERENT content
    than what's already on record for it. See
    tests/conformance/test_evidence_id_collision.py and
    docs/adversarial-results.md, attack #6 (evidence withholding /
    selective resubmission)."""


class Store:
    def __init__(self, data_dir: Path | None = None):
        base = data_dir or _default_data_dir()
        self.evidence_cas = ContentAddressedStore(base / "evidence")
        self.attestation_cas = ContentAddressedStore(base / "attestations")
        self.recomputation_input_cas = ContentAddressedStore(base / "recomputation-inputs")
        self.evidence_index: dict[str, str] = {}
        self.attestation_index: dict[str, str] = {}
        self.policies: dict[str, Policy] = {}
        self.verifications: dict[str, dict] = {}
        self.receipts: dict[str, Receipt | None] = {}

    def put_evidence(self, evidence: Evidence) -> str:
        """Store evidence keyed by its caller-supplied evidence_id, backed
        by content-addressed persistence of the actual bytes. Raises
        EvidenceConflict if evidence_id was already used for DIFFERENT
        content -- a prover doesn't get to silently overwrite what it
        already claimed under the same id."""
        # exclude_none=True must match Evidence.digest()'s own dump shape
        # exactly, or the digest used as the CAS storage key diverges from
        # the digest callers get back from evidence.digest() -- which is
        # exactly the bug this comment is here to stop someone
        # reintroducing. See tests/unit/test_evidence.py for the
        # independent digest-stability check this has to stay consistent
        # with.
        obj = evidence.model_dump(exclude_none=True, mode="json")
        new_digest = self.evidence_cas.put(obj)
        existing_digest = self.evidence_index.get(evidence.evidence_id)
        if existing_digest is not None and existing_digest != new_digest:
            raise EvidenceConflict(
                f"evidence_id {evidence.evidence_id!r} already refers to "
                f"digest {existing_digest}, cannot resubmit as {new_digest}"
            )
        self.evidence_index[evidence.evidence_id] = new_digest
        return new_digest

    def get_evidence(self, evidence_id: str) -> Evidence | None:
        digest = self.evidence_index.get(evidence_id)
        if digest is None:
            return None
        return Evidence.model_validate(self.evidence_cas.get(digest))

    def put_attestation(self, attestation_id: str, evidence: HardwareEvidence) -> str:
        # Same exclude_none consistency requirement as put_evidence above,
        # matching HardwareEvidence.digest()'s own dump shape.
        obj = evidence.model_dump(exclude_none=True, mode="json")
        digest = self.attestation_cas.put(obj)
        self.attestation_index[attestation_id] = digest
        return digest

    def put_recomputation_input(self, obj: dict) -> str:
        """Persist recomputation input by content hash so later recomputation
        uses the exact bytes/content that was submitted before seed reveal."""
        return self.recomputation_input_cas.put(obj)

    def get_recomputation_input(self, digest: str) -> dict:
        return self.recomputation_input_cas.get(digest)

    def get_attestation(self, attestation_id: str) -> HardwareEvidence | None:
        digest = self.attestation_index.get(attestation_id)
        if digest is None:
            return None
        return HardwareEvidence.model_validate(self.attestation_cas.get(digest))


store = Store()
