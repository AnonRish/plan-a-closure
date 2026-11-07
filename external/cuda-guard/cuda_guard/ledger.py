"""
cuda_guard.ledger
==================
Phase 3 (spec Sec. 26, 27): an append-only, hash-chained audit ledger,
replacing the plain list-based AuditLedger from the single-file prototype.

Honest limitation, stated once here rather than scattered as caveats:
without an independent external anchor (e.g. periodically publishing the
latest record_hash somewhere outside this process's control), this ledger
detects tampering with *retained* history -- modification (including
timestamp alteration), deletion, insertion, and reordering of records that
still exist are all detected by recomputing the chain (tested in
tests/test_ledger.py, not merely asserted here). It does NOT prevent an
attacker with full rewrite access to the underlying storage from destroying
the ledger outright or forging an entirely self-consistent alternate chain
from record 0. Spec Sec. 26 says this explicitly; this module does not
oversell past it. See docs/LIMITATIONS.md.
"""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional

from .evidence import EvidenceLayer, EvidenceRecord

GENESIS_HASH = "0" * 64


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class LedgerRecord:
    sequence_number: int
    previous_hash: str
    timestamp: str
    event_type: str
    payload: dict
    source: str
    nonce: str
    record_hash: str = ""

    def _hashable_fields(self) -> dict:
        return {
            "sequence_number": self.sequence_number, "previous_hash": self.previous_hash,
            "timestamp": self.timestamp, "event_type": self.event_type,
            "payload": self.payload, "source": self.source, "nonce": self.nonce,
        }

    def compute_hash(self) -> str:
        body = json.dumps(self._hashable_fields(), sort_keys=True, default=str)
        return hashlib.sha256(body.encode()).hexdigest()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ChainVerificationResult:
    valid: bool
    records_checked: int
    first_break_at: Optional[int]
    break_reason: Optional[str]
    duplicate_content_pairs: list  # [(seq_a, seq_b), ...] identical event_type+payload, informational only


class TamperEvidentLedger:
    """Same record()/record_external_evidence()/external_evidence()/violations()
    surface as the prototype's AuditLedger, so nothing depending on those call
    signatures breaks -- every append is now hash-chained underneath."""

    def __init__(self):
        self._records: list[LedgerRecord] = []
        self._external_evidence: dict[str, list[dict]] = {}
        self._seen_nonces: set[str] = set()

    def record(self, event_type: str, payload: dict[str, Any], source: str = "cuda_guard") -> LedgerRecord:
        seq = len(self._records)
        prev_hash = self._records[-1].record_hash if self._records else GENESIS_HASH
        nonce = secrets.token_hex(16)
        self.check_and_register_nonce(nonce)  # collision here is cryptographically negligible
        rec = LedgerRecord(sequence_number=seq, previous_hash=prev_hash, timestamp=_now(),
                            event_type=event_type, payload=payload, source=source, nonce=nonce)
        rec.record_hash = rec.compute_hash()
        self._records.append(rec)
        return rec

    def record_evidence(self, evidence: EvidenceRecord) -> LedgerRecord:
        return self.record(event_type=f"evidence.{evidence.evidence_class.value}", payload=evidence.to_dict())

    def record_external_evidence(self, source: str, data: dict[str, Any]) -> LedgerRecord:
        entry = {"source": source, "data": data, "ts": _now()}
        self._external_evidence.setdefault(source, []).append(entry)
        return self.record("external_evidence", entry, source=source)

    def external_evidence(self, source: Optional[str] = None) -> list[dict]:
        if source is None:
            return [e for entries in self._external_evidence.values() for e in entries]
        return list(self._external_evidence.get(source, []))

    def violations(self) -> list[LedgerRecord]:
        return [r for r in self._records if r.event_type == "VIOLATION"]

    def violations_by_layer(self, layer: EvidenceLayer) -> list[LedgerRecord]:
        return [v for v in self.violations() if v.payload.get("layer") == layer]

    def to_list(self) -> list[dict]:
        return [r.to_dict() for r in self._records]

    def __len__(self) -> int:
        return len(self._records)

    # --- integrity verification (spec Sec. 26) ------------------------------
    def verify_chain(self) -> ChainVerificationResult:
        prev_hash = GENESIS_HASH
        seen_content: dict[str, int] = {}
        duplicates: list[tuple] = []
        for i, rec in enumerate(self._records):
            if rec.previous_hash != prev_hash:
                return ChainVerificationResult(
                    False, i, i,
                    f"record {i}: previous_hash does not match record {i - 1}'s stored hash "
                    "(consistent with deletion, insertion, or reordering)", duplicates)
            if rec.compute_hash() != rec.record_hash:
                return ChainVerificationResult(
                    False, i, i,
                    f"record {i}: stored record_hash does not match a fresh hash of its own "
                    "content (consistent with modification, including timestamp alteration)", duplicates)
            content_key = json.dumps({"event_type": rec.event_type, "payload": rec.payload},
                                      sort_keys=True, default=str)
            if content_key in seen_content:
                duplicates.append((seen_content[content_key], i))
            else:
                seen_content[content_key] = i
            prev_hash = rec.record_hash
        return ChainVerificationResult(True, len(self._records), None, None, duplicates)

    # --- replay/nonce protection (spec Sec. 27) ------------------------------
    def check_and_register_nonce(self, nonce: str) -> bool:
        """True and registers if `nonce` is fresh; False (and NOT registered
        again) if it has been seen before anywhere in this ledger's lifetime
        -- the AUTHENTIC_EVENT vs. AUTHENTIC_EVENT_REPLAYED distinction from
        spec Sec. 27: a nonce that fails this check may be perfectly genuine
        data, replayed."""
        if nonce in self._seen_nonces:
            return False
        self._seen_nonces.add(nonce)
        return True
