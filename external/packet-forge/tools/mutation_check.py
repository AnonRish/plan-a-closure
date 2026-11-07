#!/usr/bin/env python3
"""Mutation check: inject one deliberate bug at a time into the library and require the fast test subset to fail.

A surviving mutant means the tests would not notice that bug.  The real sources are never modified: each mutant
lives in a temporary copy of src/, tests/ and corpus/ and is imported through PYTHONPATH.  The unmutated copy must
pass first, otherwise every mutant would be "killed" vacuously.  Usage: python tools/mutation_check.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src", "packet_forge")
FAST = ["tests/test_assembler_vs_oracle.py", "tests/test_frames_and_parser.py", "tests/test_corpus.py",
        "tests/test_taps_normalize_cli.py"]

MUTANTS = [
    ("assembler.py", "frozen_below = self.delivered", "frozen_below = 0", "disable the delivered-bytes freeze"),
    ("assembler.py", "winner = claim if self.policy.key(claim) < self.policy.key(p.claim) else p.claim",
     "winner = claim if self.policy.key(claim) > self.policy.key(p.claim) else p.claim", "invert the ranking"),
    ("assembler.py", "            if nb[i] != ob[i]:", "            if nb[i] == ob[i]:", "invert byte comparison"),
    ("assembler.py", "ov_a, ov_b = max(p.start, a), min(p.end, b)", "ov_a, ov_b = max(p.start, a), max(p.end, b)",
     "overlap end uses max"),
    ("assembler.py", "                self.delivered = self._pieces[k].end", "                self.delivered = self._pieces[k].end + 1",
     "delivered watermark off by one"),
    ("assembler.py", "if out and out[-1].end == p.start and out[-1].claim is p.claim:",
     "if out and out[-1].end == p.start:", "merge pieces owned by different claims"),
    ("seqspace.py", "delta = ((rel - ref + HALF) & 0xFFFFFFFF) - HALF", "delta = ((rel - ref) & 0xFFFFFFFF) - HALF",
     "sequence unwrap loses the half-window shift"),
    ("parse.py", "    payload = captured[doff:]\n", "    payload = data[tcp_off + doff:]\n",
     "payload taken from frame length (Ethernet padding leaks in)"),
    ("parse.py", "tcp_ok = ones_sum(pseudo_header(s, d, tcp_len_decl) + captured) == 0xFFFF",
     "tcp_ok = ones_sum(captured) == 0xFFFF", "TCP checksum without pseudo-header"),
    ("analyze.py", "d.base32 = seqspace.add(syns[0].seq, 1)", "d.base32 = syns[0].seq", "SYN consumes no sequence number"),
    ("analyze.py", "            if a > r.acked:\n                r.acked = a", "            if a > r.acked and False:\n                r.acked = a",
     "ACK tracking disabled"),
    ("analyze.py", "fin_offset = offs[0]        # earliest FIN", "fin_offset = offs[-1]        # earliest FIN", "latest FIN instead of earliest"),
    ("analyze.py", "if checksum == \"verify\" and (s.ip_csum_ok is False or s.tcp_csum_ok is False):",
     "if checksum == \"verify\" and (s.ip_csum_ok is False):", "TCP checksum failures accepted"),
    ("analyze.py", 'conflict_asm = StreamAssembler(POLICIES["first"], 0)', "conflict_asm = StreamAssembler(POLICIES[policies[0]], 0)",
     "conflicts taken from whichever policy is listed first"),
    ("model.py", "lambda c: (c.start, -c.end, c.arrival), True,", "lambda c: (c.start, c.end, c.arrival), True,",
     "linux policy prefers the shorter claim on equal starts"),
    ("oracle.py", "elif policy.freeze and x < frozen_below:", "elif policy.freeze and x < frozen_below - 1:",
     "oracle freeze boundary off by one (lower)"),
    ("normalize.py", "                    _refresh_tcp_checksum(buf, seg)\n", "                    pass\n",
     "normaliser leaves stale checksums"),
]


# Mutants that cannot be killed because they do not change behaviour.  Kept (and expected to survive) so the
# claim is checked, not just asserted.
EQUIVALENT = [
    ("oracle.py", "elif policy.freeze and x < frozen_below:", "elif policy.freeze and x <= frozen_below:",
     "freeze guard `<` vs `<=`: only evaluated when an incumbent exists, and the byte at the delivered watermark "
     "never has one by definition"),
]


def make_tree(fname=None, old=None, new=None) -> str:
    tmp = tempfile.mkdtemp(prefix="pf-mutant-")
    for d in ("src", "tests", "corpus"):
        shutil.copytree(os.path.join(ROOT, d), os.path.join(tmp, d), ignore=shutil.ignore_patterns("__pycache__", "*.egg-info"))
    shutil.copy(os.path.join(ROOT, "pyproject.toml"), tmp)
    if fname:
        path = os.path.join(tmp, "src", "packet_forge", fname)
        text = open(path).read()
        if text.count(old) != 1:
            raise SystemExit("BAD MUTANT (pattern found %d times): %s" % (text.count(old), fname))
        open(path, "w").write(text.replace(old, new))
    return tmp


def passes(tree: str) -> bool:
    env = dict(os.environ, PYTHONPATH=os.path.join(tree, "src"))
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider"] + FAST, cwd=tree,
                       capture_output=True, text=True, env=env)
    return r.returncode == 0


def main() -> int:
    base = make_tree()
    try:
        if not passes(base):
            print("the UNMUTATED copy fails the fast tests; every mutant would be 'killed' vacuously")
            return 2
    finally:
        shutil.rmtree(base, ignore_errors=True)
    print("unmutated copy passes")
    survived = []
    t0 = time.time()
    for fname, old, new, why in MUTANTS:
        tree = make_tree(fname, old, new)
        try:
            killed = not passes(tree)
        finally:
            shutil.rmtree(tree, ignore_errors=True)
        print("%-9s %-14s %s" % ("killed" if killed else "SURVIVED", fname, why), flush=True)
        if not killed:
            survived.append((fname, why))
    for fname, old, new, why in EQUIVALENT:
        tree = make_tree(fname, old, new)
        try:
            same = passes(tree)
        finally:
            shutil.rmtree(tree, ignore_errors=True)
        print("%-9s %-14s %s" % ("equivalent" if same else "NOT-EQUIV", fname, why), flush=True)
        if not same:
            survived.append((fname, "claimed-equivalent mutant was killed: " + why))
    print("\n%d mutants, %d killed, %d survived (%.0fs); %d claimed-equivalent checked" % (
        len(MUTANTS), len(MUTANTS) - len([x for x in survived if "claimed" not in x[1]]),
        len([x for x in survived if "claimed" not in x[1]]), time.time() - t0, len(EQUIVALENT)))
    return 1 if survived else 0


if __name__ == "__main__":
    sys.exit(main())
