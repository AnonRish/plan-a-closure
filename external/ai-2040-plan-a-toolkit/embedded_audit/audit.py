from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from typing import Any

from plan_a_protocol.protocol import EvidenceRecord, issue_receipt, compute_evidence_hash


@dataclass(frozen=True)
class AuditEvidence:
    evidence_id: str
    artifact_type: str
    subject_id: str
    content_digest: str
    source_locator: str
    challenge_response: str
    metadata: dict[str, Any]

    def to_record(self, previous_hash: str = "0" * 64) -> EvidenceRecord:
        return EvidenceRecord(
            evidence_id=self.evidence_id,
            evidence_type=self.artifact_type,
            subject_id=self.subject_id,
            source=self.source_locator,
            collected_at=self.metadata.get("collected_at", "1970-01-01T00:00:00Z"),
            payload={"content_digest": self.content_digest, "challenge_response": self.challenge_response, "metadata": self.metadata},
            previous_hash=previous_hash,
        )


@dataclass
class AuditRound:
    audit_id: str
    subject_id: str
    required_artifacts: list[str]
    nonce: str
    evidence: list[AuditEvidence]

    @classmethod
    def create(cls, audit_id: str, subject_id: str, required_artifacts: list[str]) -> "AuditRound":
        return cls(audit_id, subject_id, sorted(set(required_artifacts)), secrets.token_hex(24), [])

    def add_evidence(self, *, evidence_id: str, artifact_type: str, content: bytes, source_locator: str, response: str, metadata: dict[str, Any] | None = None) -> AuditEvidence:
        metadata = dict(metadata or {})
        expected = hashlib.sha256((self.nonce + artifact_type).encode()).hexdigest()
        if response != expected:
            raise ValueError("audit challenge response is invalid")
        ev = AuditEvidence(
            evidence_id=evidence_id,
            artifact_type=artifact_type,
            subject_id=self.subject_id,
            content_digest=hashlib.sha256(content).hexdigest(),
            source_locator=source_locator,
            challenge_response=response,
            metadata=metadata,
        )
        self.evidence.append(ev)
        return ev

    def evaluate(self) -> dict[str, Any]:
        present = {e.artifact_type for e in self.evidence}
        missing = sorted(set(self.required_artifacts) - present)
        duplicate_types = sorted(t for t in present if sum(1 for e in self.evidence if e.artifact_type == t) > 1)
        if missing:
            status = "UNKNOWN"
            reasons = [f"required audit evidence missing: {missing}"]
        elif duplicate_types:
            status = "FAIL"
            reasons = [f"duplicate artifact types submitted: {duplicate_types}"]
        else:
            status = "PASS"
            reasons = ["all required artifacts present and challenge-checked"]
        return {
            "status": status,
            "audit_id": self.audit_id,
            "subject_id": self.subject_id,
            "nonce_commitment": hashlib.sha256(self.nonce.encode()).hexdigest(),
            "evidence_ids": [e.evidence_id for e in self.evidence],
            "reasons": reasons,
        }


def build_audit_receipt(audit: AuditRound, signers, quorum: int):
    records = []
    previous = "0" * 64
    for ev in audit.evidence:
        record = ev.to_record(previous)
        records.append(record)
        previous = record.digest()
    result = audit.evaluate()
    return issue_receipt(
        receipt_id=f"{audit.audit_id}-receipt",
        track="TRACK_1",
        subject={"subject_id": audit.subject_id, "audit_id": audit.audit_id},
        claim={"statement": "Declared audit evidence satisfies the specified audit scope.", "basis": "T1 embedded-audit protocol with verifier-issued challenge"},
        evidence_chain={"root_hash": compute_evidence_hash(records), "evidence_ids": [e.evidence_id for e in audit.evidence]},
        verification={"status": result["status"], "procedure_id": "T1-EMBEDDED-AUDIT-V1", "details": {**result, "challenge_nonce_revealed": audit.nonce}},
        governance_binding={"instrument_ref": "LOCAL_OR_TREATY_INSTRUMENT_TO_BE_BOUND", "retention_days": 3650, "dispute_process": "append-only correction with superseding receipt"},
        signers=signers,
        quorum=quorum,
        limitations=[
            "Software-only audit harness; no independent site access is created by this code.",
            "Challenge freshness is represented cryptographically, but evidence completeness still depends on audit authority and access.",
        ],
    )


def run_audit_round(audit: AuditRound, *, artifacts: dict[str, bytes], source_prefix: str = "company-evidence") -> dict[str, Any]:
    for artifact_type, content in artifacts.items():
        response = hashlib.sha256((audit.nonce + artifact_type).encode()).hexdigest()
        audit.add_evidence(
            evidence_id=f"{audit.audit_id}:{artifact_type}",
            artifact_type=artifact_type,
            content=content,
            source_locator=f"{source_prefix}:{artifact_type}",
            response=response,
            metadata={"challenge_scheme": "SHA-256(nonce || artifact_type)"},
        )
    return audit.evaluate()
