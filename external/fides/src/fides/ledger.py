"""
Tamper-evident audit ledger.

This addresses a specific, separate gap in the AI 2040 verification
SITREP -- "Verification reporting", graded NOT ON TRACK:

    "The integrity of what the recomputation server reports back to the
    verifier has not been explored."

commitment.py + attestation.py assume the *prover* might lie. This module
assumes the *auditor/recomputation-server* might also be compromised,
coerced, or simply buggy, and asks: how would anyone downstream know if an
auditor quietly rewrote its own audit history after the fact (e.g. to
erase a violation finding)?

Every AuditResult is hash-chained to the previous entry (each entry's hash
covers the previous entry's hash) and signed by the auditor's key. Editing
any past entry breaks the hash chain from that point forward in a way
that's checkable by anyone holding an independent copy of the ledger --
you don't need to trust the auditor not to tamper, only to have published
each entry_hash to at least one outside party at the time.
"""

from dataclasses import dataclass, field

import blake3

from .identity import DeviceIdentity, verify_signature
from .attestation import AuditResult

GENESIS_HASH = b"\x00" * 32


@dataclass
class LedgerEntry:
    index: int
    prev_hash: bytes
    device_id: str
    epoch_id: int
    consistent: bool
    reason: str
    entry_hash: bytes
    signature: bytes

    def _payload(self) -> bytes:
        return (
            self.prev_hash
            + self.device_id.encode()
            + self.epoch_id.to_bytes(8, "big")
            + bytes([1 if self.consistent else 0])
            + self.reason.encode()
        )


class AuditLedger:
    def __init__(self, auditor_identity: DeviceIdentity = None):
        self.identity = auditor_identity or DeviceIdentity()
        self._entries: list = []

    def __len__(self) -> int:
        return len(self._entries)

    def append(self, device_id: str, result: AuditResult) -> LedgerEntry:
        prev_hash = self._entries[-1].entry_hash if self._entries else GENESIS_HASH
        entry = LedgerEntry(
            index=len(self._entries),
            prev_hash=prev_hash,
            device_id=device_id,
            epoch_id=result.epoch_id,
            consistent=result.consistent,
            reason=result.reason,
            entry_hash=b"",
            signature=b"",
        )
        entry.entry_hash = blake3.blake3(entry._payload()).digest()
        entry.signature = self.identity.sign(entry.entry_hash)
        self._entries.append(entry)
        return entry

    def verify_chain(self) -> bool:
        prev_hash = GENESIS_HASH
        for entry in self._entries:
            if entry.prev_hash != prev_hash:
                return False
            if blake3.blake3(entry._payload()).digest() != entry.entry_hash:
                return False
            if not verify_signature(self.identity.public_bytes, entry.entry_hash, entry.signature):
                return False
            prev_hash = entry.entry_hash
        return True

    def tamper(self, index: int, new_reason: str) -> None:
        """Testing helper only: simulates a compromised auditor silently
        editing a past entry after publication, to demonstrate that
        verify_chain() catches it. A real deployment has no equivalent
        method -- this exists so the property is testable."""
        self._entries[index].reason = new_reason
