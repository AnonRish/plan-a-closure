"""Where is a chip? Location bounds from timed, signed challenge-response: Scher and Thiergart's "ping-based location
tracking" (2024), a software alternative to the GPS trackers A Narrow Path proposes for existing hardware (pp. 37-38).

A landmark at a known place sends a fresh random nonce; the chip answers with an Ed25519 signature over
(landmark id || nonce) made with a key that never leaves it. No signal outruns light and a relay can only add delay,
so the chip is within c x RTT / 2 of the landmark (great-circle; c in vacuum is the sound bound, fibre is about a third
slower, so real paths make the bound looser, never wrong). This proves closeness, not absence: a landmark near the
declared site with a small round trip proves the chip is near that site; a large round trip proves nothing. Several
landmarks bound the chip to the intersection of their discs.

Soundness rests on the key staying inside the chip. Current chips may not resist physical key extraction (the
paper's caveat); a key file is a stand-in for a chip's attestation key. Timing is the landmark's own: landmarks are
the trusted party. The chip connects out to the landmark (TCP), so it works from behind NAT (a Colab VM, a cluster
node); the landmark needs a reachable port.
"""
from __future__ import annotations

import hashlib
import json
import math
import secrets
import socket
import time
from dataclasses import asdict, dataclass, field

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat, PublicFormat

C_KM_PER_S = 299_792.458
EARTH_R_KM = 6371.0088
DOMAIN = b"closure-geo-v1"


def great_circle_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance on a sphere of the Earth's mean radius."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2.0 * EARTH_R_KM * math.asin(min(1.0, math.sqrt(a)))


def max_distance_km(rtt_s: float, processing_s: float = 0.0) -> float:
    """Farthest the chip can be from the landmark: c x (RTT - processing) / 2. processing_s must be a lower bound on
    the chip's own time to answer (0 is always safe)."""
    return C_KM_PER_S * max(0.0, float(rtt_s) - float(processing_s)) / 2.0


def message(landmark_id: bytes, nonce: bytes) -> bytes:
    return DOMAIN + landmark_id + nonce


def landmark_id(name: str) -> bytes:
    """16 bytes naming the landmark inside every challenge, so an answer to one landmark is no answer to another."""
    return hashlib.sha256(DOMAIN + name.encode()).digest()[:16]


def keygen() -> Ed25519PrivateKey:
    return Ed25519PrivateKey.generate()


def save_key(key: Ed25519PrivateKey, path) -> str:
    with open(path, "wb") as f:
        f.write(key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()))
    return pub_hex(key)


def load_key(path) -> Ed25519PrivateKey:
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    with open(path, "rb") as f:
        return load_pem_private_key(f.read(), password=None)


def pub_hex(key: Ed25519PrivateKey) -> str:
    return key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()


def valid(pub: str, landmark_id: bytes, nonce: bytes, sig: bytes) -> bool:
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub)).verify(sig, message(landmark_id, nonce))
        return True
    except (InvalidSignature, ValueError):
        return False


@dataclass
class Record:
    landmark: str
    lat: float
    lon: float
    chip_pub: str
    rounds: int
    valid_rounds: int
    min_rtt_s: float | None
    max_km: float | None
    processing_s: float = 0.0
    started_utc: str = ""
    samples: list = field(default_factory=list)     # (nonce hex, signature hex, rtt s): signatures re-verifiable

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Record":
        return Record(**d)


def _recv_exact(sock, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("peer closed the connection")
        buf += chunk
    return buf


def landmark_session(conn, name: str, lat: float, lon: float, chip_pub: str, rounds: int = 50,
                     processing_s: float = 0.0) -> Record:
    """Run `rounds` timed challenges over an accepted connection from the chip; keep the fastest valid round."""
    conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    lid = landmark_id(name)
    samples, best = [], None
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for _ in range(int(rounds)):
        nonce = secrets.token_bytes(32)
        t0 = time.perf_counter_ns()
        conn.sendall(lid + nonce)
        sig = _recv_exact(conn, 64)
        rtt = (time.perf_counter_ns() - t0) / 1e9
        ok = valid(chip_pub, lid, nonce, sig)
        samples.append((nonce.hex(), sig.hex(), rtt) if ok else (nonce.hex(), sig.hex(), None))
        if ok and (best is None or rtt < best):
            best = rtt
    conn.sendall(b"\x00" * 48)                         # all-zero challenge: done
    n_ok = sum(s[2] is not None for s in samples)
    return Record(name, float(lat), float(lon), chip_pub, int(rounds), n_ok, best,
                  None if best is None else max_distance_km(best, processing_s), float(processing_s), started, samples)


def serve_landmark(host: str, port: int, name: str, lat: float, lon: float, chip_pub: str, rounds: int = 50,
                   timeout: float = 120.0, ready=None) -> Record:
    """Accept one chip connection and challenge it. `ready`, if given, is called with the bound port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, int(port)))
        s.listen(1)
        s.settimeout(timeout)
        if ready is not None:
            ready(s.getsockname()[1])
        conn, _ = s.accept()
        with conn:
            conn.settimeout(timeout)
            return landmark_session(conn, name, lat, lon, chip_pub, rounds)


def run_chip(host: str, port: int, key: Ed25519PrivateKey, timeout: float = 120.0) -> int:
    """Connect to a landmark and answer its challenges until it says done; returns the number answered."""
    n = 0
    with socket.create_connection((host, int(port)), timeout=timeout) as c:
        c.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        while True:
            req = _recv_exact(c, 48)
            if req == b"\x00" * 48:
                return n
            c.sendall(key.sign(message(req[:16], req[16:])))
            n += 1


def reverify(rec: Record) -> bool:
    """Re-check every signature in a record (the timings are the landmark's word)."""
    lid = landmark_id(rec.landmark)
    for nonce, sig, rtt in rec.samples:
        if rtt is not None and not valid(rec.chip_pub, lid, bytes.fromhex(nonce), bytes.fromhex(sig)):
            return False
    return True


def check(records: list, declared_lat: float, declared_lon: float) -> dict:
    """What a set of landmark records proves about a chip declared at (lat, lon).

    consistent: the declared site lies inside every landmark's disc (a site outside one is a false declaration).
    proven_within_km: the chip is within this distance of the declared site (triangle inequality over landmarks)."""
    per, consistent, proven = [], True, None
    for r in records:
        if r.max_km is None:
            per.append({"landmark": r.landmark, "valid_rounds": 0, "note": "no valid answer: proves nothing"})
            continue
        d = great_circle_km(r.lat, r.lon, declared_lat, declared_lon)
        inside = d <= r.max_km
        consistent &= inside
        radius = d + r.max_km
        proven = radius if proven is None else min(proven, radius)
        per.append({"landmark": r.landmark, "min_rtt_ms": 1e3 * r.min_rtt_s, "max_km": r.max_km,
                    "declared_site_km": d, "declared_site_inside": inside})
    return {"consistent": bool(consistent and proven is not None), "proven_within_km": proven, "landmarks": per}


def excluded(records: list, lat: float, lon: float) -> bool:
    """True if some landmark proves the chip cannot be at (lat, lon)."""
    return any(r.max_km is not None and great_circle_km(r.lat, r.lon, lat, lon) > r.max_km for r in records)


def load_records(paths) -> list:
    return [Record.from_dict(json.loads(open(p, encoding="utf-8").read())) for p in paths]
