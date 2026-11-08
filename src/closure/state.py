"""State closure: bandwidth-bounded memory-residency challenge (proof of secure erasure style).

The verifier streams pseudorandom blocks (AES-CTR under a key the prover never sees), then challenges
random blocks with a fresh digest key. Hidden state kept *inside* the filled region is overwritten;
state parked in a slower tier shows up as time. Verifier needs no storage: it regenerates blocks."""
from __future__ import annotations

import hashlib
import math
import os
import secrets
import time
from dataclasses import dataclass

import numpy as np
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from .conformal import t_upper, upper_conformal_quantile

KW = 4096  # digest-key words


def _keystream(key32: bytes, iv16: bytes, n: int) -> bytes:
    return Cipher(algorithms.AES(key32), modes.CTR(iv16)).encryptor().update(bytes(n))


def digest(buf, K: np.ndarray) -> int:
    """sum_i (w_i XOR K[i mod KW]) over uint32 words (uint64 accumulate)."""
    w = np.frombuffer(buf, dtype=np.uint32) if isinstance(buf, (bytes, bytearray)) else np.asarray(buf).view(np.uint32)
    n = (len(w) // len(K)) * len(K)
    return int(np.bitwise_xor(w[:n].reshape(-1, len(K)), K).sum(dtype=np.uint64))


def digest_int32_path(buf, K: np.ndarray) -> int:
    """The exact arithmetic a GPU/torch implementation performs (int32 XOR, int64 mask-sum); used to
    prove the device code path equals the reference without needing a device."""
    w = np.frombuffer(buf, dtype=np.int32)
    n = (len(w) // len(K)) * len(K)
    x = np.bitwise_xor(w[:n].reshape(-1, len(K)), K.view(np.int32)).astype(np.int64) & 0xFFFFFFFF
    return int(x.sum())


class Verifier:
    def __init__(self, n_blocks: int = 64, block_bytes: int = 1 << 20, key: bytes = None):
        assert block_bytes % (4 * KW) == 0
        self.n_blocks, self.block_bytes, self.key = n_blocks, block_bytes, key or os.urandom(32)

    def block(self, i: int) -> bytes:
        return _keystream(self.key, (i << 64).to_bytes(16, "big"), self.block_bytes)

    @staticmethod
    def digest_key(dkey: bytes) -> np.ndarray:
        return np.frombuffer(_keystream(hashlib.sha256(dkey).digest(), bytes(16), 4 * KW), dtype=np.uint32)

    def new_challenge(self, k: int):
        return sorted(secrets.SystemRandom().sample(range(self.n_blocks), k)), os.urandom(16)

    def expected(self, idx, dkey: bytes) -> int:
        K = self.digest_key(dkey)
        return sum(digest(self.block(i), K) for i in idx) % (1 << 64)


@dataclass
class TierModel:
    bw_fast: float = 4.0e12
    bw_slow: float = 5.0e10
    lat_s: float = 20e-6
    jitter_s: float = 15e-6

    def time(self, n_fast, n_slow, block_bytes, rng) -> float:
        t = self.lat_s + n_fast * block_bytes / self.bw_fast + n_slow * block_bytes / self.bw_slow
        return max(0.0, t + rng.normal(0.0, self.jitter_s))


class Prover:
    """Honest prover with a simulated two-tier memory; subclasses are the adversaries."""

    def __init__(self, tier: TierModel = None, block_bytes: int = 1 << 20, seed: int = 0):
        self.tier, self.bb, self.rng = tier or TierModel(), block_bytes, np.random.default_rng(seed)
        self.store, self.slow = {}, set()

    def receive(self, i: int, data: bytes):
        self.store[i] = data

    def answer(self, idx, K: np.ndarray):
        total = sum(digest(self.store.get(i, bytes(self.bb)), K) for i in idx) % (1 << 64)
        n_slow = sum(1 for i in idx if i in self.slow)
        return total, self.tier.time(len(idx) - n_slow, n_slow, self.bb, self.rng)

    def parked(self) -> set:
        """Blocks kept in the slow tier (known to the test harness, never to the verifier)."""
        return set(self.slow)


class DropProver(Prover):
    """Keeps hidden state by *not storing* a fraction f of the stream (zeros instead)."""

    def __init__(self, f: float, **kw):
        super().__init__(**kw)
        self.f = f

    def receive(self, i, data):
        self.store[i] = bytes(len(data)) if self.rng.random() < self.f else data


class SlowTierProver(Prover):
    """Parks a fraction f of the stream in a slower tier (e.g. host DRAM) to free fast memory."""

    def __init__(self, f: float, **kw):
        super().__init__(**kw)
        self.f = f

    def receive(self, i, data):
        super().receive(i, data)
        if self.rng.random() < self.f:
            self.slow.add(i)


def fill(verifier: Verifier, prover) -> None:
    for i in range(verifier.n_blocks):
        prover.receive(i, verifier.block(i))


def calibrate_time_threshold(honest_times, alpha: float) -> float:
    t = np.asarray(honest_times, float)
    c = upper_conformal_quantile(t, alpha)
    if np.isfinite(c):
        return float(c)
    n = len(t)
    return float(t.mean() + t_upper(alpha, n - 1) * t.std(ddof=1) * np.sqrt(1 + 1 / n))


def run_challenge(verifier: Verifier, prover, k: int, t_thr: float) -> dict:
    idx, dkey = verifier.new_challenge(k)
    d, t = prover.answer(idx, verifier.digest_key(dkey))
    ok_d = d == verifier.expected(idx, dkey)
    return {"digest_ok": ok_d, "time_ok": t <= t_thr, "elapsed_s": t, "passed": ok_d and t <= t_thr, "idx": list(idx)}


def challenge_size(n_blocks: int, park_frac: float, assurance: float = 0.999) -> int:
    """Blocks per challenge so that a uniform sample of them touches at least one parked block with probability
    >= assurance, when ceil(park_frac x n_blocks) of the n_blocks are parked (hypergeometric; ledger.audit_sample_size).
    With 8 of 32 parked, 8 blocks per challenge touch one at most 93.0% of the time and 17 do 99.94% of the time."""
    from .ledger import audit_sample_size
    parked = max(1, math.ceil(float(park_frac) * int(n_blocks) - 1e-9))
    return int(audit_sample_size(int(n_blocks), parked, float(assurance)))


def sampling_limit(n_blocks: int, n_parked: int, k: int) -> float:
    """The most a challenge of k uniform blocks can detect: P(it touches at least one of n_parked parked blocks)."""
    if n_parked <= 0:
        return 0.0
    return 1.0 - math.comb(int(n_blocks) - int(n_parked), int(k)) / math.comb(int(n_blocks), int(k))


def p_detect_digest(f_dropped: float, k: int) -> float:
    return 1.0 - (1.0 - f_dropped) ** k


class TorchProver:
    """Real prover for GPU HBM (or CPU) residency. HARDWARE-GATED: untested without a device.

    park_frac > 0 models the adversary that frees device memory by parking that fraction of the stream in
    host DRAM and swapping it back in on demand (the elapsed time then includes the PCIe transfer)."""

    def __init__(self, device: str = "cuda:0", block_bytes: int = 1 << 26, park_frac: float = 0.0, seed: int = 0):
        import torch
        self.torch, self.device, self.bb, self.blocks = torch, device, block_bytes, {}
        self.park_frac, self.rng = park_frac, np.random.default_rng(seed)

    def receive(self, i: int, data: bytes):
        t = self.torch.frombuffer(bytearray(data), dtype=self.torch.uint8)
        self.blocks[i] = t if self.rng.random() < self.park_frac else t.to(self.device)

    def parked(self) -> set:
        """Blocks left in host memory (known to the test harness, never to the verifier)."""
        dev = str(self.torch.device(self.device))
        return {i for i, b in self.blocks.items() if str(b.device) != dev}

    def answer(self, idx, K: np.ndarray):
        torch = self.torch
        Kt = torch.from_numpy(K.view(np.int32).copy()).to(self.device)
        if str(self.device).startswith("cuda"):
            torch.cuda.synchronize(self.device)
        t0, total = time.perf_counter(), 0
        for i in idx:
            b = self.blocks[i]
            if str(b.device) != str(torch.device(self.device)):
                b = b.to(self.device)                    # swap-in of a parked block
            w = b.view(torch.int32).reshape(-1, Kt.numel())
            s = (torch.bitwise_xor(w, Kt).to(torch.int64) & 0xFFFFFFFF).sum()
            total += int(s.item())                       # .item() synchronises: elapsed includes device work
        return total % (1 << 64), time.perf_counter() - t0
