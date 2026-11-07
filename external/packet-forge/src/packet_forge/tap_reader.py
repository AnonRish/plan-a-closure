"""Run the corpus through the `tap_reader` Rust crate (see adapters/tap_reader) and score the result."""
from __future__ import annotations

import os
import shutil
import subprocess
from typing import Dict, Optional

from .taps import TapVerdict

CARGO_CANDIDATES = ("cargo", "cargo-1.91", "/usr/lib/rust-1.91/bin/cargo", os.path.expanduser("~/.cargo/bin/cargo"))


def find_cargo() -> Optional[str]:
    for c in CARGO_CANDIDATES:
        p = shutil.which(c) or (c if os.path.isabs(c) and os.access(c, os.X_OK) else None)
        if p:
            return p
    return None


def build_adapter(adapter_dir: str) -> str:
    cargo = find_cargo()
    if not cargo:
        raise RuntimeError("no Rust toolchain found (need cargo)")
    env = dict(os.environ)
    env["PATH"] = os.path.dirname(os.path.realpath(cargo)) + os.pathsep + env.get("PATH", "")
    subprocess.run([cargo, "build", "--release", "--quiet"], cwd=adapter_dir, check=True, env=env)
    return os.path.join(adapter_dir, "target", "release", "tap_reader_adapter")


def run_adapter(binary: str, manifest: dict, corpus_dir: str, mode: str) -> Dict[str, dict]:
    """``mode`` is ``asis`` (exactly what tap_reader::frame::parse yields) or ``trim`` (payload cut to the IPv4
    total length first, so only ReorderBuffer's behaviour is measured)."""
    lines = "".join("%s %s %d %s\n" % (e["id"], os.path.join(corpus_dir, e["pcap"]), (e["isn"] + 1) & 0xFFFFFFFF, mode)
                    for e in manifest["cases"])
    out = subprocess.run([binary], input=lines, capture_output=True, text=True, check=True).stdout
    res: Dict[str, dict] = {}
    for ln in out.splitlines():
        _tag, cid, _mode, hx, dups, reord, gap, parsed, rej = ln.split()
        res[cid] = {"stream": b"" if hx == "-" else bytes.fromhex(hx), "duplicates_dropped": int(dups),
                    "reordered_count": int(reord), "gap_open": gap == "true", "parsed": int(parsed), "rejected": int(rej)}
    return res


def as_verdicts(res: Dict[str, dict]) -> Dict[str, TapVerdict]:
    # tap_reader has no conflict signal: it can never flag a case
    return {k: TapVerdict(v["stream"], False) for k, v in res.items()}
