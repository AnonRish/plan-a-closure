"""Differential test: interval assembler vs brute-force per-byte oracle."""
import random

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from packet_forge.assembler import StreamAssembler, merge_ranges
from packet_forge.model import POLICIES, Claim
from packet_forge.oracle import oracle


def run_both(claims, policy_name, stream_start=0):
    pol = POLICIES[policy_name]
    asm = StreamAssembler(pol, stream_start)
    for c in claims:
        asm.add(c)
    ref = oracle(claims, pol, stream_start)
    return asm, ref


def check(claims, policy_name, stream_start=0):
    asm, ref = run_both(claims, policy_name, stream_start)
    assert asm.runs() == ref.runs, (policy_name, claims)
    assert merge_ranges([(e.start, e.end) for e in asm.conflicts]) == ref.conflict_ranges
    assert asm.delivered == ref.delivered


claim_spec = st.tuples(st.integers(0, 40), st.integers(1, 16), st.integers(0, 2))


def build(specs):
    return [Claim(arrival=i, start=s, data=bytes(65 + (v + k) % 3 for k in range(ln)), frame=i + 1)
            for i, (s, ln, v) in enumerate(specs)]


@pytest.mark.parametrize("policy", sorted(POLICIES))
@settings(max_examples=400, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(st.lists(claim_spec, min_size=1, max_size=9))
def test_random_claim_sets(policy, specs):
    check(build(specs), policy)


@pytest.mark.parametrize("policy", sorted(POLICIES))
def test_dense_overlap_fuzz(policy):
    rng = random.Random(1234)
    for _ in range(3000):
        n = rng.randint(2, 12)
        claims = []
        for i in range(n):
            s = rng.randint(0, 25)
            ln = rng.randint(1, 12)
            # two-letter alphabet makes agreeing and conflicting overlaps about equally likely
            claims.append(Claim(i, s, bytes(rng.choice(b"AB") for _ in range(ln)), i + 1))
        check(claims, policy)


def test_stream_start_offset():
    claims = [Claim(0, 100, b"abcdef", 1), Claim(1, 103, b"XYZUVW", 2), Claim(2, 98, b"__cd", 3)]
    # stream_start=100: claim 2 must be trimmed by the caller, so feed only valid claims
    check(claims[:2], "linux", stream_start=100)


def test_all_policies_agree_when_no_conflict():
    data = bytes(range(60))
    rng = random.Random(7)
    for _ in range(300):
        claims = []
        for i in range(rng.randint(2, 10)):
            s = rng.randint(0, 40)
            ln = rng.randint(1, 20)
            claims.append(Claim(i, s, data[s:s + ln], i + 1))
        outs = set()
        for name in POLICIES:
            asm, _ = run_both(claims, name)
            assert asm.conflicts == []
            outs.add(tuple(asm.runs()))
        assert len(outs) == 1
