"""Reference and deliberately flawed taps, and a scorer for any tap's output.

A *tap* here is anything that turns a capture of one case into (reassembled client->server stream, did it
flag the case as ambiguous).  The flawed taps exist to show that the corpus discriminates: each one is
a plausible shortcut and each fails at least one case.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Dict, Optional

from .analyze import analyze_pcap, parse_capture


@dataclass
class TapVerdict:
    stream: bytes
    flagged: bool


def _client_dir(report, client: str):
    for d in report.directions:
        if d.flow.startswith(client + ">"):
            return d
    return None


def _via_analysis(policy: str, checksum: str, flag: bool) -> Callable[[str, str], TapVerdict]:
    def tap(pcap: str, client: str) -> TapVerdict:
        rep = analyze_pcap(pcap, policies=(policy,), checksum=checksum, include_hex=True)
        d = _client_dir(rep, client)
        stream = bytes.fromhex(d.streams[policy].hex) if d else b""
        return TapVerdict(stream, rep.failing() if flag else False)
    return tap


def naive_append(pcap: str, client: str) -> TapVerdict:
    """Concatenate client payloads in capture order; ignores sequence numbers and checksums."""
    segs, _, _ = parse_capture(pcap)
    cip, cport = client.rsplit(":", 1)
    return TapVerdict(b"".join(s.payload for s in segs if s.src == cip and s.sport == int(cport)), False)


TAPS: Dict[str, Callable[[str, str], TapVerdict]] = {
    "reference": _via_analysis("first", "verify", True),
    "checksum-blind": _via_analysis("first", "accept", True),
    "first-silent": _via_analysis("first", "accept", False),
    "last-silent": _via_analysis("last", "accept", False),
    "linux-silent": _via_analysis("linux", "verify", False),
    "naive-append": naive_append,
}


def run_tap(tap: Callable[[str, str], TapVerdict], manifest: dict, corpus_dir: str) -> Dict[str, TapVerdict]:
    return {e["id"]: tap(os.path.join(corpus_dir, e["pcap"]), e["client"]) for e in manifest["cases"]}


def score(verdicts: Dict[str, TapVerdict], manifest: dict, kernel: Optional[dict] = None) -> dict:
    """Detection: flagged exactly when the case is ambiguous.  Stream: on unambiguous cases the stream must
    be the unique correct one.  Fidelity (when kernel observations are given): stream == bytes the Linux
    application read."""
    rows = {}
    for e in manifest["cases"]:
        cid, exp = e["id"], e["expected"]
        v = verdicts.get(cid)
        if v is None:
            rows[cid] = {"pass": False, "missing": True}
            continue
        amb = exp["ambiguous"]
        detection = v.flagged == amb
        stream_ok = None if amb else v.stream.hex() == exp["streams"]["first"]["hex"]
        fidelity = None
        if kernel and cid in kernel:
            fidelity = v.stream.hex() == kernel[cid]["observed_hex"]
        rows[cid] = {"pass": detection and (stream_ok is not False), "detection": detection,
                     "stream_ok": stream_ok, "fidelity": fidelity, "ambiguous": amb}
    passed = sum(r["pass"] for r in rows.values())
    fid = [r["fidelity"] for r in rows.values() if r.get("fidelity") is not None]
    return {"cases": rows, "passed": passed, "total": len(rows),
            "fidelity_matches": sum(fid), "fidelity_total": len(fid)}
