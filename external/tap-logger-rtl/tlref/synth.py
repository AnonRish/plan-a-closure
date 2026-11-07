"""Yosys synthesis of the RTL to a generic gate-level netlist, and the resource report."""
from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from typing import Dict, Optional

from .sim import RTL_DIR, RTL_SOURCES, _BUILD


@dataclass
class SynthResult:
    netlist: str
    cells: Dict[str, int]
    total_cells: int
    flip_flops: int
    log: str


def synthesize(top: str = "tap_logger", ts_en: int = 1, genesis: bytes = bytes(32), out: Optional[str] = None) -> SynthResult:
    out = out or os.path.join(_BUILD, "%s_ts%d_%s_gates.v" % (top, ts_en, genesis.hex()[:8]))
    srcs = " ".join(RTL_SOURCES)
    chparam = ""
    if top == "tap_logger":
        chparam = "chparam -set TS_EN %d -set GENESIS 256'h%s tap_logger; " % (ts_en, genesis.hex())
    script = ("read_verilog -I %s %s; %s hierarchy -check -top %s; proc; opt; check -assert; "
              "synth -top %s -flatten; opt_clean -purge; check -assert; tee -o /dev/stdout stat; "
              "write_verilog -noattr %s") % (RTL_DIR, srcs, chparam, top, top, out)
    r = subprocess.run(["yosys", "-q", "-p", script], capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        raise RuntimeError("yosys failed:\n" + r.stdout[-3000:] + r.stderr[-3000:])
    cells: Dict[str, int] = {}
    in_cells = False
    for ln in r.stdout.splitlines():
        m = re.match(r"\s+(\$_\w+_|\$\w+)\s+(\d+)\s*$", ln)
        if m:
            cells[m.group(1)] = int(m.group(2))
    total = sum(cells.values())
    ffs = sum(v for k, v in cells.items() if "DFF" in k)
    return SynthResult(out, cells, total, ffs, r.stdout)
