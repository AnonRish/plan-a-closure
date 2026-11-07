from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(value: bytes | str) -> str:
    raw = value.encode("utf-8") if isinstance(value, str) else value
    return hashlib.sha256(raw).hexdigest()


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    evidence_type: str
    subject_id: str
    source: str
    collected_at: str
    payload: dict[str, Any]
    previous_hash: str = "0" * 64

    def body(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type,
            "subject_id": self.subject_id,
            "source": self.source,
            "collected_at": self.collected_at,
            "payload": self.payload,
            "previous_hash": self.previous_hash,
        }

    def digest(self) -> str:
        return sha256_hex(canonical_json(self.body()))


def compute_evidence_hash(records: Iterable[EvidenceRecord]) -> str:
    previous = "0" * 64
    final = previous
    for record in records:
        if record.previous_hash != previous:
            raise ValueError(f"evidence chain break at {record.evidence_id}")
        final = record.digest()
        previous = final
    return final


@dataclass(frozen=True)
class Signer:
    signer_id: str
    role: str
    public_key_b64: str
    independence_group: str


@dataclass
class Receipt:
    schema_version: str
    receipt_id: str
    track: str
    issued_at: str
    subject: dict[str, Any]
    claim: dict[str, Any]
    evidence_chain: dict[str, Any]
    verification: dict[str, Any]
    attestation: dict[str, Any]
    governance_binding: dict[str, Any]
    limitations: list[str] = field(default_factory=list)
    producer: str = "AnonRish Plan A prototypes"

    def unsigned(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "receipt_id": self.receipt_id,
            "track": self.track,
            "issued_at": self.issued_at,
            "subject": self.subject,
            "claim": self.claim,
            "evidence_chain": self.evidence_chain,
            "verification": self.verification,
            "attestation": {k: v for k, v in self.attestation.items() if k != "signatures"},
            "governance_binding": self.governance_binding,
            "limitations": self.limitations,
            "producer": self.producer,
        }

    def digest(self) -> str:
        return sha256_hex(canonical_json(self.unsigned()))

    def to_dict(self) -> dict[str, Any]:
        obj = self.unsigned()
        obj["attestation"] = self.attestation
        obj["receipt_digest"] = self.digest()
        return obj


def generate_keypair() -> tuple[Ed25519PrivateKey, str]:
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes_raw()
    return private, base64.b64encode(public).decode("ascii")


def sign_receipt(receipt: Receipt, signer: Signer, private_key: Ed25519PrivateKey) -> Receipt:
    signature = private_key.sign(canonical_json(receipt.unsigned()))
    signatures = list(receipt.attestation.get("signatures", []))
    signatures.append({
        "signer_id": signer.signer_id,
        "signature_b64": base64.b64encode(signature).decode("ascii"),
    })
    receipt.attestation["signatures"] = signatures
    return receipt


def issue_receipt(
    *,
    receipt_id: str,
    track: str,
    subject: dict[str, Any],
    claim: dict[str, Any],
    evidence_chain: dict[str, Any],
    verification: dict[str, Any],
    governance_binding: dict[str, Any],
    signers: list[tuple[Signer, Ed25519PrivateKey]],
    quorum: int,
    limitations: list[str] | None = None,
) -> Receipt:
    receipt = Receipt(
        schema_version="1.0.0",
        receipt_id=receipt_id,
        track=track,
        issued_at=now_utc_iso(),
        subject=subject,
        claim=claim,
        evidence_chain=evidence_chain,
        verification=verification,
        attestation={
            "scheme": "Ed25519-threshold",
            "required_quorum": quorum,
            "signers": [signer.__dict__.copy() for signer, _ in signers],
            "signatures": [],
        },
        governance_binding=governance_binding,
        limitations=limitations or [],
    )
    for signer, key in signers:
        sign_receipt(receipt, signer, key)
    return receipt


def verify_receipt(
    receipt: Receipt | dict[str, Any],
    *,
    require_independent_roots: bool = True,
) -> tuple[bool, list[str]]:
    obj = receipt.to_dict() if isinstance(receipt, Receipt) else receipt
    errors: list[str] = []
    att = obj.get("attestation", {})
    signer_meta = {s["signer_id"]: s for s in att.get("signers", [])}
    signatures = att.get("signatures", [])
    quorum = int(att.get("required_quorum", 1))
    unique_ids = {s.get("signer_id") for s in signatures}

    if quorum < 1:
        errors.append("required_quorum must be >= 1")
    if len(unique_ids) < quorum:
        errors.append(f"quorum unmet: {len(unique_ids)} distinct signatures for quorum {quorum}")

    groups = [signer_meta[sid].get("independence_group") for sid in unique_ids if sid in signer_meta]
    if len(groups) != len(unique_ids):
        errors.append("signature references unknown signer metadata")
    if require_independent_roots and len(set(groups)) < min(quorum, len(groups)):
        errors.append("distinct signatures collapse into the same independence group")

    unsigned = dict(obj)
    unsigned.pop("receipt_digest", None)
    unsigned["attestation"] = {k: v for k, v in att.items() if k != "signatures"}
    payload = canonical_json(unsigned)

    for item in signatures:
        sid = item.get("signer_id")
        meta = signer_meta.get(sid)
        if not meta:
            continue
        try:
            public = Ed25519PublicKey.from_public_bytes(base64.b64decode(meta["public_key_b64"]))
            public.verify(base64.b64decode(item["signature_b64"]), payload)
        except Exception:
            errors.append(f"invalid signature for signer {sid}")

    return not errors, errors


def compute_receipt_digest(receipt: Receipt | dict[str, Any]) -> str:
    obj = receipt.to_dict() if isinstance(receipt, Receipt) else dict(receipt)
    obj.pop("receipt_digest", None)
    att = dict(obj.get("attestation", {}))
    att.pop("signatures", None)
    obj["attestation"] = att
    return sha256_hex(canonical_json(obj))
