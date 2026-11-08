"""k-of-n approval of a critical action: CBPAI's "critical actions would require multiple people" and its air-gapped
multi-party controls; A Narrow Path's IASC appoints its General Secretary by a three-fourths majority of the Executive
Board. An action is a canonical JSON record; each authorised member signs its hash with Ed25519; the action is
approved only with at least k valid signatures from distinct authorised members, before it expires.
"""
from __future__ import annotations

import hashlib
import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


def action_digest(action: dict) -> bytes:
    """sha256 of the canonical JSON of the action (sorted keys, no whitespace)."""
    return hashlib.sha256(json.dumps(action, sort_keys=True, separators=(",", ":")).encode()).digest()


def public_hex(key: Ed25519PrivateKey) -> str:
    return key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()


def sign(key: Ed25519PrivateKey, action: dict) -> dict:
    return {"signer": public_hex(key), "sig": key.sign(action_digest(action)).hex()}


def majority(n_members: int, fraction: float) -> int:
    """Signatures needed for a share of members, e.g. three-fourths of a board of 15 -> 12 (rounded up)."""
    from fractions import Fraction
    q = Fraction(fraction).limit_denominator(1000) * int(n_members)
    return int(q.numerator // q.denominator + (q.numerator % q.denominator != 0))


def verify(action: dict, approvals: list, members: dict, k: int, now: float) -> dict:
    """members: {public key hex: name}. Counts valid signatures from distinct authorised members over this exact
    action; reports unknown signers, duplicates and bad signatures. Approved iff at least k and not expired
    (action['expires'] is a Unix time)."""
    d = action_digest(action)
    good, seen, problems = [], set(), []
    for a in approvals:
        s = a.get("signer", "")
        if s not in members:
            problems.append(f"unknown signer {s[:16]}")
            continue
        if s in seen:
            problems.append(f"duplicate signature from {members[s]}")
            continue
        try:
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(s)).verify(bytes.fromhex(a.get("sig", "")), d)
        except (InvalidSignature, ValueError):
            problems.append(f"bad signature from {members[s]}")
            continue
        seen.add(s)
        good.append(members[s])
    expired = "expires" in action and float(now) > float(action["expires"])
    if expired:
        problems.append("the action has expired")
    return {"approved": len(good) >= int(k) and not expired, "valid": sorted(good), "needed": int(k),
            "problems": problems, "digest": d.hex()}
