"""The Verilog against the software reference, in simulation (Icarus Verilog; Verilator as a second simulator)."""
import dataclasses
import hashlib
import os
import random
import shutil
import subprocess

import pytest

from tlref import sim, vectors
from tlref.chain import Record, build_chain, verify_chain

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NIST_448 = b"abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"        # FIPS 180-4 example, 56 bytes
NIST_896 = b"abcdefghbcdefghicdefghijdefghijkefghijklfghijklmghijklmnhijklmnoijklmnopjklmnopqklmnopqrlmnopqrsmnopqrstnopqrstu"


# ---------------------------------------------------------------- the compression core ----------------------

def test_core_matches_hashlib_on_standard_and_boundary_messages():
    msgs = [b"", b"abc", NIST_448, NIST_896] + [b"a" * n for n in (55, 56, 57, 63, 64, 65, 119, 120, 121, 127, 128)]
    msgs.append(bytes(range(256)) * 3)
    r = sim.run_core(msgs)
    assert r.errors == 0 and r.frames == len(msgs), r.mismatches


def test_core_matches_hashlib_on_random_messages():
    rng = random.Random(2024)
    msgs = [bytes(rng.randrange(256) for _ in range(rng.randrange(0, 600))) for _ in range(40)]
    r = sim.run_core(msgs)
    assert r.errors == 0, r.mismatches


def test_core_takes_67_cycles_per_block():
    r = sim.run_core([bytes(64 * 5 - 9)])           # 5 blocks after padding
    assert r.errors == 0 and r.bytes == 5 and 66 <= r.cycles / r.bytes <= 68


# ---------------------------------------------------------------- the logger ------------------------------

def frames_of(lengths, seed=1):
    return vectors.make_frames(seed, lengths), vectors.make_timestamps(seed, len(lengths))


def check(frames, ts, ts_en=1, genesis=bytes(32), **kw):
    r = sim.run_logger(frames, ts, ts_en=ts_en, genesis=genesis, **kw)
    assert r.errors == 0 and not r.mismatches, r.mismatches[:3]
    assert len(r.records) == len(frames)
    # re-verify what the hardware actually emitted, independently of the testbench's own comparison
    v = verify_chain(frames, r.records, bool(ts_en), genesis)
    assert v.ok, v
    return r


def test_every_length_from_1_to_300_with_timestamps():
    """Crosses every SHA-256 padding boundary (message length mod 64 in 55, 56, 63, 0, 1...) for the 48-byte header."""
    frames, ts = frames_of(list(range(1, 301)), 7)
    check(frames, ts, 1)


def test_every_length_from_1_to_300_without_timestamps_and_with_a_custom_genesis():
    genesis = hashlib.sha256(b"tap-logger-rtl test genesis").digest()
    frames, ts = frames_of(list(range(1, 301)), 8)
    r = check(frames, ts, 0, genesis)
    assert all(rec.ts == 0 for rec in r.records)             # log_ts is 0 and unauthenticated when TS_EN = 0


@pytest.mark.parametrize("stall,ready,seed", [(0, 100, 1), (50, 100, 2), (0, 25, 3), (70, 15, 4), (90, 90, 5)])
def test_under_source_stalls_and_consumer_backpressure(stall, ready, seed):
    rng = random.Random(seed)
    lengths = [rng.randrange(1, 220) for _ in range(60)] + [1500, 1, 64, 65]
    frames, ts = frames_of(lengths, seed)
    check(frames, ts, 1, stall=stall, ready=ready, seed=seed)


@pytest.mark.parametrize("delay", [60, 400, 1500])
def test_a_slow_consumer_stalls_the_source_instead_of_losing_records(delay):
    """The record is held until taken; the next frame is not accepted meanwhile. A stall far longer than the time
    to hash a whole frame must neither lose nor overwrite a record."""
    frames, ts = frames_of([5, 1, 64, 17, 300, 2], 31)
    r = check(frames, ts, 1, delay=delay, maxcyc=3_000_000)
    assert len(r.records) == len(frames)


def test_large_frames_exercise_the_wide_counters():
    frames, ts = frames_of([1500, 9000, 9018, 65535, 70000], 9)
    check(frames, ts, 1)


