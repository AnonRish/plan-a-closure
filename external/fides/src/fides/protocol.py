"""
High-level orchestration: wires a Prover, a Verifier, a Registry, and an
AuditLedger together into the end-to-end flow sketched in
spec/PROTOCOL.md. Registry is a minimal stand-in for the compute
declaration / chip-registry side of Plan A (what got committed and when);
AuditLedger is the tamper-evident record of what the verifier found.
"""

from dataclasses import dataclass, field

from .trace import ExecutionEpoch
from .attestation import Prover, Verifier, Commitment, AuditResult
from .ledger import AuditLedger


@dataclass
class Registry:
    """Append-only log of published commitments."""

    _log: list = field(default_factory=list)

    def publish(self, device_id: str, commitment: Commitment) -> None:
        self._log.append((device_id, commitment))

    def history_for(self, device_id: str) -> list:
        return [c for d, c in self._log if d == device_id]

    def __len__(self) -> int:
        return len(self._log)


class Tap:
    """One inference-only verification tap: a device identity plus the
    prover/verifier/registry/ledger pipeline it participates in."""

    def __init__(self, device_id: str, sample_rate: float = 0.15, seed: int = None):
        self.device_id = device_id
        self.prover = Prover(device_id)
        self.verifier = Verifier(sample_rate=sample_rate, rng_seed=seed)
        self.registry = Registry()
        self.ledger = AuditLedger()

    def run_epoch(self, epoch: ExecutionEpoch, declared_override: str = None) -> tuple:
        commitment = self.prover.commit(epoch, declared_override=declared_override)
        self.registry.publish(self.device_id, commitment)

        sample = self.verifier.choose_sample(commitment.n_events)
        revealed = self.prover.reveal(epoch.epoch_id, sample)
        result = self.verifier.audit(commitment, revealed)

        self.ledger.append(self.device_id, result)
        return commitment, result
