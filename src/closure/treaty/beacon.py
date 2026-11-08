"""Randomness no single party controls: commit-reveal among the parties, and draws (inspection samples, sortition of
citizen witnesses) that anyone can recompute.

Each party commits to sha256(party || nonce || value) before anyone reveals. Once all commitments are published, each
reveals (nonce, value); the seed is sha256 over the sorted reveals. A party that waits to see the others' values
cannot change its own without breaking its commitment; a party that refuses to reveal is identified, and the protocol
says what happens then (here: abort, so withholding cannot steer the draw). As long as one party's value is
unpredictable, the seed is. CBPAI asks for lot-selected, multinational citizen witnesses; MIRI's inspections sample
declared chips at random. Both need a draw the inspected party cannot steer.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets


def _h(*parts: bytes) -> bytes:
    h = hashlib.sha256()
    for p in parts:
        h.update(len(p).to_bytes(4, "big") + p)
    return h.digest()


def new_contribution(party: str) -> dict:
    """A party's secret value and nonce, and the commitment to publish first."""
    value, nonce = secrets.token_bytes(32), secrets.token_bytes(32)
    return {"party": party, "value": value.hex(), "nonce": nonce.hex(), "commitment": commitment(party, nonce, value)}


def commitment(party: str, nonce: bytes, value: bytes) -> str:
    return _h(b"closure-beacon-v1", party.encode(), nonce, value).hex()


class BeaconError(ValueError):
    pass


def seed(commitments: dict, reveals: dict) -> bytes:
    """32-byte seed from {party: commitment} and {party: (nonce_hex, value_hex)}. Raises BeaconError naming any party
    whose reveal is missing or does not match its commitment."""
    missing = sorted(set(commitments) - set(reveals))
    if missing:
        raise BeaconError(f"no reveal from {', '.join(missing)}: abort, so withholding cannot steer the draw")
    extra = sorted(set(reveals) - set(commitments))
    if extra:
        raise BeaconError(f"reveal without a prior commitment from {', '.join(extra)}")
    bad = [p for p in sorted(commitments) if not hmac.compare_digest(
        commitment(p, bytes.fromhex(reveals[p][0]), bytes.fromhex(reveals[p][1])), commitments[p])]
    if bad:
        raise BeaconError(f"reveal does not match the commitment: {', '.join(bad)}")
    return _h(b"closure-beacon-seed-v1", *(p.encode() + bytes.fromhex(reveals[p][1]) for p in sorted(commitments)))


def _uniform(seed_: bytes, label: str, i: int, n: int) -> int:
    """An integer uniform on [0, n) from the seed, by rejection sampling (no modulo bias)."""
    limit = (1 << 256) - ((1 << 256) % n)
    ctr = 0
    while True:
        x = int.from_bytes(_h(seed_, label.encode(), i.to_bytes(8, "big"), ctr.to_bytes(4, "big")), "big")
        if x < limit:
            return x % n
        ctr += 1


def draw(seed_: bytes, items: list, k: int, label: str = "draw") -> list:
    """k distinct items, uniformly without replacement (a seeded Fisher-Yates over the sorted items), reproducible by
    anyone with the seed and the list."""
    pool = sorted(items)
    if not 0 <= k <= len(pool):
        raise ValueError(f"cannot draw {k} of {len(pool)}")
    for i in range(k):
        j = i + _uniform(seed_, label, i, len(pool) - i)
        pool[i], pool[j] = pool[j], pool[i]
    return pool[:k]


def sortition(seed_: bytes, candidates: dict, per_group: dict) -> dict:
    """Stratified lot: per_group[g] people drawn from candidates[g] (e.g. groups = nationalities, as CBPAI's
    'lot-selected, multinational' witnesses need)."""
    return {g: draw(seed_, candidates[g], int(n), label=f"sortition:{g}") for g, n in sorted(per_group.items())}
