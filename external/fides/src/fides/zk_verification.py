"""
ZK-accumulator compliance proof: answers the same question attestation.py
does -- "does this epoch's declared workload class match what actually
ran?" -- with a soundness guarantee instead of a spot-check probability.

Where attestation.py's Verifier samples m of n committed events and catches
a lie with probability computed in security.py, ZKVerifier here checks a
proof that covers every event, with no sampling step at all. The trade a
real deployment makes between the two isn't "which is better" -- it's
proof-generation cost (this module) versus detection-probability-over-time
(attestation.py). Both are legitimate, and spec/PROTOCOL.md section 8
discusses when you'd want one over the other.

What gets accumulated is the *set of distinct op-values present in the
epoch*, not the full event-level trace -- so this proves less about timing
and ordering than attestation.py's Merkle commitment does, in exchange for
proving the "no forbidden op occurred anywhere" claim with certainty
rather than a sampled subset.
"""

from dataclasses import dataclass, field

from .trace import ExecutionEpoch
from .accumulator import (
    AccumulatorSetup,
    hash_to_prime,
    accumulate,
    nonmembership_witness,
    verify_nonmembership,
    _product,
)

FORBIDDEN_OPS = ("backward_matmul", "backward_attention", "optimizer_update")


@dataclass
class ZKComplianceProof:
    epoch_id: int
    accumulator: int
    distinct_op_count: int
    witnesses: dict = field(default_factory=dict)  # forbidden_op -> (a, b) | None


class ZKProver:
    def __init__(self, setup: AccumulatorSetup):
        self.setup = setup

    def prove_inference_only(self, epoch: ExecutionEpoch) -> ZKComplianceProof:
        distinct_ops = sorted({e.op.value for e in epoch.events})
        primes = [hash_to_prime(op.encode()) for op in distinct_ops]
        A = accumulate(self.setup, primes)
        u = _product(primes)

        witnesses = {}
        for forbidden in FORBIDDEN_OPS:
            y = hash_to_prime(forbidden.encode())
            witnesses[forbidden] = nonmembership_witness(y, u)

        return ZKComplianceProof(epoch.epoch_id, A, len(distinct_ops), witnesses)


class ZKVerifier:
    def __init__(self, setup: AccumulatorSetup):
        self.setup = setup

    def verify(self, proof: ZKComplianceProof) -> bool:
        for forbidden in FORBIDDEN_OPS:
            y = hash_to_prime(forbidden.encode())
            witness = proof.witnesses.get(forbidden)
            if not verify_nonmembership(self.setup, proof.accumulator, y, witness):
                return False
        return True
