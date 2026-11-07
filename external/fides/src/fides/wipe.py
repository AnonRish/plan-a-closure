"""
Memory wipe via forced memorization -- addresses SITREP item 15 (Memory
wipes, graded "uncertain"; existing algorithms such as PoSE are noted as
candidates).

The idea: instead of trusting a hardware "clear memory" instruction (hard
to verify from outside the device), force the *entire* addressable memory
to be overwritten with a value that could only be correctly present if the
wipe actually touched that address -- namely, a value derived from a
fresh, verifier-chosen challenge. A device that skips wiping some region
(to preserve stale data -- weights, KV-cache remnants, anything from a
prior workload) fails a spot-check at that region, because old content
won't match the challenge-derived pattern.

This reuses security.py's detection-probability math directly: if k of n
memory blocks were left unwiped, sampling m blocks at random catches it
with exactly the same hypergeometric probability as attestation.py's
spot-check scheme (see test_wipe.py). That's not a coincidence -- it's the
same commit-then-sample argument applied to memory contents instead of a
kernel-event trace.

Unlike trace verification, though, the verifier here can independently
compute the *entire* expected memory content -- it's fully determined by
the public challenge, with no dependence on anything only the prover
knows. That means spot-checking isn't actually the strongest tool
available: `expected_merkle_root` and `actual_merkle_root` below let the
verifier get a CERTAIN answer (up to BLAKE3 collision resistance) from a
single hash comparison, reusing commitment.py's Merkle tree, rather than
a probabilistic answer from sampling. `spot_check` and the hypergeometric
math above remain useful for localizing *where* a mismatch is once one is
known to exist (revealing a Merkle proof for a specific disputed block
without disclosing the rest), but for the basic yes/no "was everything
wiped" question, the Merkle comparison is strictly stronger and this
module leads with it.
"""

import blake3

from .commitment import merkle_root


def fill_block(challenge: bytes, address: int, block_size: int) -> bytes:
    """Deterministically derive the expected content of one memory block
    from the wipe challenge and its address."""
    out = b""
    counter = 0
    while len(out) < block_size:
        out += blake3.blake3(challenge + address.to_bytes(8, "big") + counter.to_bytes(4, "big")).digest()
        counter += 1
    return out[:block_size]


def wipe(memory: bytearray, challenge: bytes, block_size: int = 64) -> None:
    """Simulates a full forced-memorization wipe: every block is
    overwritten with its challenge-derived value."""
    for addr in range(0, len(memory), block_size):
        block = fill_block(challenge, addr, min(block_size, len(memory) - addr))
        memory[addr: addr + len(block)] = block


def spot_check(memory: bytearray, challenge: bytes, address: int, block_size: int = 64) -> bool:
    expected = fill_block(challenge, address, min(block_size, len(memory) - address))
    actual = bytes(memory[address: address + len(expected)])
    return actual == expected


def block_addresses(memory_size: int, block_size: int = 64) -> list:
    return list(range(0, memory_size, block_size))


def expected_merkle_root(memory_size: int, challenge: bytes, block_size: int = 64) -> bytes:
    """What the Merkle root of a correctly-wiped memory of this size
    MUST be -- computable by the verifier alone, using only public
    information (the challenge and the memory size), with no need to see
    the prover's actual memory at all."""
    leaves = [fill_block(challenge, addr, min(block_size, memory_size - addr)) for addr in block_addresses(memory_size, block_size)]
    return merkle_root(leaves)


def actual_merkle_root(memory: bytearray, block_size: int = 64) -> bytes:
    """The prover's side: a single compact commitment to what's actually
    in memory right now."""
    leaves = [bytes(memory[addr: addr + min(block_size, len(memory) - addr)]) for addr in block_addresses(len(memory), block_size)]
    return merkle_root(leaves)


def verify_wipe_certain(memory: bytearray, challenge: bytes, block_size: int = 64) -> bool:
    """A single hash comparison replacing probabilistic spot-checking:
    if the actual and expected Merkle roots match, EVERY block matches
    the challenge-derived pattern, with certainty bounded only by
    BLAKE3 collision resistance -- not a detection probability that
    needs repeated epochs to compound toward confidence."""
    return actual_merkle_root(memory, block_size) == expected_merkle_root(len(memory), challenge, block_size)
