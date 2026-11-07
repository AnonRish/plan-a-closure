"""tap-log-verify: build, verify and simulate hash-chain logs of a capture.

Every pcap record is one frame; its timestamp (nanoseconds since the epoch) is the 64-bit timestamp field.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from .chain import GENESIS_ZERO, Record, build_chain, verify_chain
from .pcap import read_pcap


def _load(path: str):
    recs = read_pcap(path)
    return [d for _, d in recs], [t for t, _ in recs]


def _genesis(a) -> bytes:
    g = bytes.fromhex(a.genesis) if a.genesis else GENESIS_ZERO
    if len(g) != 32:
        raise SystemExit("genesis must be 32 bytes (64 hex digits)")
    return g


def cmd_make(a) -> int:
    frames, ts = _load(a.pcap)
    for r in build_chain(frames, None if a.no_ts else ts, _genesis(a)):
        print(json.dumps({"index": r.index, "length": r.length, "ts": r.ts, "digest": r.digest.hex()}))
    return 0


def cmd_verify(a) -> int:
    frames, _ = _load(a.pcap)
    recs: List[Record] = []
    with open(a.log) as f:
        for ln in f:
            if ln.strip():
                j = json.loads(ln)
                recs.append(Record(j["index"], j["length"], j["ts"], bytes.fromhex(j["digest"])))
    v = verify_chain(frames, recs, not a.no_ts, _genesis(a), expected_head=bytes.fromhex(a.head) if a.head else None)
    if v.ok:
        print("OK: %d records verified, head %s" % (len(recs), recs[-1].digest.hex() if recs else "-"))
        return 0
    print("TAMPERED at record %s: %s" % (v.first_bad, v.reason))
    return 1


def cmd_sim(a) -> int:
    from . import sim
    frames, ts = _load(a.pcap)
    if not frames:
        print("capture is empty", file=sys.stderr)
        return 2
    r = sim.run_logger(frames, ts, ts_en=0 if a.no_ts else 1, genesis=_genesis(a), stall=a.stall, ready=a.ready,
                       simulator=a.simulator)
    v = verify_chain(frames, r.records, not a.no_ts, _genesis(a))
    print("RTL (%s): %d frames, %d bytes, %d cycles; testbench errors=%d; independent re-verification: %s" % (
        a.simulator, r.frames, r.bytes, r.cycles, r.errors, "OK" if v.ok else "FAILED (%s)" % v.reason))
    return 0 if (r.errors == 0 and v.ok) else 1


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="tap-log-verify", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn, helptext in (("make-log", cmd_make, "write the reference log (JSON lines) for a capture"),
                               ("verify", cmd_verify, "check a log against the frames in a capture"),
                               ("sim", cmd_sim, "run the capture through the RTL simulation and verify its records")):
        c = sub.add_parser(name, help=helptext)
        c.add_argument("pcap")
        if name == "verify":
            c.add_argument("log")
            c.add_argument("--head", help="published chain head (hex); detects tail truncation")
        c.add_argument("--no-ts", action="store_true", help="timestamps are not part of the hash")
        c.add_argument("--genesis", help="32-byte genesis digest, hex (default all zero)")
        if name == "sim":
            c.add_argument("--stall", type=int, default=0)
            c.add_argument("--ready", type=int, default=100)
            c.add_argument("--simulator", choices=["iverilog", "verilator"], default="iverilog")
        c.set_defaults(fn=fn)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
