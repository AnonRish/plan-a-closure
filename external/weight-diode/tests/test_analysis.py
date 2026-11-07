import math

import numpy as np
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from scipy import stats

from weight_diode import Encoder, Receiver, analysis as A
from weight_diode.rs import CauchyRS

KEY = Ed25519PrivateKey.generate()


@pytest.mark.parametrize("k,r", [(1, 1), (10, 6), (32, 8), (200, 55), (100, 156)])
@pytest.mark.parametrize("loss", [0.0, 0.05, 0.2, 0.5])
@pytest.mark.parametrize("passes", [1, 3])
def test_block_success_probability_matches_the_exact_binomial_tail(k, r, loss, passes):
    q = 1 - loss ** passes
    expect = stats.binom.sf(k - 1, k + r, q)
    assert A.block_success_probability(k, r, loss, passes) == pytest.approx(expect, rel=1e-9, abs=1e-12)


def test_limits():
    assert A.block_success_probability(10, 6, 0.0) == 1.0
    assert A.block_success_probability(10, 6, 1.0) == 0.0
    assert A.file_success_probability(5, 10, 6, 0.0) == 1.0
    with pytest.raises(ValueError):
        A.block_success_probability(0, 3, 0.1)
    with pytest.raises(ValueError):
        A.block_success_probability(10, 6, 1.5)


def test_block_decodes_exactly_when_at_least_k_symbols_arrive_and_frequency_matches_theory():
    k, r, loss = 10, 6, 0.3
    rs, n = CauchyRS(k, r), k + r
    rng = np.random.default_rng(0)
    data = rng.integers(0, 256, (k, 8), dtype=np.uint8)
    coded = np.vstack([data, rs.encode(data)])
    # the real decoder decodes iff at least k symbols survive, on 3,000 random loss patterns
    for _ in range(3000):
        keep = np.nonzero(rng.random(n) >= loss)[0]
        if len(keep) >= k:
            assert np.array_equal(rs.decode({int(i): coded[i] for i in keep}), data)
        else:
            with pytest.raises(ValueError):
                rs.decode({int(i): coded[i] for i in keep})
    # frequency of "at least k arrive" against the formula, 5 sigma
    trials = 200_000
    ok = ((rng.random((trials, n)) >= loss).sum(axis=1) >= k).mean()
    p = A.block_success_probability(k, r, loss)
    assert abs(ok - p) < 5 * math.sqrt(p * (1 - p) / trials)


def test_multi_pass_formula_matches_simulation():
    k, r, loss, passes = 10, 6, 0.6, 3
    rng = np.random.default_rng(1)
    trials, n = 100_000, k + r
    seen = (rng.random((trials, n, passes)) >= loss).any(axis=2)          # a symbol is missing only if every copy is lost
    freq = (seen.sum(axis=1) >= k).mean()
    p = A.block_success_probability(k, r, loss, passes)
    assert abs(freq - p) < 5 * math.sqrt(p * (1 - p) / trials)


def test_whole_file_success_rate_of_real_transfers_matches_the_formula():
    """Actual Encoder -> loss -> Receiver, manifest delivered reliably so only the erasure code is on trial."""
    data = np.random.default_rng(2).integers(0, 256, 3800, dtype=np.uint8).tobytes()
    enc = Encoder(data, KEY, symbol_size=64, k=10, r=6)               # 6 blocks
    assert enc.n_blocks == 6
    loss, trials = 0.3, 500
    rng = np.random.default_rng(3)
    syms = list(enc.one_pass())
    done = 0
    for _ in range(trials):
        rx = Receiver([KEY.public_key()])
        rx.feed(enc.manifest_packet)
        for s, keep in zip(syms, rng.random(len(syms)) >= loss):
            if keep:
                rx.feed(s)
        done += rx.result(enc.manifest_id) == data
    p = A.file_success_probability(6, 10, 6, loss)
    assert 0.1 < p < 0.9                                              # a regime where the check can fail in both directions
    assert abs(done / trials - p) < 5 * math.sqrt(p * (1 - p) / trials)


def test_min_redundancy_is_minimal_and_monotone_in_loss():
    k, B, target = 32, 1000, 1e-6
    prev = 0
    for loss in (0.01, 0.05, 0.1, 0.2):
        r = A.min_redundancy(k, B, loss, target)
        assert 1 - A.file_success_probability(B, k, r, loss) <= target
        assert r == 0 or 1 - A.file_success_probability(B, k, r - 1, loss) > target
        assert r >= prev
        prev = r
    assert A.min_redundancy(k, B, 0.3, target, passes=3) < A.min_redundancy(k, B, 0.3, target, passes=1)
    with pytest.raises(ValueError):
        A.min_redundancy(200, 100, 0.9, 1e-9)


@pytest.mark.parametrize("size,S,k,r", [(30_000, 128, 10, 6), (1, 64, 4, 2), (0, 64, 4, 2), (1_000_000, 1024, 32, 8), (12_345, 100, 7, 3)])
def test_wire_overhead_matches_the_bytes_the_encoder_actually_emits(size, S, k, r):
    data = np.random.default_rng(size).integers(0, 256, size, dtype=np.uint8).tobytes()
    enc = Encoder(data, KEY, symbol_size=S, k=k, r=r)
    actual = sum(len(p) for p in enc.one_pass())
    o = A.wire_overhead(size, S, k, r)
    assert actual == o["wire_bytes_per_pass"] == enc.wire_bytes_per_pass()
    assert o["payload_bytes"] + o["proof_bytes"] + o["header_bytes"] == o["wire_bytes_per_pass"]
    assert o["padding_bytes"] == enc.n_blocks * k * S - size
    assert o["symbols"] == enc.n_blocks * enc.n


def test_transfer_time():
    assert A.transfer_seconds(1e9, 10.0) == pytest.approx(0.8)
    assert A.transfer_seconds(1e9, 10.0, passes=3) == pytest.approx(2.4)
    with pytest.raises(ValueError):
        A.transfer_seconds(1, 0)


@pytest.mark.parametrize("mtu,size", [(1500, 40_000), (1500, 4_000), (9000, 3_000_000), (576, 20)])
def test_max_symbol_size_is_exactly_the_largest_that_fits_one_frame(mtu, size):
    data = np.random.default_rng(7).integers(0, 256, size, dtype=np.uint8).tobytes()
    k, r = 4, 2
    S = 100
    for _ in range(20):                                          # the tree size depends on S: iterate to the fixed point
        tree = -(-len(data) // (k * S)) * (k + r)
        S_new = A.max_symbol_size(mtu, tree)
        if S_new == S:
            break
        S = S_new
    else:
        pytest.fail("no fixed point for the symbol size")
    enc = Encoder(data, KEY, symbol_size=S, k=k, r=r)
    tree = enc.n_blocks * enc.n
    sizes = [len(p) for p in enc.one_pass()]
    assert max(sizes) == A.max_datagram_bytes(S, tree)            # the deepest leaf exists, so this is exact
    assert max(sizes) + A.IP_UDP_HEADERS <= mtu                   # it fits one frame
    assert A.max_datagram_bytes(S + 1, tree) + A.IP_UDP_HEADERS > mtu     # one more byte of symbol, same tree, would not


def test_mtu_too_small_is_refused():
    with pytest.raises(ValueError):
        A.max_symbol_size(100, 1 << 28)