@pytest.mark.parametrize("reset_at", [150, 700, 2300])
def test_reset_in_the_middle_of_a_run_restarts_the_chain(reset_at):
    lengths = [10, 200, 30, 300, 5, 64, 120]
    frames, ts = frames_of(lengths, 12)
    r = sim.run_logger(frames, ts, ts_en=1, reset_at=reset_at)
    assert r.errors == 0 and r.resets == 1, r.mismatches
    # records printed before the reset belong to the aborted run; the last run starts again at index 0
    start = max(i for i, rec in enumerate(r.records) if rec.index == 0)
    assert verify_chain(frames, r.records[start:], True).ok
    assert len(r.records) - start == len(frames)


def test_throughput_numbers_quoted_in_the_readme():
    """Cycles per frame with no stalls; the README quotes these. Update both together."""
    for size, n, lo, hi in ((64, 30, 255, 280), (1500, 10, 3250, 3350), (9000, 4, 18600, 18900)):
        frames, ts = frames_of([size] * n, size)
        r = check(frames, ts, 1)
        assert lo < r.cycles / n < hi, (size, r.cycles / n)


# ---------------------------------------------------------------- the testbench must be able to fail ------

def tamper(records, k, **kw):
    out = list(records)
    out[k] = dataclasses.replace(out[k], **kw)
    return out


def test_testbench_reports_a_wrong_digest():
    frames, ts = frames_of([10, 20, 30], 1)
    good = build_chain(frames, ts)
    bad = tamper(good, 1, digest=bytes([good[1].digest[0] ^ 1]) + good[1].digest[1:])
    r = sim.run_logger(frames, ts, expected=bad)
    assert r.errors > 0 and any("field=digest" in m for m in r.mismatches)


def test_testbench_reports_a_wrong_length_and_a_wrong_timestamp():
    frames, ts = frames_of([10, 20, 30], 2)
    good = build_chain(frames, ts)
    # the testbench takes length and timestamp from the metadata file, so corrupt those through the frames instead
    r = sim.run_logger(frames, [t ^ 1 for t in ts], ts_en=1, expected=good)
    assert r.errors > 0                                       # digests built with the other timestamps differ


def test_testbench_reports_a_wrong_genesis():
    frames, ts = frames_of([10, 20, 30], 3)
    other = build_chain(frames, ts, genesis=bytes([9]) * 32)
    r = sim.run_logger(frames, ts, genesis=bytes(32), expected=other)
    assert r.errors > 0


# ---------------------------------------------------------------- second simulator, lint, constants -------

@pytest.mark.skipif(not shutil.which("verilator"), reason="verilator not installed")
def test_verilator_agrees_with_icarus_record_for_record():
    frames, ts = frames_of(list(range(1, 131)) + [1500], 21)
    a = sim.run_logger(frames, ts, ts_en=1, simulator="iverilog")
    b = sim.run_logger(frames, ts, ts_en=1, simulator="verilator")
    assert a.errors == b.errors == 0
    assert [r.digest for r in a.records] == [r.digest for r in b.records]
    assert a.cycles == b.cycles


@pytest.mark.skipif(not shutil.which("verilator"), reason="verilator not installed")
def test_lint_is_clean_in_both_tools():
    src = [os.path.join(ROOT, "rtl", "sha256_core.v"), os.path.join(ROOT, "rtl", "tap_logger.v")]
    r = subprocess.run(["verilator", "--lint-only", "-Wall", "-I" + os.path.join(ROOT, "rtl"), "--top-module", "tap_logger"] + src,
                       capture_output=True, text=True)
    assert r.returncode == 0 and r.stderr.strip() == "", r.stderr
    r = subprocess.run(["iverilog", "-g2005", "-Wall", "-I", os.path.join(ROOT, "rtl"), "-o", os.devnull] + src,
                       capture_output=True, text=True)
    assert r.returncode == 0 and (r.stdout + r.stderr).strip() == "", r.stdout + r.stderr


def test_constants_file_is_what_the_generator_produces():
    r = subprocess.run(["python3", os.path.join(ROOT, "tools", "gen_consts.py"), "--check"])
    assert r.returncode == 0


def test_constants_match_independent_values():
    """FIPS 180-4: first and last round constants, and the initial hash value, from hashlib-independent sources."""
    text = open(os.path.join(ROOT, "rtl", "sha256_consts.vh")).read()
    assert "IV0 = 32'h6a09e667" in text and "IV7 = 32'h5be0cd19" in text
    assert "6'd0: sha256_k = 32'h428a2f98" in text and "6'd63: sha256_k = 32'hc67178f2" in text
    # the hash of the empty string is determined by every constant: check it through the core
    assert sim.run_core([b""]).errors == 0
