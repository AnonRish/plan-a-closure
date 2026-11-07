"""Test-vector generation: frames, timestamps, and the $readmemh files the testbenches read."""
from __future__ import annotations

import hashlib
import os
import random
import struct
from typing import List, Sequence, Tuple

from .chain import Record, build_chain


def sha_padded_blocks(msg: bytes) -> List[bytes]:
    """FIPS 180-4 s5.1.1 padding, split into 64-byte blocks (used for the core-level testbench)."""
    padded = msg + b"\x80" + b"\x00" * ((55 - len(msg)) % 64) + struct.pack(">Q", len(msg) * 8)
    assert len(padded) % 64 == 0
    return [padded[i:i + 64] for i in range(0, len(padded), 64)]


def make_frames(seed: int, lengths: Sequence[int]) -> List[bytes]:
    rng = random.Random(seed)
    return [bytes(rng.randrange(256) for _ in range(n)) for n in lengths]


def make_timestamps(seed: int, n: int) -> List[int]:
    rng = random.Random(seed ^ 0x5EED)
    edge = [0, 1, 2**32 - 1, 2**32, 2**63, 2**64 - 1]
    return [edge[i] if i < len(edge) else rng.getrandbits(64) for i in range(n)]


def _hex_lines(data: bytes, per_line: int = 32) -> str:
    return "\n".join(data[i:i + per_line].hex(" ") for i in range(0, len(data), per_line)) + "\n"


def write_logger_files(outdir: str, frames: Sequence[bytes], timestamps: Sequence[int], records: Sequence[Record]) -> dict:
    os.makedirs(outdir, exist_ok=True)
    paths = {k: os.path.join(outdir, k + ".mem") for k in ("frames", "meta", "expected")}
    with open(paths["frames"], "w") as f:
        f.write(_hex_lines(b"".join(frames)))
    with open(paths["meta"], "w") as f:
        f.write("\n".join("%08x%016x" % (len(fr), ts) for fr, ts in zip(frames, timestamps)) + "\n")
    with open(paths["expected"], "w") as f:
        f.write("\n".join(r.digest.hex() for r in records) + "\n")
    return paths


def write_core_files(outdir: str, messages: Sequence[bytes]) -> Tuple[dict, int]:
    """blocks.mem: every padded block of every message (128 hex digits each); msgs.mem: {nblocks:32, digest:256}."""
    os.makedirs(outdir, exist_ok=True)
    blocks: List[bytes] = []
    meta: List[str] = []
    for m in messages:
        bl = sha_padded_blocks(m)
        blocks.extend(bl)
        meta.append("%08x%s" % (len(bl), hashlib.sha256(m).hexdigest()))
    p = {"blocks": os.path.join(outdir, "blocks.mem"), "msgs": os.path.join(outdir, "msgs.mem")}
    with open(p["blocks"], "w") as f:
        f.write("\n".join(b.hex() for b in blocks) + "\n")
    with open(p["msgs"], "w") as f:
        f.write("\n".join(meta) + "\n")
    return p, len(blocks)
