#!/usr/bin/env python3
"""Inject one hardware bug at a time and require tools/mutation_suite.py to notice.

A surviving mutant means the simulation suite would not catch that bug.  Usage: python tools/mutate_rtl.py [first last]
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RTL = os.path.join(ROOT, "rtl")
CORE, LOG, CONSTS = (os.path.join(RTL, n) for n in ("sha256_core.v", "tap_logger.v", "sha256_consts.vh"))


def k_mutant():
    text = open(CONSTS).read()
    m = re.search(r"6'd17: sha256_k = 32'h([0-9a-f]{8});", text)
    old = m.group(0)
    return (CONSTS, old, old.replace(m.group(1), "%08x" % (int(m.group(1), 16) ^ 1)), "round constant K[17] differs in one bit")


MUTANTS = [
    (CORE, "{x[12:0], x[31:13]}", "{x[13:0], x[31:14]}", "core: Sigma0 rotates by 14 instead of 13"),
    (CORE, "wire [31:0] w_t9  = wv[223:192];", "wire [31:0] w_t9  = wv[255:224];", "core: schedule taps W[t+8] instead of W[t+9]"),
    (CORE, "bsig0(a) + maj(a, b, c);", "bsig0(a) + maj(a, b, b);", "core: Maj uses b twice"),
    (CORE, "h7 <= h7 + h;", "h7 <= h;", "core: final addition missing for h7"),
    (CORE, "            if (init) begin", "            if (1'b0) begin", "core: init never loads the initial hash value"),
    (CORE, "e  <= d + t1;", "e  <= d + t2;", "core: e update uses T2"),
    (CORE, "ch  = (x & y) ^ (~x & z);", "ch  = (x & y) ^ (x & z);", "core: Ch uses x twice"),
    (CORE, "if (t[6] == 1'b0) begin", "if (t < 7'd63) begin", "core: 63 rounds instead of 64"),
    k_mutant,
    (LOG, "(cnt == 6'd55) ? 2'd2 : 2'd1;", "(cnt == 6'd56) ? 2'd2 : 2'd1;", "logger: padding boundary off by one"),
    (LOG, "bitlen[63 - 8 * len_idx -: 8]", "bitlen[8 * len_idx +: 8]", "logger: length appended little-endian"),
    (LOG, "{chain, index, ts_reg};", "{chain, 64'd0, ts_reg};", "logger: frame index missing from the hashed header"),
    (LOG, "chain      <= core_digest;", "chain      <= chain;", "logger: chain head never advances"),
    (LOG, "after_comp <= s_tlast ? S_PAD : S_DATA;", "after_comp <= S_DATA;", "logger: tlast lost when the last byte fills a block"),
    (LOG, "frame_len <= frame_len + 32'd1;", "frame_len <= frame_len + 32'd2;", "logger: frame length counts double"),
    (LOG, "                    hdr_cnt     <= 6'd0;\n                    first_block <= 1'b1;", "                    hdr_cnt     <= 6'd0;\n                    first_block <= 1'b0;",
     "logger: new frame does not restart from the initial hash value"),
    (LOG, "ts_reg      <= TS_EN ? ts_in : 64'd0;", "ts_reg      <= 64'd0;", "logger: timestamp never sampled"),
    (LOG, "chain       <= GENESIS;", "chain       <= chain;", "logger: reset does not restore the genesis digest"),
    (LOG, "if (log_valid && log_ready)\n                log_valid <= 1'b0;", "if (log_valid)\n                log_valid <= 1'b0;", "logger: record dropped without waiting for ready"),
    (LOG, "if (s_tvalid && !log_valid) begin", "if (s_tvalid) begin", "logger: next frame starts before the record is taken"),
    (LOG, "TS_EN ? 6'd48 : 6'd40", "TS_EN ? 6'd47 : 6'd40", "logger: header one byte short"),
    (LOG, "assign s_tready   = (state == S_DATA);", "assign s_tready   = (state == S_DATA) || (state == S_HDR);", "logger: accepts bytes while injecting the header"),
    (LOG, "index      <= index + 64'd1;", "index      <= index + 64'd2;", "logger: index advances by two"),
    (LOG, "log_len    <= frame_len;", "log_len    <= nbytes;", "logger: logged length includes the header"),
]


def main() -> int:
    lo = int(sys.argv[1]) if len(sys.argv) > 2 else 0
    hi = int(sys.argv[2]) if len(sys.argv) > 2 else len(MUTANTS)
    base = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "mutation_suite.py")], capture_output=True, text=True)
    if base.returncode != 0:
        print("the UNMUTATED design fails the suite; every mutant would be 'killed' vacuously:\n" + base.stdout + base.stderr)
        return 2
    print("unmutated design passes the suite")
    survived, t0 = [], time.time()
    for n, m in enumerate(MUTANTS):
        if not lo <= n < hi:
            continue
        path, old, new, why = m() if callable(m) else m
        orig = open(path).read()
        if orig.count(old) != 1:
            print("BAD MUTANT #%d (pattern found %d times): %s" % (n, orig.count(old), why))
            return 2
        # the real sources are never modified: the mutant lives in a temporary copy of rtl/
        tmp = tempfile.mkdtemp(prefix="mutant-")
        try:
            shutil.copytree(RTL, os.path.join(tmp, "rtl"))
            mpath = os.path.join(tmp, "rtl", os.path.basename(path))
            open(mpath, "w").write(orig.replace(old, new))
            srcs = [os.path.join(tmp, "rtl", "sha256_core.v"), os.path.join(tmp, "rtl", "tap_logger.v")]
            comp = subprocess.run(["iverilog", "-g2005", "-I", os.path.join(tmp, "rtl"), "-o", os.devnull] + srcs,
                                  capture_output=True, text=True)
            if comp.returncode != 0:
                print("BAD MUTANT #%d does not compile: %s" % (n, why))
                return 2
            env = dict(os.environ, TLREF_RTL_DIR=os.path.join(tmp, "rtl"))
            r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "mutation_suite.py")], capture_output=True,
                               text=True, timeout=240, env=env)
            killed = r.returncode != 0
        except subprocess.TimeoutExpired:
            killed = True
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        print("%-9s #%02d %s" % ("killed" if killed else "SURVIVED", n, why), flush=True)
        if not killed:
            survived.append(why)
    print("\n%d mutants run, %d survived (%.0fs)" % (min(hi, len(MUTANTS)) - lo, len(survived), time.time() - t0))
    return 1 if survived else 0


if __name__ == "__main__":
    sys.exit(main())
