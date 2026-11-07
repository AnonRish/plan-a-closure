"""Tap presence monitoring with keyed canaries (Plan A SITREP, "tap installation and monitoring": not on track).

The verifier sends small canary datagrams across each tapped link. Their send times and their payloads both come from a
key the prover does not hold, so the prover can predict neither when a canary passes nor what it looks like: a canary's
payload is an HMAC output, indistinguishable from encrypted traffic. The capture host matches every captured payload
against the payloads it expects. If a tap is removed, bypassed or replaced by a device that copies only part of the link,
canaries go missing; a captured canary far from its scheduled time is reported late, and a repeated one as a replay.
A removal is noticed within one canary gap, plus jitter and tolerance (`detection_bound_s`), so the rate sets the
guarantee. Combined with traffic closure's byte accounting, a device that copies canaries but drops other traffic is also
caught, because the bytes it drops are then unexplained on the verifier's side.

Software protocol: the sender, the tap and the capture host are hardware on a real link.
"""
from __future__ import annotations

import hashlib
import hmac

PAYLOAD_BYTES = 32


def _u(key: bytes, label: bytes, seq: int) -> bytes:
    return hmac.new(key, label + int(seq).to_bytes(8, "big"), hashlib.sha256).digest()


def schedule(key: bytes, start: float, duration_s: float, rate_hz: float, jitter: float = 0.5) -> list:
    """(seq, send time) for one canary per 1/rate interval, placed inside its interval by the key."""
    if rate_hz <= 0 or not 0 <= jitter <= 1:
        raise ValueError("rate_hz must be positive and jitter in [0, 1]")
    gap, n = 1.0 / rate_hz, int(duration_s * rate_hz)
    out = []
    for s in range(n):
        u = int.from_bytes(_u(key, b"time", s)[:8], "big") / 2.0 ** 64
        out.append((s, start + (s + 0.5 + jitter * (u - 0.5)) * gap))
    return out


def payload(key: bytes, seq: int) -> bytes:
    """The canary's payload: 32 bytes that look random to anyone without the key."""
    return _u(key, b"canary", seq)[:PAYLOAD_BYTES]


def check(pairs, key: bytes, sched, tol_s: float = 0.05) -> dict:
    """pairs: (Pkt, payload bytes) from the tap capture, e.g. traffic.iter_pcap(path, with_payload=True)."""
    expected = dict(sched)
    lookup = {payload(key, s): s for s in expected}
    seen, late, replays = {}, [], 0
    for p, pay in pairs:
        s = lookup.get(bytes(pay[:PAYLOAD_BYTES]))
        if s is None:
            continue
        if s in seen:
            replays += 1
            continue
        seen[s] = p.ts
        if abs(p.ts - expected[s]) > tol_s:
            late.append(s)
    missing = sorted(set(expected) - set(seen))
    on_time = sorted(expected[s] for s in seen if s not in late)
    if expected:
        bounds = [min(expected.values())] + on_time + [max(expected.values())]
        max_gap = max(b - a for a, b in zip(bounds, bounds[1:]))
    else:
        max_gap = 0.0
    return {"expected": len(expected), "seen": len(seen), "missing": missing, "late": sorted(late), "replays": replays,
            "longest_unconfirmed_s": float(max_gap), "pass": bool(expected) and not missing and not late and not replays}


def detection_bound_s(rate_hz: float, tol_s: float = 0.05, jitter: float = 0.5) -> float:
    """Worst-case time from a tap's removal to a canary that should have been captured and was not."""
    return (1.0 + jitter) / rate_hz + tol_s
