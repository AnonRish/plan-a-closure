"""
Attestation protocol: the chip-side Prover commits to epochs (signs the
Merkle root + its self-declared workload class), and the Verifier requests
a spot-check reveal chosen *after* commitment, so the prover can't predict
which indices will be checked and selectively hide bad ones. This is a
software model of the "packet-based verification" appendix in the AI 2040
verification supplement: https://ai-2040.com/supplements/verification-plan
(section A.2, "Detection by Random Sampling").

Threat model: an honest prover always declares the class its own
classifier assigns. A dishonest/compromised prover may override the
declaration (see `declared_override` below) while the underlying hardware
actually keeps running disallowed work -- exactly the "workload approval
vs. workload verification" gap the supplement calls out: declared workload
matching actual workload is precisely what this module checks.
"""

from dataclasses import dataclass, field
import random

from .trace import ExecutionEpoch
from .features import extract
from .classifier import classify, WorkloadClass
from .commitment import merkle_root, prove, verify, decode_event, _event_bytes
from .identity import DeviceIdentity, verify_signature

_TRAINING_SIGNAL_OPS = {"backward_matmul", "backward_attention", "optimizer_update"}


@dataclass
class Commitment:
    epoch_id: int
    root: bytes
    declared_class: str
    n_events: int
    device_pubkey: bytes
    signature: bytes

    def signed_message(self) -> bytes:
        return self.root + self.declared_class.encode() + self.epoch_id.to_bytes(8, "big")


@dataclass
class Prover:
    device_id: str
    identity: DeviceIdentity = field(default_factory=DeviceIdentity)
    _epochs: dict = field(default_factory=dict)
    _leaves: dict = field(default_factory=dict)

    def commit(self, epoch: ExecutionEpoch, declared_override: str = None) -> Commitment:
        leaves = [_event_bytes(e) for e in epoch.events]
        root = merkle_root(leaves)
        declared_value = declared_override if declared_override is not None else classify(extract(epoch)).value

        self._epochs[epoch.epoch_id] = epoch
        self._leaves[epoch.epoch_id] = leaves

        commitment = Commitment(epoch.epoch_id, root, declared_value, len(epoch.events), self.identity.public_bytes, b"")
        commitment.signature = self.identity.sign(commitment.signed_message())
        return commitment

    def reveal(self, epoch_id: int, indices: list) -> list:
        leaves = self._leaves[epoch_id]
        return [(i, leaves[i], prove(leaves, i)) for i in indices]


@dataclass
class AuditResult:
    epoch_id: int
    consistent: bool
    reason: str


class Verifier:
    def __init__(self, sample_rate: float = 0.15, rng_seed: int = None):
        self.sample_rate = sample_rate
        self._rng = random.Random(rng_seed)

    def choose_sample(self, n_events: int) -> list:
        k = max(1, min(n_events, round(n_events * self.sample_rate)))
        return sorted(self._rng.sample(range(n_events), k))

    def audit(self, commitment: Commitment, revealed: list) -> AuditResult:
        if not verify_signature(commitment.device_pubkey, commitment.signed_message(), commitment.signature):
            return AuditResult(commitment.epoch_id, False, "invalid device signature")

        for i, leaf_bytes, proof in revealed:
            if not verify(leaf_bytes, proof, commitment.root):
                return AuditResult(commitment.epoch_id, False, f"merkle proof failed at index {i}")

        if commitment.declared_class == WorkloadClass.INFERENCE.value:
            for i, leaf_bytes, proof in revealed:
                op, *_ = decode_event(leaf_bytes)
                if op in _TRAINING_SIGNAL_OPS:
                    return AuditResult(
                        commitment.epoch_id, False,
                        f"declared INFERENCE but revealed event {i} is '{op}'",
                    )

        return AuditResult(commitment.epoch_id, True, "signature + sampled proofs verified; no training signal in sample")
