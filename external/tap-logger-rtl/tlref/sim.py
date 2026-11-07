"""Compile and run the Verilog testbenches with Icarus Verilog and parse their output."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .chain import GENESIS_ZERO, Record, build_chain
from .vectors import make_frames, make_timestamps, write_core_files, write_logger_files

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RTL_DIR = os.environ.get("TLREF_RTL_DIR") or os.path.join(ROOT, "rtl")   # overridable: mutation runs use a temp copy
RTL_SOURCES = [os.path.join(RTL_DIR, "sha256_core.v"), os.path.join(RTL_DIR, "tap_logger.v")]
TB_LOGGER = os.path.join(ROOT, "tb", "tb_tap_logger.v")
TB_CORE = os.path.join(ROOT, "tb", "tb_sha256_core.v")

_BUILD = tempfile.mkdtemp(prefix="tlsim-")
_compiled: Dict[tuple, str] = {}


@dataclass
class SimResult:
    errors: int
    frames: int
    bytes: int
    cycles: int
    resets: int = 0
    records: List[Record] = field(default_factory=list)
    mismatches: List[str] = field(default_factory=list)
    stdout: str = ""


def _compile(key: tuple, top_sources: Sequence[str], defines: Sequence[str], extra: Sequence[str] = (),
             simulator: str = "iverilog", top: str = "") -> str:
    """Returns the command prefix to run (a .vvp path for iverilog, an executable for verilator)."""
    key = key + (simulator,)
    if key in _compiled:
        return _compiled[key]
    n = len(_compiled)
    if simulator == "iverilog":
        out = os.path.join(_BUILD, "sim%d.vvp" % n)
        cmd = ["iverilog", "-g2005", "-Wall", "-I", RTL_DIR] + ["-D" + d for d in defines] + list(extra) + ["-o", out] + list(top_sources)
    elif simulator == "verilator":
        mdir = os.path.join(_BUILD, "vl%d" % n)
        out = os.path.join(mdir, "simv")
        cmd = (["verilator", "--binary", "--timing", "-Wno-fatal", "-Wno-lint", "-Wno-style", "-Wno-TIMESCALEMOD",
                "-I" + RTL_DIR, "--top-module", top, "-Mdir", mdir, "-o", "simv"] + ["-D" + d for d in defines]
               + list(extra) + list(top_sources))
    else:
        raise ValueError("simulator must be iverilog or verilator")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("%s failed:\n" % simulator + r.stdout[-3000:] + r.stderr[-3000:])
    _compiled[key] = out
    return out


def _runner(exe: str, simulator: str) -> List[str]:
    return ["vvp", "-n", exe] if simulator == "iverilog" else [exe]


def _parse(stdout: str) -> SimResult:
    recs, mism, done = [], [], None
    for ln in stdout.splitlines():
        if ln.startswith("LOG "):
            _, idx, ln_, ts, dg = ln.split()
            recs.append(Record(int(idx), int(ln_), int(ts, 16), bytes.fromhex(dg)))
        elif ln.startswith("MISMATCH") or ln.startswith("TIMEOUT"):
            mism.append(ln)
        elif ln.startswith("DONE "):
            done = dict(kv.split("=") for kv in ln.split()[1:])
    if done is None:
        raise RuntimeError("testbench did not finish:\n" + stdout[-2000:])
    return SimResult(int(done["errors"]), int(done["frames"]), int(done["bytes"]), int(done["cycles"]),
                     int(done.get("resets", 0)), recs, mism, stdout)


def run_logger(frames: Sequence[bytes], timestamps: Optional[Sequence[int]] = None, ts_en: int = 1,
                genesis: bytes = GENESIS_ZERO, stall: int = 0, ready: int = 100, seed: int = 1, reset_at: int = 0,
                netlist: Optional[str] = None, expected: Optional[Sequence[Record]] = None,
                simulator: str = "iverilog", maxcyc: int = 40_000_000, delay: int = 0) -> SimResult:
    """Drive ``frames`` through the logger; the testbench checks every record against ``expected`` (default: the
    hashlib reference chain) and also prints each record so it can be re-verified independently in Python."""
    timestamps = list(timestamps) if timestamps is not None else make_timestamps(1, len(frames))
    records = list(expected) if expected is not None else build_chain(frames, timestamps if ts_en else None, genesis)
    work = tempfile.mkdtemp(prefix="tlrun-", dir=_BUILD)
    paths = write_logger_files(work, frames, timestamps, records)
    key = ("logger", ts_en, genesis, netlist)
    srcs = [TB_LOGGER] + ([netlist] if netlist else RTL_SOURCES)
    defs = ["TS_EN=%d" % ts_en, "GENESIS=256'h%s" % genesis.hex()] + (["GATE=1"] if netlist else [])
    vvp = _compile(key, srcs, defs, simulator=simulator, top="tb_tap_logger")
    args = _runner(vvp, simulator) + ["+FRAMES=" + paths["frames"], "+META=" + paths["meta"], "+EXPECTED=" + paths["expected"],
            "+N=%d" % len(frames), "+STALL=%d" % stall, "+READY=%d" % ready, "+SEED=%d" % seed, "+RESET_AT=%d" % reset_at, "+MAXCYC=%d" % maxcyc, "+DELAY=%d" % delay]
    r = subprocess.run(args, capture_output=True, text=True, timeout=900)
    shutil.rmtree(work, ignore_errors=True)
    return _parse(r.stdout + r.stderr)


def run_core(messages: Sequence[bytes], netlist: Optional[str] = None, simulator: str = "iverilog") -> SimResult:
    work = tempfile.mkdtemp(prefix="tlcore-", dir=_BUILD)
    paths, _ = write_core_files(work, messages)
    srcs = [TB_CORE] + ([netlist] if netlist else [RTL_SOURCES[0]])
    vvp = _compile(("core", netlist), srcs, [], simulator=simulator, top="tb_sha256_core")
    r = subprocess.run(_runner(vvp, simulator) + ["+BLOCKS=" + paths["blocks"], "+MSGS=" + paths["msgs"], "+N=%d" % len(messages)],
                       capture_output=True, text=True, timeout=900)
    shutil.rmtree(work, ignore_errors=True)
    out = r.stdout + r.stderr
    mism = [l for l in out.splitlines() if l.startswith(("MISMATCH", "TIMEOUT"))]
    done = next((l for l in out.splitlines() if l.startswith("DONE ")), None)
    if done is None:
        raise RuntimeError("core testbench did not finish:\n" + out[-2000:])
    kv = dict(x.split("=") for x in done.split()[1:])
    return SimResult(int(kv["errors"]), int(kv["messages"]), int(kv["blocks"]), int(kv["cycles"]), 0, [], mism, out)
