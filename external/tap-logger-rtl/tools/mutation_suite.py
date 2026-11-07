#!/usr/bin/env python3
"""Fast simulation suite used by tools/mutate_rtl.py: exits non-zero on the first failure of any kind."""
import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from tlref import sim, vectors  # noqa: E402
from tlref.chain import verify_chain  # noqa: E402


def logger(lengths, vseed, ts_en=1, genesis=bytes(32), **kw):
    frames = vectors.make_frames(vseed, lengths)
    ts = vectors.make_timestamps(vseed, len(frames))
    kw.setdefault("maxcyc", 600_000)
    r = sim.run_logger(frames, ts, ts_en=ts_en, genesis=genesis, **kw)
    assert r.errors == 0 and not r.mismatches, r.mismatches[:2]
    assert verify_chain(frames, r.records[-len(frames):], bool(ts_en), genesis).ok


def main() -> int:
    r = sim.run_core([b"", b"abc", b"a" * 55, b"a" * 56, b"a" * 120, bytes(range(200))])
    assert r.errors == 0, r.mismatches
    logger(list(range(1, 131)), 1)                                                   # every padding boundary, TS on
    logger(list(range(1, 71)), 2, 0, hashlib.sha256(b"g").digest())                  # TS off, custom genesis
    logger([5, 70, 130, 1, 64, 200, 17, 16, 80] * 3, 3, stall=60, ready=20, seed=3)  # back-pressure both ways
    logger([10, 200, 30, 300, 5], 4, reset_at=700)                                   # reset mid-run
    logger([2000], 5)                                                                # one long frame
    logger([5, 1, 64, 17, 30], 6, delay=400, maxcyc=2_000_000)                       # consumer stalls longer than a frame
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:                       # any exception is a detection
        print("DETECTED:", str(e).splitlines()[0][:150] if str(e) else type(e).__name__)
        sys.exit(1)
