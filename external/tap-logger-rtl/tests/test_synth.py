"""Yosys synthesis to generic gates, and the synthesised netlist re-simulated with the same testbench."""
import hashlib

import pytest

from tlref import sim, synth, vectors
from tlref.chain import verify_chain

pytestmark = pytest.mark.slow


def run_gates(netlist, lengths, ts_en, genesis, seed):
    frames = vectors.make_frames(seed, lengths)
    ts = vectors.make_timestamps(seed, len(frames))
    r = sim.run_logger(frames, ts, ts_en=ts_en, genesis=genesis, netlist=netlist, simulator="verilator")
    assert r.errors == 0 and not r.mismatches, r.mismatches[:3]
    assert verify_chain(frames, r.records, bool(ts_en), genesis).ok
    return r


def test_synthesis_is_clean_and_has_the_expected_register_budget():
    s = synth.synthesize()                         # `check -assert` inside: no latches, loops or undriven nets
    assert not [k for k in s.cells if "LATCH" in k]
    # measured: 1,065 flip-flops in the core + about 1,400 in the logger (block buffer, chain, record registers)
    assert 2300 <= s.flip_flops <= 2600, s.flip_flops
    assert s.total_cells > 5000


def test_netlist_matches_the_reference_default_parameters():
    s = synth.synthesize()
    run_gates(s.netlist, [1, 7, 8, 15, 16, 17, 71, 72, 1500], 1, bytes(32), 3)


def test_netlist_matches_the_reference_without_timestamps_and_with_a_genesis():
    g = hashlib.sha256(b"gate level genesis").digest()
    s = synth.synthesize(ts_en=0, genesis=g)
    run_gates(s.netlist, [1, 15, 16, 17, 23, 24, 25, 55, 56, 64, 65, 100], 0, g, 4)


def test_core_netlist_matches_hashlib():
    s = synth.synthesize(top="sha256_core")
    msgs = [b"", b"abc", b"a" * 55, b"a" * 56, b"a" * 119, b"a" * 120, bytes(range(200))]
    r = sim.run_core(msgs, netlist=s.netlist, simulator="verilator")
    assert r.errors == 0, r.mismatches
